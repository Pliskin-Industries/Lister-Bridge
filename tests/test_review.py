"""
Module: test_review.py
Purpose: Tests for the Phase 5 Streamlit-free review helpers (src/ui/review.py).
         No Streamlit import, no network.
FMEA Constraints Enforced (asserted): R-PRICE, PI-006, PI-009, PI-008, PI-004,
         PI-014 (manual paste route selection and reply verification, T-027).
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.ai.manual_provider import ManualProvider, build_packet
from src.ai.provider import GeminiProvider
from src.ai.vision_agent import _EXTRACTION_PROMPT
from src.contracts import ListingPayload, VisionAgentOutput
from src.core import orchestrator
from src.core import settings
from src.ui import review


def _vision(**specifics) -> VisionAgentOutput:
    return VisionAgentOutput(item_specifics=specifics, condition="Used", defects_found=[])


def _payload(**overrides) -> ListingPayload:
    data = dict(
        item_sku="LB-F1",
        title="Sony WH-1000XM4",
        item_specifics={"Brand": "Sony"},
        condition="USED_VERY_GOOD",
        price=199.99,
        category_id="112529",
        local_image_paths=["/cache/F1.jpg"],
        fulfillment_policy_id="FP",
        payment_policy_id="PP",
        return_policy_id="RP",
        merchant_location_key="LOC",
    )
    data.update(overrides)
    return ListingPayload(**data)


# ── research links (R-PRICE) ──────────────────────────────────────────────────


def test_sold_comp_url_filters_sold_completed():
    url = review.build_sold_comp_url("Sony WH-1000XM4")
    assert "Sony+WH-1000XM4" in url
    assert "LH_Sold=1" in url and "LH_Complete=1" in url


def test_terapeak_url_has_keywords():
    url = review.build_terapeak_url("Sony WH-1000XM4")
    assert "keywords=Sony+WH-1000XM4" in url


# ── recompute (PI-006 / R-PRICE) ──────────────────────────────────────────────


def test_recompute_price_applies_floor():
    out = review.recompute_price(
        _vision(Brand="Sony"), cost=100.0, fees=20.0, active_comps=[80.0],
        user_confirmed_comp=None,
    )
    assert out.floor_applied is True
    assert out.margin_guard_price == 138.00


def test_recompute_price_uses_user_comp():
    out = review.recompute_price(
        _vision(Brand="Sony"), cost=10.0, fees=2.0, active_comps=None,
        user_confirmed_comp=250.0,
    )
    assert out.margin_guard_price == 250.0


# ── edits ─────────────────────────────────────────────────────────────────────


def test_apply_operator_edits_overrides_only_given():
    p = _payload()
    edited = review.apply_operator_edits(p, price=149.0, title="New Title")
    assert edited.price == 149.0
    assert edited.title == "New Title"
    assert edited.category_id == p.category_id  # unchanged
    assert p.price == 199.99  # original untouched (immutable copy)


# ── description edits (PI-004: operator defect-disclosure corrections) ───────


def test_apply_operator_edits_applies_description():
    """A description edit is carried into listing_description (PI-004)."""
    p = _payload(listing_description="Condition: Used.\nNo visible defects noted.")
    edited = review.apply_operator_edits(
        p, description="Condition: Used.\nNoted defects:\n- small scratch on lid"
    )
    assert edited.listing_description == (
        "Condition: Used.\nNoted defects:\n- small scratch on lid"
    )
    # Original payload is untouched (immutable copy).
    assert p.listing_description == "Condition: Used.\nNo visible defects noted."


def test_apply_operator_edits_description_none_leaves_original():
    """description=None leaves the original listing_description untouched."""
    p = _payload(listing_description="Condition: Used.\nNo visible defects noted.")
    edited = review.apply_operator_edits(p, price=149.0)
    assert edited.listing_description == p.listing_description


# ── condition enum (Fix 3: selectbox validation) ──────────────────────────────


def test_ebay_condition_values_matches_orchestrator_condition_map():
    """review.EBAY_CONDITION_VALUES covers exactly the orchestrator._CONDITION_MAP
    target enum values (as a set), so the UI selectbox and the free-text mapper
    agree on the canonical eBay condition vocabulary."""
    expected = {enum_value for _, enum_value in orchestrator._CONDITION_MAP}
    assert set(review.EBAY_CONDITION_VALUES) == expected
    # No duplicates in the UI-facing list.
    assert len(review.EBAY_CONDITION_VALUES) == len(set(review.EBAY_CONDITION_VALUES))


# ── validation (PI-009) ───────────────────────────────────────────────────────


def test_validate_passes_with_local_images_no_eps_yet():
    """EPS URLs absent pre-publish is fine when local photos exist (PI-009)."""
    assert review.validate_for_publish(_payload()) == []


def test_validate_flags_missing_category_and_policies():
    problems = review.validate_for_publish(
        _payload(category_id="", fulfillment_policy_id="")
    )
    assert any("category_id" in p for p in problems)
    assert any("fulfillment_policy_id" in p for p in problems)


def test_validate_flags_no_images_at_all():
    """With neither EPS URLs nor local images, the image requirement is flagged."""
    problems = review.validate_for_publish(_payload(local_image_paths=[]))
    assert any("EPS image URL" in p for p in problems)


# ── summary (PI-008) ──────────────────────────────────────────────────────────


def test_review_summary_is_flat_display_dict():
    from src.ai.margin_guard import price_item

    pricing = price_item(_vision(Brand="Sony"), cost=50.0, fees=10.0, active_comps=[200.0])
    summary = review.review_summary(
        _vision(Brand="Sony"), pricing
    )
    assert summary["suggested_price"] == 200.0
    assert summary["active_comp_range"] == (200.0, 200.0)
    assert "missing_inputs" in summary and "reasoning" in summary


# ── AI route selection (T-027 AC1) ────────────────────────────────────────────


def test_build_provider_selects_manual_and_binds_reply_store():
    """AI_PROVIDER=manual yields a ManualProvider over the caller's dict."""
    replies: dict[str, str] = {}
    provider = review.build_provider({"AI_PROVIDER": "manual"}, replies)
    assert isinstance(provider, ManualProvider)
    assert provider.responses is replies
    assert review.provider_mode_label({"AI_PROVIDER": "manual"}).startswith("Manual paste")


