from pathlib import Path

from fd.render import line_short, parse_report

SAMPLE = (Path(__file__).parent / "fixtures/report_sample.txt").read_text(encoding="utf-8")
URL = "https://ycy1997alex.github.io/finance-digest/2026-10-03/"


def test_parse_sections():
    r = parse_report(SAMPLE)
    assert r["parse_ok"]
    assert r["title"] == "📅 2026/10/03 (星期六) 財經節目綜合摘要"
    assert len(r["focus"]) == 2
    assert r["macro"][0]["who"] == ["王大明"] and r["macro"][0]["text"].startswith("指出，")
    assert r["macro"][1]["who"] == ["王大明", "李小華"]
    assert r["macro"][2]["who"] == []
    bull = r["consensus"]["bull"]
    assert bull["ind"] == [{"name": "AI 伺服器", "who": ["王大明", "李小華"]}]
    assert bull["stk"] == [{"name": "台積電", "code": "2330", "who": ["王大明", "李小華"]}]
    assert r["consensus"]["bear"] == {"ind": [], "stk": []}
    assert r["divergences"] == [{"topic": "國巨後市看法", "sides": [
        {"who": "王大明", "text": "看多，被動元件報價第四季調漲。"},
        {"who": "李小華", "text": "偏空，漲價題材已反映。"}]}]


def test_parse_analysts_and_stocks():
    a, b = parse_report(SAMPLE)["analysts"]
    assert a["name"] == "王大明" and a["channels"] == ["範例頻道 A", "範例頻道 B"]
    assert a["attitude"] == "偏多" and a["confidence"] == "中"
    assert a["fields"]["關鍵時程"] == "10/15：台積電法說會；11/05：聯準會利率決議"
    assert a["stocks"][0] == {"name": "台積電", "code": "2330", "attitude": "看多", "confidence": "高",
                              "horizon": "未來一季", "reason": "先進製程能見度看到明年上半年，預估毛利率 58%。",
                              "chain": "先進製程 → 中游製造"}
    assert a["stocks"][1]["chain"] == ""
    assert b["stocks"][1]["code"] is None and b["stocks"][1]["name"] == "明基材"


def test_tolerates_format_variants_seen_in_real_outputs():
    text = "\n".join([
        "📅 2026/09/18 (星期五) 財經節目綜合摘要", "",
        "▊▊▊📌 今日焦點 ▊▊▊",
        "台股暴漲 892 點，一舉站上 47,000 點大關。",                 # 沒有「・」的整段焦點
        "▊▊▊📢 總體經濟與市場環境 ▊▊▊",
        "・陳豐進：外銷訂單創新高。",                                 # 名字＋冒號
        "・美股與利率環境：殖利率逼近 5%。",                          # 冒號前是主題，不是人名
        "・油價回到 95 美元，通膨降溫放緩。（陳豐進、謝孟恭）",       # 名字放在句尾括號
        "・融資餘額創高，個股輪動（陳豐進、謝孟恭）。",               # 句號在括號後（Gemini Notebook 2026-10-05）
        "▊▊▊📈 一致看多 ▊▊▊", "【個股】", "○ 台積電（2330） ｜ 看多者：陳豐進、謝孟恭",
        "▊▊▊👤 分析師重點 ▊▊▊",
        "👤 謝孟恭 ｜ 頻道：Gooaye 股癌",                             # ｜ 前後有空白
        "・態度：看多｜信心：高",
        "★欣興（3037） ｜ 偏多 ｜ 信心（中） ｜ 中長線",
        "👤 陳豐進｜頻道：元大看盤室", "・態度：看多｜信心：高",
    ])
    r = parse_report(text)
    assert r["parse_ok"] and r["focus"] == ["台股暴漲 892 點，一舉站上 47,000 點大關。"]
    assert [m["who"] for m in r["macro"]] == [["陳豐進"], [], ["陳豐進", "謝孟恭"], ["陳豐進", "謝孟恭"]]
    assert r["macro"][0]["text"] == "外銷訂單創新高。" and r["macro"][2]["text"] == "油價回到 95 美元，通膨降溫放緩。"
    assert r["macro"][3]["text"] == "融資餘額創高，個股輪動。"
    assert r["consensus"]["bull"]["stk"] == [{"name": "台積電", "code": "2330", "who": ["陳豐進", "謝孟恭"]}]
    assert r["analysts"][0]["name"] == "謝孟恭" and r["analysts"][0]["stocks"][0]["attitude"] == "偏多"


def test_unparseable_text_falls_back_to_raw():
    r = parse_report("模型輸出了一段完全不照格式的文字")
    assert not r["parse_ok"] and r["raw"].startswith("模型輸出")


def test_line_short_keeps_four_sections_and_link():
    text = line_short(SAMPLE, URL)
    assert "▊▊▊📌 今日焦點 ▊▊▊" in text and "▊▊▊⚖️ 主要分歧 ▊▊▊" in text
    assert "分析師重點" not in text and "★" not in text
    assert text.rstrip().endswith("AI 自動摘要，非投資建議。") and URL in text


def test_line_short_marks_missing_programs():
    text = line_short(SAMPLE, URL, missing=["範例頻道 F（直播尚未結束）"])
    assert text.splitlines()[2] == "【本期缺漏】範例頻道 F（直播尚未結束）"


def test_line_short_trims_macro_to_fit_one_message():
    long = SAMPLE.replace("▊▊▊📈 一致看多 ▊▊▊", "\n".join(f"・王大明指出，第 {i} 點" + "很長的說明" * 40 for i in range(30)) + "\n\n▊▊▊📈 一致看多 ▊▊▊")
    text = line_short(long, URL)
    assert len(text) <= 5000
    assert "▊▊▊📈 一致看多 ▊▊▊" in text and "▊▊▊⚖️ 主要分歧 ▊▊▊" in text  # 刪的是總經，不是共識與分歧
