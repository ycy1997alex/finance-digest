import json

from fd.guard import check_public_tree
from fd.website import build_site
from test_website import PW, store_reports


def test_clean_tree_passes(tmp_path):
    store_reports(tmp_path, [("2026-10-02", "complete")])
    build_site(tmp_path / "data", tmp_path / "docs", PW)
    (tmp_path / "data/processed.json").write_text("{}", encoding="utf-8")
    assert check_public_tree(tmp_path) == []


def test_plaintext_report_or_unknown_file_is_caught(tmp_path):
    store_reports(tmp_path, [("2026-10-02", "complete")])
    build_site(tmp_path / "data", tmp_path / "docs", PW)
    (tmp_path / "data/reports/2026-10-03.txt").write_text("📅 明文報告", encoding="utf-8")
    (tmp_path / "docs/data/r/2026-10-04.enc").write_text(json.dumps({"text": "明文"}), encoding="utf-8")
    (tmp_path / "docs/notes.html").write_text("<p>明文</p>", encoding="utf-8")
    problems = check_public_tree(tmp_path)
    assert any("2026-10-03.txt" in p for p in problems)
    assert any("2026-10-04.enc" in p for p in problems)
    assert any("notes.html" in p for p in problems)


def test_modified_site_shell_is_caught(tmp_path):
    store_reports(tmp_path, [("2026-10-02", "complete")])
    build_site(tmp_path / "data", tmp_path / "docs", PW)
    shell = tmp_path / "docs/index.html"
    shell.write_text(shell.read_text(encoding="utf-8").replace("</body>", "<p>今日焦點：明文</p></body>"), encoding="utf-8")
    assert any("index.html" in p for p in check_public_tree(tmp_path))
