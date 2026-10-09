"""發布一份報告到網站（RUNBOOK 第 6 步；ToDo.md 第 3 節）。

    python publish.py reports/YYYY-MM-DD_EEE.txt [--no-push] [--republish]

依序：檢查報告 → 從 data/processed.json 取影片清單 → 組報告資料 → 加密存到 data/reports/ →
重建 docs/ → guard → git commit／push（只有 docs、data/reports、data/processed.json）→
等網站上線 → 寫回 processed.json。網站是唯一的發布目的地，不推 LINE（2026-10-09 本人決定）。

可重複執行：已加密存檔的報告與已發布的期別不重寫（--republish 才覆寫），
docs/ 與 data/reports/ 沒有變動就不 commit。

結束碼：
    0  完成（或沒有新內容要發布）
    1  發布前失敗：報告沒通過檢查、缺 SITE_PASSWORD、processed.json 沒有紀錄等；遠端網站沒有變動
    2  git 推送或上線確認失敗；本機檔案已更新，修好原因後用同一個指令重跑即可
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
import yaml

from fd import corrections
from fd.check import blocking_problems, warnings
from fd.guard import check_public_tree
from fd.render import line_short, parse_report
from fd.website import TPE, build_site, master_key, write_sealed

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://ycy1997alex.github.io/finance-digest/"
ENGINE = "Gemini Notebook"
CUTOFF = (21, 42)          # 每份報告的截止時間（RUNBOOK：報告日期 21:42）
ONLINE_TIMEOUT = 600       # 等 GitHub Pages 部署的上限（秒）
ONLINE_INTERVAL = 20
PUBLISH_PATHS = ("docs", "data/reports", "data/processed.json")   # AGENTS.md 允許自動 commit 的唯一路徑
_FILE = re.compile(r"(\d{4}-\d{2}-\d{2})_(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.txt")
_SOURCE = re.compile(r"^☞\s*影片(\d+)\.\s*(.+)$")
_MISSING_HEAD = "▊▊▊⚠️ 未能讀取的影片 ▊▊▊"


class StepError(Exception):
    def __init__(self, step: str, reason: str, code: int):
        super().__init__(f"{step}失敗：{reason}")
        self.code = code


def _cutoff(day: str) -> datetime:
    return datetime.combine(date.fromisoformat(day), datetime.min.time(), TPE).replace(hour=CUTOFF[0], minute=CUTOFF[1])


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def read_report(path: Path) -> tuple[str, str, str]:
    """第 1 步：回傳 (報告日期, 檔名主幹, 全文)。"""
    m = _FILE.fullmatch(path.name)
    if not m:
        raise StepError("第 1 步（讀報告）", f"檔名不是 YYYY-MM-DD_EEE.txt：{path.name}", 1)
    if not path.exists():
        raise StepError("第 1 步（讀報告）", f"找不到 {path}", 1)
    text = path.read_text(encoding="utf-8")
    problems = blocking_problems(text, m.group(1))
    if problems:
        raise StepError("第 1 步（檢查報告）", "；".join(problems), 1)
    return m.group(1), path.stem, text


def report_sources(text: str, videos: dict, stem: str) -> tuple[list[dict], list[str]]:
    """第 2 步：報告本文沒有網址（提示詞禁止），連結只能從 processed.json 來。

    processed.json 的標題是截短（有時改寫過）的，報告「影片來源」段是完整標題。先配同頻道、完整標題以截短標題
    開頭的；剩下的依同頻道內的先後順序配（來源表依上架時間排）。編號與完整標題用報告的。
    還是對不上的照 processed.json 的資料列在最後，並回傳提醒。
    """
    mine = {vid: v for vid, v in videos.items() if v.get("report") == stem and v.get("status") == "included"}
    if not mine:
        raise StepError("第 2 步（影片清單）", f"processed.json 沒有 report 為 {stem}、狀態 included 的影片", 1)
    lines = text.split("▊▊▊🔗 影片來源 ▊▊▊", 1)[1].split(_MISSING_HEAD, 1)[0].splitlines()
    listed = []
    for line in lines:
        m = _SOURCE.match(line.strip())
        if m:
            title, _, channel = m.group(2).rpartition("｜")
            listed.append((int(m.group(1)), _norm(title), _norm(channel)))
    out, notes, left = [], [], dict(sorted(mine.items(), key=lambda kv: kv[1]["published"]))

    def take(n, title, vid):
        v = left.pop(vid)
        out.append({"n": n, "video_id": vid, "title": title, "channel": v["channel"],
                    "url": f"https://www.youtube.com/watch?v={vid}", "published_at": v["published"], "minutes": v["minutes"]})

    unmatched = []
    for n, title, channel in listed:
        vid = next((k for k, v in left.items() if _norm(v["channel"]) == channel and title.startswith(_norm(v["title"]))), None)
        if vid:
            take(n, title, vid)
        else:
            unmatched.append((n, title, channel))
    for n, title, channel in unmatched:
        vid = next((k for k, v in left.items() if _norm(v["channel"]) == channel), None)
        if vid:
            take(n, title, vid)
        else:
            notes.append(f"影片{n} 在 processed.json 找不到對應的影片，網站上不列出")
    n = max([s["n"] for s in out], default=0)
    for vid, v in sorted(left.items(), key=lambda kv: kv[1]["published"]):
        n += 1
        notes.append(f"{v['channel']}｜{v['title']} 沒有出現在報告的影片來源段，編號 {n} 列在最後")
        out.append({"n": n, "video_id": vid, "title": v["title"], "channel": v["channel"],
                    "url": f"https://www.youtube.com/watch?v={vid}", "published_at": v["published"], "minutes": v["minutes"]})
    return sorted(out, key=lambda s: s["n"]), notes


def missing_videos(text: str) -> list[str]:
    """RUNBOOK 第 5 步在檔尾加註的「未能讀取的影片」。"""
    if _MISSING_HEAD not in text:
        return []
    return [l.strip().removeprefix("・").strip() for l in text.split(_MISSING_HEAD, 1)[1].splitlines() if l.strip().startswith("・")]


def find_run(state: dict, stem: str) -> dict:
    runs = [r for r in state.get("runs", []) if r.get("report") == stem]
    if not runs:
        raise StepError("第 2 步（影片清單）", f"processed.json 的 runs 沒有 {stem} 的紀錄", 1)
    run = runs[-1]
    if run.get("status") not in ("complete", "partial"):
        raise StepError("第 2 步（影片清單）", f"{stem} 的狀態是 {run.get('status')}，只發布 complete／partial", 1)
    return run


def report_window(state: dict, stem: str, edition: str) -> dict:
    """涵蓋範圍：平日版從上一份報告的截止時間起；週末版從上一份週末版起（沒有就取 7 天前）。"""
    day = stem[:10]
    prior = [r for r in state.get("runs", []) if r.get("report", "") < stem and r.get("status") in ("complete", "partial")]
    if edition == "weekend":
        prior = [r for r in prior if r.get("edition") == "weekend"]
    start = _cutoff(max(r["report"] for r in prior)[:10]) if prior else _cutoff(day) - timedelta(days=7 if edition == "weekend" else 1)
    return {"start": start.isoformat(), "end": _cutoff(day).isoformat()}


def build_report(path: Path, day: str, stem: str, text: str, state: dict, root: Path = ROOT) -> tuple[dict, list[str]]:
    """第 3 步：組出加密存檔用的報告資料。"""
    run = find_run(state, stem)
    sources, notes = report_sources(text, state.get("videos", {}), stem)
    missing = missing_videos(text)
    prompt = (root / "prompts/提示詞.txt").read_bytes()
    generated = run.get("finished_at") or datetime.fromtimestamp(path.stat().st_mtime, TPE).isoformat(timespec="seconds")
    return {
        "report_date": day, "edition": run["edition"], "status": run["status"], "text": text,
        "line_short": line_short(text, f"{SITE_URL}{day}/", missing or None),
        "parsed": parse_report(text), "sources": sources, "missing": missing, "pending": [],
        "engine": ENGINE, "prompt_hash": hashlib.sha256(prompt).hexdigest()[:8], "generated_at": generated,
        "window": report_window(state, stem, run["edition"]),
    }, notes


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}：{(r.stderr or r.stdout).strip()}")
    return r.stdout


def git_publish(day: str, run_git=git, log=print) -> bool:
    """第 7 步：docs/ 或 data/reports/ 有變動才 commit；之後一律 pull + push（補上次推送失敗的 commit）。

    commit 加上路徑限定，只會收進這三個路徑，就算 index 裡有別的 staged 檔案也不會被帶進去。
    """
    changed = run_git("status", "--porcelain", "--", "docs", "data/reports").strip()
    if changed:
        run_git("add", "--", *PUBLISH_PATHS)
        run_git("commit", "-m", f"publish: {day}", "--", *PUBLISH_PATHS)
        log(f"已 commit：publish: {day}")
    else:
        log("docs/ 與 data/reports/ 沒有變動，不 commit")
    run_git("pull", "--rebase", "--autostash", "origin", "main")
    run_git("push", "origin", "main")
    return bool(changed)


def wait_online(local: bytes, fetch=requests.get, sleep=time.sleep,
                timeout: float = ONLINE_TIMEOUT, interval: float = ONLINE_INTERVAL) -> None:
    """第 8 步：網站上的 data/index.enc 與本機一致才算上線。加時間參數避開 CDN 快取。"""
    want = hashlib.sha256(local).hexdigest()
    clock = time.monotonic
    deadline = clock() + timeout
    while True:
        try:
            r = fetch(f"{SITE_URL}data/index.enc?t={int(time.time())}", timeout=30)
            if r.status_code == 200 and hashlib.sha256(r.content).hexdigest() == want:
                return
        except requests.RequestException:
            pass
        if clock() >= deadline:
            raise TimeoutError(f"{int(timeout)} 秒內網站上的 data/index.enc 仍與本機不同")
        sleep(interval)


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def publish(path: Path, password: str | None, push: bool = True, republish: bool = False,
            root: Path = ROOT, run_git=git, fetch=requests.get, sleep=time.sleep, log=print) -> int:
    day, stem, text = read_report(path)
    for w in warnings(text):
        log(f"提醒（不擋發布）：{w}")
    try:   # 原稿不改，校正只套用在要發布的副本
        text, fixed = corrections.apply(text, corrections.load(root / "config/corrections.yaml"))
    except (ValueError, yaml.YAMLError) as ex:
        raise StepError("第 3 步（校正表）", str(ex), 1) from ex
    for f in fixed:
        log(f"校正：{f}")
    corrections.write_corrected(path, text, root / "corrected_reports")
    log(f"第 3 步：校正稿存到 corrected_reports/{path.name}")
    if not password:
        raise StepError("第 4 步（加密）", "沒有設定環境變數 SITE_PASSWORD", 1)
    state_path = root / "data/processed.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    report, notes = build_report(path, day, stem, text, state, root)
    for n in notes:
        log(f"提醒：{n}")
    p = report["parsed"]
    log(f"{day}（{report['edition']}，{report['status']}）影片 {len(report['sources'])} 支、分析師 {len(p['analysts'])} 位"
        + ("" if p["parse_ok"] else "；解析失敗，網站改顯示原文"))

    docs, data = root / "docs", root / "data"
    try:
        mk = master_key(docs, password)
    except ValueError as ex:   # WrongPassword
        raise StepError("第 4 步（加密）", str(ex), 1) from ex
    sealed = data / f"reports/{day}.json.enc"
    if sealed.exists() and not republish:
        log(f"第 4 步：{sealed.name} 已存在，不重寫（要覆寫請加 --republish）"
            + ("；本次的校正不會反映到網站上" if fixed else ""))
    else:
        write_sealed(sealed, report, mk)
        log(f"第 4 步：已加密存到 data/reports/{sealed.name}")

    summary = build_site(data, docs, password, only=day if republish else None)
    log(f"第 5 步：docs/ 共 {summary['reports']} 期，本次寫入 {summary['written']} 期")

    problems = check_public_tree(root)
    if problems:
        raise StepError("第 6 步（guard）", "；".join(problems), 1)
    log("第 6 步：guard 通過，docs/ 與 data/ 只有密文與允許的檔案")

    if not push:
        log("--no-push：不 commit、不推送、不確認上線")
        return 0
    try:
        git_publish(day, run_git, log)
    except RuntimeError as ex:
        raise StepError("第 7 步（git）", str(ex), 2) from ex
    try:
        wait_online((docs / "data/index.enc").read_bytes(), fetch=fetch, sleep=sleep)
    except TimeoutError as ex:
        raise StepError("第 8 步（確認上線）", str(ex), 2) from ex
    log(f"第 8 步：已上線 {SITE_URL}{day}/")

    run = find_run(state, stem)
    now = datetime.now(TPE).isoformat(timespec="seconds")
    if not run.get("site_published"):
        run.update(site_published=True, published_at=now)
    elif republish:
        run["republished_at"] = now
    else:
        return 0
    save_state(state_path, state)
    log("第 9 步：已寫回 processed.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="發布一份報告到網站")
    ap.add_argument("report", type=Path, help="reports/YYYY-MM-DD_EEE.txt")
    ap.add_argument("--no-push", action="store_true", help="只更新本機 docs/ 與 data/，不 commit、不推送")
    ap.add_argument("--republish", action="store_true", help="覆寫已發布的這一期（網站顯示更新時間）")
    args = ap.parse_args(argv)
    try:
        return publish(args.report, os.environ.get("SITE_PASSWORD"), push=not args.no_push, republish=args.republish)
    except StepError as ex:
        print(f"錯誤：{ex}")
        return ex.code


if __name__ == "__main__":
    sys.exit(main())
