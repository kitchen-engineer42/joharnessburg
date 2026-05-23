"""Tests for scripts/parse_govcn_html.py."""

import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import run_script


GOVCN_FIXTURE = """\
<html>
<head><title>测试法规</title></head>
<body>
  <div class="header">
    <a href="#">字号:</a> <a href="#">大</a> | <a href="#">中</a> | <a href="#">小</a>
  </div>
  <div id="UCAP-CONTENT">
    <p>第一章 总则</p>
    <p>第一条 为了规范测试法规的实施，制定本办法。</p>
    <p>第二条 本办法适用于所有测试场景。</p>
    <p>第二章 具体规定</p>
    <p>第三条 测试机构应当按照本办法执行测试任务。</p>
  </div>
  <div class="footer">
    <a href="#">返回</a> <a href="#">打印</a> <a href="#">分享</a>
  </div>
</body>
</html>
"""


class TestParseGovcnHtml(unittest.TestCase):
    def test_parses_ucap_content_container(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            src = tdp / "reg.html"
            src.write_text(GOVCN_FIXTURE, encoding="utf-8")
            out_dir = tdp / "parsed"

            rc, out, err = run_script(
                "parse_govcn_html.py", str(src), str(out_dir)
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])

            doc_md = Path(out["doc_md"]).read_text()
            # Chapter heading converted
            self.assertIn("## 第一章 总则", doc_md)
            self.assertIn("## 第二章 具体规定", doc_md)
            # Article headings converted
            self.assertIn("### 第一条", doc_md)
            self.assertIn("### 第二条", doc_md)
            self.assertIn("### 第三条", doc_md)
            # Article body preserved
            self.assertIn("为了规范测试法规的实施", doc_md)
            # Noise filtered out
            self.assertNotIn("字号", doc_md)
            self.assertNotIn("返回", doc_md)
            self.assertNotIn("打印", doc_md)
            # Metadata correct
            self.assertEqual(out["chapter_count"], 2)
            self.assertEqual(out["article_count"], 3)

    def test_errors_when_no_known_container(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            src = tdp / "plain.html"
            src.write_text(
                "<html><body><div>just some HTML with no gov.cn container</div></body></html>",
                encoding="utf-8",
            )
            out_dir = tdp / "parsed"

            rc, out, _ = run_script(
                "parse_govcn_html.py", str(src), str(out_dir)
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            self.assertIn("container", out["error"].lower())

    def test_errors_on_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, _ = run_script(
                "parse_govcn_html.py",
                str(tdp / "nope.html"),
                str(tdp / "out"),
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])

    def test_refuses_to_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            src = tdp / "reg.html"
            src.write_text(GOVCN_FIXTURE, encoding="utf-8")
            out_dir = tdp / "parsed"

            rc, _, _ = run_script("parse_govcn_html.py", str(src), str(out_dir))
            self.assertEqual(rc, 0)

            rc, out, _ = run_script("parse_govcn_html.py", str(src), str(out_dir))
            self.assertEqual(rc, 1)
            self.assertIn("force", out["error"].lower())

            rc, _, _ = run_script(
                "parse_govcn_html.py", str(src), str(out_dir), "--force"
            )
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
