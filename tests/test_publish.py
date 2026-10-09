import json
from pathlib import Path

import pytest

import publish
from fd.website import read_sealed, unwrap_key

SAMPLE = (Path(__file__).parent / "fixtures/report_sample.txt").read_text(encoding="utf-8")
PW = "測試密碼"
REPORT = SAMPLE + "\n━━━━━\n\n▊▊▊🔗 影片來源 ▊▊▊\n☞ 影片1. 第四季作帳 完整標題 #範例｜範例頻道 A\n☞ 影片2. 被動元件漲價 完整標題｜範例頻道 C\n"


class FakeGit:
    """不真的跑 git：commit 時記下 docs/ 與 data/reports/ 的內容，status 拿現況和它比。"""
    def __init__(self, root, fail_on=None):
        self.root, self.calls, self.committed, self.fail_on = root, [], {}, fail_on

    def snapshot(self):
        return {f.as_posix(): f.read_bytes() for d in ("docs", "data/reports") for f in (self.root / d).rglob("*") if f.is_file()}

    def __call__(self, *args):
        self.calls.append(args)
        if args[0] == self.fail_on:
            raise RuntimeError(f"git {args[0]}：fatal: 模擬失敗")
        if args[0] == "status":
            return "" if self.snapshot() == self.committed else " M docs/data/index.enc\n"
        if args[0] == "commit":
            self.committed = self.snapshot()
        return ""

    def count(self, cmd):
        return sum(1 for c in self.calls if c[0] == cmd)


class Resp:
    def __init__(self, content, status=200):
        self.content, self.status_code = content, status


def online(root):
    return lambda url, timeout: Resp((root / "docs/data/index.enc").read_bytes())


