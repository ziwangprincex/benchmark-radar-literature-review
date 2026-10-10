// 文献综述页：接模型 → 选领域 → ①逐篇抽卡 ②分类 ③写综述 → 看、调分类、写批注改稿
// 每个领域两块：全部综述（scope=all，全部论文）和本周小结（scope=week，最近一周新收的论文）
let rv={cfg:null,dom:'legal',scope:'all',data:{},timer:null,editing:false,view:'review',tax:null,dirty:false,q:''};
const rvKey=()=>rv.dom+'|'+rv.scope;
const rvUrl=(d,sc)=>`/api/review/${d}`+(sc==='week'?'/week':'');
const rvCur=()=>rv.data[rvKey()];
const rvT=iso=>{if(!iso)return '';const d=new Date(iso);return isNaN(d)?iso:d.toLocaleString('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})};
const RV_STATE={running:'进行中',done:'已完成',error:'出错',stale:'已中断'};

function stopRvPoll(){if(rv.timer){clearTimeout(rv.timer);rv.timer=null}}
async function rvFetch(d,sc=rv.scope){const r=await api(rvUrl(d,sc));rv.data[d+'|'+sc]=r;if(d===rv.dom&&sc===rv.scope&&!rv.dirty)rv.tax=r.taxonomy?JSON.parse(JSON.stringify(r.taxonomy)):null;return r}
async function loadReview(){rv.cfg=await api('/api/review/config');await rvFetch(rv.dom);renderReview();if(rvCur()?.status?.state==='running')pollReview()}
function pollReview(){stopRvPoll();rv.timer=setTimeout(async()=>{try{const r=await rvFetch(rv.dom);if(r.status?.state!=='running'){rv.cfg=await api('/api/review/config');if(r.status?.state==='done')toast('完成了');else if(r.status?.state==='error')toast('出错：'+(r.status.error||''))}renderReview();if(r.status?.state==='running')pollReview()}catch(e){pollReview()}},2500)}
async function rvRun(body,confirmMsg){if(confirmMsg&&!confirm(confirmMsg))return;try{await api(rvUrl(rv.dom,rv.scope)+'/run',{method:'POST',body:JSON.stringify(body)});const R=rvCur();R.status={...(R.status||{}),state:'running',step:'准备资料',done:0,total:0};renderReview();pollReview()}catch(e){toast(e.message)}}

function renderReview(){
  const c=rv.cfg;if(!c)return;const L=c.llm;
  $('#foot-llm').textContent=L.ready?`文献综述已接入 ${L.model}`:'待读清单只用本地规则；文献综述要接模型接口';
  rvConn(L);
  // 领域
  const wk=rv.scope==='week';
  $('#rv-tabs').innerHTML=c.domains.map(d=>{const x=wk?d.week:d;const tag=x.state==='running'?'<em class="run">进行中</em>':x.reviewed?`<em class="${x.review_ok?'ok':'bad'}">${x.review_ok?(wk?'已写小结':'已写综述'):(wk?'小结有问题':'综述有问题')}</em>`:x.categories?`<em>已分 ${x.categories} 类</em>`:(!wk&&d.cards)?`<em>已抽 ${d.cards} 张卡</em>`:'<em>未开始</em>';
    return `<button class="rd-tab rv-tab ${d.domain===rv.dom?'on':''}" data-d="${d.domain}"><span>${esc(d.label)}</span><div><i><b>${wk?d.week_papers:d.papers}</b>${wk?'篇本周新':'篇'}</i>${tag}</div></button>`}).join('');
  $$('#rv-tabs [data-d]').forEach(b=>b.onclick=async()=>{if(rv.dirty&&!confirm('分类改了还没保存，切换会丢掉，继续？'))return;rv.dirty=false;rv.dom=b.dataset.d;stopRvPoll();await rvFetch(rv.dom);renderReview();if(rvCur()?.status?.state==='running')pollReview()});
  const R=rvCur();if(!R)return;
  rvScope(R);rvSteps(R,L);rvViews(R);
}

function rvScope(R){
  const d=rv.cfg.domains.find(x=>x.domain===rv.dom)||{};const wkLabel=R.week?`${+R.week.slice(5,7)}月${+R.week.slice(8,10)}日那周`:'本周';
  $('#rv-scope').innerHTML=`<div class="seg rv-sseg"><button class="${rv.scope==='all'?'on':''}" data-s="all">全部综述<b>${d.papers??''} 篇</b></button><button class="${rv.scope==='week'?'on':''}" data-s="week">本周小结<b>${d.week_papers??''} 篇</b></button></div><small>${rv.scope==='all'?'用这个领域收进来的全部论文写（含补的 2023 年以来的历史论文）：大家在研究什么、还没研究什么、我们能研究什么。':`只看${wkLabel}新收的论文：先放进全部综述已有的类，放不进的算新方向；再看补上了哪些空白、和我们的方向撞没撞车。卡片和全部综述共用，不重复抽。`}</small>`;
  $$('#rv-scope [data-s]').forEach(b=>b.onclick=async()=>{if(b.dataset.s===rv.scope)return;if(rv.dirty&&!confirm('分类改了还没保存，切换会丢掉，继续？'))return;rv.dirty=false;rv.scope=b.dataset.s;rv.view='review';stopRvPoll();await rvFetch(rv.dom);renderReview();if(rvCur()?.status?.state==='running')pollReview()});
}

function rvConn(L){const box=$('#rv-conn');
  if(window.RADAR_STATIC){box.className='rv-conn';$('#foot-llm').textContent='已读勾选只存在这个浏览器里';
    box.innerHTML='<div class="rv-conn-head"><b>网页版只能看</b><small>这里展示最近一次写好的综述。要抽卡、分类、写综述，请在本地运行并接入模型，见 README。</small></div>';return}
  if(L.ready&&!rv.editing){box.className='rv-conn ok';
    box.innerHTML=`<div class="rv-conn-l"><i class="dot"></i><div><b>已接入模型</b><small>${esc(L.model)} · ${esc(L.base_url)} · 密钥 ${esc(L.api_key_hint)}</small></div></div><div class="rv-conn-r"><button class="btn ghost" id="rv-ping">测试连接</button><button class="btn ghost" id="rv-edit">改设置</button></div>`;
    $('#rv-edit').onclick=()=>{rv.editing=true;renderReview()};
  }else{box.className='rv-conn';
    box.innerHTML=`<div class="rv-conn-head"><b>接入模型接口</b><small>任何 OpenAI 兼容的接口都行（OpenAI、DeepSeek、混元、本地 vLLM 等）。设置只存在本机 <code>data/llm_config.json</code>，不进 git。</small></div>
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
  const baseNote=wk?(!R.base?.reviewed?'<p class="rv-basenote amb">这个领域还没写全部综述，小结没法判断哪些是新方向、补上了哪些空白、撞没撞车。建议先写全部综述。</p>':P.base_newer?'<p class="rv-basenote amb">全部综述更新过了，这份小结是按旧版比的，点"更新"重写。</p>':`<p class="rv-basenote">对比用的是 ${esc(rvT(R.base.built_at))} 写的全部综述（${R.base.papers} 篇）。</p>`):'';
  const nc=Object.keys(R.cards).length,ok=L.ready&&!run&&n>0;
  const live=k=>run&&st.stage===k?`<p class="rv-live"><i class="spin"></i>${esc(st.step||'')}${st.total?` · ${st.done||0}/${st.total}`:''}</p>`:'';
  const outN=T?T.outside.length:0,inN=T?T.categories.reduce((a,c)=>a+c.ids.length,0):0;
  const s1=`<div class="rv-step ${nc?'done':''}"><div class="rv-step-h"><span>01</span><b>逐篇抽卡</b></div><p class="big">${nc}<small>/ ${n} 篇</small></p><p class="sub">${P.no_card?`<em class="amb">${P.no_card} 篇还没抽</em>`:nc?'每篇摘要都抽好了':'每篇摘要抽出：测什么、输入、怎么判分、主要发现、作者承认的局限'}</p>${live('cards')}<div class="rv-step-b">${P.no_card&&nc?`<button class="btn ghost" data-run="cards" ${ok?'':'disabled'}>补抽 ${P.no_card} 篇</button>`:''}${nc?`<button class="btn ghost" data-run="cards-all" ${ok?'':'disabled'}>全部重抽</button>`:`<button class="btn ghost" data-run="cards" ${ok?'':'disabled'}>开始抽卡</button>`}</div></div>`;
  const s2=`<div class="rv-step ${T?'done':''}"><div class="rv-step-h"><span>02</span><b>分类</b>${T?`<i class="by">${T.by==='user'?'你调整过':'模型提出'}</i>`:''}</div><p class="big">${T?T.categories.length:0}<small>类 · ${inN} 篇${outN?`，${outN} 篇不算`:''}</small></p><p class="sub">${P.not_classified?`<em class="amb">${P.not_classified} 篇新论文还没分类</em>`:wk?(T?(R.base?.reviewed?(newN?`<em class="amb">${newN} 类是全部综述里没有的</em>`:'都放进了全部综述已有的类'):'在"分类"里可以挪动论文'):(R.base?.reviewed?'先往全部综述已有的类里放，放不进的算新方向':'还没有全部综述，按本周论文自己分类')):T?'在"分类"里可以挪动论文、改类名':'按"测什么"把论文分类，并说明为什么这么分'}</p>${live('taxonomy')}<div class="rv-step-b"><button class="btn ghost" data-run="taxonomy" ${ok&&nc?'':'disabled'}>${T?'重新分类':'开始分类'}</button></div></div>`;
  const chk=M?.check;const s3=`<div class="rv-step ${M?(chk.ok?'done':'bad'):''}"><div class="rv-step-h"><span>03</span><b>${wk?'写本周小结':'写综述'}</b></div><p class="big">${M?(chk.ok?'已写好':'有问题'):'—'}<small>${M?rvT(M.built_at):''}</small></p><p class="sub">${P.taxonomy_newer?`<em class="amb">分类改过了，${wk?'小结':'综述'}还是按旧分类写的</em>`:M?(chk.ok?`原话核对通过 ${chk.quotes_ok} 处`:'有原话或编号对不上，见右侧'):(wk?'程序写第一节（分类）和第四节（边界），模型写第二、三节':'程序写第一节（分类）和第五节（边界），模型写第二到四节')}</p>${live('review')}<div class="rv-step-b"><button class="btn ghost" data-run="review" ${ok&&T?'':'disabled'}>${M?(wk?'重写小结':'重写综述'):'开始写'}</button></div></div>`;
  const allBtn=`<div class="rv-step all"><b>一键更新</b><p class="sub">${wk?'只抽本周论文里还没抽过的卡，然后分类、写小结。':'只抽新论文的卡，然后重新分类、重写综述。'}${T?.by==='user'?'<em class="amb">会覆盖你调整过的分类</em>':''}</p><button class="btn primary" data-run="all" ${ok?'':'disabled'}>${run?'进行中…':'更新'}</button>${st.state==='error'?`<p class="err">${esc(st.error||'')}</p>`:''}${st.state==='stale'?'<p class="err">服务重启过，上次没跑完，重新点一下就行</p>':''}</div>`;
  $('#rv-run').className='';$('#rv-run').innerHTML=`${baseNote}<div class="rv-steps">${s1}${s2}${s3}${allBtn}</div>`;
  $$('#rv-run [data-run]').forEach(b=>b.onclick=()=>{const k=b.dataset.run;
    if(k==='cards')rvRun({start:'cards'});
    else if(k==='cards-all')rvRun({start:'cards',force_cards:true},`重新抽 ${n} 篇的卡片，并重新分类、重写综述。继续？`);
    else if(k==='taxonomy')rvRun({start:'taxonomy'},T?.by==='user'?'重新分类会覆盖你调整过的分类，并重写综述。继续？':(T?'重新分类并重写综述，继续？':null));
    else if(k==='review')rvRun({start:'review'},M?`重写会覆盖当前${wk?'小结':'综述'}（批注记录保留）。继续？`:null);
    else rvRun({start:'cards'},T?.by==='user'?'一键更新会重新分类，覆盖你调整过的分类。继续？':null)});
  $('#rv-progress').innerHTML='';
}

function rvViews(R){
  const T=R.taxonomy,nc=Object.keys(R.cards).length;
  const tabs=[['review',R.scope==='week'?'本周小结':'综述',R.review?'':'未写'],['taxonomy','分类',T?T.categories.length+' 类':'未分'],['cards','逐篇卡片',nc+' 张']];
  $('#rv-body').className='rv-wrap';
  $('#rv-body').innerHTML=`<div class="seg rv-vseg">${tabs.map(([k,l,x])=>`<button class="${k===rv.view?'on':''}" data-v="${k}">${l}<b>${x}</b></button>`).join('')}</div><div id="rv-view"></div>`;
  $$('.rv-vseg [data-v]').forEach(b=>b.onclick=()=>{rv.view=b.dataset.v;rvViews(R)});
  ({review:rvReviewView,taxonomy:rvTaxView,cards:rvCardsView})[rv.view](R);
}

function rvMeta(R){const m={};R.papers.forEach(p=>m[p.id]=p);return m}

function rvReviewView(R){
  const box=$('#rv-view'),M=R.meta;
  const wk=R.scope==='week',what=wk?'本周小结':'综述';
  if(!R.papers.length&&wk){box.innerHTML='<div class="rv-empty">这个领域本周没有新论文。</div>';return}
  if(!R.review){box.innerHTML=`<div class="rv-empty">${window.RADAR_STATIC?`这个领域还没写${what}。`:rv.cfg.llm.ready?`还没写${what}。按上面的步骤从抽卡开始，或直接点"一键更新"。`:'先在上面接入模型接口。'}</div>`;return}
  const meta=rvMeta(R),chk=M.check,p=chk.problems,w=chk.warnings;
  const list=(t,xs,f,cls)=>xs&&xs.length?`<details class="rv-iss ${cls}" open><summary>${t}<b>${xs.length}</b></summary><ul>${xs.slice(0,60).map(f).join('')}</ul></details>`:'';
  const notes=(M.notes||[]).slice().reverse();
  box.innerHTML=`<div class="rv-body"><article class="rv-doc">${rvMd(R.review,meta)}</article>
  <aside class="rv-side">
   <div class="rv-chk ${chk.ok?'':'bad'}"><b>${chk.ok?'没发现编造':'有对不上的地方'}</b><small>原话核对通过 ${chk.quotes_ok} 处 · 引用了 ${chk.cited.length} 篇${M.fixed_once?' · 已让模型按核对结果改过一次':''}</small><small>${esc(M.model||'')} · ${esc(rvT(M.built_at))}</small></div>
   ${list('原话对不上',p.fake_quotes,q=>`<li>「${esc(q.quote)}」<small>${esc(q.reason)}</small></li>`,'bad')}
   ${list('编号不存在',p.invalid_ids,i=>`<li>#${i}</li>`,'bad')}
   ${list('缺少的节',p.missing_sections,x=>`<li>${esc(x)}</li>`,'bad')}
   ${list('第二节没写到的类',w.categories_not_discussed,x=>`<li>${esc(x)}</li>`,'warn')}
   ${wk&&R.history&&R.history.length>1?`<div class="rv-hist-w"><b>以前的小结</b><small>${R.history.slice(1,9).map(h=>esc(h)).join('、')}（存在 reports/lit_review/${esc(R.domain)}/week/ 下）</small></div>`:''}
   <div class="rv-note-box"><b>批注改稿</b><small>${wk?'写下哪里不对，比如"#416 不算新方向，全部综述里的检索类就是""撞车那条其实只是部分重合"。模型会按批注改第二、三节，没提到的尽量不动。':'写下哪里不对，比如"第一类和第三类其实是一回事""第三节第 2 条 #416 已经做了""第四节方向太空，样题要具体"。模型会按批注改第二到四节，没提到的尽量不动。'}</small><textarea id="rv-notes" rows="6" placeholder="写批注…"></textarea><button class="btn primary" id="rv-revise" ${R.status?.state==='running'||!rv.cfg.llm.ready?'disabled':''}>按批注改稿</button>
   ${notes.length?`<details class="rv-hist"><summary>改过 ${notes.length} 次</summary>${notes.map(x=>`<div><small>${esc(rvT(x.at))}</small><p>${esc(x.text)}</p></div>`).join('')}</details>`:''}</div>
   <p class="rv-caveat">程序只核对编号存在、原话没改，核对不了理解得对不对。用之前请自己读一遍，点 #编号 能打开原文。</p>
  </aside></div>`;
  $('#rv-revise').onclick=()=>{const t=$('#rv-notes').value.trim();if(!t){toast('先写批注');return}rvRun({notes:t})};
}

function rvTaxView(R){
  const box=$('#rv-view'),T=rv.tax;
  if(!T){box.innerHTML=`<div class="rv-empty">还没分类。先抽卡，再点上面的"开始分类"。</div>`;return}
  const meta=rvMeta(R),cards=R.cards;
  const placed=new Set([...T.categories.flatMap(c=>c.ids),...T.outside.map(o=>o.id)]);
  const newOnes=R.papers.filter(p=>cards[p.id]&&!placed.has(p.id)).map(p=>p.id);
  const opts=cur=>T.categories.map((c,i)=>`<option value="c${i}" ${cur==='c'+i?'selected':''}>${esc(c.name)}</option>`).join('')+`<option value="out" ${cur==='out'?'selected':''}>不算（移出）</option>${cur==='new'?'<option value="new" selected>还没分类</option>':''}<option value="add">＋ 新建一类…</option>`;
  const row=(id,cur,extra='')=>{const p=meta[id],c=cards[id]||{};if(!p)return '';return `<div class="rv-trow"><div><a href="${esc(p.url||'#')}" target="_blank" rel="noopener">${esc(p.title)}</a><small>#${id}${c.kind?' · '+esc(c.kind):''}${c.task?' · '+esc(c.task):''}</small>${extra}</div><select data-id="${id}" data-cur="${cur}">${opts(cur)}</select></div>`};
  box.innerHTML=`${rv.dirty?`<div class="rv-dirty"><span>分类改了还没保存。保存后要点上面"重写综述"，综述才会按新分类写。</span><button class="btn ghost" id="rv-undo">撤销</button><button class="btn primary" id="rv-savetax">保存分类</button></div>`:''}
  <p class="rv-hint">${T.by==='user'?'这是你调整过的分类。':'这是模型提出的分类。'}${R.scope==='week'?'本周论文先放进全部综述已有的类，放不进的才新建，标"新方向"。':''}可以把论文挪到别的类、改类名和说明。分错的、和选题无关的选"不算"。</p>
  ${newOnes.length?`<div class="rv-cat newc"><div class="rv-cat-h"><b>还没分类的新论文</b><span>${newOnes.length} 篇</span></div>${newOnes.map(id=>row(id,'new')).join('')}</div>`:''}
  ${T.categories.map((c,i)=>`<div class="rv-cat ${c.new&&R.scope==='week'&&R.base?.reviewed?'isnew':''}"><div class="rv-cat-h"><input class="rv-cname" data-i="${i}" value="${esc(c.name)}">${c.new&&R.scope==='week'&&R.base?.reviewed?'<em class="newtag">新方向</em>':''}<span>${c.ids.length} 篇</span></div><textarea class="rv-ctests" data-i="${i}" rows="2" placeholder="这类测什么、输入是什么">${esc(c.tests)}</textarea>${c.why?`<p class="why">归为一类的理由：${esc(c.why)}</p>`:''}${c.ids.map(id=>row(id,'c'+i)).join('')}</div>`).join('')}
  ${T.outside.length?`<div class="rv-cat outc"><div class="rv-cat-h"><b>不算进来的</b><span>${T.outside.length} 篇</span></div>${T.outside.map(o=>row(o.id,'out',o.reason?`<em>${esc(o.reason)}</em>`:'')).join('')}</div>`:''}`;
  const mark=()=>{rv.dirty=true;rvTaxView(R)};
  $$('#rv-view select[data-id]').forEach(s=>s.onchange=()=>{const id=+s.dataset.id,from=s.dataset.cur;let to=s.value;
    if(to==='add'){const name=(prompt('新类的名字')||'').trim();if(!name){s.value=from;return}T.categories.push({name,tests:'',why:'',ids:[]});to='c'+(T.categories.length-1)}
    if(from.startsWith('c'))T.categories[+from.slice(1)].ids=T.categories[+from.slice(1)].ids.filter(x=>x!==id);
    if(from==='out')T.outside=T.outside.filter(o=>o.id!==id);
    if(to==='out')T.outside.push({id,reason:'你移出的'});else T.categories[+to.slice(1)].ids.push(id);
    T.categories=T.categories.filter(c=>c.ids.length||c.tests||c.name.trim());mark()});
  $$('#rv-view .rv-cname').forEach(x=>x.onchange=()=>{T.categories[+x.dataset.i].name=x.value.trim()||T.categories[+x.dataset.i].name;mark()});
  $$('#rv-view .rv-ctests').forEach(x=>x.onchange=()=>{T.categories[+x.dataset.i].tests=x.value.trim();mark()});
  const u=$('#rv-undo');if(u)u.onclick=()=>{rv.dirty=false;rv.tax=R.taxonomy?JSON.parse(JSON.stringify(R.taxonomy)):null;rvTaxView(R)};
  const sv=$('#rv-savetax');if(sv)sv.onclick=async()=>{T.categories=T.categories.filter(c=>c.ids.length);try{const r=await api(rvUrl(rv.dom,rv.scope)+'/taxonomy',{method:'PUT',body:JSON.stringify(T)});rv.dirty=false;R.taxonomy=r.taxonomy;rv.tax=JSON.parse(JSON.stringify(r.taxonomy));await rvFetch(rv.dom);rv.cfg=await api('/api/review/config');renderReview();toast(R.scope==='week'?'分类已保存，点"重写小结"让小结按新分类写':'分类已保存，点"重写综述"让综述按新分类写')}catch(e){toast(e.message)}};
}

function rvCardsView(R){
  const box=$('#rv-view'),meta=rvMeta(R),q=rv.q.toLowerCase();
  const ids=R.papers.map(p=>p.id).filter(id=>R.cards[id]);
  if(!ids.length){box.innerHTML='<div class="rv-empty">还没抽卡。</div>';return}
  const shown=ids.filter(id=>{if(!q)return true;const c=R.cards[id],p=meta[id];return `${p.title} ${c.task} ${c.finding} ${c.input}`.toLowerCase().includes(q)});
  const noQ=ids.filter(id=>!R.cards[id].limit_quote).length,drop=ids.filter(id=>R.cards[id].quote_dropped).length;
  box.innerHTML=`<div class="rv-cbar"><input id="rv-q" placeholder="搜标题 / 测什么 / 发现" value="${esc(rv.q)}"><small>${ids.length} 张卡 · ${ids.length-noQ} 张找到了作者承认的局限${drop?` · ${drop} 张模型给的原话对不上摘要，已删掉`:''}</small></div>
  <div class="rv-cards">${shown.map(id=>{const c=R.cards[id],p=meta[id];return `<div class="rv-card"><div class="rv-card-h"><i class="k ${c.kind==='Benchmark'?'b':''}">${esc(c.kind||'')}</i><a href="${esc(p.url||'#')}" target="_blank" rel="noopener">${esc(p.title)}</a><small>#${id} · ${esc(p.date||'')}</small></div>
   <dl><dt>测什么</dt><dd>${esc(c.task)||'<span class="mut">摘要没写</span>'}</dd><dt>输入</dt><dd>${esc(c.input)||'<span class="mut">摘要没写</span>'}</dd><dt>判分</dt><dd>${esc(c.scoring)||'<span class="mut">摘要没写</span>'}</dd><dt>数据</dt><dd>${esc(c.data)||'<span class="mut">摘要没写</span>'}</dd><dt>发现</dt><dd>${esc(c.finding)||'<span class="mut">摘要没写</span>'}</dd>
   <dt>局限</dt><dd>${c.limit_quote?`<q class="orig">${esc(c.limit_quote)}</q><span class="cn">${esc(c.limit_cn)}</span>`:c.quote_dropped?`<span class="mut">模型给的原话对不上摘要，已删掉：</span><s>${esc(c.quote_dropped)}</s>`:'<span class="mut">摘要里没写局限</span>'}</dd></dl></div>`}).join('')||'<p class="rv-empty">没搜到</p>'}</div>`;
  const inp=$('#rv-q');inp.oninput=()=>{rv.q=inp.value;const pos=inp.selectionStart;rvCardsView(R);const n=$('#rv-q');n.focus();n.setSelectionRange(pos,pos)};
}

function rvInline(s,meta){
  s=esc(s);
  s=s.replace(/\[#\s*(\d+(?:\s*[,，、]\s*#?\s*\d+)*)\s*\]/g,(m,g)=>g.match(/\d+/g).map(i=>{const p=meta[i];return p?`<a class="cite" href="${esc(p.url)}" target="_blank" rel="noopener" title="${esc(p.title)}">#${i}</a>`:`<span class="cite bad" title="资料里没有这个编号">#${i}</span>`}).join(''));
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
