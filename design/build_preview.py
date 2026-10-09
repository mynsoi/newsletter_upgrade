"""칼럼 작업실 PWA 화면 미리보기 — 실제 데이터를 넣은 클릭형 목업 (view/preview/index.html).

사용: python3 design/build_preview.py
참고 디자인: 21st.dev(왼쪽 사이드바·작은 정보 위계·호버), BoardUI(중첩 카드·상태 배지), Prompt Motion(개수 붙은 알약 필터·카드 그리드).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "view" / "preview" / "index.html"


def clean(t):
    t = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", t.strip()).strip()
    return re.sub(r"\s*\(끝\)\s*$", "", t)


def split(t):
    lines = clean(t).splitlines()
    for i, l in enumerate(lines):
        if l.strip():
            return re.sub(r"^[#*\s]+|[*\s]+$", "", l), "\n".join(lines[i + 1:]).strip()
    return "", ""


def paras(body):
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def read(p):
    p = ROOT / p
    return p.read_text(encoding="utf-8") if p.exists() else ""


def titles(p):
    return [re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", l).strip().strip("*") for l in read(p).splitlines() if l.strip()]


C = "runs/columns"
articles = []
for key, status, path, ver in [
    ("confirmed-1", "확정", "columns/2026-10-08-ai-퇴근시간.md", "확정본"),
    ("sim-C", "피드백 대기", f"{C}/sim-C/final-r1.md", "r1"),
    ("t2-B", "피드백 대기", f"{C}/t2-B/final.md", "최종"),
    ("t1-B", "피드백 대기", f"{C}/t1-B/final.md", "최종"),
    ("t3-B", "피드백 대기", f"{C}/t3-B/final.md", "최종"),
]:
    t, b = split(read(path))
    articles.append({"key": key, "status": status, "title": t, "ver": ver, "chars": len(re.sub(r"\s", "", b)),
                     "lead": paras(b)[0][:120] if b else ""})
articles.insert(1, {"key": "new-1", "status": "제목 고르는 중", "title": "(제목 미정) AI를 잘 쓰면 실력이 늘까", "ver": "0단계",
                    "chars": 0, "lead": "생각 한 줄: AI로 할 수 있는 일이 늘수록, 무엇을 만들고 무엇을 버릴지 판단하는 내 기준이 실력이 된다."})

ws_title, ws_final = split(read(f"{C}/sim-C/final-r1.md"))
_, ws_r4 = split(read(f"{C}/sim-C/r4.md"))
_, ws_draft = split(read(f"{C}/sim-C/draft.md"))
_, ws_final0 = split(read(f"{C}/sim-C/final.md"))
brief = json.loads(read(f"{C}/sim-C/brief.json") or "{}")
workspace = {
    "title": ws_title, "thesis": brief.get("thesis", ""),
    "titles": titles("runs/titles0/sim-C/astra.md"),
    "picked": 3,
    "versions": {"r1 · 피드백 반영": paras(ws_final), "최종": paras(ws_final0), "재작성(astra)": paras(ws_r4), "초안(Claude)": paras(ws_draft)},
    "feedback": read(f"{C}/sim-C/feedback-r1.txt").strip(),
}

# 원문 라이브러리 — 원문목록.md 표에서
sources = []
for line in read("sources/원문목록.md").splitlines():
    m = re.match(r"^\| (\d\d|p\d+[^|]*) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|", line)
    if not m:
        continue
    a = [x.strip() for x in m.groups()]
    if a[0].startswith("p"):
        sources.append({"kind": "경영일기", "id": a[0].replace(" ★", "").replace(" △", ""), "who": "유정식의 경영일기", "date": a[1],
                        "title": a[2], "reach": "", "core": a[5], "star": "★" in a[0]})
    else:
        kind = "Threads" if "@" in a[1] or "공냥이" in a[1] else "LinkedIn"
        sources.append({"kind": kind, "id": a[0], "who": a[1], "date": a[2], "title": a[5][:60], "reach": a[3], "core": a[5], "star": False})
# 표가 Threads·LinkedIn을 구분하는 머리글 기준으로 다시 정함
kinds, cur = {}, None
for line in read("sources/원문목록.md").splitlines():
    if line.startswith("## Threads"):
        cur = "Threads"
    elif line.startswith("## LinkedIn"):
        cur = "LinkedIn"
    elif line.startswith("## 유정식"):
        cur = "경영일기"
    m = re.match(r"^\| (\d\d) \|", line)
    if m and cur in ("Threads", "LinkedIn"):
        kinds[(cur, m.group(1))] = True
seen_t = 0
for s in sources:
    if s["kind"] != "경영일기":
        s["kind"] = "Threads" if seen_t < 12 else "LinkedIn"
        seen_t += 1

rules = []
for line in read("criteria.md").splitlines():
    m = re.match(r"^(\d+)\. \*\*(.+?)\*\*(.*)$", line)
    if m:
        rules.append({"n": int(m.group(1)), "rule": m.group(2), "note": m.group(3).strip()[:160]})

DATA = {"articles": articles, "ws": workspace, "sources": sources, "rules": rules}

HTML = r"""<!doctype html>
<html lang="ko" class="h-full"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#ffffff"><meta name="apple-mobile-web-app-capable" content="yes">
<title>칼럼 작업실</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard.min.css">
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config={darkMode:'class',theme:{extend:{fontFamily:{sans:['Pretendard','Inter','system-ui','sans-serif']}}}}</script>
<style>
html,body{-webkit-font-smoothing:antialiased;overflow-x:hidden}
.glow{position:absolute;inset:-20% -10% auto -10%;height:320px;pointer-events:none;background:radial-gradient(40% 60% at 30% 0%,rgba(59,130,246,.13),transparent 70%),radial-gradient(30% 50% at 70% 0%,rgba(236,72,153,.08),transparent 70%)}
.lift{transition:transform .18s ease,box-shadow .18s ease}.lift:hover{transform:translateY(-2px);box-shadow:0 8px 24px -12px rgba(0,0,0,.18)}
.shimmer{background:linear-gradient(90deg,rgba(0,0,0,.05) 0%,rgba(0,0,0,.10) 40%,rgba(0,0,0,.05) 80%);background-size:200% 100%;animation:sh 1.2s linear infinite}
.dark .shimmer{background:linear-gradient(90deg,rgba(255,255,255,.05) 0%,rgba(255,255,255,.12) 40%,rgba(255,255,255,.05) 80%);background-size:200% 100%}
@keyframes sh{to{background-position:-200% 0}}
.fade{animation:fd .22s ease}@keyframes fd{from{opacity:0;transform:translateY(4px)}}
.read p{font-size:16.5px;line-height:1.9;margin:0 0 16px;word-break:keep-all}
.s-add{background:rgba(34,197,94,.16);border-radius:3px}.s-del{background:rgba(239,68,68,.14);border-radius:3px;text-decoration:line-through;text-decoration-color:rgba(239,68,68,.5)}
.no-scrollbar::-webkit-scrollbar{display:none}
.spin{animation:sp 1s linear infinite}@keyframes sp{to{transform:rotate(360deg)}}
</style></head>
<body class="h-full bg-white text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
<div id="app" class="h-full flex"></div>
<script>
const D = __DATA__;
const $ = (s, r=document) => r.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const I = { // lucide 계열 단순 아이콘
  pen:'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  book:'<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',
  ruler:'<path d="M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.4 2.4 0 0 1 0-3.4l2.6-2.6a2.4 2.4 0 0 1 3.4 0Z"/><path d="m14.5 12.5 2-2"/><path d="m11.5 9.5 2-2"/><path d="m8.5 6.5 2-2"/>',
  check:'<path d="M20 6 9 17l-5-5"/>', search:'<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  plus:'<path d="M12 5v14M5 12h14"/>', bot:'<rect x="3" y="8" width="18" height="12" rx="3"/><path d="M12 8V4M8 14h.01M16 14h.01"/>',
  moon:'<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>', sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  img:'<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3-3L5 21"/>', star:'<path d="m12 2 3 7 7 .6-5.3 4.6 1.6 7.3L12 17.8 5.7 21.5l1.6-7.3L2 9.6 9 9Z"/>',
  chev:'<path d="m9 18 6-6-6-6"/>', globe:'<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>', x:'<path d="M18 6 6 18M6 6l12 12"/>',
  download:'<path d="M12 3v12m0 0-4-4m4 4 4-4M5 21h14"/>'
};
const ic = (n, c='w-4 h-4') => `<svg class="${c}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${I[n]}</svg>`;
const ST = {'확정':'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-500/20','피드백 대기':'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-500/20','제목 고르는 중':'bg-sky-50 text-sky-700 ring-sky-200 dark:bg-sky-500/10 dark:text-sky-300 dark:ring-sky-500/20','쓰는 중':'bg-violet-50 text-violet-700 ring-violet-200 dark:bg-violet-500/10 dark:text-violet-300 dark:ring-violet-500/20'};
const badge = s => `<span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ${ST[s]||'bg-zinc-100 text-zinc-600 ring-zinc-200'}"><span class="w-1.5 h-1.5 rounded-full bg-current"></span>${esc(s)}</span>`;
const state = { page: location.hash.slice(1) || 'home', step: 3, pick: D.ws.picked, ver: 'r1 · 피드백 반영', cmp: '최종', diff: true, drawer: false, srcFilter: '전체', running: false };

