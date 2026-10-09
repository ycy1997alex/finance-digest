"""把報告純文字解析成網站用的結構，並產出 LINE 精簡版（移植自 finance-digest-a）。

解析失敗（parse_ok 為 False）時網站改顯示原文，不擋發布。所有欄位都是模型輸出的文字，
放進網頁前一律轉義（網站那一側負責）。
"""
from __future__ import annotations

import re

LINE_LIMIT = 5000   # LINE 單則訊息字數上限

_HEADER = re.compile(r"^▊▊▊\s*(.+?)\s*▊▊▊\s*$")
_SECTION_KEYS = (("今日焦點", "focus"), ("總體經濟", "macro"), ("一致看多", "bull"), ("一致看空", "bear"),
                 ("主要分歧", "diverge"), ("分析師重點", "analysts"), ("影片來源", "sources"))
_VERBS = ("指出", "表示", "認為", "提到", "分析", "強調", "說明", "預估", "觀察", "警示", "引述", "提醒", "看好", "建議")


def _sections(text: str) -> tuple[str, dict[str, list[str]]]:
    lines = text.splitlines()
    title = next((l.strip() for l in lines if l.strip()), "")
    out, key = {}, None
    for raw in lines:
        line = raw.strip()
        m = _HEADER.match(line)
        if m:
            key = next((k for word, k in _SECTION_KEYS if word in m.group(1)), None)
            if key:
                out.setdefault(key, [])
        elif key and line and not set(line) <= {"━"}:
            out[key].append(line)
    return (title if title.startswith("📅") else ""), out


def _bullets(lines: list[str]) -> list[str]:
    # 少數輸出把整段寫成一行、沒有「・」，也當成一條
    return [l.removeprefix("・").strip() for l in lines]


def _names(raw: str, known: set[str]) -> list[str]:
    names = [n.strip() for n in raw.split("、")]
    return names if names and all(n in known for n in names) else []


def _macro(lines: list[str], known: set[str]) -> list[dict]:
    """講者有三種寫法：「名字指出，……」「名字：……」「……（名字、名字）」。
    只接受分析師區塊裡出現過的名字，避免把「美股與利率環境：」這類主題當成人名。"""
    items = []
    for text in _bullets(lines):
        who, body = [], text
        colon = re.match(r"^(.{1,30}?)[：:](.+)$", text)
        idx = min((i for i in (text.find(v) for v in _VERBS) if i > 0), default=-1)
        tail = re.search(r"（([^（）]+)）(。?)$", text)   # Gemini Notebook 有時把句號放在括號後
        if colon and (who := _names(colon.group(1), known)):
            body = colon.group(2).strip()
        elif idx > 0 and (who := _names(text[:idx], known)):
            body = text[idx:]
        elif tail and (who := _names(tail.group(1), known)):
            body = text[:tail.start()].rstrip() + tail.group(2)
        items.append({"who": who, "text": body})
    return items


def _code(raw: str | None) -> str | None:
    return None if raw is None or "待確認" in raw else raw


def _consensus(lines: list[str]) -> dict:
    out, part = {"ind": [], "stk": []}, "ind"
    for line in lines:
        if line.startswith("【"):
            part = "stk" if "個股" in line else "ind"
            continue
        m = re.match(r"^○\s*(.+?)\s*(?:（([^（）]+)）)?\s*｜\s*看[多空]者\s*：(.+)$", line)
        if not m:
            continue
        who = [w.strip() for w in m.group(3).split("、")]
        if part == "stk":
            out["stk"].append({"name": m.group(1).strip(), "code": _code(m.group(2)), "who": who})
        else:
            out["ind"].append({"name": m.group(1).strip(), "who": who})
    return out


def _divergences(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        if line.startswith("・"):
            out.append({"topic": line[1:].strip(), "sides": []})
        elif line.startswith("▽") and out:
            who, _, text = line[1:].strip().partition("：")
            out[-1]["sides"].append({"who": who.strip(), "text": text.strip()})
    return out


def _analysts(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        head = re.match(r"^👤\s*(.+?)\s*｜\s*頻道\s*：(.+)$", line)
        if head:
            out.append({"name": head.group(1).strip(), "channels": [c.strip() for c in head.group(2).split("、")],
                        "fields": {}, "attitude": "", "confidence": "", "stocks": []})
            continue
        if not out:
            continue
        a = out[-1]
        stock = re.match(r"^★\s*(.+?)（([^（）]+)）\s*｜\s*(.+?)\s*｜\s*信心（(.+?)）\s*｜\s*(.+)$", line)
        if stock:
            a["stocks"].append({"name": stock.group(1).strip(), "code": _code(stock.group(2)), "attitude": stock.group(3),
                                "confidence": stock.group(4), "horizon": stock.group(5).strip(), "reason": "", "chain": ""})
        elif line.startswith("▲▲理由：") and a["stocks"]:
            a["stocks"][-1]["reason"] = line.removeprefix("▲▲理由：").strip()
        elif line.startswith("◆◆供應鏈：") and a["stocks"]:
            a["stocks"][-1]["chain"] = line.removeprefix("◆◆供應鏈：").strip()
        elif line.startswith("・"):
            key, _, value = line[1:].partition("：")
            m = re.match(r"^(.+?)｜信心：(.+)$", value)
            if key == "態度" and m:
                a["attitude"], a["confidence"] = m.group(1).strip(), m.group(2).strip()
            elif value.strip():
                a["fields"][key.strip()] = value.strip()
    return out


def parse_report(text: str) -> dict:
    title, sec = _sections(text)
    analysts = _analysts(sec.get("analysts", []))
    report = {
        "title": title,
        "focus": _bullets(sec.get("focus", [])),
        "macro": _macro(sec.get("macro", []), {a["name"] for a in analysts}),
        "consensus": {"bull": _consensus(sec.get("bull", [])), "bear": _consensus(sec.get("bear", []))},
        "divergences": _divergences(sec.get("diverge", [])),
        "analysts": analysts,
        "raw": text,
    }
    report["parse_ok"] = bool(title and report["focus"] and report["analysts"])
    return report


def line_short(text: str, url: str, missing: list[str] | None = None, limit: int = LINE_LIMIT) -> str:
    """LINE 精簡版（D10）：今日焦點、總體經濟、多空共識、主要分歧，加網站連結；太長時從總經段尾端刪。"""
    lines = text.splitlines()
    cut = next((i for i, l in enumerate(lines) if (m := _HEADER.match(l.strip())) and "分析師重點" in m.group(1)), len(lines))
    body = [l.rstrip() for l in lines[:cut]]
    while body and not body[-1].strip():
        body.pop()
    head = body[:1] + [""] + ([f"【本期缺漏】{'；'.join(missing)}", ""] if missing else [])
    tail = ["", "━━━━━", f"完整報告與影片來源：{url}", "AI 自動摘要，非投資建議。"]
    rest = body[1:]
    while rest and not rest[0].strip():
        rest.pop(0)

    def build():
        return "\n".join(head + rest + tail)

    in_macro, section = [], ""   # 總經章節裡的條目位置；超過字數時從最後一條開始刪
    for i, l in enumerate(rest):
        m = _HEADER.match(l.strip())
        if m:
            section = m.group(1)
        elif l.startswith("・") and "總體經濟" in section:
            in_macro.append(i)
    while len(build()) > limit and in_macro:
        rest.pop(in_macro.pop())
    return build()
