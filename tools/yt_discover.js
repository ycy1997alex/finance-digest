// RUNBOOK 第 1、2 步：在 youtube.com 分頁用 Claude in Chrome 的 javascript_tool 執行。
// 用法：先把本檔整段送進 javascript_tool（定義函式），再呼叫
//   await discover({windows:[...]})
// windows 每項：{rep:'2026-10-12', lo:'2026-10-08T21:42', hi:'2026-10-12T21:42', weekend:true, wkLo:'2026-10-04T21:42'}
//   lo/hi 為台灣時間；weekend=true 時 weekend_only 頻道改用 wkLo 起算，並套用 days（publish_weekdays）
// 結果存在 window.CAND（全部候選）與 window.REP（各報告納入的影片：{id, ch, title}）。
// 只回傳摘要；要看清單時用 repLines('2026-10-12') 分段取出（javascript_tool 的輸出約 1,200 個中文字就會被截斷）。

window.CH = {"理財達人秀":"UCQvsuaih5lE0n_Ne54nNezg","鈔錢部署":"UCA_hK5eRICBdSOLlXKESvEg","兆華艾綸說":"UCFeC_WM6JkH9AlpkEBAmEXg","艾綸說":"UCE5zlVSpAS5BAEsH-yHJWYw","林睿閎":"UCXB8cCqwOHP3BmyhYLAUs0g","老王":"UCvnLmiWt_zIVIh0zUm_j4Hw","元大":"UCS1bMmw249R7R0wDjAmE6CA","股科大夫":"UCIGgxcEdDc09iBuzPZkYz8Q","林漢偉":"UCleWOsRmPBhWPvQlSTy7fPw","陳昆仁":"UCiBLyIFu3KjG2opa7uQHZbQ","游庭皓":"UC0lbAQVpenvfA2QqzsRtL_g","投資嗨什麼":"UC99pEneQfxE8Tg3uNa9QXEw","股癌":"UC23rnlQU_qE3cec9x709peA","柴鼠":"UC45i13dEfEVac2IEJT_Nr5Q","蔡明翰":"UCd0Ql3lJzJsSzcFo3NiGbAA","先探":"UCIq8cvi04DdnGA2qkEIJccA","李兆華":"UCKgQbeP5tNkg9rk2X6vJR7A","股添樂":"UCdTxhKgAELUs-dFRL8IYs1g","MacroMicro":"UC6LU7FUBvbFCh_cQasrHZ_Q"};

// 與 config/channels.yaml 一致；改規則時兩邊一起改。
window.RULES = {
"理財達人秀":{inc:"^【理財達人秀】",exc:"精華",min:1800},
"鈔錢部署":{inc:"",exc:"精華",min:180},
"兆華艾綸說":{inc:"^【兆華艾綸說】",exc:"精華",min:1800},
"艾綸說":{inc:"",exc:"精華|【這次綸到誰",min:180},
"林睿閎":{inc:"【請支援輸贏】",exc:"精華",min:180},
"老王":{inc:"【老王不只三分鐘】",exc:"精華",min:180},
"元大":{inc:"",exc:"精華|《睿涵說財經》",min:180},
"股科大夫":{inc:"",exc:"精華",min:180},
"林漢偉":{inc:"",exc:"精華|【台股歐嗨唷",min:180},
"陳昆仁":{inc:"",exc:"精華|盤前",min:180},
"游庭皓":{inc:"",exc:"精華",min:180},
"投資嗨什麼":{inc:"",exc:"精華",min:180},
"股癌":{inc:"",exc:"精華",min:180},
"柴鼠":{inc:"",exc:"精華",min:180,wk:1},
"蔡明翰":{inc:"《股市先修班》",exc:"",min:180,wk:1},
"先探":{inc:"鎖定投資最錢線",exc:"",min:180,wk:1,days:[5]},
"李兆華":{inc:"週報",exc:"",min:180,wk:1},
"股添樂":{inc:"",exc:"",min:180,wk:1,days:[7]},
"MacroMicro":{inc:"",exc:"",min:1800,wk:1,days:[7]}};

// 報告來源對照表用的頻道全名
window.NAME = {"理財達人秀":"理財達人秀","鈔錢部署":"鈔錢部署–華視優選","兆華艾綸說":"兆華艾綸說","艾綸說":"艾綸說","林睿閎":"林睿閎分析師-John","老王":"老王愛說笑","元大":"元大投顧財金頻道-理財最錢線","股科大夫":"股科大夫容逸燊","林漢偉":"林漢偉分析師-摩爾證券投顧","陳昆仁":"陳昆仁分析師-摩爾證券投顧","游庭皓":"游庭皓的財經皓角","投資嗨什麼":"投資嗨什麼","股癌":"Gooaye 股癌","柴鼠":"柴鼠兄弟 ZRBros","蔡明翰":"財經震翰彈_蔡明翰","先探":"先探i投資","李兆華":"李兆華River","股添樂":"股添樂 股市新觀點","MacroMicro":"MacroMicro財經M平方"};

// 會員專屬影片 Notebook 匯入不了，一律排除（reason: members_only）
window.MEMBERS_ONLY = /會員專屬|隱藏版/;

window.ytBrowse = async function (body) {
  const key = ytcfg.get('INNERTUBE_API_KEY');
  const r = await fetch(`/youtubei/v1/browse?key=${key}&prettyPrint=false`, {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({context: ytcfg.get('INNERTUBE_CONTEXT'), ...body})});
  return r.json();
};