function sidebar(){
  const nav = [['home','글','pen',D.articles.length],['sources','원문 라이브러리','book',D.sources.length],['rules','기준','ruler',D.rules.length],['confirmed','확정본','check',D.articles.filter(a=>a.status==='확정').length]];
  return `<aside class="hidden md:flex w-[248px] shrink-0 flex-col border-r border-zinc-200 bg-zinc-50/70 dark:bg-zinc-900/60 dark:border-zinc-800">
    <div class="px-4 pt-4 pb-3 flex items-center gap-2"><div class="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-white grid place-items-center text-[13px] font-bold">칼</div><div class="font-semibold text-[15px]">칼럼 작업실</div></div>
    <div class="px-3"><button class="w-full flex items-center gap-2 rounded-lg bg-zinc-200/60 dark:bg-zinc-800 px-3 py-2 text-[13px] text-zinc-500">${ic('search')}<span>원문·글 검색</span><span class="ml-auto text-[11px] rounded border border-zinc-300 dark:border-zinc-700 px-1">⌘K</span></button></div>
    <div class="px-3 pt-3"><button onclick="go('ws',1)" class="w-full flex items-center justify-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-[13px] font-medium py-2">${ic('plus')}새 글</button></div>
    <div class="px-4 pt-5 pb-1 text-[12px] font-medium text-zinc-400">작업</div>
    <nav class="px-2 space-y-0.5">${nav.map(([k,l,i,n])=>`<a href="#${k}" onclick="go('${k}');return false" class="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[14px] ${state.page===k?'bg-white dark:bg-zinc-800 shadow-sm ring-1 ring-zinc-200 dark:ring-zinc-700 font-medium':'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/60'}">${ic(i)}<span>${l}</span><span class="ml-auto text-[11px] text-zinc-400">${n}</span></a>`).join('')}</nav>
    <div class="px-4 pt-5 pb-1 text-[12px] font-medium text-zinc-400">진행자</div>
    <nav class="px-2"><a href="#" onclick="toggleDrawer();return false" class="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[14px] text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/60">${ic('bot')}<span>진행자에게 묻기</span><span class="ml-auto text-[10px] rounded-full bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-300 px-1.5">Claude</span></a></nav>
    <div class="mt-auto m-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-3">
      <div class="text-[12px] font-medium mb-2">진행 중인 작업</div>
      ${[['t2-C · 글 쓰기','재작성(astra) · 2/3',62],['원문 모으기','Threads · 7/12',45]].map(([a,b,p])=>`<div class="mb-2 last:mb-0"><div class="flex justify-between text-[11.5px]"><span>${a}</span><span class="text-zinc-400">${b}</span></div><div class="mt-1 h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden"><div class="h-full rounded-full bg-blue-500" style="width:${p}%"></div></div></div>`).join('')}
    </div></aside>`;
}