@pytest.mark.parametrize("value", ["gemini", "", "openai", None])
def test_build_provider_defaults_to_gemini_without_network(value):
    """Default and unknown values select Gemini; construction makes no call."""
    values = {"AI_PROVIDER": value} if value is not None else {}
    provider = review.build_provider(values, {})
    assert isinstance(provider, GeminiProvider)
    assert review.provider_mode_label(values) == "Gemini API"
    assert review.provider_mode(values) == settings.AI_PROVIDER_GEMINI


# ── Pending item view model (T-027 AC2) ───────────────────────────────────────


def _pending(paths=("/cache/F1/b.jpg", "/cache/F1/a.jpg")):
    """Build a fake orchestrator.PendingManualItem around a real packet."""
    packet = build_packet(list(paths), _EXTRACTION_PROMPT)
    return SimpleNamespace(
        item_sku="LB-F1", folder_name="Headphones", batch_folder_id="F1", packet=packet
    )


def test_pending_item_view_exposes_every_card_field():
    """The view carries SKU, folder, packet ID, prompt, photos, folder, and steps."""
    pending = _pending()
    view = review.pending_item_view(pending)
    assert view.item_sku == "LB-F1"
    assert view.folder_name == "Headphones"
    assert view.batch_folder_id == "F1"
    assert view.packet_id == pending.packet.packet_id
    assert view.prompt_text == pending.packet.prompt_text
    assert view.image_names == ("a.jpg", "b.jpg")
    assert view.image_paths == ("/cache/F1/a.jpg", "/cache/F1/b.jpg")
    assert view.photo_folder.replace("\\", "/").endswith("cache/F1")
    assert len(view.checklist) == 5
    assert view.packet_id in view.prompt_text


# ── Reply normalization and application (T-027 AC3) ───────────────────────────


@pytest.mark.parametrize(
    "raw",
    ["MISMATCH", "mismatch", "**MISMATCH**", "MISMATCH.", "`MISMATCH`", "_Mismatch!_ ", '"MISMATCH"'],
)
def test_normalize_recovers_decorated_mismatch(raw):
    """Markdown emphasis, ticks, quotes, and punctuation do not hide MISMATCH."""
    assert review.normalize_manual_reply(raw) == "MISMATCH"


def test_normalize_leaves_json_and_prose_alone():
    """Anything containing a JSON object, or other prose, passes through stripped."""
    assert review.normalize_manual_reply('  {"a": 1}  ') == '{"a": 1}'
    assert review.normalize_manual_reply("MISMATCH but here is {}") == "MISMATCH but here is {}"
    assert review.normalize_manual_reply("no idea") == "no idea"
    assert review.normalize_manual_reply("The MISMATCH word appears later") == "The MISMATCH word appears later"


def test_normalize_recovers_mismatch_followed_by_explanation():
    """MISMATCH plus the model's own explanation still counts as MISMATCH (critic F12c)."""
    assert review.normalize_manual_reply("MISMATCH — the second photo shows a lamp") == "MISMATCH"
    assert review.normalize_manual_reply("**MISMATCH**: photos do not match the list.") == "MISMATCH"


def test_apply_manual_reply_guards_pathological_and_non_string_input():
    """A RecursionError-class paste and a non-string yield guidance, never a raw exception."""
    replies: dict[str, str] = {}
    provider = ManualProvider(replies)
    pending = _pending()
    deep = '{"a":' * 20000
    result = review.apply_manual_reply(provider, pending.packet, deep)
    assert result.ok is False
    assert "could not be read" in result.message or "not a JSON object" in result.message
    assert replies == {}
    result = review.apply_manual_reply(provider, pending.packet, None)  # type: ignore[arg-type]
    assert result.ok is False
    assert "Paste the model's reply first" in result.message


