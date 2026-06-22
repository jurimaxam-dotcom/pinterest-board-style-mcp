#!/usr/bin/env python3
"""Test-Gate (stdlib unittest, KEIN Netz): fetch_board + validate_tokens + mcp_server.

Deterministisch ueber eine RSS-Fixture (tests/fixtures/board.rss) und die committeten
Beispiel-Tokens. Live-Fetch wird hier NICHT getestet (das ist die manuelle End-to-End-Pruefung).
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import fetch_board as fb           # noqa: E402
import validate_tokens as vt       # noqa: E402
import mcp_server as srv           # noqa: E402

FIXTURE = (REPO / "tests" / "fixtures" / "board.rss").read_text(encoding="utf-8")
GOOD_TOKENS = REPO / "examples" / "homedepot-bath-ideas-and-inspiration.tokens.json"
RICH_TOKENS = REPO / "tests" / "fixtures" / "rich.tokens.json"


class TestUrlDerivation(unittest.TestCase):
    def test_board_url_to_rss_and_slug(self):
        rss, slug = fb.derive_rss_and_slug("https://www.pinterest.com/testuser/test-board/")
        self.assertEqual(rss, "https://www.pinterest.com/testuser/test-board.rss")
        self.assertEqual(slug, "testuser-test-board")

    def test_already_rss_url(self):
        rss, slug = fb.derive_rss_and_slug("https://www.pinterest.com/testuser/test-board.rss")
        self.assertEqual(rss, "https://www.pinterest.com/testuser/test-board.rss")
        self.assertEqual(slug, "testuser-test-board")

    def test_invalid_url_raises(self):
        with self.assertRaises(fb.FetchError):
            fb.derive_rss_and_slug("https://example.com/not-a-board")


class TestImageUrl(unittest.TestCase):
    def test_upgrade_size_segment(self):
        raw = "https://i.pinimg.com/236x/ab/cd/ef/0123456789abcdef0123456789ab01.jpg"
        self.assertEqual(
            fb.upgrade_image_url(raw, "1200x"),
            "https://i.pinimg.com/1200x/ab/cd/ef/0123456789abcdef0123456789ab01.jpg",
        )

    def test_non_pinimg_unchanged(self):
        url = "https://example.com/img.jpg"
        self.assertEqual(fb.upgrade_image_url(url, "1200x"), url)

    def test_extract_none_when_no_image(self):
        self.assertIsNone(fb.extract_image_url(None))
        self.assertIsNone(fb.extract_image_url("kein Bild hier"))


class TestParseItems(unittest.TestCase):
    def test_parses_three_items(self):
        items = fb.parse_items(FIXTURE)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["pin_title"], "Pin One")
        self.assertEqual(items[0]["pin_link"], "https://www.pinterest.com/pin/111/")
        self.assertEqual(
            items[0]["image_url_raw"],
            "https://i.pinimg.com/236x/ab/cd/ef/0123456789abcdef0123456789ab01.jpg",
        )

    def test_doctype_rejected_xxe_guard(self):
        evil = '<?xml version="1.0"?><!DOCTYPE rss [<!ENTITY x "y">]><rss><channel></channel></rss>'
        with self.assertRaises(fb.FetchError):
            fb.parse_items(evil)

    def test_malformed_xml_raises(self):
        with self.assertRaises(fb.FetchError):
            fb.parse_items("<rss><channel><item></rss>")


class TestValidator(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(GOOD_TOKENS.read_text(encoding="utf-8"))

    def test_good_tokens_pass(self):
        self.assertEqual(vt.validate(self.doc), [])

    def test_bad_hex_fails(self):
        self.doc["color"]["accent"]["$value"] = "not-a-hex"
        self.assertTrue(vt.validate(self.doc))

    def test_bad_enum_fails(self):
        self.doc["$extensions"]["boardStyle"]["temperature"] = "lauwarm"
        self.assertTrue(vt.validate(self.doc))

    def test_missing_role_fails(self):
        del self.doc["color"]["primary"]
        self.assertTrue(vt.validate(self.doc))


class TestValidatorRichFields(unittest.TestCase):
    """Stufe-1-Felder sind additiv/optional: vorhanden -> validiert; fehlend -> egal."""
    def setUp(self):
        self.doc = json.loads(RICH_TOKENS.read_text(encoding="utf-8"))

    def test_rich_tokens_pass(self):
        self.assertEqual(vt.validate(self.doc), [])

    def test_minimal_tokens_without_rich_fields_still_pass(self):
        self.assertEqual(vt.validate(json.loads(GOOD_TOKENS.read_text(encoding="utf-8"))), [])

    def test_bad_accent_hex_fails(self):
        self.doc["$extensions"]["boardStyle"]["accentPalette"][0]["$value"] = "xyz"
        self.assertTrue(vt.validate(self.doc))

    def test_bad_motif_role_fails(self):
        self.doc["$extensions"]["boardStyle"]["motifs"][0]["uiRole"] = "bogus"
        self.assertTrue(vt.validate(self.doc))

    def test_bad_image_role_fails(self):
        self.doc["$extensions"]["boardStyle"]["imageRoles"]["01"] = ["not-a-role"]
        self.assertTrue(vt.validate(self.doc))

    def test_bad_webfont_role_fails(self):
        self.doc["$extensions"]["boardStyle"]["webfonts"][0]["role"] = "footer"
        self.assertTrue(vt.validate(self.doc))

    def test_bad_edgecolor_hex_fails(self):
        self.doc["$extensions"]["boardStyle"]["edgeColors"]["01"]["top"] = "nope"
        self.assertTrue(vt.validate(self.doc))


class TestInstructionRichFields(unittest.TestCase):
    def test_instruction_requests_new_fields(self):
        for kw in ("accentPalette", "webfonts", "motifs", "imageRoles", "edgeColors"):
            self.assertIn(kw, srv.INSTRUCTION, f"INSTRUCTION verlangt '{kw}' nicht")

    def test_render_instruction_survives_literal_braces(self):
        # Regression: INSTRUCTION enthaelt literale JSON-{...} -> .format() crasht mit KeyError.
        out = srv.render_instruction(7, "demo-board", "/cache/demo-board")
        self.assertIn("7", out)
        self.assertIn("demo-board", out)
        self.assertIn("/cache/demo-board", out)
        self.assertIn("webfonts", out)           # literale Klammern muessen ueberleben
        self.assertNotIn("{count}", out)
        self.assertNotIn("{slug}", out)
        self.assertNotIn("{cache}", out)


class TestShortUrl(unittest.TestCase):
    def test_is_short_url_pinit(self):
        self.assertTrue(fb.is_short_url("https://pin.it/7KaLebnvd"))

    def test_full_board_url_not_short(self):
        self.assertFalse(fb.is_short_url("https://www.pinterest.com/user/board/"))

    def test_resolve_short_url_follows_and_strips_query(self):
        class _Resp:
            def __enter__(self_): return self_
            def __exit__(self_, *a): return False
            def geturl(self_): return "https://www.pinterest.com/kvdwerf/meubels/?utm_source=share"
        out = fb.resolve_short_url("https://pin.it/x", _opener=lambda req, timeout=None: _Resp())
        self.assertEqual(out, "https://www.pinterest.com/kvdwerf/meubels/")

    def test_resolved_shortlink_then_derives_board(self):
        rss, slug = fb.derive_rss_and_slug("https://www.pinterest.com/kvdwerf/meubels/")
        self.assertEqual(slug, "kvdwerf-meubels")


class TestPinLinkMessage(unittest.TestCase):
    def test_single_pin_url_gives_clear_error(self):
        with self.assertRaises(fb.FetchError) as ctx:
            fb.derive_rss_and_slug("https://www.pinterest.com/pin/123456789/")
        self.assertIn("Pin", str(ctx.exception))


class TestMcpProtocol(unittest.TestCase):
    def test_initialize_echoes_protocol(self):
        r = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(r["result"]["serverInfo"]["name"], "pinterest-board-style")
        self.assertEqual(r["result"]["protocolVersion"], "2025-06-18")

    def test_tools_list(self):
        r = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual([t["name"] for t in r["result"]["tools"]], ["get_board_style"])

    def test_unknown_tool_errors(self):
        r = srv.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": "nope", "arguments": {}}})
        self.assertEqual(r["error"]["code"], -32602)

    def test_notification_no_response(self):
        self.assertIsNone(srv.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_ping(self):
        r = srv.handle({"jsonrpc": "2.0", "id": 4, "method": "ping"})
        self.assertEqual(r["result"], {})

    def test_tool_call_missing_arg_is_error(self):
        # kein Netz: fehlende board_url -> ValueError -> isError, bevor irgendein Fetch passiert
        r = srv.handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                        "params": {"name": "get_board_style", "arguments": {}}})
        self.assertTrue(r["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