function topbar(title, sub, right=''){
  return `<header class="sticky top-0 z-20 flex items-center gap-3 px-5 md:px-8 py-3.5 bg-white/80 dark:bg-zinc-950/80 backdrop-blur border-b border-zinc-100 dark:border-zinc-900">
    <div class="min-w-0"><div class="text-[17px] font-semibold truncate">${title}</div>${sub?`<div class="text-[12.5px] text-zinc-500 truncate">${sub}</div>`:''}</div>
    <div class="ml-auto flex items-center gap-1.5">${right}
      <button onclick="toggleDrawer()" class="hidden md:inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 px-2.5 py-1.5 text-[13px] hover:bg-zinc-50 dark:hover:bg-zinc-900">${ic('bot')}진행자</button>
      <button onclick="theme()" class="rounded-lg border border-zinc-200 dark:border-zinc-800 p-1.5 hover:bg-zinc-50 dark:hover:bg-zinc-900">${ic(document.documentElement.classList.contains('dark')?'sun':'moon')}</button>
    </div></header>`;
}

function pills(list, cur, fn){
  return `<div class="flex gap-1.5 overflow-x-auto no-scrollbar">${list.map(([k,n])=>`<button onclick="${fn}('${k}')" class="shrink-0 rounded-full border px-3 py-1 text-[13px] ${cur===k?'border-zinc-900 bg-zinc-900 text-white dark:bg-white dark:text-zinc-900 dark:border-white':'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-300 hover:border-zinc-400'}">${k}${n!==undefined?` <span class="opacity-60">${n}</span>`:''}</button>`).join('')}</div>`;
}

function home(){
  const cnt = s => D.articles.filter(a=>a.status===s).length;
  return topbar('글', '주제 한 줄 → 제목 → 본문 → 다듬기 → 이미지·확정', `<button onclick="go('ws',1)" class="md:hidden shrink-0 whitespace-nowrap inline-flex items-center gap-1 rounded-lg bg-blue-600 text-white px-2.5 py-1.5 text-[13px]">${ic('plus')}새 글</button>`) + `
  <div class="relative overflow-hidden px-5 md:px-8 py-6 max-w-[1180px] fade"><div class="glow"></div>
    <div class="relative mb-5">${pills([['전체',D.articles.length],['제목 고르는 중',cnt('제목 고르는 중')],['쓰는 중',cnt('쓰는 중')],['피드백 대기',cnt('피드백 대기')],['확정',cnt('확정')]],'전체','noop')}</div>
    <div class="relative rounded-2xl bg-zinc-100/70 dark:bg-zinc-900 p-2.5 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
      ${D.articles.map(a=>`<button onclick="go('ws',${a.status==='제목 고르는 중'?2:a.status==='확정'?5:4})" class="lift text-left rounded-xl bg-white dark:bg-zinc-950 ring-1 ring-zinc-200/80 dark:ring-zinc-800 p-4 flex flex-col gap-2 min-h-[164px]">
        <div class="flex items-center justify-between">${badge(a.status)}<span class="text-[11.5px] text-zinc-400">${esc(a.ver)}${a.chars?` · ${a.chars.toLocaleString()}자`:''}</span></div>
        <div class="text-[15.5px] font-semibold leading-snug">${esc(a.title)}</div>
        <div class="text-[13px] text-zinc-500 leading-relaxed line-clamp-3">${esc(a.lead)}</div>
        ${a.status==='확정'?`<div class="mt-auto h-16 rounded-lg bg-gradient-to-br from-sky-200 via-indigo-200 to-pink-200 dark:from-sky-900 dark:via-indigo-900 dark:to-pink-900 grid place-items-center text-[11px] text-zinc-600 dark:text-zinc-300">${ic('img')} 대표 이미지</div>`:''}
      </button>`).join('')}
    </div></div>`;
}

