#!/usr/bin/env python3
"""artifact_data.json 을 임베드한 인터랙티브 HTML(browser.html) 생성."""
import json, os
HERE=os.path.dirname(__file__)
DATA=os.path.join(HERE,"..","results","compcert_report","artifact_data.json")
OUT=os.path.join(HERE,"..","results","compcert_report","browser.html")

data=open(DATA,encoding="utf-8").read()
data_safe=data.replace("</","<\\/")  # </script> breakout 방지 (JSON 에선 \/ == /)

HTML=r"""<title>rango 실패 × 형제 이식 브라우저</title>
<style>
:root{
  --bg:#fbfcfd; --surf:#ffffff; --surf2:#f2f5f9; --bd:#e0e5ec; --tx:#1a2130; --dim:#5b6678;
  --acc:#5b57e0; --pin:#dd9407; --pass:#16a34a; --part:#d97706; --fail:#dc2626; --muted:#94a3b8;
  --kw:#7c3aed; --tac:#2563eb; --cmt:#5f7a52; --code-bg:#f6f8fb;
  --shadow:0 1px 2px rgba(20,30,55,.06),0 4px 14px rgba(20,30,55,.05);
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0e1116; --surf:#161b22; --surf2:#1b222c; --bd:#29313d; --tx:#e6e9ef; --dim:#98a2b3;
  --acc:#8f8bff; --pin:#f5b544; --pass:#3fb950; --part:#e3a008; --fail:#f85149; --muted:#6b7684;
  --kw:#c9a1f0; --tac:#79b8ff; --cmt:#8faf7a; --code-bg:#0c1117;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 6px 18px rgba(0,0,0,.25);
}}
:root[data-theme="light"]{
  --bg:#fbfcfd; --surf:#ffffff; --surf2:#f2f5f9; --bd:#e0e5ec; --tx:#1a2130; --dim:#5b6678;
  --acc:#5b57e0; --pin:#dd9407; --pass:#16a34a; --part:#d97706; --fail:#dc2626; --muted:#94a3b8;
  --kw:#7c3aed; --tac:#2563eb; --cmt:#5f7a52; --code-bg:#f6f8fb;
  --shadow:0 1px 2px rgba(20,30,55,.06),0 4px 14px rgba(20,30,55,.05);
}
:root[data-theme="dark"]{
  --bg:#0e1116; --surf:#161b22; --surf2:#1b222c; --bd:#29313d; --tx:#e6e9ef; --dim:#98a2b3;
  --acc:#8f8bff; --pin:#f5b544; --pass:#3fb950; --part:#e3a008; --fail:#f85149; --muted:#6b7684;
  --kw:#c9a1f0; --tac:#79b8ff; --cmt:#8faf7a; --code-bg:#0c1117;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 6px 18px rgba(0,0,0,.25);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans KR",sans-serif;
  font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
.mono{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 80px}
header.top{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--bd);padding:14px 0 12px;margin-bottom:18px}
.hgrid{max-width:1180px;margin:0 auto;padding:0 20px}
h1{margin:0;font-size:17px;font-weight:650;letter-spacing:-.01em;text-wrap:balance}
.sub{color:var(--dim);font-size:12.5px;margin-top:2px}
.tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}
#q{display:block;width:100%;background:var(--surf);border:1px solid var(--bd);border-radius:9px;
  padding:8px 11px;color:var(--tx);font-size:13px;outline:none;margin-top:12px}
#q:focus{border-color:var(--acc);box-shadow:0 0 0 3px color-mix(in srgb,var(--acc) 22%,transparent)}
.chip{border:1px solid var(--bd);background:var(--surf);color:var(--dim);border-radius:20px;
  padding:5px 11px;font-size:12px;cursor:pointer;user-select:none;white-space:nowrap;
  font-variant-numeric:tabular-nums;transition:.12s}
.chip:hover{border-color:var(--acc);color:var(--tx)}
.chip.on{background:var(--acc);border-color:var(--acc);color:#fff}
.chip .n{opacity:.7;margin-left:4px}
button.ghost{border:1px solid var(--bd);background:var(--surf);color:var(--dim);border-radius:9px;
  padding:7px 10px;cursor:pointer;font-size:12.5px}
button.ghost:hover{color:var(--tx);border-color:var(--acc)}
.zone-h{display:flex;align-items:center;gap:8px;margin:22px 2px 10px;font-size:12px;
  text-transform:uppercase;letter-spacing:.08em;color:var(--dim);font-weight:600}
.zone-h .ln{flex:1;height:1px;background:var(--bd)}
.count{color:var(--dim);font-weight:600;font-variant-numeric:tabular-nums}
.card{background:var(--surf);border:1px solid var(--bd);border-left:3px solid color-mix(in srgb,var(--acc) 60%,var(--bd));
  border-radius:4px 12px 12px 4px;margin-bottom:9px;box-shadow:var(--shadow);overflow:hidden}
.card.open{border-left-color:var(--acc)}
.card.pinned{border-color:color-mix(in srgb,var(--pin) 55%,var(--bd));border-left:3px solid var(--pin)}
.chead{display:flex;align-items:center;gap:10px;padding:11px 13px;cursor:pointer}
.chead:hover{background:var(--surf2)}
.star{flex:none;width:30px;height:30px;border-radius:8px;border:1px solid var(--bd);background:var(--surf);
  cursor:pointer;display:grid;place-items:center;font-size:15px;color:var(--muted);transition:.12s;line-height:1}
.star:hover{border-color:var(--pin);color:var(--pin)}
.star.on{color:var(--pin);border-color:color-mix(in srgb,var(--pin) 55%,var(--bd));
  background:color-mix(in srgb,var(--pin) 12%,var(--surf))}
.idx{flex:none;font-size:11.5px;font-weight:700;color:var(--acc);
  background:color-mix(in srgb,var(--acc) 12%,transparent);border-radius:6px;padding:2px 7px;font-variant-numeric:tabular-nums}
.names{flex:1;min-width:0}
.names .pair{font-weight:600;font-size:13.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.names .pair .arr{color:var(--dim);font-weight:400;margin:0 5px}
.names .loc{color:var(--dim);font-size:11.5px;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.badges{flex:none;display:flex;gap:5px;align-items:center;flex-wrap:wrap;justify-content:flex-end;max-width:340px}
.bdg{font-size:11px;font-weight:600;border-radius:6px;padding:2px 7px;white-space:nowrap;line-height:1.5}
.bdg.pass{color:#fff;background:var(--pass)} .bdg.part{color:#fff;background:var(--part)}
.bdg.fail{color:#fff;background:var(--fail)} .bdg.na{color:var(--dim);background:var(--surf2);border:1px solid var(--bd)}
.bdg.av{color:var(--pass);background:color-mix(in srgb,var(--pass) 14%,transparent)}
.bdg.later{color:var(--part);background:color-mix(in srgb,var(--part) 15%,transparent)}
.bdg.cross{color:var(--dim);background:var(--surf2)}
.bdg.rango{color:var(--fail);background:color-mix(in srgb,var(--fail) 12%,transparent)}
.caret{flex:none;color:var(--muted);transition:.15s;font-size:12px}
.card.open .caret{transform:rotate(90deg)}
.body{display:none;border-top:1px solid var(--bd);padding:12px 13px 14px;background:var(--surf)}
.card.open .body{display:block}
.tabs{display:flex;gap:6px;margin-bottom:10px}
.tab{font-size:12px;padding:5px 11px;border-radius:8px;border:1px solid var(--bd);background:var(--surf);
  color:var(--dim);cursor:pointer}
.tab.on{background:var(--surf2);color:var(--tx);border-color:var(--acc)}
.rango-line{font-size:12px;color:var(--dim);margin:2px 2px 10px}
.rango-line b{color:var(--fail)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:720px){.cols{grid-template-columns:1fr}}
.col h4{margin:0 0 5px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);font-weight:650}
.col .cap{font-size:11px;color:var(--muted);margin-bottom:5px}
pre.code{margin:0;background:var(--code-bg);border:1px solid var(--bd);border-radius:9px;padding:10px 11px;
  overflow-x:auto;font-size:12px;line-height:1.5;max-height:460px}
pre.code code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.kw{color:var(--kw);font-weight:600} .tac{color:var(--tac)} .cmt{color:var(--cmt);font-style:italic}
.trace{border-left:2px solid color-mix(in srgb,var(--acc) 30%,var(--bd));padding-left:10px;margin-left:1px}
.trace details{border-left:2px solid color-mix(in srgb,var(--acc) 45%,var(--bd));border-radius:0 7px 7px 0;
  margin:5px 0;background:color-mix(in srgb,var(--acc) 5%,var(--surf));overflow:hidden}
.trace details[open]{background:color-mix(in srgb,var(--acc) 8%,var(--surf))}
.trace summary{cursor:pointer;padding:6px 9px 6px 11px;font-size:12px;list-style:none;display:flex;gap:8px;align-items:baseline}
.trace summary::-webkit-details-marker{display:none}
.trace summary::before{content:"▸";color:var(--acc);font-size:10px;flex:none;transform:translateY(-1px)}
.trace details[open]>summary::before{content:"▾"}
.trace details[open]>summary{border-bottom:1px solid var(--bd)}
/* 스텝 탭 헤더에 계층 힌트 */
.pane[data-pane="steps"] .col>h4::before{content:"┌ ";color:var(--acc);opacity:.6}
.trace summary .sn{flex:none;color:var(--acc);font-weight:700;font-size:10.5px;font-variant-numeric:tabular-nums;
  min-width:16px;text-align:right}
.trace summary .st-tac{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11.5px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--tx)}
.trace summary.init-s .st-tac{color:var(--dim);font-style:italic;font-family:inherit}
.trace .stbody{padding:8px 9px}
pre.st{max-height:300px;font-size:11.5px;margin:0}
.trace .none{color:var(--muted);font-size:11.5px;padding:8px 9px}
.empty{color:var(--dim);text-align:center;padding:40px;font-size:13px}
.legend{font-size:11.5px;color:var(--dim);margin-top:6px;display:flex;gap:14px;flex-wrap:wrap}
.legend span{display:inline-flex;align-items:center;gap:5px}
.sw{width:10px;height:10px;border-radius:3px;display:inline-block}
</style>

<header class="top">
 <div class="hgrid">
  <div style="display:flex;align-items:flex-start;gap:12px">
   <div style="flex:1">
    <h1>rango 실패 × 형제 증명 이식 브라우저</h1>
    <div class="sub">CompCert 1000-run 에서 rango 가 놓친 80건 — 대상↔이웃 코드, rango 가 막힌 지점, 우리 이식(composed) 결과. ⭐ 로 즐겨찾기(브라우저에 저장).</div>
   </div>
   <button class="ghost" id="theme">◐ 테마</button>
  </div>
  <input class="mono" id="q" placeholder="검색: 정리명 / idx / 파일…" autocomplete="off">
  <div class="tools" id="filters"></div>
  <div class="legend">
   <span><span class="sw" style="background:var(--pass)"></span>이식 PASS</span>
   <span><span class="sw" style="background:var(--part)"></span>부분(STUCK)</span>
   <span><span class="sw" style="background:var(--fail)"></span>실패(NOFIX)</span>
   <span><span class="sw" style="background:var(--muted)"></span>미평가</span>
   <span>·</span>
   <span>이웃 <b style="color:var(--pass)">avail</b>=rango 접근가능 / <b style="color:var(--part)">later</b>=파일 뒤(미접근) / cross=타파일</span>
  </div>
 </div>
</header>

<div class="wrap">
 <div id="pinzone"></div>
 <div class="zone-h"><span>전체 <span class="count" id="alln"></span></span><span class="ln"></span></div>
 <div id="list"></div>
 <div class="empty" id="empty" style="display:none">검색/필터에 맞는 항목이 없습니다.</div>
</div>

<script id="D" type="application/json">__DATA__</script>
<script>
const DATA=JSON.parse(document.getElementById('D').textContent);
const byIdx=Object.fromEntries(DATA.map(d=>[d.idx,d]));
const LS_PIN='rango-tp-pins-v1', LS_TH='rango-tp-theme';
let pins=[]; try{pins=JSON.parse(localStorage.getItem(LS_PIN))||[]}catch(e){pins=[]}
let q='', filt='all', openSet=new Set();

// 테마
const root=document.documentElement;
const savedTh=localStorage.getItem(LS_TH); if(savedTh)root.setAttribute('data-theme',savedTh);
document.getElementById('theme').onclick=()=>{
  const cur=root.getAttribute('data-theme')|| (matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
  const nx=cur==='dark'?'light':'dark'; root.setAttribute('data-theme',nx); localStorage.setItem(LS_TH,nx);
};

const cstClass={PASS:'pass',STUCK:'part',NOFIX:'fail',NOSTATE:'fail',SKIP_BIG:'na',NOEVAL:'na'};
const cstLabel=d=>({PASS:'이식 ✅ 종결',STUCK:'이식 ◑ '+(d.creach||'부분'),NOFIX:'이식 ✗ 실패',
  NOSTATE:'이식 ✗ 상태추출',SKIP_BIG:'거대증명 제외',NOEVAL:'미평가'})[d.cst];
const avClass={avail:'av',later:'later',cross:'cross'}, avLabel={avail:'이웃 avail ✅',later:'이웃 later ⚠️',cross:'타파일'};

const FILTERS=[['all','전체'],['PASS','PASS'],['STUCK','STUCK'],['NOFIX','NOFIX'],['avail','이웃 avail'],['pin','⭐ 즐겨찾기']];
function matches(d){
  if(q){const s=(d.idx+' '+d.t+' '+d.n+' '+d.tf).toLowerCase(); if(!s.includes(q))return false;}
  if(filt==='all')return true;
  if(filt==='avail')return d.avail==='avail';
  if(filt==='pin')return pins.includes(d.idx);
  return d.cst===filt;
}
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function traceCol(tr,label){
  if(!tr||!tr.steps){return `<div class="col"><h4>${label}</h4><div class="none">(스텝 상태 추출 없음 — 파일/타임아웃)</div></div>`;}
  let inner=`<details><summary class="init-s"><span class="sn">0</span><span class="st-tac">초기 goal (증명 시작 상태)</span></summary><div class="stbody"><pre class="code st"><code>${tr.init||'(없음)'}</code></pre></div></details>`;
  tr.steps.forEach((s,i)=>{
    const state = s.st && s.st.trim() ? s.st : '<span class="cmt">증명 종료 — no more goals</span>';
    inner+=`<details><summary><span class="sn">${i+1}</span><span class="st-tac">${esc(s.tac)}</span></summary><div class="stbody"><pre class="code st"><code>${state}</code></pre></div></details>`;
  });
  return `<div class="col"><h4>${label}</h4><div class="cap">각 스텝을 펼치면 그 tactic 직후의 goal state(가설 포함)</div><div class="trace">${inner}</div></div>`;
}
function card(d){
  const pinned=pins.includes(d.idx);
  const open=openSet.has(d.idx);
  const el=document.createElement('div');
  el.className='card'+(pinned?' pinned':'')+(open?' open':'');
  el.innerHTML=`
   <div class="chead">
     <button class="star ${pinned?'on':''}" title="즐겨찾기" data-pin="${d.idx}">${pinned?'★':'☆'}</button>
     <span class="idx">#${d.idx}</span>
     <div class="names">
       <div class="pair mono">${esc(d.t)}<span class="arr">←</span>${esc(d.n)}</div>
       <div class="loc mono">${esc(d.tf)}:L${d.tL} &nbsp;←&nbsp; ${esc(d.nf)}:L${d.nL}</div>
     </div>
     <div class="badges">
       <span class="bdg rango">rango ❌</span>
       <span class="bdg ${cstClass[d.cst]}">${cstLabel(d)}</span>
       <span class="bdg ${avClass[d.avail]}">${avLabel[d.avail]}</span>
     </div>
     <span class="caret">▶</span>
   </div>
   <div class="body">
     <div class="tabs">
       <span class="tab on" data-tab="code">코드 대조 (§6.1)</span>
       <span class="tab" data-tab="steps">스텝별 goal state</span>
       <span class="tab" data-tab="stuck">rango 막힌 지점 (§6.2)</span>
     </div>
     <div class="pane" data-pane="code">
       <div class="cols">
         <div class="col"><h4>대상 (rango 실패)</h4><div class="cap mono">${esc(d.tf)}:L${d.tL}</div><pre class="code"><code>${d.tcode||'(추출 실패)'}</code></pre></div>
         <div class="col"><h4>이웃 (형제)</h4><div class="cap mono">${esc(d.nf)}:L${d.nL} · suffix ${d.suf}/full ${d.fm}</div><pre class="code"><code>${d.ncode||'(추출 실패)'}</code></pre></div>
       </div>
     </div>
     <div class="pane" data-pane="steps" style="display:none">
       <div class="cols">
         ${traceCol(d.tst,'대상 '+esc(d.t))}
         ${traceCol(d.nst,'이웃 '+esc(d.n))}
       </div>
     </div>
     <div class="pane" data-pane="stuck" style="display:none">
       <div class="rango-line">rango: <b>${d.rsteps}</b>회 tactic 시도 (VALID ${d.rvalid}) → <b>${esc(d.rend)}</b> 후 포기</div>
       <div class="col" style="margin-bottom:10px"><h4>막힌 goal (rango 포기 시점)</h4><pre class="code"><code>${d.sgoal||'(없음)'}</code></pre></div>
       <div class="cols">
         <div class="col"><h4>rango 포기 직전 부분증명 — 발산·정지</h4><pre class="code"><code>${d.sproof||'(없음)'}</code></pre></div>
         <div class="col"><h4>이웃 형제 증명 (참조·이식원)</h4><div class="cap mono">${esc(d.nf)}:L${d.nL}</div><pre class="code"><code>${d.ncode||'(추출 실패)'}</code></pre></div>
       </div>
     </div>
   </div>`;
  // 이벤트
  el.querySelector('.star').addEventListener('click',ev=>{ev.stopPropagation();togglePin(d.idx)});
  el.querySelector('.chead').addEventListener('click',()=>{
    if(openSet.has(d.idx))openSet.delete(d.idx); else openSet.add(d.idx); render();
  });
  el.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',ev=>{
    ev.stopPropagation();
    el.querySelectorAll('.tab').forEach(x=>x.classList.remove('on')); t.classList.add('on');
    el.querySelectorAll('.pane').forEach(p=>p.style.display=p.dataset.pane===t.dataset.tab?'':'none');
  }));
  return el;
}
function togglePin(idx){
  const i=pins.indexOf(idx);
  if(i>=0)pins.splice(i,1); else pins.unshift(idx); // 새로 핀하면 맨 위로
  localStorage.setItem(LS_PIN,JSON.stringify(pins));
  render();
}
function render(){
  // 필터칩 카운트
  const fbox=document.getElementById('filters'); fbox.innerHTML='';
  FILTERS.forEach(([k,lab])=>{
    let n; if(k==='all')n=DATA.length; else if(k==='avail')n=DATA.filter(d=>d.avail==='avail').length;
    else if(k==='pin')n=pins.length; else n=DATA.filter(d=>d.cst===k).length;
    const c=document.createElement('div'); c.className='chip'+(filt===k?' on':'');
    c.innerHTML=lab+`<span class="n">${n}</span>`; c.onclick=()=>{filt=k;render()}; fbox.appendChild(c);
  });
  const shown=DATA.filter(matches);
  const pinnedShown=pins.map(i=>byIdx[i]).filter(d=>d&&matches(d));
  const rest=shown.filter(d=>!pins.includes(d.idx));
  // 핀 존
  const pz=document.getElementById('pinzone'); pz.innerHTML='';
  if(pinnedShown.length){
    const h=document.createElement('div'); h.className='zone-h';
    h.innerHTML=`<span>📌 즐겨찾기 <span class="count">${pinnedShown.length}</span></span><span class="ln"></span>`;
    pz.appendChild(h); pinnedShown.forEach(d=>pz.appendChild(card(d)));
  }
  // 전체
  const list=document.getElementById('list'); list.innerHTML='';
  rest.forEach(d=>list.appendChild(card(d)));
  document.getElementById('alln').textContent=rest.length;
  document.getElementById('empty').style.display=shown.length?'none':'block';
}
document.getElementById('q').addEventListener('input',e=>{q=e.target.value.trim().toLowerCase();render()});
render();
</script>
"""

open(OUT,"w",encoding="utf-8").write(HTML.replace("__DATA__", data_safe))
print("wrote", OUT, round(os.path.getsize(OUT)/1024),"KB")
