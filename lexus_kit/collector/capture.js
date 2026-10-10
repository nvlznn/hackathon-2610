// Lexus 論壇擷取書籤（Mobile01 / Dcard）
// 用法：在瀏覽器打開一頁，點書籤一次 → 下載一個 lexus_cap_*.json 到「下載」資料夾。
// - 文章頁：存主文與留言（Mobile01 多頁的串，每一頁各點一次）
// - 列表／搜尋頁：存這頁所有文章連結，之後用 import_captures.py --queue 產生待讀清單
// 只讀你正在看的這一頁，不會自己去抓其他網址。
(async () => {
  const S = ms => new Promise(r => setTimeout(r, ms));
  const clean = t => (t || '').replace(/ /g, ' ').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  const host = location.hostname;
  const toast = msg => {
    const d = document.createElement('div');
    d.textContent = msg;
    d.style.cssText = 'position:fixed;z-index:2147483647;right:16px;bottom:16px;background:#111;color:#fff;padding:10px 14px;border-radius:8px;font:14px sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.4)';
    document.body.appendChild(d); setTimeout(() => d.remove(), 3500);
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
    const arts = [...document.querySelectorAll('article[id^="article_"]')];
    if (!arts.length) {
      const items = links(/https:\/\/www\.mobile01\.com\/topicdetail\.php\?f=\d+&t=\d+/);
      save({ kind: 'queue', site: 'Mobile01', url: location.href, items }, `lexus_queue_m01_${Date.now()}.json`);
      return toast(`Mobile01 列表：存了 ${items.length} 個連結`);
    }
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
    return toast(`Mobile01 第 ${p} 頁：${posts.length} 則` + (next ? '｜還有下一頁，記得也點' : '｜已是最後一頁'));
  }

  if (host.includes('dcard.tw')) {
    const id = (location.pathname.match(/\/p\/(\d+)/) || [])[1];
    if (!id) {
      const items = links(/https:\/\/www\.dcard\.tw\/f\/[^/]+\/p\/\d+/);
      save({ kind: 'queue', site: 'Dcard', url: location.href, items }, `lexus_queue_dcard_${Date.now()}.json`);
      return toast(`Dcard 列表：存了 ${items.length} 個連結`);
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
    return toast(`Dcard：主文 + ${comments.length} 則留言已存`);
  }
  toast('這個書籤只支援 Mobile01 與 Dcard');
})();
