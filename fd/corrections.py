"""發布前的校正表：修正 Gemini 聽錯或寫法不一致的人名、頻道與用詞（config/corrections.yaml）。

reports/ 是原稿，一字不改（AGENTS.md 紅線）；校正後的稿存在 corrected_reports/（同檔名，本機閱讀用，明文不進 git），
網站、LINE 版與追蹤索引都用校正後的文字。corrected_reports/ 是產生出來的，不要手改，要修就改校正表。
校正表改了之後：python -m fd.corrections 重產全部校正稿；已發布的期別要用 publish.py --republish 重發網站才會更新。

三種校正：
    text       全文逐字替換。只放不會誤傷其他字的錯字（例如 黃風凱 → 黃豐凱）
    analysts   分析師別名 → 正式名稱。只改「人名的位置」：👤 行、看多者／看空者名單、▽ 分歧、總經的講者，
               所以「艾綸 → 劉育綸」不會把頻道名「艾綸說」改成「劉育綸說」；影片來源段是 YouTube 原始標題，也不改
    channels   頻道寫法 → 正式頻道名。只改 👤 行的「頻道：」欄位，改完重複的合併

    python -m fd.corrections     重產 corrected_reports/，列出每份報告被改到的地方，以及校正後還剩下的人名與頻道寫法（找新的別名用）
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from .render import _VERBS, parse_report

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "config/corrections.yaml"
CORRECTED = ROOT / "corrected_reports"
KINDS = ("text", "analysts", "channels")
_BEFORE = r"👤▽・、（(：:\s"            # 人名前面會出現的字元
_AFTER = r"｜|、）)：:\s"               # 人名後面會出現的字元（另外還有「指出」等動詞與行尾）
_SOURCES = "▊▊▊🔗 影片來源 ▊▊▊"
_HEAD = re.compile(r"^(\s*👤\s*.+?\s*｜\s*頻道\s*：)(.+)$", re.M)


def load(path: Path = TABLE) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {k: {} for k in KINDS}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    unknown = set(raw) - set(KINDS)
    if unknown:
        raise ValueError(f"{path.name} 有不認得的分類：{'、'.join(sorted(unknown))}（只能是 {'、'.join(KINDS)}）")
    table = {}
    for k in KINDS:
        part = raw.get(k) or {}
        if not isinstance(part, dict) or not all(isinstance(a, str) and a and isinstance(b, str) and b for a, b in part.items()):
            raise ValueError(f"{path.name} 的 {k} 必須是「原本的寫法: 正確寫法」的對照，兩邊都不能空白")
        table[k] = part
    return table


def apply(text: str, table: dict[str, dict[str, str]]) -> tuple[str, list[str]]:
    """回傳 (校正後全文, 套用紀錄)。別名長的先換，「劉育綸（艾綸）」不會先被「艾綸」切壞。"""
    done = []
    for old, new in table["text"].items():
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            done.append(f"用詞 {old} → {new}：{n} 處")
    # 影片來源段是 YouTube 的原始標題（例如「李兆華、艾綸、張林忠」），別名不改那裡
    body, sep, sources = text.partition(_SOURCES)
    verbs = "|".join(_VERBS)
    for old in sorted(table["analysts"], key=len, reverse=True):
        new = table["analysts"][old]
        body, n = re.subn(rf"(?<=[{_BEFORE}]){re.escape(old)}(?=[{_AFTER}]|{verbs}|$)", new, body, flags=re.M)
        if n:
            done.append(f"分析師 {old} → {new}：{n} 處")
    text = body + sep + sources
    if table["channels"]:
        changed = 0

        def fix(m: re.Match) -> str:
            nonlocal changed
            out = []
            for raw in m.group(2).split("、"):
                c = table["channels"].get(raw.strip(), raw.strip())
                changed += c != raw.strip()
                if c not in out:
                    out.append(c)
            return m.group(1) + "、".join(out)

        text = _HEAD.sub(fix, text)
        if changed:
            done.append(f"頻道寫法：{changed} 處")
    return text, done


def write_corrected(original: Path, text: str, out_dir: Path = CORRECTED) -> Path:
    """把校正後的全文存成 out_dir/<原檔名>；內容沒變就不寫（沒有要校正的報告也存一份，資料夾才完整）。"""
    out = out_dir / original.name
    if not out.exists() or out.read_text(encoding="utf-8") != text:
        out_dir.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    table = load()
    people = defaultdict(lambda: {"days": [], "channels": set()})
    for f in sorted((ROOT / "reports").glob("*.txt")):
        text, done = apply(f.read_text(encoding="utf-8"), table)
        write_corrected(f, text)
        print(f"{f.name}：{'；'.join(done) if done else '沒有要校正的地方'}")
        for a in parse_report(text)["analysts"]:
            people[a["name"]]["days"].append(f.name[5:10])
            people[a["name"]]["channels"].update(a["channels"])
    print(f"\n校正稿已更新到 {CORRECTED.relative_to(ROOT)}/")
    print("\n校正後的分析師（依頻道排序；同一人出現兩種寫法，就把別名加進 analysts）：")
    for name, e in sorted(people.items(), key=lambda kv: sorted(kv[1]["channels"])):
        print(f"  {name}\t{len(e['days'])} 期\t{'、'.join(sorted(e['channels']))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
