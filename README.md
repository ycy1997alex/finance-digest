# finance-digest

台灣財經 YouTube 節目每日摘要，改用 **Claude Desktop 排程任務 + Claude in Chrome + Gemini Notebook（原 NotebookLM）** 的路線。

每天 21:42 由排程任務讀 `RUNBOOK.md` 照做：用 Chrome 找出各頻道的新影片 → 貼進固定的 Gemini Notebook 筆記本 → 用提示詞檔產生當日綜合報告 → 存成 `reports/YYYY-MM-DD_EEE.txt` → 執行 `publish.py` 發布到加密網站 https://ycy1997alex.github.io/finance-digest/ 。網站是唯一的發布方式，不做 LINE 推播。22:22 補跑，今天已完成就直接結束。

## 和 finance-digest-a 的差別

`D:\Repo\finance-digest-a` 走 GitHub Actions + YouTube Data API + Gemini API，程式完整，但卡在 Gemini API 免費層：

- 每天 20 次請求、8 小時影片的上限，逐支摘要 + 合併很快就用完（10/6 合併時被 429 擋下）
- 模型忙碌（503）時整批失敗，10/5、10/6 三次執行都是 `failed`，沒有產出任何報告

這個版本把「讀影片、寫摘要」換回已用了幾個月、品質穩定的 Gemini Notebook，其餘盡量沿用 -a 的成果：

| 沿用 | 來源 |
|---|---|
| 19 個頻道與篩選規則 | `config/channels.yaml`（原檔照抄） |
| 證交所休市日期表 | `config/twse_holidays.json` |
| 平日版／週日週末版／休市不出報告（D17） | 寫進 `RUNBOOK.md` 第 0 步 |
| 待補 48 小時／3 次期限（D13） | 寫進 `RUNBOOK.md` 第 2 步 |
| 加密網站 | -a 的 `render`、`crypto`、`publish`、`guard` 模組與網站模板，複製到 `fd/`（不 import 舊 repo）；網站設計照舊 |
| LINE 推播 | 不沿用（2026-10-09 決定只發布網站）；網站上的「複製 LINE 版」按鈕保留，需要時手動貼 |

## 目錄

```
finance-digest/
├── RUNBOOK.md              排程任務每天照做的步驟
├── prompts/提示詞.txt       Gemini Notebook 用的提示詞原稿（筆記本裡是它的貼上文字來源）
├── tools/
│   ├── yt_discover.js      在 youtube.com 分頁執行：找新影片、套篩選規則、分配到各報告
│   └── notebook_run.js     在筆記本分頁執行：換影片來源、送指令、等生成、讀出報告
├── config/
│   ├── channels.yaml       頻道與篩選規則
│   └── twse_holidays.json  證交所休市日期表
├── data/
│   ├── processed.json      已處理影片、待補影片、每次執行紀錄
│   └── reports/            加密後的報告資料 YYYY-MM-DD.json.enc（進 git）
├── reports/                每日報告明文 YYYY-MM-DD_EEE.txt（不進 git）
├── logs/                   每次執行的紀錄
├── publish.py              發布一份報告到網站（RUNBOOK 第 6 步）
├── fd/                     publish.py 用的模組
│   ├── render.py           報告文字 → 網站用結構、「複製 LINE 版」用的精簡版
│   ├── website.py          產生 docs/（只寫有變動的檔案）
│   ├── crypto.py           PBKDF2 + AES-GCM，與瀏覽器 WebCrypto 相容
│   ├── guard.py            確認 docs/、data/ 只有密文
│   ├── check.py            報告格式檢查
│   └── site_template/      網站本體 index.html
├── docs/                   GitHub Pages 網站（全部是密文，publish.py 產生）
└── tests/                  pytest
```

## 網站

- 網址 https://ycy1997alex.github.io/finance-digest/ ，GitHub Pages 從 `main` 分支的 `/docs` 部署，本機 push 後自動上線。
- 打開時輸入密碼（使用者環境變數 `SITE_PASSWORD`）才看得到內容：瀏覽器用密碼解開 `docs/data/keyring.json` 裡的主金鑰，再解開各期報告。repo 與網站上都只有密文，`noindex`。
- 每期固定網址 `…/finance-digest/YYYY-MM-DD/`，會轉到該期頁面。
- 換密碼：`fd.website.rotate_key(data_dir, docs_dir, 舊密碼, 新密碼)` 換新的主金鑰並重新加密全部檔案（只重新包主金鑰擋不住知道舊密碼的人，因為 git 歷史裡還有舊 keyring），然後改 `SITE_PASSWORD`、commit 並 push。

## 安裝與執行

```powershell
$py = "C:\Users\Alex\anaconda3\envs\finance-digest\python.exe"   # conda 環境 finance-digest：cryptography、requests、pytest
$env:PYTHONIOENCODING = "utf-8"
& $py publish.py reports\2026-10-08_Thu.txt --no-push   # 只在本機產生 docs\
& $py -m pytest -q
```

不需要 `pip install`：`publish.py` 直接 import 同目錄的 `fd/`，`pyproject.toml` 只放依賴說明與 pytest 設定。

## 分工

- **Claude Desktop（排程任務）**：每天照 `RUNBOOK.md` 執行。
- **Claude in Chrome**：操作 YouTube 與 Gemini Notebook 網頁。
- **Claude Code**：開發與維護 `publish.py`、除錯。
- **你**：看報告、改提示詞、需要時修改 `RUNBOOK.md`。
