"""網站產生：把 data/reports/ 的加密報告轉成 GitHub Pages 的 docs/（移植自 finance-digest-a 的 publish.py）。

docs/
├─ index.html              解鎖頁與網站程式（不含任何報告內容）
├─ YYYY-MM-DD/index.html   每期的固定網址，轉址到 ../#/d/YYYY-MM-DD
└─ data/
   ├─ keyring.json         用密碼包起來的主金鑰；只在第一次建立（或 rotate_key）時寫
   ├─ index.enc            各期清單與追蹤索引；內容有變才重寫
   └─ r/YYYY-MM-DD.enc     每期一檔；已存在的不重寫，只寫新的與指定重發的

和 -a 的差別：-a 每次發布都重新包 keyring、重寫 index.enc，內容沒變也會換新的 salt／IV，
每跑一次就多一個 commit。這裡內容沒變就不寫檔，同一份報告重跑時 git 看不到任何變動。
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .crypto import new_master_key, open_sealed, seal, unwrap_key, wrap_key

TPE = timezone(timedelta(hours=8))   # 台灣沒有日光節約時間，固定 UTC+8
TEMPLATE = Path(__file__).with_name("site_template") / "index.html"
TRACK_DAYS = 90   # 追蹤頁（熱門個股、分析師歷次觀點）涵蓋的天數
STUB = """<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="robots" content="noindex, nofollow">
<meta http-equiv="refresh" content="0; url=../#/d/{day}"><title>財經節目每日摘要</title></head>
<body><a href="../#/d/{day}">前往 {day} 的報告</a></body></html>
"""


def master_key(site_dir: Path, password: str) -> bytes:
    """第一次執行時產生主金鑰並包好存檔；之後一律用密碼解開既有的 keyring。"""
    path = site_dir / "data/keyring.json"
    if path.exists():
        return unwrap_key(json.loads(path.read_text(encoding="utf-8")), password)
    mk = new_master_key()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(wrap_key(mk, password)), encoding="utf-8")
    return mk


def _md_hm(iso: str) -> str:
    t = datetime.fromisoformat(iso)
    return f"{t.month}/{t.day} {t:%H:%M}"


def _split(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"[、，,]", text) if x.strip()]


def _timeline(text: str) -> list[dict]:
    items = []
    for part in re.split(r"[；;]", text):
        if part.strip():
            when, sep, what = part.strip().partition("：")
            items.append({"when": when, "what": what} if sep else {"when": "", "what": when})
    return items


def site_payload(r: dict) -> dict:
    """把 publish.py 存下的報告轉成網站一期的資料。"""
    p = r["parsed"]
    analysts = []
    for a in p["analysts"]:
        f = a["fields"]
        analysts.append({
            "name": a["name"], "channels": a["channels"], "topic": f.get("主題", ""), "view": f.get("市場看法", ""),
            "strategy": f.get("投資策略", ""), "bull_ind": _split(f.get("看好產業", "")), "bear_ind": _split(f.get("看壞產業", "")),
            "timeline": _timeline(f.get("關鍵時程", "")), "risk": f.get("風險提示", ""),
            "attitude": a["attitude"], "confidence": a["confidence"], "stocks": a["stocks"],
        })
    return {
        "date": r["report_date"], "edition": r["edition"], "status": r["status"],
        "coverage": {"included": len(r["sources"]), "expected": len(r["sources"]) + len(r["missing"])},
        "missing": r["missing"], "pending": r.get("pending", []),
        "window": f"{_md_hm(r['window']['start'])} – {_md_hm(r['window']['end'])}",
        "generated_at": r["generated_at"], "updated_at": r.get("updated_at"),
        "model": r["engine"], "prompt": r["prompt_hash"],
        "focus": p["focus"], "macro": p["macro"], "consensus": p["consensus"], "divergences": p["divergences"],
        "analysts": analysts,
        "sources": [{"n": s["n"], "channel": s["channel"], "title": s["title"], "url": s["url"],
                     "published": _md_hm(s["published_at"]), "minutes": s["minutes"]} for s in r["sources"]],
        "line_short": r["line_short"], "raw": r["text"], "parse_ok": p["parse_ok"],
    }


def _index(reports: list[dict], track_days: int = TRACK_DAYS) -> dict:
    """各期清單（全部）與追蹤索引（最近 track_days 天的個股與分析師觀點），新到舊。"""
    reports = sorted(reports, key=lambda r: r["report_date"], reverse=True)
    mentions, analysts = [], {}
    cutoff = (date.fromisoformat(reports[0]["report_date"]) - timedelta(days=track_days)).isoformat() if reports else ""
    for r in reports:
        day = r["report_date"]
        if day < cutoff:
            continue
        for a in r["parsed"]["analysts"]:
            e = analysts.setdefault(a["name"], {"name": a["name"], "channels": [], "days": []})
            e["channels"] += [c for c in a["channels"] if c not in e["channels"]]
            e["days"].append({"d": day, "a": a["attitude"], "f": a["confidence"], "t": a["fields"].get("主題", ""),
                              "v": a["fields"].get("市場看法", ""), "s": [[s["name"], s["attitude"], s["code"]] for s in a["stocks"]]})
            for s in a["stocks"]:
                mentions.append({"d": day, "s": s["name"], "c": s["code"], "w": a["name"], "a": s["attitude"],
                                 "f": s["confidence"], "h": s["horizon"], "r": s["reason"]})
    return {
        "dates": [{"date": r["report_date"], "edition": r["edition"], "status": r["status"],
                   "included": len(r["sources"]), "expected": len(r["sources"]) + len(r["missing"])} for r in reports],
        "mentions": mentions, "analysts": list(analysts.values()),
    }


def write_sealed(path: Path, obj: dict, mk: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(seal(json.dumps(obj, ensure_ascii=False), mk)), encoding="utf-8")


def read_sealed(path: Path, mk: bytes) -> dict:
    return json.loads(open_sealed(json.loads(path.read_text(encoding="utf-8")), mk))


def _write_text_if_changed(path: Path, text: str) -> None:
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def build_site(data_dir: Path, site_dir: Path, password: str, only: str | None = None) -> dict:
    """only：重新加密指定那一期（YYYY-MM-DD）或 "all"；其他已存在的期別不動。"""
    mk = master_key(site_dir, password)
    reports = [read_sealed(f, mk) for f in sorted((data_dir / "reports").glob("*.json.enc"))]
    written = 0
    for r in reports:
        day = r["report_date"]
        target = site_dir / f"data/r/{day}.enc"
        if not target.exists() or only in (day, "all"):
            payload = site_payload(r)
            if target.exists() and only == day:   # 同一期重新發布：頁面顯示更新時間
                payload["updated_at"] = datetime.now(TPE).isoformat(timespec="seconds")
            write_sealed(target, payload, mk)
            written += 1
        _write_text_if_changed(site_dir / day / "index.html", STUB.format(day=day))
    index_path = site_dir / "data/index.enc"
    index = _index(reports)
    if not index_path.exists() or read_sealed(index_path, mk) != index:
        write_sealed(index_path, index, mk)
    _write_text_if_changed(site_dir / "index.html", TEMPLATE.read_text(encoding="utf-8"))
    return {"reports": len(reports), "written": written}


def rotate_key(data_dir: Path, site_dir: Path, password: str, new_password: str | None = None) -> dict:
    """換一把新的主金鑰並重新加密全部報告與網站資料；可同時換密碼。

    只重新包主金鑰擋不住知道舊密碼的人：git 歷史裡的舊 keyring 仍能用舊密碼解開舊主金鑰，
    而舊主金鑰解得開所有沒重新加密的檔案。要真正停用舊密碼，就要用這個函式。
    """
    old = master_key(site_dir, password)
    new = new_master_key()
    files = sorted((data_dir / "reports").glob("*.json.enc"))
    for f in files:
        f.write_text(json.dumps(seal(open_sealed(json.loads(f.read_text(encoding="utf-8")), old), new)), encoding="utf-8")
    (site_dir / "data/keyring.json").write_text(json.dumps(wrap_key(new, new_password or password)), encoding="utf-8")
    (site_dir / "data/index.enc").unlink(missing_ok=True)   # 舊金鑰加密的索引，讓 build_site 重建
    return {"reports": len(files), **build_site(data_dir, site_dir, new_password or password, only="all")}
