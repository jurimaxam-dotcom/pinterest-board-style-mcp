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
