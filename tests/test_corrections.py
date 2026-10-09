import pytest

from fd.corrections import apply, load, write_corrected
from fd.render import parse_report

TABLE = {
    "text": {"黃風凱": "黃豐凱"},
    "analysts": {"艾綸": "劉育綸", "劉育綸（艾綸）": "劉育綸"},
    "channels": {"EP703 ｜ 🏈（Gooaye 股癌）": "Gooaye 股癌"},
}
TEXT = "\n".join([
    "📅 2026/10/02 (星期五) 財經節目綜合摘要", "",
    "▊▊▊📌 今日焦點 ▊▊▊", "・台股創高。",
    "▊▊▊📢 總體經濟與市場環境 ▊▊▊",
    "・艾綸指出，融資創高。",
    "・美債殖利率走高（游庭皓、艾綸）。",
    "▊▊▊📈 一致看多 ▊▊▊", "【個股】", "○ 國巨（2327）｜看多者：林漢偉、艾綸",
    "▊▊▊⚖️ 主要分歧 ▊▊▊", "・記憶體", "▽ 艾綸：看多。", "▽ 黃風凱：偏空。",
    "▊▊▊👤 分析師重點 ▊▊▊",
    "👤 艾綸｜頻道：艾綸說、兆華艾綸說", "・態度：看多｜信心：高",
    "👤 劉育綸（艾綸）｜頻道：兆華艾綸說", "・態度：看多｜信心：中",
    "👤 謝孟恭｜頻道：EP703 ｜ 🏈（Gooaye 股癌）、Gooaye 股癌", "・態度：偏多｜信心：中",
    "▊▊▊🔗 影片來源 ▊▊▊", "☞ 影片1. 劉育綸 艾綸說【10月開跑】｜艾綸說", "☞ 影片2. 黃風凱來賓｜理財達人秀",
    "☞ 影片3. 【兆華艾綸說】迎五萬｜李兆華、艾綸、張林忠2026.10.06｜兆華艾綸說",
])


def test_analyst_alias_changes_names_but_not_channel_names():
    out, done = apply(TEXT, TABLE)
    assert "👤 劉育綸｜頻道：艾綸說、兆華艾綸說" in out                  # 頻道名「艾綸說」不被改成「劉育綸說」
    assert out.count("👤 劉育綸｜") == 2                               # 「劉育綸（艾綸）」整個換掉，沒被切成「劉育綸（劉育綸）」
    assert "・劉育綸指出" in out and "（游庭皓、劉育綸）" in out and "看多者：林漢偉、劉育綸" in out and "▽ 劉育綸：" in out
    assert "☞ 影片1. 劉育綸 艾綸說【10月開跑】｜艾綸說" in out          # 影片標題裡的「艾綸說」不動
    assert "｜李兆華、艾綸、張林忠2026.10.06｜" in out                   # 影片來源是 YouTube 原始標題，別名不改
    assert any("艾綸 → 劉育綸" in d for d in done)


def test_text_and_channel_corrections():
    out, done = apply(TEXT, TABLE)
    assert "黃風凱" not in out and "▽ 黃豐凱：" in out and "黃豐凱來賓" in out
    assert "👤 謝孟恭｜頻道：Gooaye 股癌\n" in out                       # 改完重複的頻道合併
    assert any("頻道" in d for d in done)


def test_corrected_text_merges_analysts_for_tracking():
    names = [a["name"] for a in parse_report(apply(TEXT, TABLE)[0])["analysts"]]
    assert names == ["劉育綸", "劉育綸", "謝孟恭"]


def test_load_missing_file_means_no_corrections(tmp_path):
    table = load(tmp_path / "none.yaml")
    assert apply(TEXT, table) == (TEXT, [])


def test_load_rejects_bad_table(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("analysts:\n  艾綸:\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load(p)
    p.write_text("names:\n  a: b\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load(p)


def test_write_corrected_keeps_name_and_skips_unchanged(tmp_path):
    original = tmp_path / "reports/2026-10-02_Fri.txt"
    out = write_corrected(original, "校正後\n", tmp_path / "corrected_reports")
    assert out.name == original.name and out.read_text(encoding="utf-8") == "校正後\n"
    before = out.stat().st_mtime_ns
    write_corrected(original, "校正後\n", tmp_path / "corrected_reports")
    assert out.stat().st_mtime_ns == before                              # 內容沒變就不重寫


def test_repo_table_loads():
    table = load()
    assert table["analysts"]["艾綸"] == "劉育綸"
