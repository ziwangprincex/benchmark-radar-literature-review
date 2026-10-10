// 文献综述页：接模型 → 选领域 → ①逐篇抽卡 ②分类 ③写综述 → 看、调分类、写批注改稿
// 每个领域两块：全部综述（scope=all，全部论文）和本周小结（scope=week，最近一周新收的论文）
// 会话：编号只记在这台电脑的这个浏览器里（localStorage），保存一天。别人的浏览器有自己的编号，互相看不到。
const RV_KEY='radar-review-session',RV_DAY=864e5;
const RV_SESS=(()=>{const now=Date.now();try{const o=JSON.parse(localStorage.getItem(RV_KEY)||'null');if(o&&/^[A-Za-z0-9_-]{8,64}$/.test(o.id)&&now-o.at<RV_DAY)return o}catch(e){}
  const id=(crypto.randomUUID?crypto.randomUUID():now.toString(36)+Math.random().toString(36).slice(2)).replace(/[^A-Za-z0-9_-]/g,''),o={id,at:now};
  try{localStorage.setItem(RV_KEY,JSON.stringify(o))}catch(e){}return o})();
const RV_SID=RV_SESS.id;
let rv={cfg:null,dom:'legal',scope:'all',data:{},timer:null,editing:false,view:'review',tax:null,dirty:false,q:''};
const rvKey=()=>rv.dom+'|'+rv.scope;
const rvUrl=(d,sc,tail='')=>`/api/review/${d}`+(sc==='week'?'/week':'')+tail+`?sid=${RV_SID}`;
const rvCfgUrl=`/api/review/config?sid=${RV_SID}`;
const RV_G=['QA','Agent'],RV_GCN={QA:'QA 类',Agent:'Agent 类'},RV_GDEF={QA:'模型拿到题目和材料，答一次就判分',Agent:'模型要在环境里连续行动才能完成任务'};