// 從 browse 回應抓影片（lockupViewModel）與「下一頁」token（只取影片格線最後一格的 continuation）
window.lk = function (o, acc) {
  if (!o || typeof o !== 'object') return;
  if (Array.isArray(o) && o.some(x => x && x.richItemRenderer)) {
    const t = o.at(-1)?.continuationItemRenderer?.continuationEndpoint?.continuationCommand?.token;
    if (t) acc.c = t;
  }
  if (o.lockupViewModel && o.lockupViewModel.contentType === 'LOCKUP_CONTENT_TYPE_VIDEO') {
    const s = JSON.stringify(o.lockupViewModel);
    acc.v.push({id: o.lockupViewModel.contentId,
      title: (s.match(/"lockupMetadataViewModel":\{"title":\{"content":"((?:[^"\\]|\\.)*)"/) || [])[1] || '',
      ago: (s.match(/"content":"([^"]*前)"/) || [])[1] || ''});
    return;
  }
  for (const k in o) window.lk(o[k], acc);
};

// 「X 天前」粗篩：只保留兩週內（精確時間之後由觀看頁取得）
window.recent = a => { a = a.replace(/^.*?：/, ''); return /(分鐘|小時|秒)前/.test(a) || /^([1-9]|1[0-3]) 天前/.test(a) || /^[12] 週前/.test(a) || a === ''; };

window.tab = async function (id, params, pages) {
  let all = [], acc = {v:[], c:null};
  window.lk(await ytBrowse({browseId:id, params}), acc); all.push(...acc.v);
  for (let i = 1; i < pages && acc.c && recent(all.at(-1)?.ago || ''); i++) {
    const tok = acc.c; acc = {v:[], c:null};
    window.lk(await ytBrowse({continuation: tok}), acc); all.push(...acc.v);
  }
  const seen = new Set(); return all.filter(v => !seen.has(v.id) && seen.add(v.id));
};

window.watchInfo = async function (v) {
  const h = await (await fetch('/watch?v=' + v.id)).text();
  const g = re => (h.match(re) || [])[1];
  v.sec = +g(/"lengthSeconds":"(\d+)"/) || 0;
  v.pub = g(/"publishDate":"([^"]+)"/);
  v.end = g(/"endTimestamp":"([^"]+)"/);
  v.isLive = g(/"isLiveNow":(true|false)/);
  v.upcoming = /"isUpcoming":true/.test(h);
  // 會員專屬：標題不一定有「會員專屬」字樣（例：先探 kW0wSz7zOZE），以觀看頁的徽章／無法播放狀態判斷
  v.members = /BADGE_STYLE_TYPE_MEMBERS_ONLY|"sponsorsOnly"|會員專屬/.test(h) && /"playabilityStatus":\{"status":"(UNPLAYABLE|LOGIN_REQUIRED)"/.test(h);
  v.ttl = (g(/<meta name="title" content="([^"]*)"/) || v.title).replace(/&quot;/g,'"').replace(/&amp;/g,'&').replace(/&#39;/g,"'");
  return v;
};

window.discover = async function ({windows, skip = []}) {
  const T = s => Date.parse(s + '+08:00');
  const dow = ms => (new Date(ms + 8*3600e3).getUTCDay() || 7);
  window.CAND = [];
  await Promise.all(Object.entries(CH).map(async ([n, id]) => {
    const v = await tab(id, 'EgZ2aWRlb3PyBgQKAjoA', 6);            // 影片分頁
    const s = await tab(id, 'EgdzdHJlYW1z8gYECgJ6AA%3D%3D', 4).catch(() => []);  // 直播分頁
    const r = RULES[n], seen = new Set();
    for (const x of [...v, ...s]) {
      if (seen.has(x.id) || !recent(x.ago)) continue; seen.add(x.id);
      const t = x.title.replace(/\\"/g, '"');
      if (r.inc && !new RegExp(r.inc).test(t)) continue;
      if (r.exc && new RegExp(r.exc).test(t)) continue;
      CAND.push({ch:n, id:x.id, title:t});
    }
  }));
  for (let i = 0; i < CAND.length; i += 8) await Promise.all(CAND.slice(i, i+8).map(v => watchInfo(v).catch(e => v.err = String(e))));
  for (const v of CAND) {
    const r = RULES[v.ch]; v.rep = null;
    v.t = Date.parse(v.end || v.pub);
    if (skip.includes(v.id)) { v.why = 'already_included'; continue; }
    if (v.err || !v.t) { v.why = 'noinfo'; continue; }
    if (v.isLive === 'true') { v.why = 'live_not_ended'; continue; }
    if (v.upcoming && !v.end) { v.why = 'upcoming'; continue; }
    for (const w of windows) {
      if (r.wk && !w.weekend) continue;
      const lo = T(r.wk && w.weekend ? w.wkLo : w.lo), hi = T(w.hi);
      if (v.t > lo && v.t <= hi) { v.rep = w.rep; break; }
    }
    if (!v.rep) { v.why = 'out_of_window'; continue; }
    if (v.sec <= r.min) { v.why = 'too_short'; continue; }
    if (r.days && !r.days.includes(dow(Date.parse(v.pub)))) { v.why = 'weekday_filtered'; continue; }
    if (v.members || MEMBERS_ONLY.test(v.ttl)) { v.why = 'members_only'; continue; }
    v.why = 'OK';
  }
  window.REP = {};
  for (const v of CAND.filter(v => v.why === 'OK').sort((a, b) => a.t - b.t)) (REP[v.rep] ||= []).push({id:v.id, ch:NAME[v.ch], title:v.ttl});
  const sum = {}; for (const v of CAND) if (v.rep || v.why === 'live_not_ended' || v.why === 'upcoming') { const k = (v.rep || '-') + '|' + v.why; sum[k] = (sum[k] || 0) + 1; }
  return JSON.stringify(sum);
};

// 一行一支：影片ID|標題｜頻道全名
window.repLines = rep => (REP[rep] || []).map(v => `${v.id}|${v.title}｜${v.ch}`).join('\n');
