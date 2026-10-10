// Lexus 論壇擷取書籤（Mobile01 / Dcard）
// 用法：在瀏覽器打開一頁，點書籤一次 → 下載一個 lexus_cap_*.json 到「下載」資料夾。
// - 文章頁：存主文與留言；每頁由使用者按書籤觸發
// - 列表／搜尋頁：將連結加入本網站瀏覽器佇列，並下載備份
// 只讀你正在看的這一頁，不會自己去抓其他網址。
(async () => {
  const S = ms => new Promise(r => setTimeout(r, ms));
  const clean = t => (t || '').replace(/ /g, ' ').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  const host = location.hostname;
  const toast = (msg, action) => {
    const d = document.createElement('div');
    d.style.cssText = 'position:fixed;z-index:2147483647;right:16px;bottom:16px;background:#111;color:#fff;padding:10px 14px;border-radius:8px;font:14px sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.4);max-width:90vw';
    const label = document.createElement('span'); label.textContent = msg; d.appendChild(label);
    if (action) {
      const b = document.createElement('button'); b.textContent = '停止自動跳轉';
      b.style.cssText = 'margin-left:12px;padding:5px 8px;cursor:pointer';
      b.onclick = () => { action.cancelled = true; b.textContent = '已停止'; };
      d.appendChild(b);
    }
    document.body.appendChild(d); setTimeout(() => d.remove(), 3500);
  };
  const readQueue = () => { try { const q = JSON.parse(localStorage.getItem('lexus_queue') || '[]'); return Array.isArray(q) ? q : []; } catch (_) { return []; } };
  const readDone = () => { try { const d = JSON.parse(localStorage.getItem('lexus_done') || '[]'); return Array.isArray(d) ? d : []; } catch (_) { return []; } };
  const saveQueue = items => {
    const q = readQueue(), byUrl = new Map(q.map(x => [x.url, x]));
    items.forEach(x => { if (x.url && !byUrl.has(x.url)) byUrl.set(x.url, x); });
    localStorage.setItem('lexus_queue', JSON.stringify([...byUrl.values()]));
    return [...byUrl.values()];
  };
  const itemId = url => { try { const u = new URL(url); return u.hostname.includes('mobile01.com') ? (u.searchParams.get('t') || url) : ((u.pathname.match(/\/p\/(\d+)/) || [])[1] || url); } catch (_) { return url; } };
  const progress = () => { const q = readQueue(), d = readDone(); return `已完成 ${q.filter(x => d.includes(x.url) || d.includes(itemId(x.url))).length}／佇列 ${q.length}`; };
  const nextQueued = () => { const q = readQueue(), d = readDone(); return q.find(x => !d.includes(x.url) && !d.includes(itemId(x.url))); };
  const markDone = (url, id) => { const d = readDone(); [url, id].forEach(x => { if (x && !d.includes(x)) d.push(x); }); localStorage.setItem('lexus_done', JSON.stringify(d)); };
  const goWithToast = (url, msg) => {
    const control = { cancelled: false };
    toast(`${msg}｜${progress()}`, control);
    setTimeout(() => { if (!control.cancelled) location.href = url; }, 2000);
  };
  const save = (rec, name) => {
    rec.captured_at = new Date().toISOString();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(rec)], { type: 'application/json' }));
    a.download = name; document.body.appendChild(a); a.click(); a.remove();
  };
  const links = (re) => {
    const seen = new Map();
    document.querySelectorAll('a[href]').forEach(a => {
      const m = a.href.match(re); const title = clean(a.innerText).split('\n')[0];
      if (m && title && !seen.has(m[0])) seen.set(m[0], title);
    });
    return [...seen].map(([url, title]) => ({ url, title }));
  };

  if (host.includes('mobile01.com')) {
    const u = new URL(location.href);
    if (!document.querySelector('article[id^="article_"]')) {
      const items = links(/https:\/\/www\.mobile01\.com\/topicdetail\.php\?f=\d+&t=\d+/);
      saveQueue(items);
      save({ kind: 'queue', site: 'Mobile01', url: location.href, items }, `lexus_queue_m01_${Date.now()}.json`);
      return toast(`Mobile01 列表：存了 ${items.length} 個連結｜${progress()}`);
    }
    toast('Mobile01：載入文章中，請稍候…');
    let stable = 0, height = 0;
    for (let i = 0; i < 20 && stable < 3; i++) {
      window.scrollTo(0, document.body.scrollHeight); await S(600);
      const h = document.body.scrollHeight; stable = h === height ? stable + 1 : 0; height = h;
    }
    const arts = [...document.querySelectorAll('article[id^="article_"]')];
    const posts = arts.map(a => {
      let c = a;
      while (c.parentElement && !c.querySelector('.c-authorInfo__id')) c = c.parentElement;
      const body = a.cloneNode(true);
      body.querySelectorAll('blockquote, script, style').forEach(b => b.remove());
      const m = (c.innerText.match(/(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*#(\d+)/) || []);
      return {
        aid: a.id,
        user: clean(c.querySelector('.c-authorInfo__id')?.innerText),
        time: m[1] || '', floor: m[2] ? +m[2] : null,
        content: clean(body.innerText),
      };
    });
    const t = u.searchParams.get('t'), p = +(u.searchParams.get('p') || 1);
    save({ kind: 'thread', site: 'Mobile01', board: u.searchParams.get('f'), thread: t, page: p,
           url: location.href, title: document.title.replace(/\s*-\s*Mobile01\s*$/, ''), posts },
         `lexus_cap_m01_${t}_p${p}.json`);
    const next = document.querySelector('a[href*="&p=' + (p + 1) + '"]');
    if (next) return goWithToast(next.href, `2 秒後前往下一頁（再按一次書籤）`);
    const url = location.href, id = t || url; markDone(url, id);
    const queued = nextQueued();
    return queued ? goWithToast(queued.url, `Mobile01 第 ${p} 頁：${posts.length} 則已存，前往下一串`) : toast(`Mobile01 第 ${p} 頁：${posts.length} 則已存｜佇列已完成｜${progress()}`);
  }

  if (host.includes('dcard.tw')) {
    const id = (location.pathname.match(/\/p\/(\d+)/) || [])[1];
    if (!id) {
      const items = links(/https:\/\/www\.dcard\.tw\/f\/[^/]+\/p\/\d+/);
      saveQueue(items);
      save({ kind: 'queue', site: 'Dcard', url: location.href, items }, `lexus_queue_dcard_${Date.now()}.json`);
      return toast(`Dcard 列表：存了 ${items.length} 個連結｜${progress()}`);
    }
    toast('Dcard：載入留言中，請稍候…');
    for (let i = 0; i < 12; i++) {
      window.scrollTo(0, document.body.scrollHeight);
      await S(700);
      [...document.querySelectorAll('button, span, div')]
        .filter(e => e.children.length === 0 && /^(View \d+ more (comments|replies)|查看(其他|更多)?\s*\d*\s*則?(留言|回覆)|顯示更多留言)/.test(e.textContent.trim()))
        .forEach(e => e.click());
    }
    const art = document.querySelector('article');
    const times = [...document.querySelectorAll('time[datetime]')];
    const outside = times.filter(t => !art || !art.contains(t));
    const comments = []; const seen = new Set();
    outside.forEach(t => {
      let c = t;
      while (c.parentElement && c.parentElement.querySelectorAll('time').length === 1) c = c.parentElement;
      const text = clean(c.innerText.replace(/\n(Reply|Quote|Share|回覆|引用|分享)(?=\n|$)/g, ''));
      if (text && !seen.has(text) && text.length < 4000) { seen.add(text); comments.push({ time: t.getAttribute('datetime'), content: text }); }
    });
    const forum = (location.pathname.match(/\/f\/([^/]+)/) || [])[1];
    const title = clean(art?.querySelector('h1, h2')?.innerText) || document.title;
    let content = clean(art ? art.innerText : '');
    const full = document.body.innerText, i0 = full.indexOf(title);
    if (i0 >= 0) {
      const ends = ['More posts from', '更多來自', 'Check out', 'All comments', '全部留言'].map(k => full.indexOf(k, i0)).filter(x => x > 0);
      const alt = clean(full.slice(i0, ends.length ? Math.min(...ends) : i0 + 8000));
      if (alt.length > content.length) content = alt;
    }
    save({ kind: 'post', site: 'Dcard', id, board: forum, url: location.href.split('?')[0],
           title,
           published: (art?.querySelector('time[datetime]') || times[0])?.getAttribute('datetime') || '',
           content, comments },
         `lexus_cap_dcard_${id}.json`);
    const url = location.href.split('?')[0]; markDone(url, id);
    const queued = nextQueued();
    return queued ? goWithToast(queued.url, `Dcard：主文 + ${comments.length} 則留言已存，前往下一篇`) : toast(`Dcard：主文 + ${comments.length} 則留言已存｜佇列已完成｜${progress()}`);
  }
  toast('這個書籤只支援 Mobile01 與 Dcard');
})();
