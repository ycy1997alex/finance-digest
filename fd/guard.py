"""commit 前的明文檢查：repo 是公開的，data/ 與 docs/ 只能有密文與白名單上的檔案（移植自 finance-digest-a）。

    data/processed.json                        公開影片的標題與執行紀錄（本來就是公開資訊）
    data/reports/YYYY-MM-DD.json.enc           密文
    docs/index.html                            必須與網站模板完全相同
    docs/YYYY-MM-DD/index.html                 轉址頁
    docs/data/keyring.json、*.enc               密文
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .website import STUB, TEMPLATE

_SEALED = {"v", "iv", "ct", "encoding"}
_RING = {"v", "kdf", "salt", "iv", "wrapped"}
_DAY = r"\d{4}-\d{2}-\d{2}"


def _keys(path: Path) -> set[str]:
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return set()


def check_public_tree(root: Path) -> list[str]:
    problems = []
    data, site = root / "data", root / "docs"
    for f in sorted(p for p in data.rglob("*") if p.is_file()) if data.exists() else []:
        rel = f.relative_to(root).as_posix()
        if rel == "data/processed.json":
            continue
        if re.fullmatch(rf"data/reports/{_DAY}\.json\.enc", rel) and _keys(f) == _SEALED:
            continue
        problems.append(f"不允許或不是密文：{rel}")
    for f in sorted(p for p in site.rglob("*") if p.is_file()) if site.exists() else []:
        rel = f.relative_to(root).as_posix()
        if rel == "docs/index.html":
            if f.read_text(encoding="utf-8") != TEMPLATE.read_text(encoding="utf-8"):
                problems.append("docs/index.html 與網站模板不同")
            continue
        m = re.fullmatch(rf"docs/({_DAY})/index\.html", rel)
        if m and f.read_text(encoding="utf-8") == STUB.format(day=m.group(1)):
            continue
        if rel == "docs/data/keyring.json" and _keys(f) == _RING:
            continue
        if (rel == "docs/data/index.enc" or re.fullmatch(rf"docs/data/r/{_DAY}\.enc", rel)) and _keys(f) == _SEALED:
            continue
        problems.append(f"不允許或不是密文：{rel}")
    return problems
