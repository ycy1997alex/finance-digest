# ToDo — finance-digest（Chrome + Gemini Notebook 版）

> 建立：2026-10-09（Claude，在 Claude Desktop 對話中整理）
> 本檔是計畫與待辦的唯一來源。「本人待辦」是 Alex 自己要做或決定的事，其餘交給 Claude Code。
> 完成一項就打勾，並在後面寫上驗證結果與日期。「本人待辦」只有本人說完成才打勾。
> 每日流程看 `RUNBOOK.md`；專案規則看 `AGENTS.md`；背景與目錄看 `README.md`。

---

## 現況（2026-10-09）

- 每日流程第 0～5 步已實測可行：Claude in Chrome 取片（`tools/yt_discover.js`）→ Gemini Notebook 產報告（`tools/notebook_run.js`）→ 本機接收器存檔（`tools/receive_server.py`）。
- 已補跑 10/1～10/8 共 7 份報告，存在 `reports/`（全部完整）；狀態在 `data/processed.json`，過程在 `logs/2026-10-09_backfill.log`。
- 第 6 步「發布」：`publish.py` 與加密網站已完成並在本機驗證（2026-10-09），10/1～10/8 共 7 期已在 https://ycy1997alex.github.io/finance-digest/ 上線。網站是唯一的發布方式，不做 LINE 推播（2026-10-09 本人決定）。
- GitHub **public** repo `ycy1997alex/finance-digest` 已有第一次 commit 並 push（2026-10-09）。
- 舊專案 `D:\Repo\finance-digest-a`（GitHub Actions + Gemini API）因 API 免費層額度與 503 失敗而放棄，但它的**網站（加密靜態頁）已寫好並測過**，本專案直接移植，不重新設計；它的 LINE 推播程式不沿用。

---

## 本人待辦

### 現在

- [ ] 確認 D1～D4（下一節）的建議做法，或告訴 Claude Code 要改哪一項
- [x] 讓 Claude Code 做第一次 commit 與 push（第 1 節）時，在對話中明確授權（2026-10-09 本人授權）
- [ ] 停用舊專案的排程：GitHub → `finance-digest-a` → Actions → daily → 右上「⋯」→ **Disable workflow**。不停的話它每天 21:42、22:22 還會跑，失敗就寄信
- [x] repo `finance-digest` → Settings → Pages：Source 選 **Deploy from a branch**，Branch 選 `main`、資料夾 `/docs`（2026-10-09 本人完成，網站已上線）

### 排程任務

- [ ] 照 **`ToDo_ClaudeDesktop.md`** 完成 Claude Desktop 端的設定與兩個排程任務（前置、排程設定、第一次執行後的檢查都在那份檔案）

### 長期注意

- Gemini Notebook 有用量上限：2026-10-09 一口氣跑 7 份報告後達上限，每天 1 份不會碰到；補跑多天時要分批
- 要分享給家人或朋友的 LINE 群組、社群時，由本人用網站上的「複製 LINE 版」按鈕手動貼，或直接給網址與密碼

---

## 待決定事項（建議做法已寫好，本人沒有異議就照做）

| # | 項目 | 建議做法 | 理由 |
|---|---|---|---|
| D1 | 報告明文要不要進 public repo | **不進**。`reports/` 已加進 `.gitignore`（2026-10-09 先加，本人改決定的話再拿掉）；網站上的報告一律加密 | 沿用舊專案的決定（密碼鎖 + noindex）。公開 repo 一旦 push 明文就永久留在 git 歷史，事後無法撤回 |
| D2 | 網站放哪裡 | 本 repo 的 GitHub Pages，`main` 分支的 `/docs` 資料夾：`https://ycy1997alex.github.io/finance-digest/` | public repo 免費可開 Pages；用 `/docs` 不需要 GitHub Actions workflow，本機 push 後 Pages 自動部署 |
| D3 | 網站密碼 | 沿用本機已有的使用者環境變數 `SITE_PASSWORD`（舊專案設定的那組） | 不需要新設定；換密碼的做法照舊專案 README「密碼與主金鑰」 |
| D4 | 補跑的 10/1～10/8 要不要推 LINE | 已不適用：2026-10-09 本人決定完全不做 LINE 推播 | — |

---

## 1. Repo 初始化與第一次推送

