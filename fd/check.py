"""報告格式與截斷檢查（移植自 finance-digest-a 的 check.py；代號比對不搬，Gemini Notebook 已依提示詞處理）。"""
from __future__ import annotations

import re

TITLE = re.compile(r"^📅 (\d{4})/(\d{2})/(\d{2}) \(星期[一二三四五六日]\) 財經節目綜合摘要$")
REQUIRED = ("▊▊▊📌 今日焦點 ▊▊▊", "▊▊▊👤 分析師重點 ▊▊▊", "▊▊▊🔗 影片來源 ▊▊▊")
# 常見的簡體字（繁體寫法不同者）；報告是給台灣親友看的
SIMPLIFIED = set("时们这说为发应经实动后过个来对会报价产业买卖涨张长门问间关开东车万与当没现进种头样让从内网电亿汇钱银币观点资")


def blocking_problems(text: str, day: str | None = None) -> list[str]:
    """有任何一項就不發布（ToDo.md 第 3 節第 1 步）。day（YYYY-MM-DD）有給時，標題日期必須相同。"""
    problems = []
    if len(text.strip()) < 200:
        problems.append("內容太短")
    cjk = len(re.findall(r"[一-鿿]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if cjk / max(cjk + latin, 1) < 0.6:
        problems.append("非繁體中文為主")
    m = TITLE.match(text.lstrip().splitlines()[0] if text.strip() else "")
    if not m:
        problems.append("第一行不是「📅 yyyy/MM/dd (星期X) 財經節目綜合摘要」")
    elif day and "-".join(m.groups()) != day:
        problems.append(f"標題日期 {'-'.join(m.groups())} 與檔名 {day} 不同")
    problems += [f"缺少章節：{h}" for h in REQUIRED if h not in text]
    found = sorted({ch for ch in text if ch in SIMPLIFIED})
    if found:
        problems.append("含簡體字：" + "".join(found))
    return problems


def warnings(text: str) -> list[str]:
    """只印出、不擋發布：報告已經存檔，內容一字不改，網站照原文顯示（parse 不到的部分用原文）。"""
    problems = []
    if re.search(r"^\s*(#{1,6}\s|[*-]\s|>\s)", text, re.M) or "**" in text:
        problems.append("含 Markdown 符號")
    if re.search(r"https?://|youtu\.?be|youtube\.com", text):
        problems.append("含網址")
    # 被截斷時，最後一位分析師通常缺「態度」那一行
    blocks = re.split(r"^👤 ", text.split("▊▊▊👤 分析師重點 ▊▊▊")[-1], flags=re.M)[1:]
    for b in blocks:
        if "・態度：" not in b:
            problems.append(f"分析師區塊可能被截斷：{b.splitlines()[0][:20]}")
    return problems
