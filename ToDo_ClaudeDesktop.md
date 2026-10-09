# ToDo — Claude Desktop 端（排程任務）

> 建立：2026-10-09（Claude Code 整理）。這裡只放要在 **Claude Desktop** 或這台電腦上由本人動手的事；其餘計畫與決策看 `ToDo.md`。
> 每日流程本身寫在 `RUNBOOK.md`，排程任務只做「讀 RUNBOOK 並照做」，流程要改時改 RUNBOOK，不改排程任務。
> 完成一項就打勾，寫上日期與結果。

---

## 1. 前置（建排程之前）

- [ ] Claude Desktop 已連到這台電腦，而且 Claude in Chrome 擴充功能已連上（Desktop 對話裡能操作 Chrome 分頁）
- [ ] Claude in Chrome 連的那個 Chrome 設定檔，登入的是指定的 Google 帳號（2026-10-09 已確認目前是）
- [ ] `D:\Repo\finance-digest\config\account.local.txt` 存在，第一行是指定信箱（2026-10-09 由 Claude Code 建立；這個檔案不進 git）
- [ ] Claude in Chrome 對 `youtube.com`、`notebook.google.com` 設為永久允許（2026-10-09 實測時沒有跳出詢問，應已允許）
- [ ] Chrome 允許 `notebook.google.com` 存取本機（存檔時會連 `127.0.0.1:8765`）：第一次排程執行時如果跳出「允許網站存取本機裝置」，按允許
- [ ] 電源設定：插電時不睡眠、不休眠；Chrome 與 Claude Desktop 設為開機自動啟動。21:42～23:30 電腦一定要開著（補跑 22:44 開始，重跑整個流程最多約 40 分鐘）
- [ ] 使用者環境變數 `SITE_PASSWORD` 存在（發布網站要用；2026-10-09 已確認存在）。Claude Desktop 是在設定這個變數之前開的話，要重開一次才讀得到

## 2. 建立兩個排程任務

在 Claude Desktop 開新對話（連到這台電腦），請 Claude 建兩個排程任務，或自己在排程介面新增：

| 項目 | 主排程 | 補跑 |
|---|---|---|
| 名稱 | 財經摘要 每日 | 財經摘要 補跑 |
| 時間 | 每天 21:42（台灣時間） | 每天 22:44 |
| 指令 | 見下方 | 同左 |
| 模型 | Sonnet 5.5 | Sonnet 5.5 |
| Effort | 中等 | 中等 |
| 需要這台電腦 | 開 | 開 |
| 核准方式 | 自動核准 | 自動核准 |

指令（兩個排程一樣）：

```text
讀 D:\Repo\finance-digest\RUNBOOK.md，從第 0 步照順序做到最後。檔案裡的規則優先；遇到和 RUNBOOK 描述不同的畫面，照 RUNBOOK「出錯時的原則」處理。
```

- 週六、休市日不用另外設定，RUNBOOK 第 0 步會判斷並直接結束。
- 22:44 補跑的行為：今天已完成就略過；報告做好但網站沒上線就只補發布；21:42 那次還在跑（`logs/.running`）就略過；其餘情況整個重跑。
- 介面如果沒有模型或 Effort 的選項，就用預設值，在下面「4. 紀錄」寫明實際用的是什麼。
- [ ] 主排程已建立
- [ ] 補跑已建立
- [ ] 手動「立即執行」主排程一次測試（在休市日或週六執行，應該只看到 log 寫「不出報告」就結束，不會產生報告）

## 3. 第一次正式執行後

第一份會真的產生報告的是 **2026-10-11（日）週末版**（10/9 國慶日休市、10/10 週六）。

- [ ] 隔天檢查：`logs/2026-10-11_Sun.log` 每一步都有結果、`reports/2026-10-11_Sun.txt` 存在、`data/processed.json` 的 `runs` 有這一筆且 `site_published: true`、網站上看得到 10/11
- [ ] `logs/.running` 沒有殘留（有的話代表某次執行中途結束沒收尾，把 log 給 Claude Code 看）
- [ ] 連續 7 天沒有人工介入，每天都有明確狀態（complete／partial／none／failed 或「不出報告」）
- [ ] 如果第一週常卡在網頁操作或判斷錯誤，改用 Opus 5.5 再觀察一週

## 4. 紀錄

| 日期 | 事項 |
|---|---|
| 2026-10-09 | 本人決定排程先用 Sonnet 5.5、Effort 中等 |