def setup(tmp_path, text=REPORT, name="2026-10-03_Sat.txt"):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts/提示詞.txt").write_text("範例提示詞", encoding="utf-8")
    (tmp_path / "reports").mkdir()
    (tmp_path / "data").mkdir()
    state = {
        "last_success_at": "2026-10-03T21:42:00+08:00",
        "videos": {
            "vidA_000001": {"channel": "範例頻道 A", "title": "第四季作帳", "published": "2026-10-03T09:00:00+08:00",
                            "minutes": 33, "status": "included", "report": "2026-10-03_Sat"},
            "vidC_000002": {"channel": "範例頻道 C", "title": "被動元件漲價", "published": "2026-10-03T18:00:00+08:00",
                            "minutes": 41, "status": "included", "report": "2026-10-03_Sat"},
            "vidX_000003": {"channel": "範例頻道 C", "title": "會員影片", "published": "2026-10-03T19:00:00+08:00",
                            "minutes": 10, "status": "excluded", "report": "2026-10-03_Sat", "reason": "members_only"},
        },
        "runs": [
            {"report": "2026-10-02_Fri", "edition": "weekday", "status": "complete"},
            {"report": "2026-10-03_Sat", "edition": "weekday", "status": "complete"},
        ],
    }
    (tmp_path / "data/processed.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    path = tmp_path / "reports" / name
    path.write_text(text, encoding="utf-8")
    return path


def run(tmp_path, path, git, **kw):
    kw.setdefault("fetch", online(tmp_path))
    logs = []
    code = publish.publish(path, kw.pop("password", PW), root=tmp_path, run_git=git, sleep=lambda _: None, log=logs.append, **kw)
    return code, logs


def state(tmp_path):
    return json.loads((tmp_path / "data/processed.json").read_text(encoding="utf-8"))


def test_publish_twice_commits_once_and_records_state(tmp_path):
    path = setup(tmp_path)
    git = FakeGit(tmp_path)
    assert run(tmp_path, path, git)[0] == 0
    assert git.count("commit") == 1 and git.count("push") == 1
    commit = next(c for c in git.calls if c[0] == "commit")
    assert commit[1:3] == ("-m", "publish: 2026-10-03") and commit[4:] == publish.PUBLISH_PATHS   # 只 commit 這三個路徑
    rec = state(tmp_path)["runs"][-1]
    assert rec["site_published"] is True and rec["published_at"]
    saved = (tmp_path / "data/processed.json").read_text(encoding="utf-8")

    code, logs = run(tmp_path, path, git)
    assert code == 0 and git.count("commit") == 1          # 第二次不重複 commit
    assert any("不 commit" in l for l in logs)
    assert (tmp_path / "data/processed.json").read_text(encoding="utf-8") == saved


def test_report_data_uses_full_titles_and_links_from_processed_json(tmp_path):
    path = setup(tmp_path)
    run(tmp_path, path, FakeGit(tmp_path), push=False)
    ring = json.loads((tmp_path / "docs/data/keyring.json").read_text(encoding="utf-8"))
    r = read_sealed(tmp_path / "data/reports/2026-10-03.json.enc", unwrap_key(ring, PW))
    assert [(s["n"], s["title"], s["url"]) for s in r["sources"]] == [
        (1, "第四季作帳 完整標題 #範例", "https://www.youtube.com/watch?v=vidA_000001"),
        (2, "被動元件漲價 完整標題", "https://www.youtube.com/watch?v=vidC_000002")]
    assert r["engine"] == "Gemini Notebook" and len(r["prompt_hash"]) == 8 and r["parsed"]["parse_ok"]
    assert r["window"] == {"start": "2026-10-02T21:42:00+08:00", "end": "2026-10-03T21:42:00+08:00"}
    assert "https://ycy1997alex.github.io/finance-digest/2026-10-03/" in r["line_short"]


def test_rewritten_short_title_is_matched_by_channel_order():
    # processed.json 的標題有時不是完整標題的開頭（2026-10-02 艾綸說），改依同頻道的先後順序配對
    videos = {
        "early": {"channel": "頻道 A", "title": "早上節目【濾鏡】", "published": "2026-10-03T09:00:00+08:00", "minutes": 9,
                  "status": "included", "report": "R"},
        "late": {"channel": "頻道 A", "title": "晚上節目", "published": "2026-10-03T19:00:00+08:00", "minutes": 30,
                 "status": "included", "report": "R"},
    }
    text = "▊▊▊🔗 影片來源 ▊▊▊\n☞ 影片1. 早上節目 副標題 【濾鏡】- EP15｜頻道 A\n☞ 影片2. 晚上節目 完整版｜頻道 A\n"
    sources, notes = publish.report_sources(text, videos, "R")
    assert [(s["n"], s["video_id"]) for s in sources] == [(1, "early"), (2, "late")] and notes == []


def test_annotated_missing_videos_reach_the_site(tmp_path):
    text = REPORT + "\n▊▊▊⚠️ 未能讀取的影片 ▊▊▊\n・（範例頻道 F）晚間節目（將於下次報告重試）\n"
    path = setup(tmp_path, text)
    run(tmp_path, path, FakeGit(tmp_path), push=False)
    ring = json.loads((tmp_path / "docs/data/keyring.json").read_text(encoding="utf-8"))
    r = read_sealed(tmp_path / "data/reports/2026-10-03.json.enc", unwrap_key(ring, PW))
    assert r["missing"] == ["（範例頻道 F）晚間節目（將於下次報告重試）"] and len(r["sources"]) == 2


def test_no_push_touches_neither_git_nor_state(tmp_path):
    path = setup(tmp_path)
    before = (tmp_path / "data/processed.json").read_text(encoding="utf-8")
    git = FakeGit(tmp_path)
    assert run(tmp_path, path, git, push=False)[0] == 0
    assert git.calls == [] and (tmp_path / "docs/index.html").exists()
    assert (tmp_path / "data/processed.json").read_text(encoding="utf-8") == before


def test_republish_rewrites_the_day_and_records_it(tmp_path):
    path = setup(tmp_path)
    git = FakeGit(tmp_path)
    run(tmp_path, path, git)
    assert run(tmp_path, path, git, republish=True)[0] == 0
    assert git.count("commit") == 2 and state(tmp_path)["runs"][-1]["republished_at"]


def test_missing_password_fails_before_writing_anything(tmp_path):
    path = setup(tmp_path)
    with pytest.raises(publish.StepError) as e:
        run(tmp_path, path, FakeGit(tmp_path), password=None)
    assert e.value.code == 1 and "SITE_PASSWORD" in str(e.value)
    assert not (tmp_path / "docs").exists() and not (tmp_path / "data/reports").exists()


def test_wrong_password_is_reported_without_echoing_it(tmp_path):
    path = setup(tmp_path)
    run(tmp_path, path, FakeGit(tmp_path), push=False)
    with pytest.raises(publish.StepError) as e:
        run(tmp_path, path, FakeGit(tmp_path), password="不對的密碼", push=False)
    assert e.value.code == 1 and "不對的密碼" not in str(e.value)


@pytest.mark.parametrize("text, name, expect", [
    (SAMPLE, "2026-10-03_Sat.txt", "影片來源"),                     # 回覆中途中斷
    (REPORT, "2026-10-04_Sun.txt", "標題日期"),                     # 檔名和標題日期不同
    (REPORT, "20261003.txt", "檔名"),
])
def test_broken_report_is_rejected(tmp_path, text, name, expect):
    path = setup(tmp_path, text, name)
    with pytest.raises(publish.StepError) as e:
        run(tmp_path, path, FakeGit(tmp_path))
    assert e.value.code == 1 and expect in str(e.value) and "第 1 步" in str(e.value)
    assert not (tmp_path / "docs").exists()


def test_report_without_run_record_is_rejected(tmp_path):
    path = setup(tmp_path)
    s = state(tmp_path)
    s["runs"] = s["runs"][:1]
    (tmp_path / "data/processed.json").write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(publish.StepError) as e:
        run(tmp_path, path, FakeGit(tmp_path))
    assert e.value.code == 1 and "runs" in str(e.value)


def test_git_failure_exits_2_and_rerun_pushes_again(tmp_path):
    path = setup(tmp_path)
    with pytest.raises(publish.StepError) as e:
        run(tmp_path, path, FakeGit(tmp_path, fail_on="push"))
    assert e.value.code == 2 and "第 7 步" in str(e.value)
    assert "site_published" not in state(tmp_path)["runs"][-1]


def test_site_not_online_in_time_exits_2(tmp_path, monkeypatch):
    path = setup(tmp_path)
    ticks = iter(range(0, 10_000, 100))
    monkeypatch.setattr(publish.time, "monotonic", lambda: next(ticks))
    with pytest.raises(publish.StepError) as e:
        run(tmp_path, path, FakeGit(tmp_path), fetch=lambda url, timeout: Resp(b"stale"))
    assert e.value.code == 2 and "第 8 步" in str(e.value)
