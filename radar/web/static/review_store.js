// 综述结果只在浏览器 IndexedDB 保存，密钥仍独立保存在 localStorage。
const RV_LOCAL=(()=>{
  const DB='radar-review-local',STORE='domains',TTL=864e5;
  let opening=null;
  const open=()=>opening||(opening=new Promise((resolve,reject)=>{
    if(!window.indexedDB){reject(new Error('浏览器不支持本地结果存储'));return}
    const r=indexedDB.open(DB,1);
    r.onupgradeneeded=()=>r.result.createObjectStore(STORE,{keyPath:'domain'});
    r.onsuccess=()=>{r.result.onversionchange=()=>{r.result.close();opening=null};resolve(r.result)};
    r.onerror=()=>{opening=null;reject(new Error('本地结果存储不可用'))};
    r.onblocked=()=>reject(new Error('本地存储升级受阻，请关闭其他页面'));
  }));
  async function read(domain){
    const db=await open();
    return new Promise((resolve,reject)=>{
      const tx=db.transaction(STORE,'readwrite'),store=tx.objectStore(STORE),r=store.get(domain);
      let files={};
      r.onsuccess=()=>{const o=r.result;if(o&&Date.now()-o.at<TTL)files=o.files;else if(o)store.delete(domain)};
      tx.oncomplete=()=>resolve(files);
      tx.onerror=tx.onabort=()=>reject(new Error('无法读取本地结果'));
    });
  }
  async function write(domain,files){
    const db=await open();
    return new Promise((resolve,reject)=>{
      const tx=db.transaction(STORE,'readwrite');
      tx.objectStore(STORE).put({domain,at:Date.now(),files});
      tx.oncomplete=()=>resolve();
      tx.onerror=tx.onabort=()=>reject(new Error('本地结果保存失败，请下载当前综述'));
    });
  }
  function summary(files,scope='all'){
    const p=scope==='week'?'week/':'';
    const get=n=>{try{return JSON.parse(files[p+n]||'null')}catch(e){return null}};
    let cards={};try{cards=JSON.parse(files['cards.json']||'{}').cards||{}}catch(e){}
    const t=get('taxonomy.json'),m=get('review.json'),s=get('status.json');
    return {cards:Object.keys(cards).length,categories:t?.categories?.length||0,
      reviewed:!!m,review_ok:!!m?.check?.ok,state:s?.state==='running'?'stale':s?.state||null};
  }
  return {read,write,summary};
})();