const STEPS = ['주제·원문','제목','본문','다듬기','이미지·확정'];
function stepper(){
  return `<div class="flex gap-1.5 overflow-x-auto no-scrollbar">${STEPS.map((s,i)=>{const n=i+1, on=state.step===n, done=state.step>n;
    return `<button onclick="setStep(${n})" class="shrink-0 inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[13px] border ${on?'border-blue-600 bg-blue-600 text-white':done?'border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-200':'border-dashed border-zinc-300 dark:border-zinc-700 text-zinc-400'}"><span class="w-4 h-4 rounded-full grid place-items-center text-[10px] ${on?'bg-white/25':done?'bg-emerald-500 text-white':'bg-zinc-100 dark:bg-zinc-800'}">${done?'✓':n}</span>${s}</button>`}).join('')}</div>`;
}

function ws(){
  const body = [step1,step2,step3,step4,step5][state.step-1]();
  return topbar(esc(state.step>=3?D.ws.title:'새 글'), '생각 한 줄: '+esc(D.ws.thesis.slice(0,70))+'…') + `
  <div class="px-5 md:px-8 pt-4 pb-3 border-b border-zinc-100 dark:border-zinc-900">${stepper()}</div>
  <div class="px-5 md:px-8 py-6 max-w-[1100px] fade">${body}</div>`;
}

function card(inner, cls=''){return `<div class="rounded-2xl bg-zinc-100/70 dark:bg-zinc-900 p-2.5 ${cls}"><div class="rounded-xl bg-white dark:bg-zinc-950 ring-1 ring-zinc-200/80 dark:ring-zinc-800 p-4">${inner}</div></div>`}
const h = (t, s='') => `<div class="mb-3"><div class="text-[15px] font-semibold">${t}</div>${s?`<div class="text-[12.5px] text-zinc-500 mt-0.5">${s}</div>`:''}</div>`;

function srcCard(s, sel){
  const k = {Threads:'bg-zinc-900 text-white dark:bg-white dark:text-zinc-900', LinkedIn:'bg-sky-600 text-white', '경영일기':'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300'}[s.kind];
  return `<label class="lift cursor-pointer rounded-xl bg-white dark:bg-zinc-950 ring-1 ${sel?'ring-blue-500 ring-2':'ring-zinc-200/80 dark:ring-zinc-800'} p-3.5 flex flex-col gap-1.5 break-inside-avoid mb-2.5">
    <div class="flex items-center gap-1.5"><span class="rounded-md px-1.5 py-0.5 text-[10.5px] font-medium ${k}">${s.kind}</span><span class="text-[12px] text-zinc-500 truncate">${esc(s.who)}</span><span class="ml-auto text-[11px] text-zinc-400">${esc(s.date)}</span></div>
    <div class="text-[13.5px] leading-relaxed">${esc(s.core)}</div>
    <div class="flex items-center gap-2 text-[11.5px] text-zinc-400">${s.reach?`♥ ${esc(s.reach)}`:''}${s.star?'<span class="text-amber-500">★ 주제 직결</span>':''}${sel?`<span class="ml-auto text-blue-600 font-medium">${sel}</span>`:''}</div></label>`;
}

function step1(){
  const pick = {'05':'중심','04':'보조'};
  const list = D.sources.filter(s=>s.kind!=='경영일기').slice(0,12);
  return `<div class="grid lg:grid-cols-[1fr_340px] gap-5"><div>
    ${card(h('이 글이 말할 것 (생각 한 줄)','멘토가 정합니다. 이 한 줄이 제목 후보와 본문의 기준이 됩니다.')+`<textarea class="w-full min-h-[84px] rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-3 text-[14px] leading-relaxed">${esc(D.ws.thesis)}</textarea>`)}
    <div class="mt-5 flex items-end justify-between gap-3 mb-3">${h('원문 고르기','중심 원문 1개 + 보조 원문. 원문은 통째로 글쓴이에게 넘어갑니다.')}
      <button onclick="sheet()" class="shrink-0 inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 px-3 py-1.5 text-[13px] hover:bg-zinc-50 dark:hover:bg-zinc-900">${ic('globe')}aside로 더 모으기</button></div>
    <div class="mb-3">${pills([['전체',D.sources.length],['Threads',12],['LinkedIn',10],['경영일기',D.sources.filter(s=>s.kind==='경영일기').length]],'전체','noop')}</div>
    <div class="columns-1 sm:columns-2 gap-2.5">${list.map(s=>srcCard(s, s.kind==='LinkedIn'&&s.id==='04'?'중심':s.kind==='Threads'&&s.id==='05'?'보조 (5~9편)':'')).join('')}</div>
  </div>
  <div class="lg:sticky lg:top-24 h-fit">${card(h('선택한 원문')+`<div class="space-y-2 text-[13px]"><div class="flex gap-2"><span class="text-blue-600 font-medium w-8">중심</span><span>LinkedIn · 프로덕트 디자인 디렉터 (1,070자)</span></div><div class="flex gap-2"><span class="text-zinc-500 w-8">보조</span><span>Threads · 기업 AI 교육 강사 5~9편</span></div></div>
    <button onclick="setStep(2)" class="mt-4 w-full rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-[14px] font-medium py-2.5">제목 후보 뽑기 <span class="opacity-70 text-[12px]">astra · 약 1분</span></button>`)}</div></div>`;
}

