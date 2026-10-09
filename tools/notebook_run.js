// RUNBOOK 第 3、4 步：在 Gemini Notebook 筆記本分頁用 Claude in Chrome 的 javascript_tool 執行。
// 用法：
//   1. 本檔整段送進 javascript_tool（定義函式）
//   2. runReport('2026-10-12', ids, lines)   ← 不要 await，它在背景跑（javascript_tool 單次最多 45 秒）
//      ids   = 影片 ID 陣列；lines = 「標題｜頻道全名」陣列（順序與 ids 相同）
//   3. 每 30～60 秒查一次：JSON.stringify(JS)  → step 依序為 remove / add / ask / gen / done（或 error）
//   4. done 之後報告全文在 localStorage 'fd_<日期>'；讀出方法見 RUNBOOK 第 5 步
// 前提：視窗夠寬（約 1400px），窄版面會變成「來源／對話／工作室」分頁，textarea 找不到。

const sleep = ms => new Promise(r => setTimeout(r, ms));

// 固定來源：TWSE 三個 ISIN 頁面與提示詞（貼上文字來源，標題「台灣財經 YouTube 影片摘要指令」）。其餘都視為影片來源。
window.KEEP = t => /^https:\/\/isin\.twse\.com\.tw/.test(t) || t.startsWith('台灣財經 YouTube 影片摘要指令');

window.srcTitles = () => {
  const seen = new Set();
  return [...document.querySelectorAll('.single-source-container')].map(e => ({
    t: (e.querySelector('[class*=source-title]')?.innerText || '').trim(),
    err: !!e.querySelector('[aria-label="錯誤資訊"]'),
    busy: !!e.querySelector('mat-spinner,[role=progressbar],.mat-mdc-progress-spinner')
  })).filter(x => x.t && !seen.has(x.t) && seen.add(x.t));
};

// 刪除所有影片來源（固定來源不動）。每支會跳出「要刪除…嗎？」確認框，按「刪除」。
window.removeVideos = async function () {
  let n = 0;
  for (let k = 0; k < 60; k++) {
    const it = [...document.querySelectorAll('.single-source-container')].find(e => { const t = (e.querySelector('[class*=source-title]')?.innerText || '').trim(); return t && !KEEP(t); });
    if (!it) break;
    [...it.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === '更多').click(); await sleep(600);
    [...document.querySelectorAll('[role=menuitem]')].find(m => m.innerText.includes('移除來源')).click(); await sleep(700);
    [...document.querySelectorAll('[role=dialog] button')].find(b => b.innerText.trim() === '刪除').click(); await sleep(1500);
    n++;
  }
  return n;
};

// 清掉上一次的對話，避免舊報告影響新報告（筆記本設定 → 刪除對話記錄）
window.clearChat = async function () {
  [...document.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === '筆記本設定').click(); await sleep(800);
  const mi = [...document.querySelectorAll('[role=menuitem]')].find(m => m.innerText.includes('刪除對話記錄'));
  if (mi && !mi.hasAttribute('disabled') && mi.getAttribute('aria-disabled') !== 'true') {
    mi.click(); await sleep(800);
    const b = [...document.querySelectorAll('[role=dialog] button')].find(b => b.innerText.trim() === '刪除');
    if (b) { b.click(); await sleep(1500); }
  } else {
    document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    document.querySelector('.cdk-overlay-backdrop')?.click(); await sleep(400);
  }
};

// 新增來源 → 網站 → 一次貼上多個網址（換行分隔）→ 插入
window.addUrls = async function (urls) {
  [...document.querySelectorAll('button')].find(b => b.innerText.trim().endsWith('新增來源')).click(); await sleep(1200);
  [...document.querySelectorAll('[role=dialog] button')].find(b => b.innerText.includes('網站')).click(); await sleep(1000);
  const ta = document.querySelector('[role=dialog] textarea');
  ta.focus(); ta.value = urls.join('\n'); ta.dispatchEvent(new Event('input', {bubbles: true})); await sleep(500);
  [...document.querySelectorAll('[role=dialog] button')].find(b => b.innerText.trim() === '插入').click();
  return urls.length;
};

window.ask = async function (msg) {
  const ta = document.querySelector('textarea[aria-label="查詢方塊"]');
  ta.focus(); ta.value = msg; ta.dispatchEvent(new Event('input', {bubbles: true})); await sleep(600);
  [...document.querySelectorAll('button[aria-label="提交"]')].at(-1).click();
};

// 讀最後一則回覆。回覆裡每一行是一個 <span>，換行是內容只有空白的 <span>；段落是 div.paragraph。
window.grab = function () {
  const c = [...document.querySelectorAll('.to-user-message-inner-content')].at(-1);
  return [...c.querySelectorAll('div.paragraph')].map(p =>
    [...p.querySelectorAll('span')].filter(s => !s.querySelector('span'))
      .map(s => /^\s+$/.test(s.textContent) ? '\n' : s.textContent).join('')
      .replace(/[ \t]+\n/g, '\n').trim()
  ).join('\n\n');
};

window.runReport = async function (date, ids, lines) {
  window.JS = {date, step: 'start'};
  try {
    JS.step = 'remove'; JS.removed = await removeVideos(); await clearChat();
    JS.step = 'add'; await addUrls(ids.map(i => 'https://www.youtube.com/watch?v=' + i)); await sleep(5000);
    for (let i = 0; i < 60; i++) { const s = srcTitles(); if (!s.some(x => x.busy)) break; await sleep(3000); }
    await sleep(3000);
    const s = srcTitles();
    JS.sources = s.length;
    JS.failed = s.filter(x => x.err && !KEEP(x.t)).map(x => x.t);
    // 匯入失敗的影片從來源對照表拿掉（失敗來源的標題可能是網址，也可能是影片標題）
    const bad = (i, l) => JS.failed.some(t => t.includes(ids[i]) || l.startsWith(t.slice(0, 20)));
    JS.failedIds = ids.filter((id, i) => bad(i, lines[i]));
    lines = lines.filter((l, i) => !bad(i, l));
    if (!lines.length) { JS.step = 'error'; JS.err = 'all_imports_failed'; return; }
    JS.step = 'ask';
    const msg = '依照來源「台灣財經 YouTube 影片摘要指令」的規則書，處理本筆記本中的全部 YouTube 影片來源，直接輸出最終報告。\n本次來源對照表如下，這是唯一合法的標題與頻道來源：\n'
      + lines.map((l, i) => `☞ 影片${i + 1}. ${l}`).join('\n');
    await ask(msg); await sleep(8000);
    JS.step = 'gen';
    for (let i = 0; i < 120; i++) { const ta = document.querySelector('textarea[aria-label="查詢方塊"]'); if (!/正在回覆/.test(ta.placeholder || '')) break; await sleep(5000); }
    await sleep(4000);
    const rep = grab();
    localStorage.setItem('fd_' + date, rep);
    JS.len = rep.length; JS.head = rep.slice(0, 40); JS.step = 'done';
  } catch (e) { JS.step = 'error'; JS.err = String(e); }
};
