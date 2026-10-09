from pathlib import Path

from fd.check import blocking_problems, warnings

SAMPLE = (Path(__file__).parent / "fixtures/report_sample.txt").read_text(encoding="utf-8")
GOOD = SAMPLE + "\n━━━━━\n\n▊▊▊🔗 影片來源 ▊▊▊\n☞ 影片1. 範例節目｜範例頻道 A\n"


def test_good_report_passes():
    assert blocking_problems(GOOD, "2026-10-03") == [] and warnings(GOOD) == []


def test_blocks_wrong_title_date_missing_sources_and_simplified():
    assert any("標題日期" in p for p in blocking_problems(GOOD, "2026-10-04"))
    assert any("第一行" in p for p in blocking_problems("前言\n" + GOOD))
    assert any("影片來源" in p for p in blocking_problems(SAMPLE))      # 回覆中途中斷
    assert any("簡體字" in p and "时" in p for p in blocking_problems(GOOD + "这个时间點"))
    assert "非繁體中文為主" in blocking_problems("This report is written in English. " * 30)


def test_truncated_analyst_markdown_and_urls_are_only_warnings():
    truncated = GOOD.replace("・態度：偏空｜信心：低\n", "")
    assert blocking_problems(truncated, "2026-10-03") == []
    assert any("截斷" in w for w in warnings(truncated))
    w = warnings(GOOD + "\n## 小標\n**粗體** https://youtu.be/x")
    assert any("Markdown" in x for x in w) and any("網址" in x for x in w)
