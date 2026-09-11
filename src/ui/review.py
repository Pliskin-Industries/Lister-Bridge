"""
Module: review.py
Purpose: Pure, Streamlit-free helpers for the review/approve screen — comp-search
         links, price recomputation, operator-edit application, and pre-publish
         validation. Kept separate from app.py so it is unit-testable without
         Streamlit.
Primary Responsibilities:
  - Build the operator's Terapeak / sold-comp research links (human-in-the-loop).
  - Recompute the Margin-Guard price when the operator enters a comp / cost / fees.
  - Apply operator edits (including description corrections) to a ListingPayload
    immutably.
  - Expose the canonical eBay condition enum for the UI's condition selectbox,
    mirroring orchestrator._CONDITION_MAP without importing streamlit-side code
    into core.
  - Report pre-publish validation problems + remaining missing inputs.
Key Interfaces:
  - Input: VisionAgentOutput, MarginGuardOutput, ListingPayload + operator edits.
  - Output: URLs, recomputed MarginGuardOutput, edited ListingPayload, problem lists.
FMEA Constraints Enforced:
  - PI-006 / R-PRICE — recompute routes through margin_guard (floor + missing_inputs).
  - PI-009 — validate_for_publish reuses EbayClient.validate_offer before Approve.
  - PI-008 — surfaces tidy fields (no raw JSON) for the UI to render.
  - PI-004 — apply_operator_edits carries operator corrections to the defect-
    disclosure description through to the payload instead of discarding them.
  - PI-014 / R-COST — build_provider selects the Gemini or manual paste route
    from AI_PROVIDER; apply_manual_reply routes a pasted reply through the
    packet-ID check and turns every rejection into operator-readable guidance
    (T-027).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import MutableMapping
from urllib.parse import quote_plus

from src.ai import margin_guard
from src.ai.manual_provider import (
    MISMATCH_WORD,
    ManualPacket,
    ManualPacketMismatch,
    ManualProvider,
    build_packet,
)
from src.ai.provider import AIProvider, GeminiProvider
from src.ai.vision_agent import _EXTRACTION_PROMPT
from src.api.ebay_client import EbayClient
from src.contracts import ListingPayload, MarginGuardOutput, VisionAgentOutput
from src.core import settings as settings_logic

# eBay marketplace used for the research links.
_SOLD_SEARCH_BASE = "https://www.ebay.com/sch/i.html"
_TERAPEAK_BASE = "https://www.ebay.com/sh/research"

# Canonical eBay condition enum values, in the same order as (and mirroring)
# orchestrator._CONDITION_MAP's target values (deduplicated, order-preserved).
# Kept here — rather than imported from orchestrator — so app.py (a Streamlit
# module) never needs to import core orchestrator internals just to populate a
# selectbox; if _CONDITION_MAP's target set changes, update this list to match.
EBAY_CONDITION_VALUES: list[str] = [
    "FOR_PARTS_OR_NOT_WORKING",
    "LIKE_NEW",
    "NEW_OTHER",
    "NEW",
    "USED_EXCELLENT",
    "USED_VERY_GOOD",
    "USED_ACCEPTABLE",
    "USED_GOOD",
]


def build_sold_comp_url(query: str) -> str:
    """
    Build a public eBay "sold + completed" search URL for operator comp checks.

    Args:
        query: The item search text (e.g. "Sony WH-1000XM4").

    Returns:
        A URL filtering to sold, completed listings.

    Side Effects:
        None.

    FMEA Constraints:
        R-PRICE — supports the human-in-the-loop sold-comp confirmation step.
    """
    q = quote_plus(query.strip())
    return f"{_SOLD_SEARCH_BASE}?_nkw={q}&LH_Sold=1&LH_Complete=1"


def build_terapeak_url(query: str) -> str:
    """
    Build a Terapeak (Seller Hub research) URL for the given query.

    Args:
        query: The item search text.

    Returns:
        A Terapeak research URL (requires the operator to be signed in).

    Side Effects:
        None.

    FMEA Constraints:
        R-PRICE — the preferred sold-data research tool surfaced to the operator.
    """
    q = quote_plus(query.strip())
    return f"{_TERAPEAK_BASE}?marketplace=EBAY-US&keywords={q}&tabName=SOLD"


def recompute_price(
    vision: VisionAgentOutput,
    *,
    cost: float | None,
    fees: float | None,
    active_comps: list[float] | None,
    user_confirmed_comp: float | None,
) -> MarginGuardOutput:
    """
    Recompute the Margin-Guard price from the operator's current inputs.

    Thin passthrough to margin_guard.price_item so the UI re-prices live as the
    operator enters a confirmed comp / cost / fees.

    Args:
        vision: The item's extraction result.
        cost: Operator-entered cost (USD) or None.
        fees: Operator-entered fees (USD) or None.
        active_comps: Active comps already fetched (anchor), if any.
        user_confirmed_comp: Operator-entered sold-comp price, if any.

    Returns:
        A fresh MarginGuardOutput (price, floor_applied, missing_inputs, reasoning).

    Side Effects:
        None.

    FMEA Constraints:
        PI-006 / R-PRICE — floor + missing-input handling live in price_item.
    """
    return margin_guard.price_item(
        vision,
        cost=cost,
        fees=fees,
        active_comps=active_comps,
        user_confirmed_comp=user_confirmed_comp,
    )


def apply_operator_edits(
    payload: ListingPayload,
    *,
    title: str | None = None,
    price: float | None = None,
    condition: str | None = None,
    category_id: str | None = None,
    item_specifics: dict[str, str] | None = None,
    description: str | None = None,
) -> ListingPayload:
    """
    Return a copy of the payload with the operator's edits applied.

    Args:
        payload: The original assembled ListingPayload.
        title: Edited title, if changed.
        price: Edited final price (USD), if changed.
        condition: Edited eBay condition enum, if changed.
        category_id: Edited eBay category ID, if changed.
        item_specifics: Edited aspects map, if changed.
        description: Edited listing description, if changed. Operator
            corrections here matter because the description is where PI-004
            defect disclosures live — leaving this unread from the UI silently
            discards operator fixes to defect-disclosure text.

    Returns:
        A new ListingPayload with the provided fields overridden (others kept).

    Side Effects:
        None (pydantic model_copy is immutable-style).

    FMEA Constraints:
        PI-004 — description edits (defect disclosures) are applied like every
        other field; None leaves the original text untouched.
    """
    updates: dict = {}
    if title is not None:
        updates["title"] = title
    if price is not None:
        updates["price"] = price
    if condition is not None:
        updates["condition"] = condition
    if category_id is not None:
        updates["category_id"] = category_id
    if item_specifics is not None:
        updates["item_specifics"] = item_specifics
    if description is not None:
        updates["listing_description"] = description
    return payload.model_copy(update=updates)


def validate_for_publish(payload: ListingPayload) -> list[str]:
    """
    Return the list of problems blocking publish (empty == ready to Approve).

    Args:
        payload: The (possibly operator-edited) ListingPayload.

    Returns:
        Human-readable problem strings from EbayClient.validate_offer (PI-009).
        Note: images upload at publish time, so an empty eps_image_urls is NOT
        flagged here when local_image_paths are present.

    Side Effects:
        None.

    FMEA Constraints:
        PI-009 — the same required-field check the publish path enforces, surfaced
        in the UI before the operator can Approve.
    """
    problems = EbayClient.validate_offer(payload)
    # Pre-publish, EPS URLs don't exist yet; treat local photos as sufficient.
    if payload.local_image_paths:
        problems = [p for p in problems if "EPS image URL" not in p]
    return problems


def review_summary(
    vision: VisionAgentOutput, pricing: MarginGuardOutput
) -> dict:
    """
    Build a tidy, operator-facing summary dict (no raw JSON dumps; PI-008).

    Args:
        vision: The item's extraction result.
        pricing: The item's Margin-Guard result.

    Returns:
        A flat dict of display rows: specifics, condition, defects, suggested
        price, comp anchor/range, floor status, and any unresolved inputs.

    Side Effects:
        None.

    FMEA Constraints:
        PI-008 — a clean summary table, not raw JSON, drives operator review.
    """
    return {
        "specifics": dict(vision.item_specifics),
        "condition": vision.condition,
        "defects_found": list(vision.defects_found),
        "dropped_fields": list(vision.dropped_fields),
        "suggested_price": pricing.margin_guard_price,
        "active_comp_anchor": pricing.active_comp_anchor,
        "active_comp_range": (pricing.active_comp_range.low, pricing.active_comp_range.high),
        "floor_price": pricing.floor_price,
        "floor_applied": pricing.floor_applied,
        "reasoning": pricing.reasoning,
        "missing_inputs": list(pricing.missing_inputs),
    }


# ── AI route selection and the manual paste workflow (T-027) ──────────────────

# Operator-facing names for the two AI routes, keyed by settings.ai_provider_mode.
PROVIDER_LABELS: dict[str, str] = {
    settings_logic.AI_PROVIDER_GEMINI: "Gemini API",
    settings_logic.AI_PROVIDER_MANUAL: "Manual paste (your own chat subscription)",
}

# Chat UIs wrap a one-word answer in Markdown emphasis, code ticks, or quotes
# and may add punctuation; normalize_manual_reply tolerates all of these via a
# leading non-word-character skip and a word boundary (see the regex there).


def provider_mode(values: dict) -> str:
    """
    Return the normalized AI route for the given settings.

    Args:
        values: Settings dict from settings.read_settings() or the Setup tab.

    Returns:
        settings.AI_PROVIDER_GEMINI or settings.AI_PROVIDER_MANUAL.

    Side Effects:
        None.
    """
    return settings_logic.ai_provider_mode(values)


def provider_mode_label(values: dict) -> str:
    """
    Return the operator-facing label for the active AI route.

    Args:
        values: Settings dict.

    Returns:
        A short label for the sidebar banner (see PROVIDER_LABELS).

    Side Effects:
        None.
    """
    return PROVIDER_LABELS[provider_mode(values)]


def build_provider(values: dict, manual_replies: MutableMapping[str, str]) -> AIProvider:
    """
    Construct the AIProvider selected by AI_PROVIDER.

    Args:
        values: Settings dict; AI_PROVIDER decides the route.
        manual_replies: The caller-owned reply store (packet_id -> raw reply)
            used only by the manual route. Pass a dedicated nested dict, not
            the whole Streamlit session state, so UUID keys never mix with
            widget keys.

    Returns:
        A ManualProvider bound to manual_replies, or a GeminiProvider (which
        reads GEMINI_API_KEY lazily and makes no network call here).

    Side Effects:
        None at construction time.

    FMEA Constraints:
        R-COST — the manual route makes zero API calls.
        PI-014 — the manual route verifies packet IDs before any reply is used.
    """
    if provider_mode(values) == settings_logic.AI_PROVIDER_MANUAL:
        return ManualProvider(manual_replies)
    return GeminiProvider()


@dataclass(frozen=True)
class PendingItemView:
    """
    Display model for one item waiting on an operator-pasted AI reply.

    Attributes:
        item_sku: The item's deterministic SKU.
        folder_name: The Drive batch folder name.
        batch_folder_id: The Drive batch folder ID.
        packet_id: The ID the pasted reply must echo (PI-014).
        prompt_text: The full packet text to copy into the chat.
        image_paths: Local photo paths to display and attach, sorted by name.
        image_names: File names only, matching the list inside the packet.
        photo_folder: The common local folder holding the photos, for the
            operator's file picker.
        checklist: Ordered operator steps from the packet.
    """

    item_sku: str
    folder_name: str
    batch_folder_id: str
    packet_id: str
    prompt_text: str
    image_paths: tuple[str, ...]
    image_names: tuple[str, ...]
    photo_folder: str
    checklist: tuple[str, ...]


def pending_item_view(pending) -> PendingItemView:
    """
    Flatten an orchestrator PendingManualItem into a display model.

    Args:
        pending: An object exposing item_sku, folder_name, batch_folder_id,
            and packet (a ManualPacket), as orchestrator.PendingManualItem does.

    Returns:
        A PendingItemView with everything the pending card renders.

    Side Effects:
        None. Photo files are not opened.

    FMEA Constraints:
        PI-008 — the card shows photos, names, and one copyable block, not JSON.
        PI-014 — the packet ID is exposed for the operator to recognise.
    """
    packet: ManualPacket = pending.packet
    paths = tuple(packet.image_paths)
    # All cache files for one batch share a directory; take the first path's
    # parent so the operator knows where to browse when attaching photos.
    photo_folder = str(Path(paths[0]).parent) if paths else ""
    return PendingItemView(
        item_sku=pending.item_sku,
        folder_name=pending.folder_name,
        batch_folder_id=pending.batch_folder_id,
        packet_id=packet.packet_id,
        prompt_text=packet.prompt_text,
        image_paths=paths,
        image_names=tuple(Path(p).name for p in paths),
        photo_folder=photo_folder,
        checklist=tuple(packet.operator_checklist),
    )


def normalize_manual_reply(raw: str) -> str:
    """
    Recover a decorated one-word MISMATCH answer; pass everything else through.

    Chat interfaces often wrap a bare word in Markdown emphasis or add a full
    stop (``**MISMATCH**``, ``MISMATCH.``). Without this step those variants
    fall through to the JSON parser and the operator is told the reply was
    malformed JSON instead of that the model flagged a photo mismatch.

    Args:
        raw: The pasted reply text.

    Returns:
        MISMATCH_WORD when the reply is that word under decoration and contains
        no JSON object; otherwise the stripped original text.

    Side Effects:
        None.
    """
    text = (raw or "").strip()
    if "{" in text:
        return text
    # A bare word, or the word followed by the model's own explanation
    # ("**MISMATCH**: the second photo shows a different item"), both mean the
    # model flagged the photos; neither contains a JSON object. Leading
    # non-word characters (emphasis, quotes) are skipped and the word must end
    # at a word boundary so "MISMATCHED" or "The MISMATCH..." do not qualify.
    if re.match(rf"^[\W_]*{MISMATCH_WORD}\b", text, flags=re.IGNORECASE):
        return MISMATCH_WORD
    return text


# Longest operator-facing message we will echo back; longer text is cut with
# an ellipsis so a hostile or accidental multi-kilobyte paste cannot flood
# the page (critic F7).
_MESSAGE_MAX_LEN = 400


def _truncate_message(text: str) -> str:
    """
    Cut an over-long message from the middle so both ends survive.

    Args:
        text: The operator-facing message.

    Returns:
        The text unchanged when it fits _MESSAGE_MAX_LEN; otherwise its head
        and tail joined by an ellipsis. Keeping the tail preserves this item's
        own packet ID, which the mismatch message places last (critic N1).

    Side Effects:
        None.
    """
    if len(text) <= _MESSAGE_MAX_LEN:
        return text
    keep = (_MESSAGE_MAX_LEN - 1) // 2
    return text[:keep] + "…" + text[-keep:]


@dataclass(frozen=True)
class ManualReplyResult:
    """
    Outcome of applying a pasted reply.

    Attributes:
        ok: True when the reply was verified and stored.
        message: Operator-facing text; never a traceback.
    """

    ok: bool
    message: str


def apply_manual_reply(provider: ManualProvider, packet: ManualPacket, raw: str) -> ManualReplyResult:
    """
    Verify and store one pasted reply, returning operator-readable guidance.

    Args:
        provider: The session's ManualProvider.
        packet: The packet the reply answers (from the pending item).
        raw: The pasted reply text.

    Returns:
        ManualReplyResult(ok=True, ...) when stored; otherwise ok=False with a
        message that names the problem and the next step. The item stays
        pending in every failure case because nothing is stored.

    Side Effects:
        On success, one entry is written to the provider's reply store.

    FMEA Constraints:
        PI-014 — a wrong-item or ID-less reply is refused here, before parsing.
        PI-001 pattern — failures are human-readable messages, never tracebacks.
    """
    # The route is re-read from settings on every run, so a Setup-tab save of
    # AI route = gemini can arrive while manual cards are still on screen
    # (cycle-2 critic C1). Say so plainly instead of failing inside the guard.
    if not isinstance(provider, ManualProvider):
        return ManualReplyResult(
            False,
            "The AI route is no longer manual paste. Set AI route back to manual "
            "on the Setup tab, or click Scan to process waiting items with the "
            "Gemini API.",
        )
    text = normalize_manual_reply(raw if isinstance(raw, str) else "")
    if not text:
        return ManualReplyResult(False, "Paste the model's reply first, then click Use response.")
    try:
        provider.store_response(packet, text)
    except ManualPacketMismatch as exc:
        # The provider's messages are already operator-facing and name the IDs.
        # The echoed ID is operator-controlled text, so cap the message length
        # (critic F7).
        return ManualReplyResult(False, _truncate_message(str(exc)))
    except ValueError:
        return ManualReplyResult(
            False,
            "The reply is not a JSON object. Copy the model's entire reply, "
            "starting with { and ending with }, and paste it again.",
        )
    except Exception:  # noqa: BLE001 - a pathological paste must not crash the page
        # For example a RecursionError from absurdly nested JSON (critic F6).
        return ManualReplyResult(
            False,
            "The reply could not be read. Copy the model's JSON reply again "
            "and paste only that.",
        )
    return ManualReplyResult(
        True, "Reply accepted; re-scanning to extract and price this item."
    )


def release_manual_reply(manual_replies: MutableMapping[str, str], image_paths: list[str]) -> bool:
    """
    Drop the stored reply for an item once it has been fulfilled.

    Rebuilds the item's packet ID from its photos so the reply cannot be reused
    against a later same-named photo set in this session (critic F2 mitigation).

    Args:
        manual_replies: The session reply store.
        image_paths: The fulfilled payload's local_image_paths.

    Returns:
        True if a reply was removed, False if none was stored.

    Side Effects:
        Removes at most one entry from manual_replies.
    """
    if not image_paths:
        return False
    packet_id = build_packet(image_paths, _EXTRACTION_PROMPT).packet_id
    return manual_replies.pop(packet_id, None) is not None


def existing_image_paths(image_paths) -> list[str]:
    """Return the subset of paths that exist locally, preserving order."""
    return [str(p) for p in image_paths if os.path.exists(str(p))]
