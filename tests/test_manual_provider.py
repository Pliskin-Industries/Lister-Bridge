"""
Module: test_manual_provider.py
Purpose: Tests for the T-026 manual paste AI provider — deterministic packets,
         packet-ID verification, the AIProvider contract, the orchestrator's
         pending path, and the AI_PROVIDER settings switch. No network, no SDK.
FMEA Constraints Enforced (asserted): PI-014, PI-003, PI-004, PI-005, R-COST.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ai import manual_provider
from src.ai.manual_provider import (
    ManualPacket,
    ManualPacketMismatch,
    ManualProvider,
    ManualResponsePending,
    build_packet,
    parse_manual_response,
)
from src.ai.vision_agent import _EXTRACTION_PROMPT, extract_item
from src.contracts import ItemStatus, VisionAgentOutput
from src.core import orchestrator
from src.core import settings
from src.core.state_store import StateStore


_PHOTOS = ["/cache/b.jpg", "/cache/a.jpg", "/cache/c.heic"]


def _reply(packet: ManualPacket, **overrides) -> str:
    """Build a valid model reply echoing the packet ID, with optional overrides."""
    body = {
        "item_specifics": {"Brand": "Sony", "Model": "WH-1000XM4"},
        "condition": "Used - Very Good",
        "defects_found": ["scuff on left cup"],
        "dropped_fields": [],
        manual_provider.PACKET_ID_KEY: packet.packet_id,
    }
    body.update(overrides)
    return json.dumps(body)


# ── build_packet ──────────────────────────────────────────────────────────────


def test_build_packet_is_deterministic_and_order_insensitive():
    """Equal inputs give byte-identical packets regardless of path order."""
    first = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    second = build_packet(list(reversed(_PHOTOS)), _EXTRACTION_PROMPT)
    assert first == second
    assert first.image_paths == ("/cache/a.jpg", "/cache/b.jpg", "/cache/c.heic")


def test_build_packet_id_changes_with_photo_set_prompt_and_adapter_version():
    """Any change to photos, prompt, or adapter version yields a new ID (PI-014)."""
    base = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    fewer = build_packet(_PHOTOS[:2], _EXTRACTION_PROMPT)
    other_prompt = build_packet(_PHOTOS, _EXTRACTION_PROMPT + "\nExtra line.")
    other_version = build_packet(_PHOTOS, _EXTRACTION_PROMPT, adapter_version="9.9.9")
    ids = {base.packet_id, fewer.packet_id, other_prompt.packet_id, other_version.packet_id}
    assert len(ids) == 4


def test_build_packet_uses_file_names_not_directories():
    """A moved cache directory does not invalidate stored replies."""
    moved = [f"/elsewhere/{Path(p).name}" for p in _PHOTOS]
    assert build_packet(moved, _EXTRACTION_PROMPT).packet_id == (
        build_packet(_PHOTOS, _EXTRACTION_PROMPT).packet_id
    )


def test_build_packet_prompt_contains_required_parts():
    """The packet embeds the frozen prompt, photo names, ID, and echo rule."""
    packet = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    text = packet.prompt_text
    assert _EXTRACTION_PROMPT.strip() in text
    assert packet.packet_id in text
    assert '"packet_id"' in text
    for name in ("a.jpg", "b.jpg", "c.heic"):
        assert name in text
    assert "3 photo(s)" in text
    assert manual_provider.MISMATCH_WORD in text
    assert len(packet.operator_checklist) == 5


def test_build_packet_rejects_empty_inputs():
    """No photos or a blank prompt is a caller error."""
    with pytest.raises(ValueError, match="image path"):
        build_packet([], _EXTRACTION_PROMPT)
    with pytest.raises(ValueError, match="prompt"):
        build_packet(_PHOTOS, "   ")


# ── parse_manual_response ─────────────────────────────────────────────────────


def test_parse_strips_packet_id_and_keeps_contract_keys():
    """The echoed key is removed so the frozen contract parses unchanged."""
    packet = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    cleaned = json.loads(parse_manual_response(_reply(packet), packet))
    assert manual_provider.PACKET_ID_KEY not in cleaned
    assert cleaned["defects_found"] == ["scuff on left cup"]
    VisionAgentOutput(**cleaned)


def test_parse_accepts_fenced_reply_and_case_insensitive_id():
    """Code fences and ID case differences from the chat UI are tolerated."""
    packet = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    upper_id = _reply(packet, packet_id=packet.packet_id.upper())
    fenced = f"```json\n{upper_id}\n```"
    cleaned = json.loads(parse_manual_response(fenced, packet))
    assert cleaned["condition"] == "Used - Very Good"


def test_parse_rejects_missing_packet_id():
    """A reply without the echo is rejected before any field is trusted (PI-014)."""
    packet = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    body = json.loads(_reply(packet))
    del body[manual_provider.PACKET_ID_KEY]
    with pytest.raises(ManualPacketMismatch, match="no 'packet_id'"):
        parse_manual_response(json.dumps(body), packet)


def test_parse_rejects_reply_for_another_item():
    """Item A's reply pasted against item B is rejected and names both IDs."""
    packet_a = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    packet_b = build_packet(_PHOTOS[:1], _EXTRACTION_PROMPT)
    with pytest.raises(ManualPacketMismatch) as excinfo:
        parse_manual_response(_reply(packet_a), packet_b)
    assert packet_a.packet_id in str(excinfo.value)
    assert packet_b.packet_id in str(excinfo.value)