def test_apply_manual_reply_truncates_operator_controlled_echo():
    """A multi-kilobyte echoed packet_id cannot flood the error box (critic F7),
    and the middle cut keeps this item's own packet ID visible (critic N1)."""
    replies: dict[str, str] = {}
    provider = ManualProvider(replies)
    pending = _pending()
    huge_id = "**bold**" * 600
    result = review.apply_manual_reply(provider, pending.packet, _reply_for(pending.packet, packet_id=huge_id))
    assert result.ok is False
    assert len(result.message) <= review._MESSAGE_MAX_LEN
    assert "…" in result.message
    assert pending.packet.packet_id in result.message
    assert replies == {}


def test_apply_manual_reply_names_route_switch_when_provider_is_not_manual():
    """A Gemini provider (route switched mid-session) yields route guidance (critic C1)."""
    pending = _pending()
    result = review.apply_manual_reply(GeminiProvider(), pending.packet, _reply_for(pending.packet))  # type: ignore[arg-type]
    assert result.ok is False
    assert "no longer manual paste" in result.message
    assert "Setup" in result.message


def _reply_for(packet, **overrides) -> str:
    """A valid reply echoing the packet ID."""
    body = {
        "item_specifics": {"Brand": "Sony"},
        "condition": "Used - Good",
        "defects_found": [],
        "dropped_fields": [],
        "packet_id": packet.packet_id,
    }
    body.update(overrides)
    return json.dumps(body)


def test_apply_manual_reply_success_stores_and_reports():
    """A verified reply is stored under the packet ID with a success message."""
    replies: dict[str, str] = {}
    provider = ManualProvider(replies)
    pending = _pending()
    result = review.apply_manual_reply(provider, pending.packet, _reply_for(pending.packet))
    assert result.ok is True
    assert "re-scanning" in result.message.lower()
    assert set(replies) == {pending.packet.packet_id}


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        ("", "Paste the model's reply first"),
        ("   \n", "Paste the model's reply first"),
        ("**MISMATCH**", "did not match"),
        ("Sure! Here is my analysis of the item.", "not a JSON object"),
        ('{"item_specifics": {}, "condition": "Used", "defects_found": []}', "no 'packet_id'"),
    ],
)
def test_apply_manual_reply_failures_are_readable_and_store_nothing(raw, fragment):
    """Every failure yields plain guidance, no traceback, and an empty store."""
    replies: dict[str, str] = {}
    provider = ManualProvider(replies)
    pending = _pending()
    result = review.apply_manual_reply(provider, pending.packet, raw)
    assert result.ok is False
    assert fragment in result.message
    assert "Traceback" not in result.message
    assert not result.message.startswith(("ValueError", "ManualPacketMismatch"))
    assert replies == {}


def test_apply_manual_reply_wrong_item_names_both_ids_and_stores_nothing():
    """Item A's reply pasted for item B is refused with both IDs named (PI-014)."""
    replies: dict[str, str] = {}
    provider = ManualProvider(replies)
    item_a = _pending()
    item_b = _pending(paths=("/cache/F2/z.jpg",))
    result = review.apply_manual_reply(provider, item_b.packet, _reply_for(item_a.packet))
    assert result.ok is False
    assert item_a.packet.packet_id in result.message
    assert item_b.packet.packet_id in result.message
    assert replies == {}


# ── Reply release after fulfilment (T-026 critic F2 mitigation) ───────────────


def test_release_manual_reply_drops_only_the_fulfilled_item():
    """Releasing by photo paths removes that item's reply and nothing else."""
    replies: dict[str, str] = {}
    provider = ManualProvider(replies)
    item_a = _pending()
    item_b = _pending(paths=("/cache/F2/z.jpg",))
    provider.store_response(item_a.packet, _reply_for(item_a.packet))
    provider.store_response(item_b.packet, _reply_for(item_b.packet))

    assert review.release_manual_reply(replies, list(item_a.packet.image_paths)) is True
    assert set(replies) == {item_b.packet.packet_id}
    assert review.release_manual_reply(replies, list(item_a.packet.image_paths)) is False
    assert review.release_manual_reply(replies, []) is False


def test_existing_image_paths_filters_missing_files(tmp_path):
    """Only files that exist are returned, in the original order."""
    present = tmp_path / "a.jpg"
    present.write_bytes(b"x")
    result = review.existing_image_paths([str(present), str(tmp_path / "missing.jpg")])
    assert result == [str(present)]


def test_review_module_does_not_import_streamlit():
    """review.py stays importable without streamlit installed."""
    from pathlib import Path as _Path

    source = _Path(review.__file__).read_text(encoding="utf-8")
    for line in source.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("import streamlit")
        assert not stripped.startswith("from streamlit")
