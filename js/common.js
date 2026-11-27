/* 星匣 · 公共工具 */
/* 统一 SVG 图标库（描边风格，currentColor 继承，18/24 两种尺寸） */
const ICONS = {
  sparkle:'<path d="M12 2l1.6 6.4L20 10l-6.4 1.6L12 18l-1.6-6.4L4 10l6.4-1.6L12 2z"/><path d="M19 15l.7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7L19 15z"/>',
  image:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="M21 16l-5-5-6 7-3-3-4 5"/>',
  file:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h6"/>',
  article:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  book:'<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 5v16M8 7h7"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  pen:'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z"/>',
  upload:'<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  download:'<path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>',
  globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/>',
  lock:'<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  key:'<circle cx="8" cy="15" r="4"/><path d="M11 12l8-8M16 7l2 2M14 9l2 2"/>',
  eye:'<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"/><circle cx="12" cy="12" r="3"/>',
  pin:'<path d="M12 17v5"/><path d="M9 3h6l-1 6 3 3H7l3-3z"/>',
  copy:'<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  link:'<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
  trash:'<path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6"/>',
  edit:'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  users:'<circle cx="9" cy="8" r="3.5"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M17 5a3.5 3.5 0 0 1 0 7M18 21a7 7 0 0 0 4-6"/>',
  box:'<path d="M21 8l-9-5-9 5 9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8M12 13v8"/>',
  settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1-2.8 2.8-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21h-4v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1L4.4 17l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3v-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8L4.2 7.3 7 4.5l.1.1a1.6 1.6 0 0 0 1.8.3 1.6 1.6 0 0 0 1-1.5V3h4v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1 2.8 2.8-.1.1a1.6 1.6 0 0 0-.3 1.8 1.6 1.6 0 0 0 1.5 1H21v4h-.1a1.6 1.6 0 0 0-1.5 1z"/>',
  shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
  ban:'<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/>',
  key2:'<circle cx="8" cy="15" r="4"/><path d="M11 12l8-8M16 7l2 2M14 9l2 2"/>',
  inbox:'<path d="M3 12h5l2 3h4l2-3h5"/><path d="M4 5h16l1 7v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-6z"/>',
  layers:'<path d="M12 2l9 5-9 5-9-5 9-5z"/><path d="M3 12l9 5 9-5M3 17l9 5 9-5"/>',
  gallery:'<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>',
  heart:'<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.7-7.5 1.1-1.1a5.5 5.5 0 0 0 0-7.8z"/>',
  heartFill:'<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.7-7.5 1.1-1.1a5.5 5.5 0 0 0 0-7.8z" fill="currentColor" stroke="none"/>',
  share:'<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 10.5l6.8-4M8.6 13.5l6.8 4"/>',
  bolt:'<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
  sparkOff:'<path d="M12 2l1.6 6.4L20 10l-6.4 1.6L12 18l-1.6-6.4L4 10l6.4-1.6L12 2z"/>'
};
function icon(name, size=18, cls=''){
  const p = ICONS[name] || ICONS.file;
  return `<svg class="ico ${cls}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
}
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));
const esc = (s='') => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmtSize = n => n < 1024 ? n+' B' : n < 1048576 ? (n/1024).toFixed(1)+' KB' : (n/1048576).toFixed(1)+' MB';
const fmtDate = s => (s||'').replace(' ', ' · ').slice(0,16);

let CONFIG = {};
async function api(path, opts={}){
  const r = await fetch(path, {credentials:'same-origin', ...opts,
    headers: opts.body instanceof FormData ? (opts.headers||{}) : {'Content-Type':'application/json', ...(opts.headers||{})} });
  let d = {};
  try { d = await r.json(); } catch(e){}
  if(!r.ok){
    const err = new Error(d.error || ('请求失败 '+r.status));
    err.data = d; err.status = r.status;
    throw err;
  }
  return d;
}
const post = (p, d) => api(p, {method:'POST', body: JSON.stringify(d||{})});
const patch = (p, d) => api(p, {method:'PATCH', body: JSON.stringify(d||{})});
const del = p => api(p, {method:'DELETE'});
const ME = () => CONFIG.me;

async function loadConfig(){
  CONFIG = await api('/api/config');
  $$('.logo-mark').forEach(el => { el.innerHTML = icon('sparkle',19); });
  document.title = (CONFIG.site_name || '星匣') + (document.title.includes('·') ? document.title.slice(document.title.indexOf('·')) : ' · 个人内容站');
  const logoName = $('#logoName'); if(logoName) logoName.textContent = CONFIG.site_name || '星匣';
  const foot = $('#footerText'); if(foot) foot.textContent = CONFIG.footer || '星匣 · 自建内容站';
  if(CONFIG.announcement){
    const ann = $('#announcement');
    if(ann){ ann.textContent = CONFIG.announcement; ann.style.display='block'; }
  }
  return CONFIG;
}

function renderNav(active){
  const box = $('#nav'); if(!box) return;
  const me = ME();
  box.innerHTML = `
    <a href="index.html" class="${active==='home'?'active':''}">作品集</a>
    <a href="studio.html" class="${active==='studio'?'active':''}">创作</a>
    ${me && me.role==='admin' ? '<a href="admin.html" class="'+ (active==='admin'?'active':'') +'">管理</a>' : ''}
    ${me
      ? `<button class="avatar-btn" id="userBtn" title="${esc(me.username)}">${esc(me.username[0].toUpperCase())}</button>`
      : '<a class="btn btn-primary btn-sm" href="auth.html">登录 / 注册</a>'}`;
  const btn = $('#userBtn');
  if(btn) btn.onclick = () => {
    const menu = $('#userMenu');
    if(menu){ menu.classList.toggle('show'); }
    else {
      const m = document.createElement('div');
      m.id = 'userMenu';
      m.style.cssText = 'position:absolute;right:24px;top:62px;background:#14161f;border:1px solid rgba(212,175,122,.28);border-radius:12px;box-shadow:0 18px 50px rgba(0,0,0,.6);padding:8px;min-width:170px;z-index:80;backdrop-filter:blur(12px)';
      m.innerHTML = `<div style="padding:8px 12px;font-size:11px;color:#6d6a63;letter-spacing:1px;border-bottom:1px solid rgba(255,255,255,.09);margin-bottom:5px">${esc(me.username)} · ${me.role==='admin'?'管理员':'用户'}</div>
        <a href="profile.html?user=${encodeURIComponent(me.username)}" style="display:block;padding:9px 12px;border-radius:8px;color:#a7a298">我的主页</a>
        <a href="settings.html" style="display:block;padding:9px 12px;border-radius:8px;color:#a7a298">账号设置</a>
        <button id="logoutBtn" style="width:100%;text-align:left;padding:9px 12px;border:0;background:transparent;color:#e5646a;border-radius:8px">退出登录</button>`;
      document.body.appendChild(m);
      $('#logoutBtn').onclick = async () => { await post('/api/logout'); location.href='index.html'; };
      document.addEventListener('click', e => { if(!m.contains(e.target) && e.target!==btn){ m.remove(); } }, {once:true});
    }
  };
}

let toastTimer;
function toast(msg){
  const t = $('#toast'); if(!t) return;
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(()=>t.classList.remove('show'), 2600);
}

function kindMeta(kind){
  return {image:['image','图片'], file:['file','文件'], post:['article','文章']}[kind] || ['file','内容'];
}
function visMeta(v){
  return {public:['公开','public'], private:['私密','private'], password:['密码','password']}[v] || [v,v];
}

function cardHTML(it){
  const [kicon,kname] = kindMeta(it.kind);
  const [vname, vcls] = visMeta(it.visibility);
  let media;
  if(it.kind==='image' && it.media_url){
    media = `<img src="${esc(it.thumb_url||it.media_url)}" alt="${esc(it.title)}" loading="lazy">`;
  } else if(it.kind==='post'){
    const preview = (it.body||'').replace(/[#*`>\-\[\]]/g,'').replace(/\s+/g,' ').trim().slice(0,90);
    media = `<div class="ph ph-post"><div class="ph-post-inner">${icon('article',30)}<p>${esc(preview||'一篇文字')}</p></div></div>`;
  } else {
    media = `<div class="ph ph-file">${icon('file',44)}<span>${esc((it.ext||'FILE').toUpperCase().slice(0,5))}</span></div>`;
  }
  const excerpt = it.kind==='post'
    ? (it.body||'').replace(/[#*`>\[\]!\-]/g,'').slice(0,100)
    : (it.kind==='file' ? `${esc(it.filename)} · ${fmtSize(it.size)}` : '点击查看详情与大图');
  return `<article class="card">
    <div class="card-media">${media}
      <span class="badge">${icon(kicon,12)} ${kname}</span>
      ${it.visibility!=='public'?`<span class="badge ${vcls}">${icon(it.locked?'lock':'eye',12)} ${vname}</span>`:''}
      ${it.pinned?`<span class="badge pinned">${icon('pin',12)} 置顶</span>`:''}
    </div>
    <div class="card-body">
      <h3 class="card-title"><a href="item.html?id=${it.id}">${esc(it.title)}</a></h3>
      <div class="card-excerpt">${esc(excerpt)}</div>
      <div class="card-tags">${(it.tags||[]).slice(0,4).map(t=>`<span class="mini-tag">#${esc(t)}</span>`).join('')}</div>
      <div class="card-meta"><span>${icon('user',12)} ${esc(it.owner)}</span><span>${icon('clock',12)} ${fmtDate(it.created_at)}</span><span>${icon('eye',12)} ${it.views}</span></div>
    </div>
  </article>`;
}

function collectionCardHTML(col){
  const cover = (col.cover_thumb_url || col.cover_url)
    ? `<img src="${esc(col.cover_thumb_url||col.cover_url)}" alt="${esc(col.title)}" loading="lazy">`
    : `<div class="ph">${icon('layers',44)}</div>`;
  const vcls = col.visibility==='public'?'':col.visibility;
  return `<article class="card card-collection">
    <div class="card-media">${cover}
      <span class="badge">${icon('layers',12)} 作品集</span>
      ${col.visibility!=='public'?`<span class="badge ${vcls}">${icon(col.locked?'lock':'eye',12)} ${visMeta(col.visibility)[0]}</span>`:''}
      <span class="col-count">${icon('image',13)} ${col.count}</span>
    </div>
    <div class="card-body">
      <h3 class="card-title"><a href="collection.html?id=${col.id}">${esc(col.title)}</a></h3>
      <div class="card-excerpt">${esc(col.description||'一组收藏')}</div>
      <div class="card-tags">${(col.tags||[]).slice(0,4).map(t=>`<span class="mini-tag">#${esc(t)}</span>`).join('')}</div>
      <div class="card-meta"><span>${icon('user',12)} ${esc(col.owner)}</span><span>${icon('eye',12)} ${col.views}</span>${col.picks?`<span>${icon('heart',12)} ${col.picks}</span>`:''}</div>
    </div>
  </article>`;
}

function modal(title, content, onOk, okText='保存'){
  const mask = $('#modalMask');
  mask.innerHTML = `<div class="modal"><h2>${esc(title)}</h2><div id="modalContent">${content}</div>
    <div class="modal-foot"><button class="btn" id="modalCancel">取消</button><button class="btn btn-primary" id="modalOk">${esc(okText)}</button></div></div>`;
  mask.classList.add('show');
  $('#modalCancel').onclick = closeModal;
  mask.onclick = e => { if(e.target===mask) closeModal(); };
  $('#modalOk').onclick = async () => {
    try { await onOk(); closeModal(); }
    catch(e){ toast(e.message); }
  };
}
function closeModal(){ const m=$('#modalMask'); m.classList.remove('show'); m.innerHTML=''; }

function fillIcons(root=document){
  $$('[data-ico]', root).forEach(el => {
    if(el.dataset.done) return;
    el.innerHTML = icon(el.dataset.ico, parseInt(el.dataset.size||'18'));
    el.dataset.done = '1';
  });
}
document.addEventListener('DOMContentLoaded', () => {
  fillIcons();
  const t = document.createElement('div'); t.id='toast'; document.body.appendChild(t);
  const m = document.createElement('div'); m.id='modalMask'; m.className='modal-mask'; document.body.appendChild(m);
});