def test_parse_treats_mismatch_word_as_rejection():
    """The model's MISMATCH answer is a rejection, not a JSON error."""
    packet = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    with pytest.raises(ManualPacketMismatch, match="did not match"):
        parse_manual_response(" mismatch \n", packet)


def test_parse_non_json_reply_raises_value_error():
    """Prose replies surface the shared parser's ValueError."""
    packet = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_manual_response("Sure! Here is what I see...", packet)


# ── ManualProvider ────────────────────────────────────────────────────────────


def test_provider_raises_pending_with_packet_when_no_reply_stored():
    """Without a stored reply the provider asks for one and makes no call."""
    provider = ManualProvider()
    assert provider.model_name == manual_provider.ADAPTER_CODE
    with pytest.raises(ManualResponsePending) as excinfo:
        provider.generate_from_images(_PHOTOS, _EXTRACTION_PROMPT)
    assert excinfo.value.packet == build_packet(_PHOTOS, _EXTRACTION_PROMPT)


def test_provider_store_then_generate_feeds_extract_item():
    """A stored reply flows through vision_agent with PI-004/PI-005 intact."""
    provider = ManualProvider()
    packet = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    provider.store_response(
        packet,
        _reply(packet, item_specifics={"Brand": "Sony", "Color": "Purple"}),
    )

    output = extract_item(
        _PHOTOS,
        provider,
        category_aspect_enums={"Color": ["Black", "Silver"]},
    )
    assert output.defects_found == ["scuff on left cup"]
    assert output.item_specifics == {"Brand": "Sony"}
    assert output.dropped_fields == ["Color"]


def test_provider_store_response_validates_and_never_stores_bad_reply():
    """A mismatched paste is rejected at store time and leaves the store empty."""
    provider = ManualProvider()
    packet = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    other = build_packet(_PHOTOS[:1], _EXTRACTION_PROMPT)
    with pytest.raises(ManualPacketMismatch):
        provider.store_response(packet, _reply(other))
    assert provider.responses == {}
    with pytest.raises(ManualResponsePending):
        provider.generate_from_images(_PHOTOS, _EXTRACTION_PROMPT)


def test_provider_uses_injected_store_and_forget_response():
    """A caller-owned mapping (e.g. session_state) is read and written in place."""
    shared: dict[str, str] = {}
    provider = ManualProvider(shared)
    packet = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    provider.store_response(packet, _reply(packet))
    assert set(shared) == {packet.packet_id}
    provider.forget_response(packet.packet_id)
    assert shared == {}
    provider.forget_response("never-stored")


def test_provider_is_stateless_across_items():
    """Two items with separate packets never see each other's replies (PI-003)."""
    provider = ManualProvider()
    packet_a = build_packet(_PHOTOS, _EXTRACTION_PROMPT)
    packet_b = build_packet(_PHOTOS[:1], _EXTRACTION_PROMPT)
    provider.store_response(packet_a, _reply(packet_a, condition="A"))
    with pytest.raises(ManualResponsePending):
        provider.generate_from_images(_PHOTOS[:1], _EXTRACTION_PROMPT)
    provider.store_response(packet_b, _reply(packet_b, condition="B"))
    assert json.loads(provider.generate_from_images(_PHOTOS, _EXTRACTION_PROMPT))["condition"] == "A"
    assert json.loads(provider.generate_from_images(_PHOTOS[:1], _EXTRACTION_PROMPT))["condition"] == "B"


# ── Orchestrator pending path ─────────────────────────────────────────────────


@pytest.fixture
def store():
    """An ephemeral in-memory StateStore."""
    s = StateStore(":memory:")
    yield s
    s.close()


@pytest.fixture
def mock_drive(monkeypatch):
    """Two pending batches whose downloads return fixed local photo paths."""
    batches = [
        {"folder_id": "F1", "folder_name": "Headphones", "image_files": []},
        {"folder_id": "F2", "folder_name": "Camera", "image_files": []},
    ]
    monkeypatch.setattr(orchestrator.drive_fetcher, "list_pending_batches", lambda: batches)
    monkeypatch.setattr(
        orchestrator.drive_fetcher,
        "download_batch_images",
        lambda batch: ([f"/cache/{batch['folder_id']}.jpg"], False),
    )
    return batches


