// 网页版（GitHub Pages）专用：没有后端，把 /api/* 的读请求换成同目录下导出的 JSON。
// 已读 / 不用读 存在浏览器本地（localStorage），换浏览器或清缓存会丢。
// 其他写操作（跑模型、重建索引、添加资料）在网页版里不能用，要本地运行。
(function () {
  window.RADAR_STATIC = true;
  const KEY = 'radar-reading-state';
  const realFetch = window.fetch.bind(window);
  const local = () => { try { return JSON.parse(localStorage.getItem(KEY) || '{}') } catch (e) { return {} } };
  const save = m => localStorage.setItem(KEY, JSON.stringify(m));
  const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  const READONLY = '网页版只能看。勾选已读以外的操作（跑模型、重新生成、添加资料）要在本地运行，见 README';

  window.fetch = async function (url, opt = {}) {
    if (typeof url !== 'string' || !url.startsWith('/api/')) return realFetch(url, opt);
    const method = (opt.method || 'GET').toUpperCase();
    const path = url.split('?')[0].replace(/^\/api\//, '').replace(/\/$/, '');

    if (method === 'GET') {
      const r = await realFetch(`api/${path}.json`, { cache: 'no-cache' });
      if (!r.ok) return json({ error: '网页版没有这项数据' }, 404);
      const data = await r.json();
      if (path === 'reading') {
        const m = local();
        data.items.forEach(x => { if (m[x.id]) x.state = m[x.id] });
      }
      return json(data);
    }

    if (method === 'PUT' && path.startsWith('reading')) {
      const body = JSON.parse(opt.body || '{}'), state = body.state || 'unread';
      const ids = path === 'reading/batch' ? (body.ids || []) : [+path.split('/')[1]];
      const m = local();
      ids.forEach(id => { m[id] = state });
      save(m);
      return json({ ok: true, updated: ids.length, state });
    }
    return json({ error: READONLY }, 400);
  };

  document.addEventListener('DOMContentLoaded', () => {
    ['#add-signal', '#collect-online'].forEach(s => { const el = document.querySelector(s); if (el) el.hidden = true });
    const h = document.querySelector('.health span'); if (h) h.textContent = '网页版 · 每周一更新';
    const f = document.querySelector('#foot-llm'); if (f) f.textContent = '已读勾选只存在这个浏览器里';
  });
})();