function step2(){
  return `${h('제목 후보 (astra)','생각 한 줄과 원문만 보고 지은 8개입니다. 고른 제목은 이후 단계에서 바뀌지 않습니다.')}
  <div class="grid sm:grid-cols-2 gap-2.5">${D.ws.titles.map((t,i)=>`<button onclick="state.pick=${i+1};render()" class="lift text-left rounded-xl p-4 ring-1 ${state.pick===i+1?'ring-2 ring-blue-500 bg-blue-50/50 dark:bg-blue-500/10':'ring-zinc-200 dark:ring-zinc-800 bg-white dark:bg-zinc-950'}">
    <div class="flex items-start gap-3"><span class="mt-0.5 w-5 h-5 shrink-0 rounded-full grid place-items-center text-[11px] ${state.pick===i+1?'bg-blue-600 text-white':'bg-zinc-100 dark:bg-zinc-800 text-zinc-500'}">${i+1}</span><span class="text-[15px] font-medium leading-snug">${esc(t)}</span></div></button>`).join('')}</div>
  <div class="mt-4 flex flex-wrap gap-2 items-center">
    <input placeholder="직접 쓰기" class="flex-1 min-w-[220px] rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-3 py-2 text-[14px]">
    <button class="rounded-lg border border-zinc-200 dark:border-zinc-800 px-3 py-2 text-[13px]">다시 뽑기</button>
    <button onclick="runWrite()" class="rounded-lg bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 text-[14px] font-medium">이 제목으로 쓰기 <span class="opacity-70 text-[12px]">약 8~10분</span></button></div>`;
}

const STAGES = [['초안','Claude · 원문 통째 + 경영일기 3편 문체 참고',311],['재작성','astra · "경영일기 필자가 직접 썼다면" (p724·p669)',65],['기준 반영','astra · 멘토 기준 13개 원문 그대로',75]];
function step3(){
  if (state.running) return `${h('글 쓰는 중','창을 닫아도 서버에서 계속 돕니다. 다시 열면 이어서 보입니다.')}
    <div class="space-y-2.5">${STAGES.map(([n,d,s],i)=>{const st = i<state.runIdx?'done':i===state.runIdx?'run':'wait';
      return `<div class="rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-4 flex items-center gap-3 ${st==='wait'?'opacity-50':''}">
        <div class="w-7 h-7 rounded-full grid place-items-center ${st==='done'?'bg-emerald-500 text-white':st==='run'?'bg-blue-50 text-blue-600 dark:bg-blue-500/10':'bg-zinc-100 dark:bg-zinc-800 text-zinc-400'}">${st==='done'?ic('check'):st==='run'?'<svg class="w-4 h-4 spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.2-8.6"/></svg>':i+1}</div>
        <div class="min-w-0 flex-1"><div class="text-[14px] font-medium">${n}</div><div class="text-[12.5px] text-zinc-500 truncate">${d}</div>${st==='run'?'<div class="mt-2 h-2 rounded shimmer"></div>':''}</div>
        <div class="text-[12px] text-zinc-400 tabular-nums">${st==='done'?s+'초':st==='run'?'진행 중':''}</div></div>`}).join('')}</div>`;
  return reader();
}

function sents(t){return t.replace(/\s+/g,' ').split(/(?<=[.?!])\s+/).filter(Boolean)}
function lcs(a,b){const n=a.length,m=b.length,d=Array.from({length:n+1},()=>new Int16Array(m+1));for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)d[i][j]=a[i]===b[j]?d[i+1][j+1]+1:Math.max(d[i+1][j],d[i][j+1]);const ka=new Set(),kb=new Set();let i=0,j=0;while(i<n&&j<m){if(a[i]===b[j]){ka.add(i);kb.add(j);i++;j++}else if(d[i+1][j]>=d[i][j+1])i++;else j++}return[ka,kb]}
function reader(){
  const vs = Object.keys(D.ws.versions), cur = D.ws.versions[state.ver], base = D.ws.versions[state.cmp];
  let html;
  if (state.diff && state.cmp !== state.ver){
    const A = base.flatMap(p=>sents(p)).map(s=>s.replace(/\s/g,'')), keep = lcs(A, cur.flatMap(p=>sents(p)).map(s=>s.replace(/\s/g,'')))[1];
    let k=0; html = cur.map(p=>'<p>'+sents(p).map(s=>{const c=keep.has(k++)?'':'s-add';return `<span class="${c}">${esc(s)}</span>`}).join(' ')+'</p>').join('');
  } else html = cur.map(p=>`<p>${esc(p)}</p>`).join('');
  const chars = cur.join('').replace(/\s/g,'').length;
  return `<div class="grid lg:grid-cols-[1fr_300px] gap-6"><article>
    <div class="flex flex-wrap items-center gap-2 mb-4">${pills(vs.map(v=>[v]),state.ver,'setVer')}</div>
    <h1 class="text-[24px] md:text-[26px] font-bold leading-snug tracking-tight mb-5">${esc(D.ws.title)}</h1>
    <div class="read">${html}</div></article>
  <aside class="lg:sticky lg:top-24 h-fit space-y-3">
    ${card(`<div class="text-[12px] text-zinc-500">분량</div><div class="text-[22px] font-semibold tabular-nums">${chars.toLocaleString()}<span class="text-[13px] font-normal text-zinc-500"> 자 (공백 제외)</span></div>
      <div class="mt-3 flex items-center justify-between text-[13px]"><span>바뀐 문장 표시</span><button onclick="state.diff=!state.diff;render()" class="w-10 h-6 rounded-full p-0.5 ${state.diff?'bg-blue-600':'bg-zinc-300 dark:bg-zinc-700'}"><span class="block w-5 h-5 rounded-full bg-white transition ${state.diff?'translate-x-4':''}"></span></button></div>
      <div class="mt-2 text-[12.5px] text-zinc-500">비교 기준 <select onchange="state.cmp=this.value;render()" class="ml-1 rounded border border-zinc-200 dark:border-zinc-800 bg-transparent px-1 py-0.5">${vs.map(v=>`<option ${v===state.cmp?'selected':''}>${v}</option>`).join('')}</select></div>`)}
    ${card(`<div class="text-[13px] font-medium mb-1.5">이번에 반영한 피드백</div><div class="text-[13px] text-zinc-600 dark:text-zinc-300 rounded-lg bg-zinc-50 dark:bg-zinc-900 p-2.5">“${esc(D.ws.feedback)}”</div>
      <button onclick="setStep(4)" class="mt-3 w-full rounded-lg border border-zinc-200 dark:border-zinc-800 py-2 text-[13px]">피드백 더 주기</button>
      <button onclick="setStep(5)" class="mt-2 w-full rounded-lg bg-blue-600 text-white py-2 text-[13px] font-medium">이미지 만들고 확정</button>`)}
  </aside></div>`;
}