- [x] 確認 `.gitignore` 含 `reports/`（D1）與 `.env`、`__pycache__/` 等 → verify: `git status --untracked-files=all` 看不到 `reports/*.txt`（2026-10-09：只列出 `reports/.gitkeep`）
- [x] `git config core.quotepath false`（讓 `prompts/提示詞.txt` 正常顯示）（2026-10-09）
- [x] 掃描要 commit 的檔案裡沒有金鑰、token、密碼 → verify: 搜尋 `token`、`key`、`password`、`SITE_PASSWORD=` 等字串沒有實值（2026-10-09：命中的都是說明文字；`tools/yt_discover.js` 的 `INNERTUBE_API_KEY` 是執行時從頁面讀，沒有實值）
- [x] `git remote add origin https://github.com/ycy1997alex/finance-digest.git`（2026-10-09）
- [x] 第一次 commit 與 push（**本人授權後才做**）→ verify: GitHub 上看得到 `AGENTS.md`、`RUNBOOK.md`、`tools/`，看不到 `reports/`（2026-10-09：`ebf6a1c 🎉 feat: initial commit`；GitHub API 列出 `AGENTS.md`、`RUNBOOK.md`、`tools` 等，`reports/` 只有 `.gitkeep`）

## 2. 移植舊專案的網站程式

來源：`D:\Repo\finance-digest-a\src\finance_digest_a\`（Python 3.13，conda 環境 `finance-digest` 已裝好 `cryptography`、`requests`、`pyyaml`）。**複製再改，不 import 舊 repo**，兩個專案要能各自獨立。

| 舊檔 | 用途 | 移植時要改的地方 |
|---|---|---|
| `render.py` | 報告文字 → 網站用結構（章節、分析師、個股）；產生 LINE 精簡版 `line_short` | 舊版處理的是 Gemini API 的輸出，新版是 Gemini Notebook 的輸出，**章節模板相同**（同一份提示詞衍生），先直接拿 `reports/` 的 7 份實測 `parse_report`，看哪裡解析失敗再改 |
| `crypto.py` | PBKDF2-SHA256 + AES-GCM 站台主金鑰，與瀏覽器 WebCrypto 相容 | 原樣搬 |
| `publish.py` | 產生網站：`index.html`、`data/keyring.json`、`data/index.enc`、`data/r/YYYY-MM-DD.enc`、`YYYY-MM-DD/index.html` 轉址頁 | 輸出目錄從 `site/` 改成 `docs/`；網址前綴從 `/finance-digest-a/` 改成 `/finance-digest/` |
| `site_template/index.html` | 網站本體（解鎖頁 + 單頁應用：最新一期、封存月曆、追蹤） | 改標題、網址前綴；確認「影片來源」連結仍只接受 youtube.com/watch 網址 |
| `guard.py` | commit 前確認 `data/` 與 `docs/` 只有密文（白名單） | 路徑改 `docs/` |
| `line.py` | LINE Messaging API 推播 | **不搬**（2026-10-09 決定不做 LINE 推播） |
| `check.py` | 報告檢查（章節、繁中、簡體字、截斷）與 ISIN 代號比對 | **只搬格式與截斷檢查**；代號比對 Gemini Notebook 已依提示詞用 TWSE 來源處理，先不做 |
| `tests/` | 對應模組的 pytest | 一起搬，fixture 只能用虛構或公開資料（repo 是 public） |

- [x] 建立套件結構（建議 `src/finance_digest/` + `pyproject.toml`，或扁平的 `fd/`，由 Claude Code 決定，寫進 README）→ verify: `pytest -q` 可以跑（2026-10-09：扁平 `fd/` ＋ 根目錄 `publish.py`，不需安裝；`pyproject.toml` 只放 pytest 設定）
- [x] 搬 `crypto.py`、`guard.py` 與測試 → verify: 測試全過（2026-10-09；`line.py` 不搬，見決策紀錄）
- [x] 搬 `render.py`，用 `reports/` 的 7 份報告逐份 `parse_report` → verify: 7 份都 `parse_ok`，分析師數與報告中 `👤` 開頭的行數一致；不 ok 的修 parser，不改報告（2026-10-09：7 份都 ok，分析師數 12／10／9／11／17／10／14 與 `👤` 行數一致。修了一處 parser：總經段「……（名字、名字）。」句號在括號後的寫法，10/05 原本一個講者都解析不到）
- [x] 搬 `publish.py` 與 `site_template/index.html` → verify: 本機產生 `docs/`，用瀏覽器開 `docs/index.html` 輸入密碼看得到 7 期、封存月曆正確（10/3、10/9 灰色）、追蹤頁有資料（2026-10-09：用臨時密碼的複本在 127.0.0.1 檢查，7 期、月曆、追蹤、影片來源連結都正確。修了模板一行 CSS：追蹤頁兩欄 `.grid2` 被長頻道名撐開，桌面版熱門個股欄只剩 131px、手機版橫向溢出 359px，改成 `minmax(0,…)` 後正常）
- [x] 確認 `docs/` 與 `data/` 沒有明文 → verify: `guard` 通過；搜尋報告裡的特徵字串（如「財經節目綜合摘要」）在 `docs/`、`data/` 搜不到（2026-10-09：guard 通過；只在 `docs/index.html` 搜到模板本身的 UI 文字，guard 已確認它與模板逐字相同）

## 3. `publish.py`（RUNBOOK 第 6 步）

命令列：`python publish.py reports/YYYY-MM-DD_EEE.txt [--no-push] [--republish]`

依序做：

1. 讀報告並檢查：第一行是「📅 yyyy/MM/dd (星期X) 財經節目綜合摘要」、有「🔗 影片來源」段、繁體中文。不通過就以非零結束碼結束，不發布。
2. 從 `data/processed.json` 取這份報告的影片清單（`videos` 裡 `report` 等於這份、`status` 為 `included`），組出影片連結 `https://www.youtube.com/watch?v=<id>`。報告本文沒有網址（提示詞禁止），連結只能從這裡來。
3. 組報告資料：日期、版本（平日／週末）、狀態（complete／partial）、影片清單與連結、產生時間、引擎「Gemini Notebook」、提示詞版本（`prompts/提示詞.txt` 的 SHA-256 前 8 碼）、`parse_report` 結果、`line_short`（網站「複製 LINE 版」按鈕用）。
4. 加密存到 `data/reports/YYYY-MM-DD.json.enc`（金鑰來自 `SITE_PASSWORD`）。
5. 重建 `docs/`；已發布的期別不重寫，`--republish` 才覆寫並記更新時間。
6. `guard` 檢查 `docs/` 與 `data/` 只有密文。
7. `git add docs data/reports data/processed.json` → commit `publish: YYYY-MM-DD` → `git pull --rebase` → `git push`（`--no-push` 時跳過）。**這是 AGENTS.md 允許的唯一自動 commit**，只能加這幾個路徑，要在 AGENTS.md 寫明。
8. 輪詢 `https://ycy1997alex.github.io/finance-digest/data/index.enc`，直到 SHA-256 與本機一致（最多 10 分鐘），才算上線。
9. 在 `processed.json` 這份報告的 `runs` 紀錄寫回 `site_published`、`published_at`。

