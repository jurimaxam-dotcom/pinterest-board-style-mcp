#!/usr/bin/env python3
"""Test-Gate (stdlib unittest, KEIN Netz): fetch_board + validate_tokens + mcp_server.

Deterministisch ueber eine RSS-Fixture (tests/fixtures/board.rss) und die committeten
Beispiel-Tokens. Live-Fetch wird hier NICHT getestet (das ist die manuelle End-to-End-Pruefung).
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import board_assets as ba         # noqa: E402
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


class TestSharedAssetPipeline(unittest.TestCase):
    def test_runtime_mode_returns_bytes(self):
        with patch("board_assets.http_get", side_effect=[FIXTURE, b"img-1", b"img-2", b"img-3"]):
            assets = ba.fetch_board_assets(
                "https://www.pinterest.com/testuser/test-board/",
                max_images=3,
                size="1200x",
                mode="runtime",
            )
        self.assertEqual(assets["image_count"], 3)
        self.assertTrue(all(img["data"] for img in assets["images"]))
        self.assertTrue(all(img["path"] is None for img in assets["images"]))

    def test_temp_mode_writes_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("board_assets.http_get", side_effect=[FIXTURE, b"img-1", b"img-2", b"img-3"]):
                assets = ba.fetch_board_assets(
                    "https://www.pinterest.com/testuser/test-board/",
                    max_images=3,
                    size="1200x",
                    mode="temp",
                    temp_dir=tmp,
                )
            self.assertEqual(assets["image_count"], 3)
            for img in assets["images"]:
                self.assertTrue(Path(img["path"]).exists())

    def test_mcp_tool_writes_export_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("mcp_server.CACHE_ROOT", Path(tmp) / "cache"):
                with patch("board_assets.http_get", side_effect=[FIXTURE, b"img-1", b"img-2", b"img-3"]):
                    output = srv.tool_get_board_style(
                        {
                            "board_url": "https://www.pinterest.com/testuser/test-board/",
                            "max_images": 3,
                            "export_format": "design-system",
                            "export_dir": tmp,
                        }
                    )
            self.assertTrue(any(item.get("type") == "text" and "Export gespeichert" in item.get("text", "") for item in output))
            self.assertTrue(Path(tmp, "images", "01.jpg").exists())
            self.assertTrue(Path(tmp, "embeddable-images.json").exists())

    def test_export_bundle_contains_no_invented_tokens(self):
        """Das Bundle darf nur Echtes liefern: keine Slug-Hash-Palette, keine erfundenen
        Radius-Werte, kein styles.css, das nur erfundene Tokens importiert. Echte Tokens
        entstehen erst NACH der Analyse (build_style_skill.py)."""
        with tempfile.TemporaryDirectory() as tmp:
            with patch("mcp_server.CACHE_ROOT", Path(tmp) / "cache"):
                with patch("board_assets.http_get", side_effect=[FIXTURE, b"img-1", b"img-2", b"img-3"]):
                    srv.tool_get_board_style(
                        {
                            "board_url": "https://www.pinterest.com/testuser/test-board/",
                            "max_images": 3,
                            "export_format": "design-system",
                            "export_dir": tmp,
                        }
                    )
            self.assertFalse(Path(tmp, "tokens").exists(), "tokens/ mit erfundener Palette darf nicht existieren")
            self.assertFalse(Path(tmp, "styles.css").exists(), "styles.css importiert nur erfundene Tokens")
            skill_md = Path(tmp, "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("tokens/", skill_md, "SKILL.md darf nicht auf nicht-existente tokens/ verweisen")
            readme = Path(tmp, "readme.md").read_text(encoding="utf-8")
            self.assertNotIn("tokens/", readme, "readme darf nicht auf nicht-existente tokens/ verweisen")

    def test_mcp_tool_uses_sandbox_root_when_export_dir_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            with patch("mcp_server.discover_sandbox_root", return_value=sandbox):
                with patch("mcp_server.CACHE_ROOT", Path(tmp) / "cache"):
                    with patch("board_assets.http_get", side_effect=[FIXTURE, b"img-1", b"img-2", b"img-3"]):
                        srv.tool_get_board_style(
                            {
                                "board_url": "https://www.pinterest.com/testuser/test-board/",
                                "max_images": 3,
                                "export_format": "design-system",
                            }
                        )
            self.assertTrue((sandbox / "testuser-test-board" / "design-system" / "images" / "01.jpg").exists())

    def test_mcp_tool_auto_exports_style_skill_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            with patch("mcp_server.discover_sandbox_root", return_value=sandbox):
                with patch("mcp_server.CACHE_ROOT", Path(tmp) / "cache"):
                    with patch("board_assets.http_get", side_effect=[FIXTURE, b"img-1", b"img-2", b"img-3"]):
                        output = srv.tool_get_board_style(
                            {
                                "board_url": "https://www.pinterest.com/testuser/test-board/",
                                "max_images": 3,
                            }
                        )
            target = sandbox / "testuser-test-board" / "style-skill"
            self.assertTrue((target / "images" / "01.jpg").exists())
            self.assertTrue((target / "SKILL.md").exists())
            self.assertTrue(any(str(target) in item.get("text", "") for item in output if item.get("type") == "text"))

    def test_mcp_tool_writes_embeddable_data_uri_manifest_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            with patch("mcp_server.discover_sandbox_root", return_value=sandbox):
                with patch("mcp_server.CACHE_ROOT", Path(tmp) / "cache"):
                    with patch("board_assets.http_get", side_effect=[FIXTURE, b"img-1", b"img-2", b"img-3"]):
                        output = srv.tool_get_board_style(
                            {
                                "board_url": "https://www.pinterest.com/testuser/test-board/",
                                "max_images": 3,
                            }
                        )
            manifest = sandbox / "testuser-test-board" / "style-skill" / "embeddable-images.json"
            self.assertTrue(manifest.exists())
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["images"][0]["file"], "01.jpg")
            self.assertEqual(data["images"][0]["src"], "data:image/jpeg;base64,aW1nLTE=")
            self.assertEqual(data["images"][0]["css"], "background-image: url('data:image/jpeg;base64,aW1nLTE=');")
            text = "\n".join(item.get("text", "") for item in output if item.get("type") == "text")
            self.assertIn("EMBEDDABLE_IMAGE_SOURCES", text)
            self.assertIn(str(manifest), text)
            self.assertNotIn('src="data:image/jpeg;base64,aW1nLTE="', text)


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

    def test_export_dir_description_names_sandbox_default(self):
        tool = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"][0]
        desc = tool["inputSchema"]["properties"]["export_dir"]["description"]
        self.assertIn("Claude-sichtbarer Sandbox-/Upload-Pfad", desc)
        self.assertNotIn("~/.cache/pinterest-board-style", desc)

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