const rvCur=()=>rv.data[rvKey()];
const rvT=iso=>{if(!iso)return '';const d=new Date(iso);return isNaN(d)?iso:d.toLocaleString('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})};
const RV_STATE={running:'进行中',done:'已完成',error:'出错',stale:'已中断'};

function stopRvPoll(){if(rv.timer){clearTimeout(rv.timer);rv.timer=null}}
async function rvFetch(d,sc=rv.scope){const r=await api(rvUrl(d,sc));rv.data[d+'|'+sc]=r;if(d===rv.dom&&sc===rv.scope&&!rv.dirty)rv.tax=r.taxonomy?JSON.parse(JSON.stringify(r.taxonomy)):null;return r}
async function loadReview(){rv.cfg=await api(rvCfgUrl);await rvFetch(rv.dom);renderReview();if(rvCur()?.status?.state==='running')pollReview()}
function pollReview(){stopRvPoll();rv.timer=setTimeout(async()=>{try{const r=await rvFetch(rv.dom);if(r.status?.state!=='running'){rv.cfg=await api(rvCfgUrl);if(r.status?.state==='done')toast('完成了');else if(r.status?.state==='error')toast('出错：'+(r.status.error||''))}renderReview();if(r.status?.state==='running')pollReview()}catch(e){pollReview()}},2500)}
async function rvRun(body,confirmMsg){if(confirmMsg&&!confirm(confirmMsg))return;try{await api(rvUrl(rv.dom,rv.scope,'/run'),{method:'POST',body:JSON.stringify(body)});const R=rvCur();R.status={...(R.status||{}),state:'running',step:'准备资料',done:0,total:0};renderReview();pollReview()}catch(e){toast(e.message)}}

function renderReview(){
  const c=rv.cfg;if(!c)return;const L=c.llm;
  rvConn(L);
  // 领域
  const wk=rv.scope==='week';
  $('#rv-tabs').innerHTML=c.domains.map(d=>{const x=wk?d.week:d;const tag=x.state==='running'?'<em class="run">进行中</em>':x.reviewed?`<em class="${x.review_ok?'ok':'bad'}">${x.review_ok?(wk?'已写小结':'已写综述'):(wk?'小结有问题':'综述有问题')}</em>`:x.categories?`<em>已分 ${x.categories} 类</em>`:(!wk&&d.cards)?`<em>已抽 ${d.cards} 张卡</em>`:'<em>未开始</em>';
    return `<button class="rd-tab rv-tab ${d.domain===rv.dom?'on':''}" data-d="${d.domain}"><span>${esc(d.label)}</span><div><i><b>${wk?d.week_papers:d.papers}</b>${wk?'篇本周新':'篇'}</i>${tag}</div></button>`}).join('');
  $$('#rv-tabs [data-d]').forEach(b=>b.onclick=async()=>{if(rv.dirty&&!confirm('分类修改未保存，切换后将丢失，是否继续？'))return;rv.dirty=false;rv.dom=b.dataset.d;stopRvPoll();await rvFetch(rv.dom);renderReview();if(rvCur()?.status?.state==='running')pollReview()});
  const R=rvCur();if(!R)return;
  rvScope(R);rvSteps(R,L);rvViews(R);
}

function rvScope(R){
  const d=rv.cfg.domains.find(x=>x.domain===rv.dom)||{};const wkLabel=R.week?`${+R.week.slice(5,7)}月${+R.week.slice(8,10)}日那周`:'本周';
  $('#rv-scope').innerHTML=`<div class="seg rv-sseg"><button class="${rv.scope==='all'?'on':''}" data-s="all">全部综述<b>${d.papers??''} 篇</b></button><button class="${rv.scope==='week'?'on':''}" data-s="week">本周小结<b>${d.week_papers??''} 篇</b></button></div>`;
  $$('#rv-scope [data-s]').forEach(b=>b.onclick=async()=>{if(b.dataset.s===rv.scope)return;if(rv.dirty&&!confirm('分类修改未保存，切换后将丢失，是否继续？'))return;rv.dirty=false;rv.scope=b.dataset.s;rv.view='review';stopRvPoll();await rvFetch(rv.dom);renderReview();if(rvCur()?.status?.state==='running')pollReview()});
}

function rvConn(L){const box=$('#rv-conn');
  if(window.RADAR_STATIC){box.className='rv-conn';
    box.innerHTML='<div class="rv-conn-head"><b>网页版不能写综述</b><small>综述要接模型现写，写好的结果不在网上保存。请在本地运行并接入模型，见 README。</small></div>';return}
  if(L.ready&&!rv.editing){box.className='rv-conn ok';
    box.innerHTML=`<div class="rv-conn-l"><i class="dot"></i><div><b>已接入模型</b><small>${esc(L.model)} · ${esc(L.base_url)} · 密钥 ${esc(L.api_key_hint)}</small></div></div><div class="rv-conn-r"><button class="btn ghost" id="rv-ping">测试连接</button><button class="btn ghost" id="rv-edit">改设置</button></div>`;
    $('#rv-edit').onclick=()=>{rv.editing=true;renderReview()};
  }else{box.className='rv-conn';
    box.innerHTML=`<div class="rv-conn-head"><b>接入模型接口</b></div>
    <div class="rv-form"><label>接口地址<input id="rv-base" value="${esc(L.base_url||'')}" placeholder="https://api.openai.com/v1"></label>
    <label>模型名<input id="rv-model" value="${esc(L.model||'')}" placeholder="例如 gpt-4.1、deepseek-chat"></label>
    <label>密钥<input id="rv-key" type="password" placeholder="${L.api_key_set?'已填 '+esc(L.api_key_hint)+'，留空不改':'sk-...'}"></label>
    <div class="rv-form-b"><button class="btn primary" id="rv-save">保存</button>${L.ready?'<button class="btn ghost" id="rv-cancel">取消</button>':''}<button class="btn ghost" id="rv-ping">测试连接</button></div></div>`;
    $('#rv-save').onclick=async()=>{try{const r=await api('/api/review/config',{method:'PUT',body:JSON.stringify({base_url:$('#rv-base').value.trim(),model:$('#rv-model').value.trim(),api_key:$('#rv-key').value.trim()})});rv.cfg.llm=r.llm;rv.editing=!r.llm.ready;toast(r.llm.ready?'已保存':'还缺模型名或密钥');renderReview()}catch(e){toast(e.message)}};
    const cc=$('#rv-cancel');if(cc)cc.onclick=()=>{rv.editing=false;renderReview()};
  }
  $('#rv-ping').onclick=async e=>{const b=e.target;b.disabled=true;b.textContent='连接中…';try{const r=await api('/api/review/ping',{method:'POST'});toast('连上了，模型回复：'+r.reply)}catch(err){toast(err.message)}finally{b.disabled=false;b.textContent='测试连接'}};
}

function rvSteps(R,L){
  const st=R.status||{},run=st.state==='running',n=R.papers.length,P=R.pending,T=R.taxonomy,M=R.meta,wk=R.scope==='week';
  const newN=T&&wk?T.categories.filter(c=>c.new).length:0;
  const baseNote=wk?(!R.base?.reviewed?'<p class="rv-basenote amb">缺少全部综述，第三节无法对比</p>':P.base_newer?'<p class="rv-basenote amb">全部综述已更新，本小结基于旧版</p>':`<p class="rv-basenote">对比基准：${esc(rvT(R.base.built_at))} 版全部综述（${R.base.papers} 篇）</p>`):'';
  const nc=Object.keys(R.cards).length,ok=L.ready&&!run&&n>0;
  const live=k=>run&&st.stage===k?`<p class="rv-live"><i class="spin"></i>${esc(st.step||'')}${st.total?` · ${st.done||0}/${st.total}`:''}</p>`:'';
  const outN=T?T.outside.length:0,inN=T?T.categories.reduce((a,c)=>a+c.ids.length,0):0;
  const s1=`<div class="rv-step ${nc?'done':''}"><div class="rv-step-h"><span>01</span><b>逐篇抽卡</b></div><p class="big">${nc}<small>/ ${n} 篇</small></p><p class="sub">${P.no_card?`<em class="amb">未抽卡 ${P.no_card} 篇</em>`:''}</p>${live('cards')}<div class="rv-step-b">${P.no_card&&nc?`<button class="btn ghost" data-run="cards" ${ok?'':'disabled'}>补抽 ${P.no_card} 篇</button>`:''}${nc?`<button class="btn ghost" data-run="cards-all" ${ok?'':'disabled'}>全部重抽</button>`:`<button class="btn ghost" data-run="cards" ${ok?'':'disabled'}>开始抽卡</button>`}</div></div>`;
  const s2=`<div class="rv-step ${T?'done':''}"><div class="rv-step-h"><span>02</span><b>分类</b>${T?`<i class="by">${T.by==='user'?'手动调整':'模型生成'}</i>`:''}</div><p class="big">${T?T.categories.length:0}<small>个主题 · ${inN} 篇${outN?`，${outN} 篇不算`:''}</small></p>${T?`<p class="rv-gline">${RV_G.map(g=>{const cs=T.categories.filter(c=>(c.group||'QA')===g);return `<span class="g-${g} ${cs.length?'':'z'}">${RV_GCN[g]} ${cs.reduce((a,c)=>a+c.ids.length,0)} 篇 · ${cs.length} 个主题</span>`}).join('')}</p>`:''}<p class="sub">${P.not_classified?`<em class="amb">未分类 ${P.not_classified} 篇</em>`:wk&&T&&R.base?.reviewed&&newN?`<em class="amb">新增主题 ${newN} 个</em>`:''}</p>${live('taxonomy')}<div class="rv-step-b"><button class="btn ghost" data-run="taxonomy" ${ok&&nc?'':'disabled'}>${T?'重新分类':'开始分类'}</button></div></div>`;
  const chk=M?.check;const s3=`<div class="rv-step ${M?(chk.ok?'done':'bad'):''}"><div class="rv-step-h"><span>03</span><b>${wk?'写本周小结':'写综述'}</b></div><p class="big">${M?(chk.ok?'已写好':'有问题'):'—'}<small>${M?rvT(M.built_at):''}</small></p><p class="sub">${P.taxonomy_newer?`<em class="amb">分类已变更，${wk?'小结':'综述'}未同步</em>`:M&&!chk.ok?'<em class="amb">引文核对未通过</em>':''}</p>${live('review')}<div class="rv-step-b"><button class="btn ghost" data-run="review" ${ok&&T?'':'disabled'}>${M?(wk?'重写小结':'重写综述'):'开始写'}</button></div></div>`;
  const allBtn=`<div class="rv-step all"><b>更新与下载</b>${T?.by==='user'?'<p class="sub"><em class="amb">将覆盖手动调整的分类</em></p>':''}<div class="rv-all-b"><button class="btn primary" data-run="all" ${ok?'':'disabled'}>${run?'进行中…':'更新'}</button><button class="btn ghost" id="rv-dl" ${R.review?'':'disabled'}>下载 .md</button></div>${st.state==='error'?`<p class="err">${esc(st.error||'')}</p>`:''}${st.state==='stale'?'<p class="err">任务因服务重启中断，请重新运行</p>':''}</div>`;
  $('#rv-run').className='';$('#rv-run').innerHTML=`${baseNote}<div class="rv-steps">${s1}${s2}${s3}${allBtn}</div>`;
  $$('#rv-run [data-run]').forEach(b=>b.onclick=()=>{const k=b.dataset.run;
    if(k==='cards')rvRun({start:'cards'});
    else if(k==='cards-all')rvRun({start:'cards',force_cards:true},`重新抽 ${n} 篇的卡片，并重新分类、重写综述。继续？`);
    else if(k==='taxonomy')rvRun({start:'taxonomy'},T?.by==='user'?'重新分类将覆盖手动调整的分类并重写综述，是否继续？':(T?'重新分类并重写综述，是否继续？':null));
    else if(k==='review')rvRun({start:'review'},M?`重写会覆盖当前${wk?'小结':'综述'}（批注记录保留）。继续？`:null);
    else rvRun({start:'cards'},T?.by==='user'?'一键更新会重新分类，覆盖你调整过的分类。继续？':null)});
  $('#rv-dl').onclick=()=>rvDownload(R);
  $('#rv-progress').innerHTML='';
}

function rvViews(R){
  const T=R.taxonomy,nc=Object.keys(R.cards).length;
  const tabs=[['review',R.scope==='week'?'本周小结':'综述',R.review?'':'未写'],['taxonomy','分类',T?T.categories.length+' 个主题':'未分'],['cards','逐篇卡片',nc+' 张']];
  $('#rv-body').className='rv-wrap';
  $('#rv-body').innerHTML=`<div class="seg rv-vseg">${tabs.map(([k,l,x])=>`<button class="${k===rv.view?'on':''}" data-v="${k}">${l}<b>${x}</b></button>`).join('')}</div><div id="rv-view"></div>`;
  $$('.rv-vseg [data-v]').forEach(b=>b.onclick=()=>{rv.view=b.dataset.v;rvViews(R)});
  ({review:rvReviewView,taxonomy:rvTaxView,cards:rvCardsView})[rv.view](R);
}

function rvMeta(R){const m={};R.papers.forEach(p=>m[p.id]=p);return m}

function rvReviewView(R){
  const box=$('#rv-view'),M=R.meta;
  const wk=R.scope==='week',what=wk?'本周小结':'综述';
  if(!R.papers.length&&wk){box.innerHTML='<div class="rv-empty">本周无新论文</div>';return}
  if(!R.review){box.innerHTML=`<div class="rv-empty">${window.RADAR_STATIC?`暂无${what}`:rv.cfg.llm.ready?`暂无${what}`:'未接入模型'}</div>`;return}
  const meta=rvMeta(R),chk=M.check,p=chk.problems,w=chk.warnings;
  const list=(t,xs,f,cls)=>xs&&xs.length?`<details class="rv-iss ${cls}" open><summary>${t}<b>${xs.length}</b></summary><ul>${xs.slice(0,60).map(f).join('')}</ul></details>`:'';
  const notes=(M.notes||[]).slice().reverse();
  box.innerHTML=`<div class="rv-body"><article class="rv-doc">${rvMd(R.review,meta)}</article>
  <aside class="rv-side">
   <div class="rv-chk ${chk.ok?'':'bad'}"><b>${chk.ok?'核对通过':'核对未通过'}</b><small>原话 ${chk.quotes_ok} 处 · 引用 ${chk.cited.length} 篇${M.fixed_once?' · 已按核对结果修订 1 次':''}</small><small>${esc(M.model||'')} · ${esc(rvT(M.built_at))}</small></div>
   ${list('原话不一致',p.fake_quotes,q=>`<li>「${esc(q.quote)}」<small>${esc(q.reason)}</small></li>`,'bad')}
   ${list('编号不存在',p.invalid_ids,i=>`<li>#${i}</li>`,'bad')}
   ${list('缺少的节',p.missing_sections,x=>`<li>${esc(x)}</li>`,'bad')}
   ${list('第二节没写到的类',w.categories_not_discussed,x=>`<li>${esc(x)}</li>`,'warn')}
   <div class="rv-note-box"><b>批注改稿</b><textarea id="rv-notes" rows="6" placeholder="哪里不对，比如：第一类和第三类是一回事"></textarea><button class="btn primary" id="rv-revise" ${R.status?.state==='running'||!rv.cfg.llm.ready?'disabled':''}>按批注改稿</button>
   ${notes.length?`<details class="rv-hist"><summary>改过 ${notes.length} 次</summary>${notes.map(x=>`<div><small>${esc(rvT(x.at))}</small><p>${esc(x.text)}</p></div>`).join('')}</details>`:''}</div>
  </aside></div>`;
  $('#rv-revise').onclick=()=>{const t=$('#rv-notes').value.trim();if(!t){toast('先写批注');return}rvRun({notes:t})};
}

// 下载：编号换成可点的链接，离开这个页面也能打开原文
function rvDownload(R){
  const meta=rvMeta(R),M=R.meta||{},wk=R.scope==='week',what=wk?'本周小结':'全部综述';
  const link=i=>meta[i]?`[#${i}](${meta[i].url})`:`[#${i}]`;
  let md=R.review.replace(/\[#\s*(\d+(?:\s*[,，、]\s*#?\s*\d+)*)\s*\]/g,(m,g)=>g.match(/\d+/g).map(link).join(''));
  md=md.replace(/(^|[^\w#\[])#(\d{2,6})\b(?!\]\()/g,(m,pre,i)=>meta[i]?pre+link(i):m);
  const day=(M.built_at||new Date().toISOString()).slice(0,10);
  const head=`# ${R.label}领域${what}${wk&&R.week?`（${R.week} 那周）`:''}\n\n> 生成于 ${rvT(M.built_at)} · 模型 ${M.model||'未知'} · ${R.papers.length} 篇论文 · 原话核对${M.check?.ok?'通过':'有问题'}\n\n`;
  const blob=new Blob([head+md],{type:'text/markdown;charset=utf-8'}),a=document.createElement('a');
  a.href=URL.createObjectURL(blob);a.download=`${R.label}-${what}-${day}.md`;document.body.appendChild(a);a.click();
  setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500);
}

function rvTaxView(R){
  const box=$('#rv-view'),T=rv.tax;
  if(!T){box.innerHTML=`<div class="rv-empty">暂无分类</div>`;return}
  const meta=rvMeta(R),cards=R.cards;
  const placed=new Set([...T.categories.flatMap(c=>c.ids),...T.outside.map(o=>o.id)]);
  const newOnes=R.papers.filter(p=>cards[p.id]&&!placed.has(p.id)).map(p=>p.id);
  T.categories.forEach(c=>{if(!RV_G.includes(c.group))c.group='QA'});
  const opts=cur=>RV_G.map(g=>`<optgroup label="${RV_GCN[g]}">${T.categories.map((c,i)=>c.group===g?`<option value="c${i}" ${cur==='c'+i?'selected':''}>${esc(c.name)}</option>`:'').join('')}</optgroup>`).join('')+`<option value="out" ${cur==='out'?'selected':''}>不算（移出）</option>${cur==='new'?'<option value="new" selected>还没分类</option>':''}<option value="add">＋ 新建一类…</option>`;
  const row=(id,cur,extra='')=>{const p=meta[id],c=cards[id]||{};if(!p)return '';return `<div class="rv-trow"><div><a href="${esc(p.url||'#')}" target="_blank" rel="noopener">${esc(p.title)}</a><small>#${id}${c.kind?' · '+esc(c.kind):''}${c.task?' · '+esc(c.task):''}</small>${extra}</div><select data-id="${id}" data-cur="${cur}">${opts(cur)}</select></div>`};
  box.innerHTML=`${rv.dirty?`<div class="rv-dirty"><span>分类修改未保存</span><button class="btn ghost" id="rv-undo">撤销</button><button class="btn primary" id="rv-savetax">保存分类</button></div>`:''}
  ${newOnes.length?`<div class="rv-cat newc"><div class="rv-cat-h"><b>未分类论文</b><span>${newOnes.length} 篇</span></div>${newOnes.map(id=>row(id,'new')).join('')}</div>`:''}
  ${RV_G.map(g=>{const cs=T.categories.map((c,i)=>[c,i]).filter(([c])=>c.group===g),n=cs.reduce((a,[c])=>a+c.ids.length,0);
    return `<section class="rv-grp g-${g}"><div class="rv-grp-h"><b>${RV_GCN[g]}</b><span>${n} 篇 · ${cs.length} 个主题</span></div>${cs.map(([c,i])=>`<div class="rv-cat ${c.new&&R.scope==='week'&&R.base?.reviewed?'isnew':''}"><div class="rv-cat-h"><input class="rv-cname" data-i="${i}" value="${esc(c.name)}" aria-label="主题名">${c.new&&R.scope==='week'&&R.base?.reviewed?'<em class="newtag">新方向</em>':''}<select class="rv-cgrp" data-i="${i}" aria-label="大类">${RV_G.map(x=>`<option value="${x}" ${x===g?'selected':''}>${RV_GCN[x]}</option>`).join('')}</select><span>${c.ids.length} 篇</span></div><textarea class="rv-ctests" data-i="${i}" rows="2" placeholder="这个主题测什么、输入是什么">${esc(c.tests)}</textarea>${c.why?`<p class="why">归为一类的理由：${esc(c.why)}</p>`:''}${c.ids.map(id=>row(id,'c'+i)).join('')}</div>`).join('')||'<p class="rv-grp-empty">暂无论文</p>'}</section>`}).join('')}
  ${T.outside.length?`<div class="rv-cat outc"><div class="rv-cat-h"><b>已排除</b><span>${T.outside.length} 篇</span></div>${T.outside.map(o=>row(o.id,'out',o.reason?`<em>${esc(o.reason)}</em>`:'')).join('')}</div>`:''}`;
  const mark=()=>{rv.dirty=true;rvTaxView(R)};
  $$('#rv-view select[data-id]').forEach(s=>s.onchange=()=>{const id=+s.dataset.id,from=s.dataset.cur;let to=s.value;
    if(to==='add'){const name=(prompt('新主题的名字（建好后可以在主题右边改成 QA 类或 Agent 类）')||'').trim();if(!name){s.value=from;return}T.categories.push({group:from.startsWith('c')?T.categories[+from.slice(1)].group:'QA',name,tests:'',why:'',ids:[]});to='c'+(T.categories.length-1)}
    if(from.startsWith('c'))T.categories[+from.slice(1)].ids=T.categories[+from.slice(1)].ids.filter(x=>x!==id);
    if(from==='out')T.outside=T.outside.filter(o=>o.id!==id);
    if(to==='out')T.outside.push({id,reason:'你移出的'});else T.categories[+to.slice(1)].ids.push(id);
    T.categories=T.categories.filter(c=>c.ids.length||c.tests||c.name.trim());mark()});
  $$('#rv-view .rv-cname').forEach(x=>x.onchange=()=>{T.categories[+x.dataset.i].name=x.value.trim()||T.categories[+x.dataset.i].name;mark()});
  $$('#rv-view .rv-ctests').forEach(x=>x.onchange=()=>{T.categories[+x.dataset.i].tests=x.value.trim();mark()});
  $$('#rv-view .rv-cgrp').forEach(x=>x.onchange=()=>{T.categories[+x.dataset.i].group=x.value;mark()});
  const u=$('#rv-undo');if(u)u.onclick=()=>{rv.dirty=false;rv.tax=R.taxonomy?JSON.parse(JSON.stringify(R.taxonomy)):null;rvTaxView(R)};
  const sv=$('#rv-savetax');if(sv)sv.onclick=async()=>{T.categories=T.categories.filter(c=>c.ids.length);try{const r=await api(rvUrl(rv.dom,rv.scope,'/taxonomy'),{method:'PUT',body:JSON.stringify(T)});rv.dirty=false;R.taxonomy=r.taxonomy;rv.tax=JSON.parse(JSON.stringify(r.taxonomy));await rvFetch(rv.dom);rv.cfg=await api(rvCfgUrl);renderReview();toast(R.scope==='week'?'分类已保存，点"重写小结"让小结按新分类写':'分类已保存，点"重写综述"让综述按新分类写')}catch(e){toast(e.message)}};
}

function rvCardsView(R){
  const box=$('#rv-view'),meta=rvMeta(R),q=rv.q.toLowerCase();
  const ids=R.papers.map(p=>p.id).filter(id=>R.cards[id]);
  if(!ids.length){box.innerHTML='<div class="rv-empty">暂无卡片</div>';return}
  const shown=ids.filter(id=>{if(!q)return true;const c=R.cards[id],p=meta[id];return `${p.title} ${c.task} ${c.finding} ${c.input}`.toLowerCase().includes(q)});
  const noQ=ids.filter(id=>!R.cards[id].limit_quote).length,drop=ids.filter(id=>R.cards[id].quote_dropped).length;
  box.innerHTML=`<div class="rv-cbar"><input id="rv-q" placeholder="搜标题 / 测什么 / 发现" value="${esc(rv.q)}"><small>${ids.length} 张卡 · ${ids.length-noQ} 张含作者自述局限${drop?` · ${drop} 张原话与摘要不符，已移除`:''}</small></div>
  <div class="rv-cards">${shown.map(id=>{const c=R.cards[id],p=meta[id];return `<div class="rv-card"><div class="rv-card-h"><i class="k ${c.kind==='Benchmark'?'b':''}">${esc(c.kind||'')}</i><a href="${esc(p.url||'#')}" target="_blank" rel="noopener">${esc(p.title)}</a><small>#${id} · ${esc(p.date||'')}</small></div>
   <dl><dt>测什么</dt><dd>${esc(c.task)||'<span class="mut">摘要没写</span>'}</dd><dt>输入</dt><dd>${esc(c.input)||'<span class="mut">摘要没写</span>'}</dd><dt>判分</dt><dd>${esc(c.scoring)||'<span class="mut">摘要没写</span>'}</dd><dt>数据</dt><dd>${esc(c.data)||'<span class="mut">摘要没写</span>'}</dd><dt>发现</dt><dd>${esc(c.finding)||'<span class="mut">摘要没写</span>'}</dd>
   <dt>局限</dt><dd>${c.limit_quote?`<q class="orig">${esc(c.limit_quote)}</q><span class="cn">${esc(c.limit_cn)}</span>`:c.quote_dropped?`<span class="mut">原话与摘要不符，已移除：</span><s>${esc(c.quote_dropped)}</s>`:'<span class="mut">摘要未提及局限</span>'}</dd></dl></div>`}).join('')||'<p class="rv-empty">没搜到</p>'}</div>`;
  const inp=$('#rv-q');inp.oninput=()=>{rv.q=inp.value;const pos=inp.selectionStart;rvCardsView(R);const n=$('#rv-q');n.focus();n.setSelectionRange(pos,pos)};
}

function rvInline(s,meta){
  s=esc(s);
  s=s.replace(/\[#\s*(\d+(?:\s*[,，、]\s*#?\s*\d+)*)\s*\]/g,(m,g)=>g.match(/\d+/g).map(i=>{const p=meta[i];return p?`<a class="cite" href="${esc(p.url)}" target="_blank" rel="noopener" title="${esc(p.title)}">#${i}</a>`:`<span class="cite bad" title="资料里没有这个编号">#${i}</span>`}).join(''));
  s=s.replace(/(^|[^\w#\["'>])#(\d{2,6})\b/g,(m,pre,i)=>{const p=meta[i];return p?`${pre}<a class="cite" href="${esc(p.url)}" target="_blank" rel="noopener" title="${esc(p.title)}">#${i}</a>`:m});
  s=s.replace(/「([^」]+)」/g,'<q class="orig">$1</q>');
  s=s.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>');
  return s;
}
function rvMd(md,meta){
  const out=[];let list=null,para=[],table=[];
  const flushP=()=>{if(para.length){out.push(`<p>${rvInline(para.join(' '),meta)}</p>`);para=[]}};
  const flushL=()=>{if(list){out.push(`<${list.t}>${list.items.map(x=>`<li>${rvInline(x,meta)}</li>`).join('')}</${list.t}>`);list=null}};
  const flushT=()=>{if(table.length){const rows=table.filter(r=>!/^\s*\|?\s*:?-{2,}/.test(r)).map(r=>r.replace(/^\s*\||\|\s*$/g,'').split('|'));out.push(`<div class="rv-tbl"><table>${rows.map((r,i)=>`<tr>${r.map(c=>i?`<td>${rvInline(c.trim(),meta)}</td>`:`<th>${rvInline(c.trim(),meta)}</th>`).join('')}</tr>`).join('')}</table></div>`);table=[]}};
  const flush=()=>{flushP();flushL();flushT()};
  for(const raw of md.split('\n')){const l=raw.trimEnd();let m;
    if(!l.trim()){flush();continue}
    if(/^\s*\|/.test(l)){flushP();flushL();table.push(l);continue}else flushT();
    if(m=l.match(/^(#{1,4})\s+(.*)/)){flush();const n=Math.min(4,Math.max(2,m[1].length));out.push(`<h${n}>${rvInline(m[2],meta)}</h${n}>`);continue}
    if(m=l.match(/^\s*[-*+]\s+(.*)/)){flushP();if(!list||list.t!=='ul'){flushL();list={t:'ul',items:[]}}list.items.push(m[1]);continue}
    if(m=l.match(/^\s*\d+[.、)]\s+(.*)/)){flushP();if(!list||list.t!=='ol'){flushL();list={t:'ol',items:[]}}list.items.push(m[1]);continue}
    if(list&&/^\s{2,}\S/.test(raw)){list.items[list.items.length-1]+=' '+l.trim();continue}
    flushL();para.push(l.trim());
  }
  flush();return out.join('');
}