function step4(){
  return `<div class="grid lg:grid-cols-[1fr_340px] gap-6"><div>${reader()}</div></div>`.replace('</aside></div>', `</aside></div>`) .replace('<aside class="lg:sticky lg:top-24 h-fit space-y-3">', `<aside class="lg:sticky lg:top-24 h-fit space-y-3">${card(`<div class="text-[14px] font-semibold mb-1">피드백</div><div class="text-[12.5px] text-zinc-500 mb-2">쓴 그대로 astra에게 넘어갑니다. Claude가 고쳐 옮기지 않습니다.</div>
      <textarea placeholder="예) 출처를 문장에다가 남길 필요 없어." class="w-full min-h-[110px] rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-2.5 text-[13.5px]"></textarea>
      <label class="mt-2 flex items-center gap-2 text-[12.5px]"><input type="checkbox" class="accent-blue-600"> 이 피드백을 기준에도 추가 (다음 글부터 적용)</label>
      <button class="mt-3 w-full rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 py-2 text-[13px] font-medium">반영해서 다시 쓰기 <span class="opacity-60">astra · 약 1분</span></button>`)}`);
}

function step5(){
  const P = ['회의실 테이블 위, 노트북 화면에 AI가 만든 슬라이드 여러 장이 펼쳐져 있고 한 사람이 그중 한 장에만 펜으로 표시하는 장면. 따뜻한 오후 빛, 사실적인 사진 느낌.',
             '책상 위 종이 더미에서 몇 장만 골라 오른쪽으로 옮기고 나머지는 상자에 넣는 손. 위에서 내려다본 구도, 차분한 색.',
             '디자이너의 모니터 앞, 같은 화면을 여러 버전으로 띄워 놓고 하나를 지우는 순간. 단색 배경의 간결한 일러스트.'];
  const G = ['from-amber-200 via-orange-200 to-rose-200 dark:from-amber-900 dark:via-orange-900 dark:to-rose-900','from-slate-200 via-zinc-200 to-stone-300 dark:from-slate-800 dark:via-zinc-800 dark:to-stone-800','from-sky-200 via-indigo-200 to-violet-200 dark:from-sky-900 dark:via-indigo-900 dark:to-violet-900'];
  return `${h('대표 이미지','astra가 본문을 읽고 그림 설명 3개를 쓰고, gti(god-tibo-imagen)가 1536×1024로 만듭니다.')}
  <div class="grid md:grid-cols-3 gap-3">${P.map((p,i)=>`<button class="lift text-left rounded-2xl ring-1 ${i===0?'ring-2 ring-blue-500':'ring-zinc-200 dark:ring-zinc-800'} overflow-hidden bg-white dark:bg-zinc-950">
    <div class="aspect-[3/2] bg-gradient-to-br ${G[i]} grid place-items-center text-[12px] text-zinc-600 dark:text-zinc-300">${ic('img','w-6 h-6')}<span class="sr-only">이미지 ${i+1}</span></div>
    <div class="p-3"><div class="text-[11.5px] text-zinc-400 mb-1">그림 설명 ${i+1} · astra</div><div class="text-[12.5px] leading-relaxed line-clamp-3">${esc(p)}</div></div></button>`).join('')}</div>
  <div class="mt-5 flex flex-wrap gap-2"><button class="rounded-lg border border-zinc-200 dark:border-zinc-800 px-3 py-2 text-[13px]">설명 다시 뽑기</button><button class="rounded-lg border border-zinc-200 dark:border-zinc-800 px-3 py-2 text-[13px]">이미지 다시 만들기</button>
    <button onclick="go('confirmed')" class="ml-auto rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 text-[14px] font-medium">${ic('check','w-4 h-4 inline -mt-0.5')} 확정 — 확정본 폴더에 저장</button></div>`;
}

function sources(){
  const f = state.srcFilter, list = D.sources.filter(s=>f==='전체'||s.kind===f);
  return topbar('원문 라이브러리', '모은 원문은 요약하지 않고 그대로 저장합니다 · 발행물에는 옮기지 않습니다', `<button onclick="sheet()" class="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 text-white px-3 py-1.5 text-[13px]">${ic('globe')}aside로 모으기</button>`) + `
  <div class="px-5 md:px-8 py-6 max-w-[1180px] fade"><div class="mb-4">${pills([['전체',D.sources.length],['Threads',12],['LinkedIn',10],['경영일기',D.sources.filter(s=>s.kind==='경영일기').length]],f,'setSrc')}</div>
  <div class="columns-1 sm:columns-2 lg:columns-3 gap-2.5">${list.map(s=>srcCard(s,'')).join('')}</div></div>`;
}