- [x] 實作上述流程 → verify: 同一份報告連跑兩次，第二次不重複 commit（2026-10-09：`tests/test_publish.py` 用假的 git 驗證；真的 push 要等 GitHub Pages 開好再驗。為此改了 -a 的做法：keyring 不再每次重新包、`index.enc` 內容沒變不重寫，否則每跑一次就多一個 commit）
- [x] 錯誤處理：任何一步失敗都要寫清楚哪一步、印出原因、非零結束碼；token 與密碼不出現在任何輸出 → verify: 故意不設 `SITE_PASSWORD`、故意給壞掉的報告，各跑一次（2026-10-09：兩者都印「第 N 步（…）失敗：原因」、結束碼 1；密碼錯誤的訊息不含密碼）
- [ ] 更新 `RUNBOOK.md` 第 6 步（實際指令、結束碼代表什麼、失敗時怎麼記 log）與 `AGENTS.md` 常用指令、自動 commit 的例外 → verify: 本人讀過（2026-10-09 已更新，等本人讀）
- [x] 補發布 10/1～10/8 → verify: `https://ycy1997alex.github.io/finance-digest/` 輸入密碼看得到 7 期；手機開三篇不同長度的報告不爆版（2026-10-09：Pages 開好後 7 份各跑一次 `publish.py`，都確認上線且「沒有變動，不 commit」，`processed.json` 寫回 `site_published`；本人手機實測發現分析師頁頻道名太長會橫向溢出，已修，390px 寬度下 52 位分析師頁與 7 期報告都無溢出）

## 4. LINE 推播（已取消）

2026-10-09 本人決定不做：網頁版已完全達到需要的效果。原本的 LINE 官方帳號、token、群組 ID、`line.py` 移植等項目全部取消；分享改由本人用網站的「複製 LINE 版」按鈕手動貼。

## 5. 排程任務（本人在 Claude Desktop 建立，Claude Code 不需要做）

