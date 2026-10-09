import json
from pathlib import Path

from fd.crypto import open_sealed, seal, unwrap_key
from fd.render import parse_report
from fd.website import build_site, master_key, rotate_key, site_payload

SAMPLE = (Path(__file__).parent / "fixtures/report_sample.txt").read_text(encoding="utf-8")
PW = "測試密碼"


def report(day, status="complete"):
    return {
        "report_date": day, "edition": "weekday", "status": status, "text": SAMPLE, "line_short": "精簡版",
        "parsed": parse_report(SAMPLE),
        "sources": [{"n": 1, "video_id": "abc", "title": "節目標題", "channel": "範例頻道 A",
                     "url": "https://www.youtube.com/watch?v=abc", "published_at": f"{day}T16:00:00+08:00", "minutes": 33}],
        "missing": ["範例頻道 F 晚間節目（將於下次報告重試）"] if status == "partial" else [], "pending": [],
        "engine": "Gemini Notebook", "prompt_hash": "3f9c2a7e", "generated_at": f"{day}T21:56:00+08:00",
        "window": {"start": "2026-10-01T21:42:00+08:00", "end": f"{day}T21:42:00+08:00"},
    }


def store_reports(tmp_path, days):
    mk = master_key(tmp_path / "docs", PW)
    (tmp_path / "data/reports").mkdir(parents=True)
    for day, status in days:
        (tmp_path / f"data/reports/{day}.json.enc").write_text(json.dumps(seal(json.dumps(report(day, status)), mk)), encoding="utf-8")
    return mk


def decrypt(path, mk):
    return json.loads(open_sealed(json.loads(path.read_text(encoding="utf-8")), mk))


def snapshot(root):
    return {f.relative_to(root).as_posix(): f.read_bytes() for f in root.rglob("*") if f.is_file()}


def test_site_payload_reshapes_analyst_fields():
    p = site_payload(report("2026-10-03", "partial"))
    assert p["coverage"] == {"included": 1, "expected": 2} and p["status"] == "partial"
    a = p["analysts"][0]
    assert a["topic"] == "第四季作帳行情與資金輪動" and a["bull_ind"] == ["AI 伺服器", "被動元件"]
    assert a["timeline"] == [{"when": "10/15", "what": "台積電法說會"}, {"when": "11/05", "what": "聯準會利率決議"}]
    assert p["sources"][0] == {"n": 1, "channel": "範例頻道 A", "title": "節目標題", "url": "https://www.youtube.com/watch?v=abc",
                               "published": "10/3 16:00", "minutes": 33}
    assert p["window"] == "10/1 21:42 – 10/3 21:42" and p["model"] == "Gemini Notebook"


def test_build_site_writes_only_ciphertext_plus_shell_and_stubs(tmp_path):
    mk = store_reports(tmp_path, [("2026-10-02", "complete"), ("2026-10-03", "partial")])
    summary = build_site(tmp_path / "data", tmp_path / "docs", PW)
    site = tmp_path / "docs"
    assert summary["reports"] == 2
    assert (site / "index.html").exists() and "noindex" in (site / "index.html").read_text(encoding="utf-8")
    assert "#/d/2026-10-03" in (site / "2026-10-03/index.html").read_text(encoding="utf-8")
    index = decrypt(site / "data/index.enc", mk)
    assert [d["date"] for d in index["dates"]] == ["2026-10-03", "2026-10-02"]
    assert {m["s"] for m in index["mentions"]} >= {"台積電", "國巨"}
    assert decrypt(site / "data/r/2026-10-03.enc", mk)["status"] == "partial"
    for f in (site / "data").rglob("*"):
        if f.is_file():
            assert "財經" not in f.read_text(encoding="utf-8") and "台積電" not in f.read_text(encoding="utf-8")


def test_rebuilding_without_changes_touches_no_file(tmp_path):
    # 同一份報告重跑時 git 不能看到任何變動，否則每次都會多一個 commit
    store_reports(tmp_path, [("2026-10-02", "complete")])
    build_site(tmp_path / "data", tmp_path / "docs", PW)
    before = snapshot(tmp_path / "docs")
    build_site(tmp_path / "data", tmp_path / "docs", PW)
    assert snapshot(tmp_path / "docs") == before


def test_new_report_rewrites_index_but_keeps_keyring_and_old_files(tmp_path):
    mk = store_reports(tmp_path, [("2026-10-02", "complete")])
    site = tmp_path / "docs"
    build_site(tmp_path / "data", site, PW)
    before = snapshot(site)
    (tmp_path / "data/reports/2026-10-03.json.enc").write_text(json.dumps(seal(json.dumps(report("2026-10-03")), mk)), encoding="utf-8")
    build_site(tmp_path / "data", site, PW)
    after = snapshot(site)
    assert after["data/keyring.json"] == before["data/keyring.json"]
    assert after["data/r/2026-10-02.enc"] == before["data/r/2026-10-02.enc"]
    assert after["data/index.enc"] != before["data/index.enc"] and "data/r/2026-10-03.enc" in after


def test_republishing_a_day_marks_it_updated(tmp_path):
    mk = store_reports(tmp_path, [("2026-10-02", "complete")])
    site = tmp_path / "docs"
    build_site(tmp_path / "data", site, PW, only="2026-10-02")      # 第一次發布
    assert decrypt(site / "data/r/2026-10-02.enc", mk)["updated_at"] is None
    build_site(tmp_path / "data", site, PW, only="2026-10-02")      # --republish
    assert decrypt(site / "data/r/2026-10-02.enc", mk)["updated_at"]  # 網站會顯示「已更新 HH:MM」


def test_tracking_index_keeps_only_recent_days(tmp_path):
    mk = store_reports(tmp_path, [("2026-06-01", "complete"), ("2026-10-02", "complete")])
    build_site(tmp_path / "data", tmp_path / "docs", PW)
    index = decrypt(tmp_path / "docs/data/index.enc", mk)
    assert [d["date"] for d in index["dates"]] == ["2026-10-02", "2026-06-01"]   # 封存清單全部保留
    assert {m["d"] for m in index["mentions"]} == {"2026-10-02"}                 # 追蹤只留最近 90 天


def test_rotate_key_reencrypts_everything_and_can_change_password(tmp_path):
    old_mk = store_reports(tmp_path, [("2026-10-02", "complete")])
    site = tmp_path / "docs"
    build_site(tmp_path / "data", site, PW)
    stale_ring = json.loads((site / "data/keyring.json").read_text(encoding="utf-8"))
    rotate_key(tmp_path / "data", site, PW, "新密碼")
    new_mk = unwrap_key(json.loads((site / "data/keyring.json").read_text(encoding="utf-8")), "新密碼")
    assert new_mk != old_mk and unwrap_key(stale_ring, PW) == old_mk   # git 歷史裡的舊 keyring 只解得開舊金鑰
    assert decrypt(tmp_path / "data/reports/2026-10-02.json.enc", new_mk)["report_date"] == "2026-10-02"
    assert decrypt(site / "data/r/2026-10-02.enc", new_mk)["date"] == "2026-10-02"
    assert decrypt(site / "data/index.enc", new_mk)["dates"][0]["date"] == "2026-10-02"