function rules(){
  return topbar('기준', '멘토 피드백을 원문 그대로 쌓습니다. 모든 글의 기준 반영 단계에 그대로 들어갑니다.', `<button class="inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 px-3 py-1.5 text-[13px]">${ic('plus')}기준 추가</button>`) + `
  <div class="px-5 md:px-8 py-6 max-w-[900px] fade space-y-2">${D.rules.map(r=>`<div class="lift rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 bg-white dark:bg-zinc-950 p-4 flex gap-3">
    <span class="w-6 h-6 shrink-0 rounded-full bg-zinc-100 dark:bg-zinc-800 grid place-items-center text-[11px] text-zinc-500">${r.n}</span>
    <div class="min-w-0 flex-1"><div class="text-[14px] font-medium leading-snug">${esc(r.rule)}</div>${r.note?`<div class="text-[12.5px] text-zinc-500 mt-1">${esc(r.note)}</div>`:''}</div>
    <button class="self-start w-9 h-5 rounded-full p-0.5 bg-blue-600"><span class="block w-4 h-4 rounded-full bg-white translate-x-4"></span></button></div>`).join('')}</div>`;
}

function confirmed(){
  const a = D.articles.filter(x=>x.status==='확정');
  return topbar('확정본', '확정한 글과 대표 이미지 · 발행 도구(.md 업로드)로 넘길 수 있습니다') + `
  <div class="px-5 md:px-8 py-6 max-w-[1180px] fade grid sm:grid-cols-2 lg:grid-cols-3 gap-3">${a.map(x=>`<div class="lift rounded-2xl ring-1 ring-zinc-200 dark:ring-zinc-800 overflow-hidden bg-white dark:bg-zinc-950">
    <div class="aspect-[3/2] bg-gradient-to-br from-sky-200 via-indigo-200 to-pink-200 dark:from-sky-900 dark:via-indigo-900 dark:to-pink-900"></div>
    <div class="p-4"><div class="text-[11.5px] text-zinc-400 mb-1">2026-10-08 · ${x.chars.toLocaleString()}자</div><div class="text-[15px] font-semibold leading-snug">${esc(x.title)}</div>
    <div class="mt-3 flex gap-1.5"><button class="rounded-lg border border-zinc-200 dark:border-zinc-800 px-2.5 py-1 text-[12.5px]">${ic('download','w-3.5 h-3.5 inline -mt-0.5')} .md</button><button class="rounded-lg border border-zinc-200 dark:border-zinc-800 px-2.5 py-1 text-[12.5px]">발행 도구로</button></div></div></div>`).join('')}</div>`;
}

function drawer(){
  if (!state.drawer) return '';
  const M = [['me','새 글 시작합니다. 제목 후보 뽑아 주세요.'],['ai','설정의 중심 원문 경로 <code>originals/linkedin/4.md</code>에 파일이 없습니다. 실제 이름은 <code>04.md</code>입니다(앞의 0 누락). 고치시면 바로 제목 후보를 뽑겠습니다.'],['me','04.md가 맞아. 고쳐서 진행해 줘.'],['ai','경로를 고친 뒤 astra로 제목 후보 8개를 뽑았습니다. 번호를 고르시거나 직접 주세요.'],['me','왜 이 원문을 중심으로 썼어?'],['ai','원문은 설정에 정해져 있었고, 파이프라인은 첫 원문을 중심 재료로 넘깁니다. 본문 앞쪽 절반(주니어→시니어, AI로 직접 만들게 된 경험, 무엇을 버릴지는 내가 판단)이 LinkedIn 글에서, 뒤쪽 경고(인지적 오프로딩, 3~5년 감각)가 Threads 5~9편에서 왔습니다.']];
  return `<div class="fixed inset-0 z-40 md:static md:z-auto md:w-[360px] md:shrink-0 md:border-l border-zinc-200 dark:border-zinc-800 bg-black/30 md:bg-transparent" onclick="if(event.target===this)toggleDrawer()">
   <div class="absolute bottom-0 inset-x-0 h-[78%] md:h-full md:static rounded-t-2xl md:rounded-none bg-white dark:bg-zinc-950 flex flex-col fade">
    <div class="flex items-center gap-2 px-4 py-3 border-b border-zinc-100 dark:border-zinc-900">${ic('bot')}<div class="text-[14px] font-semibold">진행자</div><span class="text-[11px] text-zinc-400">Claude · 이 글 세션 이어 가기</span><button onclick="toggleDrawer()" class="ml-auto p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-900">${ic('x')}</button></div>
    <div class="flex-1 overflow-y-auto p-4 space-y-3">${M.map(([w,t])=>`<div class="flex ${w==='me'?'justify-end':''}"><div class="max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[13.5px] leading-relaxed ${w==='me'?'bg-blue-600 text-white rounded-br-md':'bg-zinc-100 dark:bg-zinc-900 rounded-bl-md'}">${t}</div></div>`).join('')}
      <div class="text-[11px] text-center text-zinc-400">이 글에서 진행자 비용 $1.23 · 글은 쓰지 않고 진행만 합니다</div></div>
    <div class="px-3 pt-2 flex gap-1.5 overflow-x-auto no-scrollbar">${['원문 더 모아 줘','오류 원인 찾아 줘','왜 이렇게 바뀌었어?'].map(x=>`<button class="shrink-0 rounded-full border border-zinc-200 dark:border-zinc-800 px-2.5 py-1 text-[12px]">${x}</button>`).join('')}</div>
    <div class="p-3"><div class="flex gap-2 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-1.5"><input placeholder="진행자에게 묻기" class="flex-1 min-w-0 bg-transparent px-2 text-[13.5px] outline-none"><button class="shrink-0 whitespace-nowrap rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 px-3 py-1.5 text-[13px]">보내기</button></div></div>
   </div></div>`;
}