設定、待辦與第一次執行後的檢查都移到 **`ToDo_ClaudeDesktop.md`**（2026-10-09 本人要求另立一份，避免和這裡重複，這裡不再列項目）。

## 6. 改善項目（不急）

- [ ] `tools/yt_discover.js` 的 `RULES` 與 `config/channels.yaml` 是兩份手寫資料，加一個檢查（pytest 讀 yaml 與 js 比對 inc／exc／min／weekend_only／publish_weekdays）→ verify: 改一邊不改另一邊時測試失敗
- [ ] `config/twse_holidays.json` 只到 2026 年；年底前抓 2027 年的證交所休市日期表（`https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule`）
- [x] `reports/2026-10-02_Fri.txt` 影片來源清單把「黃豐凱」寫成「黃風凱」（Gemini 抄錯）；本人決定要不要手改（2026-10-09：改用校正表 `config/corrections.yaml` 在發布時修正，原稿不動）
- [ ] 校正表 `config/corrections.yaml` 裡待確認的項目：元大 10/07 的「張豐進」是否為「陳豐進」→ 本人確認後拿掉該行開頭的 `#`，重發 10/07
- [ ] 每週看一次 `python -m fd.corrections` 的人名清單，有同一人兩種寫法就加進校正表、重發受影響的期別
- [ ] 每月檢查一次 `processed.json` 有沒有照 RUNBOOK 刪掉 30 天前的紀錄

---

## 決策紀錄

| 日期 | 決定 |
|---|---|
| 2026-10-08 | 放棄 GitHub Actions + Gemini API 路線（免費層每日 20 次請求、模型忙碌 503，10/5～10/6 三次執行全失敗），改用 Claude Desktop 排程 + Claude in Chrome + Gemini Notebook |
| 2026-10-08 | 共用同一本 Gemini Notebook 筆記本，每次只換影片來源並清對話；報告檔名 `YYYY-MM-DD_EEE.txt` |
| 2026-10-09 | 影片清單改用 YouTube 內部 browse API ＋ 觀看頁（RSS 只有 15 支，回溯不夠） |
| 2026-10-09 | 會員專屬影片（標題含「會員專屬」「隱藏版」，或觀看頁有會員徽章且無法播放）一律排除；匯入失敗屬預期，不重試、不註記 |
| 2026-10-09 | 報告從瀏覽器存到本機用 `tools/receive_server.py`（127.0.0.1:8765，閒置 10 分鐘自動結束） |
| 2026-10-09 | GitHub repo `finance-digest` 設為 public |
| 2026-10-09 | 網站 `https://ycy1997alex.github.io/finance-digest/`，設計沿用 finance-digest-a；LINE 推播先不做，先把網站做好 |
| 2026-10-09 | 網站寬度比照 ycy1997alex.github.io：閱讀寬度 820px，電腦版（> 768px）頁首有「滿版寬度」切換鈕，選擇記在 localStorage `fd-width`；報告頁「分析師重點」加「卡片／表格」切換，表格模式有「分析師對照」與「個股 × 分析師」兩張表（記在 `fd-anview`） |
| 2026-10-09 | 主排程 21:42、補跑 22:22 維持；RUNBOOK 第 0 步最先建立執行中鎖檔 `logs/.running`，避免兩次執行重疊（含第 6 步發布）；第 1 步前先檢查 Chrome 帳號，指定信箱放在不進 git 的 `config/account.local.txt`；排程先用 Sonnet 5.5、Effort 中等（Claude Desktop 端待辦見 `ToDo_ClaudeDesktop.md`） |
| 2026-10-09 | Gemini 的人名、頻道寫法不一致或聽錯，用校正表 `config/corrections.yaml` 在發布時修正（`fd/corrections.py`）：只改要發布的副本，`reports/` 原稿不改；分析師別名只改人名位置，影片來源段（YouTube 原始標題）不改 |
| 2026-10-09 | **不做 LINE 推播**：網頁版已完全達到需要的效果，網站是唯一的發布方式。保留網站的「複製 LINE 版」按鈕（`line_short`），需要分享時本人手動貼；不建 LINE 官方帳號、不搬 `line.py` |
| 2026-10-09 | 本人授權 Claude Code 在對話中先用 `/git-commit` 寫訊息後自行 commit 與 push（每段對話各自授權，寫進 AGENTS.md） |
| 2026-10-09 | 報告檢查只有「標題與日期、必要章節（含影片來源）、繁中、無簡體字」擋發布；分析師區塊截斷等只印提醒（10/04 林漢偉區塊是 Gemini 漏寫，報告不改，照原文發布） |
