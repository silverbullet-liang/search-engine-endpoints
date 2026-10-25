#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线自查：用 samples/async-fragment.html 验证解析器行为。不联网。

    python3 test/test_parse.py
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "examples"))

import parse_images  # noqa: E402

SAMPLE = os.path.join(ROOT, "samples", "async-fragment.html")


def load():
    with open(SAMPLE, encoding="utf-8") as f:
        return f.read()


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.raw = load()

    def test_count(self):
        self.assertEqual(len(parse_images.parse(self.raw)), 3)

    def test_field_mapping(self):
        it = parse_images.parse(self.raw)[0]
        self.assertEqual(it["cid"], "AAAABBBB")
        self.assertEqual(it["page_url"], "https://example.com/article/1")
        self.assertEqual(it["image_url"], "https://cdn.example.com/photos/1.jpg")
        self.assertEqual(it["title"], "示例图片一")
        self.assertEqual(len(it["md5"]), 32)

    def test_html_unescape(self):
        # turl 里是 &amp;pid=15.1，必须还原成 &pid=15.1
        it = parse_images.parse(self.raw)[0]
        self.assertIn("&pid=15.1", it["thumbnail_url"])
        self.assertNotIn("&amp;", it["thumbnail_url"])

    def test_pua_stripped_by_default(self):
        it = parse_images.parse(self.raw)[1]
        self.assertEqual(it["desc"], "示例图片二的描述文本")
        self.assertNotIn("\ue000", it["desc"])
        self.assertNotIn("\ue001", it["desc"])

    def test_pua_to_mark(self):
        it = parse_images.parse(self.raw, mark=True)[1]
        self.assertEqual(it["desc"], "示例<mark>图片</mark>二的描述文本")

    def test_explicit_host_preserved(self):
        it = parse_images.parse(self.raw)[2]
        self.assertIn("ts3.explicit.bing.net", it["thumbnail_url"])

    def test_dedupe(self):
        items = parse_images.parse(self.raw)
        doubled = items + items
        self.assertEqual(len(parse_images.dedupe(doubled, "md5")), 3)
        self.assertEqual(len(parse_images.dedupe(doubled, "cid")), 3)

    def test_bad_json_skipped(self):
        broken = '<a class="iusc" m="{&quot;cid&quot;:&quot;X&quot;,}"></a>'
        self.assertEqual(parse_images.parse(broken), [])

    def test_no_match_returns_empty(self):
        self.assertEqual(parse_images.parse("<html><body>nothing</body></html>"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
