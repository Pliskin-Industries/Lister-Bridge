"""
Module: manual_provider.py
Purpose: Subscription-chat AI route. Render a self-contained extraction packet
         the operator pastes (with the item photos) into any multimodal chat,
         then validate the pasted JSON reply against that packet before the
         unchanged vision parser runs. No API key and no per-call API spend.
Primary Responsibilities:
  - build_packet(): produce a deterministic ManualPacket (packet ID, prompt
    text, photo list, operator checklist) for one item.
  - parse_manual_response(): verify the echoed packet_id, strip it, and return
    the remaining JSON text for vision_agent.extract_item.
  - ManualProvider: an AIProvider that returns a stored reply for a packet or
    raises ManualResponsePending so the caller can show the packet to the
    operator and wait.
Key Interfaces:
  - Input: local image paths plus the extraction prompt (from vision_agent);
    operator-pasted reply text keyed by packet ID.
  - Output: raw JSON text consumed by vision_agent.extract_item; ManualPacket
    objects consumed by the review UI (T-027).
FMEA Constraints Enforced:
  - PI-014 — the packet ID is embedded in the prompt, must be echoed in the
    reply, and is verified before parsing, so a reply cannot be attributed to
    the wrong item.
  - PI-003 — stateless per call: one packet, one reply, no chat memory assumed.
  - PI-004 / PI-005 — unchanged: the frozen extraction prompt and the existing
    parser are reused verbatim, so forced defects and drop-not-invent hold.
  - R-COST — zero API spend; the operator's chat subscription does the work.

NOTE: this module must NEVER import streamlit or google-genai. It is imported
by the orchestrator and by tests that have neither installed.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import MutableMapping

from src.ai.provider import AIProvider
from src.ai.vision_agent import _parse_json_block

# Identity of this adapter; both values feed the packet ID so a prompt or
# adapter change produces a new ID and stale replies stop matching.
ADAPTER_CODE = "manual-paste"
ADAPTER_VERSION = "1.0.0"

# The extra key the model must echo. It is stripped before the JSON reaches the
# frozen VisionAgentOutput contract (extra="forbid").
PACKET_ID_KEY = "packet_id"

# The single-word reply the packet asks for when the attached photos do not
# match the listed file names.
MISMATCH_WORD = "MISMATCH"


@dataclass(frozen=True)
class ManualPacket:
    """
    One copy/paste extraction packet for one item.

    Attributes:
        packet_id: Deterministic ID over adapter identity, prompt, and sorted
            photo file names. Echoed by the model and verified on paste (PI-014).
        prompt_text: The complete text the operator pastes into the chat.
        image_paths: Local photo paths the operator must attach, sorted by name.
        operator_checklist: Ordered plain-language steps for the operator.
        adapter_version: ADAPTER_VERSION at build time.
    """

    packet_id: str
    prompt_text: str
    image_paths: tuple[str, ...]
    operator_checklist: tuple[str, ...]
    adapter_version: str = ADAPTER_VERSION


class ManualResponsePending(Exception):
    """
    Raised by ManualProvider when no reply is stored for a packet yet.

    Attributes:
        packet: The ManualPacket the operator must carry to the chat.
    """

    def __init__(self, packet: ManualPacket) -> None:
        """Record the packet and build a short human-readable message."""
        self.packet = packet
        super().__init__(
            f"Manual AI reply pending for packet {packet.packet_id}; paste the "
            "packet into your chat and return the JSON reply."
        )


class ManualPacketMismatch(ValueError):
    """Raised when a pasted reply does not carry the expected packet ID (PI-014)."""


def _sorted_image_paths(image_paths: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Return the image paths sorted by file name so order of discovery is irrelevant."""
    return tuple(sorted((str(path) for path in image_paths), key=lambda p: Path(p).name))