def test_scan_reports_pending_items_and_leaves_status_new(mock_drive, store):
    """Pending manual items are neither payloads nor errors; status stays NEW."""
    provider = ManualProvider()
    summary = orchestrator.scan_and_prepare(provider, store)

    assert summary.payloads == []
    assert summary.errors == []
    assert [item.item_sku for item in summary.pending] == ["LB-F1", "LB-F2"]
    assert summary.pending[0].folder_name == "Headphones"
    assert summary.pending[0].packet.image_paths == ("/cache/F1.jpg",)
    assert store.get_item("LB-F1").status is ItemStatus.NEW
    assert store.get_item("LB-F2").status is ItemStatus.NEW


def test_rescan_completes_items_after_replies_are_stored(mock_drive, store):
    """Storing replies for the surfaced packets completes items on rescan."""
    provider = ManualProvider()
    first = orchestrator.scan_and_prepare(provider, store)
    for item in first.pending:
        provider.store_response(item.packet, _reply(item.packet))

    second = orchestrator.scan_and_prepare(provider, store)
    assert second.pending == []
    assert second.errors == []
    assert sorted(payload.item_sku for payload in second.payloads) == ["LB-F1", "LB-F2"]
    assert store.get_item("LB-F1").status is ItemStatus.PRICED
    assert store.get_item("LB-F2").status is ItemStatus.PRICED


def test_partial_replies_complete_only_answered_items(mock_drive, store):
    """One answered packet yields one payload while the other stays pending."""
    provider = ManualProvider()
    first = orchestrator.scan_and_prepare(provider, store)
    answered = first.pending[0]
    provider.store_response(answered.packet, _reply(answered.packet))

    second = orchestrator.scan_and_prepare(provider, store)
    assert [payload.item_sku for payload in second.payloads] == [answered.item_sku]
    assert [item.item_sku for item in second.pending] == [first.pending[1].item_sku]


def test_injected_wrong_item_reply_is_an_error_not_a_payload(mock_drive, store):
    """A reply smuggled under another packet's ID fails closed as a batch error."""
    provider = ManualProvider()
    first = orchestrator.scan_and_prepare(provider, store)
    item_a, item_b = first.pending
    # Bypass store_response validation to simulate a corrupted reply store.
    provider.responses[item_b.packet.packet_id] = _reply(item_a.packet)

    second = orchestrator.scan_and_prepare(provider, store)
    assert second.payloads == []
    assert [item.item_sku for item in second.pending] == [item_a.item_sku]
    assert len(second.errors) == 1
    assert second.errors[0].batch_folder_id == item_b.batch_folder_id
    assert "ManualPacketMismatch" in second.errors[0].reason
    assert store.get_item(item_b.item_sku).status is ItemStatus.ERROR


# ── Settings switch ───────────────────────────────────────────────────────────


def test_ai_provider_mode_normalizes_values():
    """manual is recognized case-insensitively; anything else means gemini."""
    assert settings.ai_provider_mode({"AI_PROVIDER": " Manual "}) == settings.AI_PROVIDER_MANUAL
    assert settings.ai_provider_mode({"AI_PROVIDER": "gemini"}) == settings.AI_PROVIDER_GEMINI
    assert settings.ai_provider_mode({}) == settings.AI_PROVIDER_GEMINI
    assert settings.ai_provider_mode({"AI_PROVIDER": "openai"}) == settings.AI_PROVIDER_GEMINI


def test_manual_mode_drops_gemini_key_from_missing_required():
    """AI_PROVIDER=manual removes GEMINI_API_KEY; the default keeps it."""
    values = {f.key: f.default for f in settings._all_fields()}
    values["GEMINI_API_KEY"] = ""
    values["EBAY_CLIENT_ID"] = ""

    assert "GEMINI_API_KEY" in settings.missing_required(values)

    values["AI_PROVIDER"] = "manual"
    missing = settings.missing_required(values)
    assert "GEMINI_API_KEY" not in missing
    assert "EBAY_CLIENT_ID" in missing

    values["AI_PROVIDER"] = "typo"
    assert "GEMINI_API_KEY" in settings.missing_required(values)


def test_ai_provider_field_is_in_schema_and_env_example():
    """The switch is a documented, non-secret, optional setting."""
    field_ = settings._FIELDS_BY_KEY["AI_PROVIDER"]
    assert field_.required is False
    assert field_.secret is False
    assert field_.default == "gemini"
    env_example = (Path(__file__).resolve().parent.parent / ".env.example").read_text(
        encoding="utf-8"
    )
    assert "AI_PROVIDER=gemini" in env_example


# ── Import purity ─────────────────────────────────────────────────────────────


def test_manual_provider_module_imports_no_streamlit_or_gemini_sdk():
    """The module stays importable without streamlit or google-genai installed."""
    source = Path(manual_provider.__file__).read_text(encoding="utf-8")
    import_lines = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert "streamlit" not in line
        assert "google" not in line