function sheetHTML(){
  return `<div id="sheet" class="fixed inset-0 z-50 bg-black/30 grid place-items-end md:place-items-center" onclick="if(event.target===this)this.remove()">
   <div class="w-full md:w-[520px] rounded-t-2xl md:rounded-2xl bg-white dark:bg-zinc-950 p-5 fade">
    <div class="flex items-center mb-1"><div class="text-[16px] font-semibold">aside로 원문 모으기</div><button onclick="$('#sheet').remove()" class="ml-auto p-1">${ic('x')}</button></div>
    <div class="text-[12.5px] text-zinc-500 mb-4">진행자(Claude)가 aside로 찾고, 원문은 요약하지 않고 그대로 저장합니다. 읽기만 합니다.</div>
    <label class="text-[13px] font-medium">무엇을 찾을까요</label><input value="AI를 쓰면서 오히려 실력이 줄었다는 경험담" class="mt-1 mb-3 w-full rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 px-3 py-2 text-[14px]">
    <label class="text-[13px] font-medium">어디서</label><div class="mt-1 mb-3 flex flex-wrap gap-1.5">${['Threads','LinkedIn','경영일기','직접 URL'].map((x,i)=>`<button class="rounded-full border px-3 py-1 text-[13px] ${i<2?'border-blue-600 bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300':'border-zinc-200 dark:border-zinc-800'}">${x}</button>`).join('')}</div>
    <div class="flex items-center gap-3 text-[13px]"><span>최대</span><input type="range" min="3" max="15" value="8" class="flex-1 accent-blue-600"><span class="tabular-nums">8개</span></div>
    <button onclick="$('#sheet').remove()" class="mt-5 w-full rounded-lg bg-blue-600 text-white py-2.5 text-[14px] font-medium">모으기 시작 <span class="opacity-70 text-[12px]">약 10~20분 · 끝나면 알림</span></button></div></div>`;
}

function mobileNav(){
  const t = [['home','글','pen'],['sources','원문','book'],['rules','기준','ruler'],['confirmed','확정본','check']];
  return `<nav class="md:hidden fixed bottom-0 inset-x-0 z-30 border-t border-zinc-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-950/90 backdrop-blur pb-[env(safe-area-inset-bottom)]">
    <div class="grid grid-cols-5">${t.map(([k,l,i])=>`<button onclick="go('${k}')" class="py-2 flex flex-col items-center gap-0.5 text-[11px] ${state.page===k?'text-blue-600':'text-zinc-500'}">${ic(i,'w-5 h-5')}${l}</button>`).join('')}
    <button onclick="toggleDrawer()" class="py-2 flex flex-col items-center gap-0.5 text-[11px] text-zinc-500">${ic('bot','w-5 h-5')}진행자</button></div></nav>`;
}

function render(){
  const pages = {home, ws, sources, rules, confirmed};
  $('#app').innerHTML = sidebar() + `<main class="flex-1 min-w-0 h-full overflow-y-auto overflow-x-hidden pb-20 md:pb-0">${(pages[state.page]||home)()}</main>` + drawer() + mobileNav();
}
function go(p, step){ state.page = p; if (step) state.step = step; state.running=false; location.hash = p; render(); }
function setStep(n){ state.step = n; state.running=false; render(); }
function setVer(v){ state.ver = v; if (state.cmp===v) state.cmp = Object.keys(D.ws.versions).find(x=>x!==v); render(); }
function setSrc(v){ state.srcFilter = v; render(); }
function toggleDrawer(){ state.drawer = !state.drawer; render(); }
function sheet(){ document.body.insertAdjacentHTML('beforeend', sheetHTML()); }
function theme(){ document.documentElement.classList.toggle('dark'); render(); }
function noop(){}
function runWrite(){ state.step = 3; state.running = true; state.runIdx = 0; render();
  const tick = () => { state.runIdx++; if (state.runIdx >= STAGES.length) { state.running=false; state.ver='최종'; state.cmp='재작성(astra)'; } render(); if (state.running) setTimeout(tick, 1600); };
  setTimeout(tick, 1600); }
if (matchMedia('(prefers-color-scheme: dark)').matches) document.documentElement.classList.add('dark');
const Q = new URLSearchParams(location.search);
if (Q.get('step')) state.step = +Q.get('step'); if (Q.has('drawer')) state.drawer = true;
if (Q.has('dark')) document.documentElement.classList.add('dark'); if (Q.has('light')) document.documentElement.classList.remove('dark');
window.addEventListener('hashchange', ()=>{ const p = location.hash.slice(1); if (p && p!==state.page){ state.page=p; render(); } });
render();
</script></body></html>"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(HTML.replace("__DATA__", json.dumps(DATA, ensure_ascii=False)), encoding="utf-8")
print(OUT, "· 글", len(articles), "· 원문", len(sources), "· 기준", len(rules), "· 제목 후보", len(workspace["titles"]))