def _packet_id_for(prompt: str, image_names: tuple[str, ...], adapter_version: str) -> str:
    """
    Derive the deterministic packet ID.

    Args:
        prompt: The extraction prompt text.
        image_names: Sorted photo file names (not full paths, so a moved cache
            directory does not change the ID).
        adapter_version: The adapter version string.

    Returns:
        A UUID-formatted string derived from a SHA-256 over the canonical JSON
        of the inputs. Equal inputs always give the same ID.
    """
    seed = json.dumps(
        {
            "adapter": ADAPTER_CODE,
            "adapter_version": adapter_version,
            "prompt": prompt,
            "images": list(image_names),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    # Fold the first 128 bits into UUID form so the ID is short, copyable,
    # and visibly distinct from SKUs and folder IDs.
    return str(uuid.UUID(digest[:32]))


def _render_prompt(packet_id: str, prompt: str, image_names: tuple[str, ...]) -> str:
    """
    Render the complete paste-able packet text.

    Args:
        packet_id: The packet ID to embed and require in the reply.
        prompt: The frozen extraction prompt, included verbatim.
        image_names: Sorted photo file names the operator attaches.

    Returns:
        The full packet text (Markdown-flavored plain text).
    """
    photo_lines = "\n".join(f"{index}. {name}" for index, name in enumerate(image_names, 1))
    return (
        "# Lister-Bridge manual extraction packet\n"
        "\n"
        f"Packet ID: {packet_id}\n"
        f"Adapter: {ADAPTER_CODE} {ADAPTER_VERSION}\n"
        "\n"
        "A human operator pasted this packet. Attached to this message are "
        f"{len(image_names)} photo(s) of ONE item, in this order:\n"
        f"{photo_lines}\n"
        "\n"
        "If the attached photos do not match that list exactly, reply with the "
        f"single word {MISMATCH_WORD} and nothing else.\n"
        "\n"
        "## Extraction task\n"
        "\n"
        f"{prompt.rstrip()}\n"
        "\n"
        "## Reply requirements\n"
        "\n"
        f'1. Add exactly one extra key to the JSON object: "{PACKET_ID_KEY}": "{packet_id}".\n'
        "2. Return only the JSON object. No prose before or after it.\n"
        "3. Treat this item in isolation; ignore any earlier content in this chat.\n"
    )


def _operator_checklist() -> tuple[str, ...]:
    """Return the ordered operator steps shown beside every packet."""
    return (
        "Open a fresh chat in your subscription model; never reuse a chat from another item.",
        "Attach the listed photos from the folder Lister-Bridge shows for this item.",
        "Paste the whole packet as one message and send it.",
        "Copy the JSON reply exactly and paste it into this item's reply box.",
        f"If the model answers {MISMATCH_WORD}, re-check the attached photos and send again.",
    )


def build_packet(
    image_paths: list[str] | tuple[str, ...],
    prompt: str,
    *,
    adapter_version: str = ADAPTER_VERSION,
) -> ManualPacket:
    """
    Build the deterministic manual packet for one item.

    Args:
        image_paths: Local photo paths for the item (one batch subfolder).
        prompt: The extraction prompt (vision_agent supplies its frozen prompt).
        adapter_version: Adapter version folded into the packet ID.

    Returns:
        A ManualPacket whose ID and text are byte-identical for equal inputs
        regardless of the order the paths were discovered in.

    Side Effects:
        None. Photo files are not opened; only their names are used.

    Raises:
        ValueError: If image_paths is empty or prompt is blank.

    FMEA Constraints:
        PI-014 — the ID binds prompt, adapter, and photo set to one reply.
        PI-003 — a packet carries no state from any other item.
    """
    if not image_paths:
        raise ValueError("build_packet requires at least one image path")
    if not prompt or not prompt.strip():
        raise ValueError("build_packet requires a non-empty prompt")

    ordered_paths = _sorted_image_paths(image_paths)
    image_names = tuple(Path(path).name for path in ordered_paths)
    packet_id = _packet_id_for(prompt, image_names, adapter_version)
    return ManualPacket(
        packet_id=packet_id,
        prompt_text=_render_prompt(packet_id, prompt, image_names),
        image_paths=ordered_paths,
        operator_checklist=_operator_checklist(),
        adapter_version=adapter_version,
    )


def parse_manual_response(raw: str, packet: ManualPacket) -> str:
    """
    Verify a pasted reply against its packet and return contract-ready JSON.

    Args:
        raw: The operator-pasted reply text (bare JSON or a fenced block).
        packet: The ManualPacket the reply is claimed to answer.

    Returns:
        JSON text of the reply with the packet_id key removed, suitable for
        vision_agent._parse_json_block and the frozen VisionAgentOutput.

    Side Effects:
        None.

    Raises:
        ManualPacketMismatch: If the reply is the MISMATCH word, lacks a
            packet_id, or carries a packet_id other than the packet's own.
        ValueError: If the reply is not a JSON object (propagated from the
            shared parser, so the operator sees the same message Gemini
            replies would produce).

    FMEA Constraints:
        PI-014 — the echoed ID must equal the packet ID before any field is
        trusted; a wrong-item reply never reaches the contract.
    """
    text = (raw or "").strip()
    # The packet asks the model to answer MISMATCH when the photos do not match
    # the listed names; treat that as a rejection, not a parse error.
    if text.upper() == MISMATCH_WORD:
        raise ManualPacketMismatch(
            "The model reported that the attached photos did not match the packet; "
            "re-check the photos and send the packet again."
        )

    parsed = _parse_json_block(text)
    echoed = parsed.get(PACKET_ID_KEY)
    if echoed is None:
        raise ManualPacketMismatch(
            f"The reply has no {PACKET_ID_KEY!r} key; paste the reply for packet "
            f"{packet.packet_id} exactly as the model returned it."
        )
    if str(echoed).strip().lower() != packet.packet_id.lower():
        raise ManualPacketMismatch(
            f"The reply belongs to packet {str(echoed).strip()}, not to this item's "
            f"packet {packet.packet_id}; it was not applied."
        )

    # Strip the echo so the frozen contract (extra="forbid") parses unchanged.
    remaining = {key: value for key, value in parsed.items() if key != PACKET_ID_KEY}
    return json.dumps(remaining)


class ManualProvider(AIProvider):
    """
    AIProvider backed by operator copy/paste instead of an API.

    The caller (orchestrator) runs the normal pipeline. When no reply is stored
    for an item's packet, generate_from_images raises ManualResponsePending
    carrying the packet; the UI shows it, the operator pastes the reply, and
    the next scan completes the item through the unchanged parser.
    """

    def __init__(self, responses: MutableMapping[str, str] | None = None) -> None:
        """
        Create the provider around a reply store.

        Args:
            responses: Mapping of packet_id -> raw reply text. Pass a
                Streamlit session_state dict so replies survive reruns; None
                creates a private in-memory dict.

        Side Effects:
            None. No network, no SDK, no file access.
        """
        self._responses: MutableMapping[str, str] = responses if responses is not None else {}

    @property
    def model_name(self) -> str:
        """Return the adapter code; there is no pinned vendor model."""
        return ADAPTER_CODE

    @property
    def responses(self) -> MutableMapping[str, str]:
        """Return the live reply store (packet_id -> raw reply text)."""
        return self._responses

    def store_response(self, packet: ManualPacket, raw: str) -> None:
        """
        Validate and store an operator-pasted reply for one packet.

        Args:
            packet: The packet the reply answers.
            raw: The pasted reply text.

        Returns:
            None

        Side Effects:
            Writes one entry to the reply store on success only.

        Raises:
            ManualPacketMismatch / ValueError: Propagated from
                parse_manual_response; nothing is stored when validation fails,
                so a bad paste can never be applied later by accident (PI-014).
        """
        # Fail fast: a reply that cannot pass verification is never stored.
        parse_manual_response(raw, packet)
        self._responses[packet.packet_id] = raw

    def forget_response(self, packet_id: str) -> None:
        """Remove a stored reply (for example after the item is priced)."""
        self._responses.pop(packet_id, None)

    def generate_from_images(
        self,
        image_paths: list[str],
        prompt: str,
        *,
        response_mime_type: str = "application/json",
        media_resolution: str = "HIGH",
        thinking_level: str = "HIGH",
    ) -> str:
        """
        Return the verified reply for this item's packet, or ask for one.

        Args:
            image_paths: Local photo paths for the item.
            prompt: The extraction prompt (vision_agent's frozen text).
            response_mime_type: Accepted for interface parity; replies are JSON.
            media_resolution: Accepted for interface parity; the operator's chat
                controls image fidelity.
            thinking_level: Accepted for interface parity.

        Returns:
            Contract-ready JSON text with the packet_id removed.

        Side Effects:
            None. No network call is ever made.

        Raises:
            ManualResponsePending: When no reply is stored for the packet.
            ManualPacketMismatch: When a stored reply's echoed ID is wrong.

        FMEA Constraints:
            PI-014 — reply verified against the packet before use.
            PI-003 — one stateless lookup per item; no cross-item context.
            R-COST — zero API spend.
        """
        packet = build_packet(image_paths, prompt)
        raw = self._responses.get(packet.packet_id)
        if raw is None:
            raise ManualResponsePending(packet)
        return parse_manual_response(raw, packet)
