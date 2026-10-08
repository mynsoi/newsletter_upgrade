"""mentor-lab 실험 결과를 한 장짜리 비교 화면(view/index.html)으로 만든다.

사용: python3 build_view.py   → mentor-lab/view/index.html
- runs/skilltest/<워크트리>/{A,B}.md, runs/rewrite/<모델>-R?/output.md 를 모은다.
- 글마다 분량·AI 버릇 개수(ai_tells.py와 같은 패턴)를 계산해 넣는다.
- 화면: 두 편을 골라 나란히 보기, 바뀐 문장 표시, 판마다 점수·메모(브라우저에 저장, 내보내기).
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
OUT = ROOT / "view" / "index.html"

PATS = {
    "대비": r"아니라|(?:것은|건|게|때문은) 아닙|보다[ ,]",
    "나열": r"(?:^|\s)(?:첫째|둘째|셋째|첫 번째|두 번째|세 번째)[,는 ]",
    "선언": r"분명히 말|말하고 싶|말씀드리겠",
    "번역투": r"(?:을|를) 통해|에 있어(?:서)?\b|에 의해",
}

GROUPS = [
    ("draft", "공통 초안"),
    ("A", "1단계 · 처음부터 쓰기 (워크트리별 스킬)"),
    ("B", "2단계 · 같은 초안 다듬기 (스킬 효과만)"),
    ("R", "재작성 · \"영어로 쓰면 좋은데 한국어로 쓰니 이상한 글\" 고치기"),
    ("S", "기준안 · R4·astra + 멘토 피드백(출처 소개 빼기)"),
]

DESC = {
    "base": "스킬 없음",
    "fluent-korean": "fluent-korean (출력 스타일)",
    "yoonmoon": "yoonmoon:polish-all",
    "im-not-ai": "im-not-ai humanize-korean",
    "avoid-ai-writing": "avoid-ai-writing (영어 기준 스킬)",
}
RDESC = {
    "R1": "멘토 평 그대로만 주고 다시 쓰기",
    "R2": "멘토 평 + 영어식 뼈대 진단(주제문·첫째둘째·선언·경구·대구)",
    "R3": "말로 풀어 본 뒤 그 말투로 글에 옮기기",
    "R4": "유정식 경영일기 2편을 주고 그 필자가 썼다면",
    "R5": "korean-lover 스킬(번역체 제거)로 다시 쓰기",
}


def clean(t):
    t = t.strip()
    t = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", t).strip()
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S).strip()
    return t


def split_title(t):
    lines = t.splitlines()
    for i, l in enumerate(lines):
        if l.strip():
            title = re.sub(r"^[#*\s]+|[*\s]+$", "", l)
            return title, "\n".join(lines[i + 1:]).strip()
    return "", t


def metrics(body):
    n = len(re.sub(r"\s", "", body))
    m = {k: len(re.findall(v, body, flags=re.M)) for k, v in PATS.items()}
    m["분량"] = n
    return m


items = []


def add(key, group, label, desc, path):
    p = Path(path)
    if not p.exists() or p.stat().st_size < 50:
        return
    title, body = split_title(clean(p.read_text(encoding="utf-8")))
    items.append({"key": key, "group": group, "label": label, "desc": desc,
                  "title": title, "body": body, "m": metrics(body)})


st = RUNS / "skilltest"
add("draft", "draft", "공통 초안 (base · 1단계)", "제 방식: 공냥이 18편 원문 + 보조 원문 + 경영일기 3편 문체 참고, 스킬 없음", st / "base" / "A.md")
for wt, d in DESC.items():
    if wt != "base":  # base의 1단계 = 공통 초안
        add(f"A-{wt}", "A", f"1단계 · {wt}", f"처음부터 쓰고 {d}로 다듬음", st / wt / "A.md")
for wt, d in DESC.items():
    add(f"B-{wt}", "B", f"2단계 · {wt}", f"공통 초안을 {d}로 다듬음" if wt != "base" else "공통 초안을 스킬 없이 '소리 내 읽고 다듬기'", st / wt / "B.md")
rw = RUNS / "rewrite"
for r, d in RDESC.items():
    for model in ("claude", "astra"):
        add(f"{r}-{model}", "R", f"{r} · {model}", f"{d} — {'Claude Opus (claude -p)' if model == 'claude' else 'GPT-6 astra (codex exec)'}", rw / f"{model}-{r}" / "output.md")

sd = RUNS / "standard"
for key, label, desc in [
    ("S1-revise-astra", "기준안 수정 · astra", "기준 글(R4·astra)에 멘토 피드백만 반영해 고침 — astra", ),
    ("S2-rerun-astra", "기준 절차 재실행 · astra", "공통 초안 + 경영일기 2편 + 멘토 피드백으로 R4 절차를 처음부터 다시 — astra"),
    ("S1-revise-claude", "기준안 수정 · claude", "기준 글(R4·astra)에 멘토 피드백만 반영해 고침 — Claude (비교용)"),
]:
    model = key.rsplit("-", 1)[1]; stem = key.rsplit("-", 1)[0]
    add(key, "S", label, desc, sd / f"{model}-{stem}" / "output.md")
items.sort(key=lambda i: [g for g, _ in GROUPS].index(i["group"]))
data = json.dumps({"items": items, "groups": GROUPS}, ensure_ascii=False)

PAGE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>칼럼 판 비교</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard.min.css">
<style>
:root{--bg:#f7f6f3;--card:#fff;--ink:#1f1f1f;--sub:#6b6b6b;--line:#e4e2dc;--add:#e3f4e6;--del:#fbe4e4;--acc:#2f5bd3;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17181a;--card:#202124;--ink:#ececec;--sub:#a0a0a0;--line:#34363a;--add:#1f3a27;--del:#45262a;--acc:#8fb0ff;}}
:root[data-theme="dark"]{--bg:#17181a;--card:#202124;--ink:#ececec;--sub:#a0a0a0;--line:#34363a;--add:#1f3a27;--del:#45262a;--acc:#8fb0ff;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Pretendard,-apple-system,"Apple SD Gothic Neo",sans-serif;}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
header h1{font-size:16px;margin:0 12px 0 0}
select,button{font:inherit;font-size:14px;padding:6px 8px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:6px}
button{cursor:pointer}label{font-size:13px;color:var(--sub)}
main{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px;max-width:1500px;margin:0 auto}
@media (max-width:900px){main{grid-template-columns:1fr}}
.col{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px 22px;min-width:0}
.meta{font-size:12.5px;color:var(--sub);margin-bottom:10px;line-height:1.6}
.chips span{display:inline-block;margin:2px 4px 2px 0;padding:1px 7px;border:1px solid var(--line);border-radius:999px;font-size:12px}
.chips span.hot{border-color:#d9822b;color:#d9822b}
h2{font-size:20px;line-height:1.45;margin:6px 0 14px}
.body p{font-size:16px;line-height:1.85;margin:0 0 14px;word-break:keep-all}
.s.add{background:var(--add);border-radius:3px}.s.del{background:var(--del);border-radius:3px}
.rate{margin-top:14px;border-top:1px dashed var(--line);padding-top:12px;display:flex;flex-direction:column;gap:6px}
.rate textarea{width:100%;min-height:70px;font:inherit;font-size:14px;padding:8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}
.stars button{padding:3px 9px;margin-right:3px}.stars button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
#overview{max-width:1500px;margin:0 auto;padding:0 16px 30px}
table{border-collapse:collapse;width:100%;font-size:13px;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
td.n{text-align:right;font-variant-numeric:tabular-nums}
tr:hover td{background:var(--bg)}a.pick{color:var(--acc);cursor:pointer;text-decoration:none}
details{margin:14px 0}summary{cursor:pointer;color:var(--sub);font-size:13px}
</style></head><body>
<header>
  <h1>칼럼 판 비교</h1>
  <label>왼쪽 <select id="L"></select></label>
  <label>오른쪽 <select id="R"></select></label>
  <label><input type="checkbox" id="diff" checked> 바뀐 문장 표시</label>
  <button id="swap">⇄</button>
  <button id="export">메모 내보내기</button>
</header>
<main><div class="col" id="cL"></div><div class="col" id="cR"></div></main>
<section id="overview">
  <details open><summary>전체 판 한눈에 보기 (제목 누르면 오른쪽에 띄움 · 대비/나열/선언/번역투 = 개수)</summary><div id="tbl"></div></details>
</section>
<script>
const DATA = __DATA__;
const items = DATA.items, byKey = Object.fromEntries(items.map(i=>[i.key,i]));
const store = { get(k){try{return JSON.parse(localStorage.getItem('mentor-lab:'+k)||'null')}catch(e){return null}}, set(k,v){try{localStorage.setItem('mentor-lab:'+k,JSON.stringify(v))}catch(e){}} };
const esc = s => s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const sents = t => t.replace(/\s+/g,' ').split(/(?<=[.?!])\s+/).map(s=>s.trim()).filter(Boolean);
const norm = s => s.replace(/\s/g,'');
function lcs(a,b){const n=a.length,m=b.length,d=Array.from({length:n+1},()=>new Int16Array(m+1));
  for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)d[i][j]=a[i]===b[j]?d[i+1][j+1]+1:Math.max(d[i+1][j],d[i][j+1]);
  const ka=new Set(),kb=new Set();let i=0,j=0;while(i<n&&j<m){if(a[i]===b[j]){ka.add(i);kb.add(j);i++;j++}else if(d[i+1][j]>=d[i][j+1])i++;else j++}return [ka,kb];}
function render(el,it,keep,cls){
  const paras = it.body.split(/\n\s*\n/).map(p=>p.replace(/^[#>*\-\s]+/,'').trim()).filter(Boolean);
  let idx=0; const html = paras.map(p=>'<p>'+sents(p).map(s=>{const k=keep?keep.has(idx):true; idx++; return `<span class="s ${k?'':cls}">${esc(s)}</span>`}).join(' ')+'</p>').join('');
  const m=it.m, hot=v=>v>0?'hot':'';
  const r=store.get(it.key)||{score:0,memo:''};
  el.innerHTML = `<div class="meta"><b>${esc(it.label)}</b><br>${esc(it.desc)}<div class="chips"><span>공백 제외 ${m['분량'].toLocaleString()}자</span><span class="${hot(m['대비'])}">대비 ${m['대비']}</span><span class="${hot(m['나열'])}">나열 ${m['나열']}</span><span class="${hot(m['선언'])}">선언 ${m['선언']}</span><span class="${hot(m['번역투'])}">번역투 ${m['번역투']}</span></div></div>
  <h2>${esc(it.title)}</h2><div class="body">${html}</div>
  <div class="rate"><div class="stars">점수 ${[1,2,3,4,5].map(n=>`<button data-n="${n}" class="${r.score==n?'on':''}">${n}</button>`).join('')}</div>
  <textarea placeholder="이 판에 대한 메모 (브라우저에 저장됩니다)">${esc(r.memo||'')}</textarea></div>`;
  el.querySelectorAll('.stars button').forEach(b=>b.onclick=()=>{const v=store.get(it.key)||{};v.score=+b.dataset.n;store.set(it.key,v);draw()});
  el.querySelector('textarea').oninput=e=>{const v=store.get(it.key)||{};v.memo=e.target.value;store.set(it.key,v)};
}
function draw(){
  const a=byKey[L.value], b=byKey[R.value]; store.set('sel',[L.value,R.value]);
  let ka=null,kb=null; if(diff.checked){const sa=sents(a.body).map(norm), sb=sents(b.body).map(norm); [ka,kb]=lcs(sa,sb);}
  render(cL,a,ka,'del'); render(cR,b,kb,'add');
}
function opts(sel){sel.innerHTML=DATA.groups.map(([g,name])=>`<optgroup label="${esc(name)}">`+items.filter(i=>i.group===g).map(i=>`<option value="${i.key}">${esc(i.label)}</option>`).join('')+'</optgroup>').join('');}
opts(L);opts(R);
const saved=store.get('sel'); L.value=(saved&&byKey[saved[0]])?saved[0]:'draft'; R.value=(saved&&byKey[saved[1]])?saved[1]:(items.find(i=>i.group==='R')||items[1]).key;
[L,R,diff].forEach(x=>x.onchange=draw); swap.onclick=()=>{[L.value,R.value]=[R.value,L.value];draw()};
exportBtn=document.getElementById('export'); exportBtn.onclick=()=>{const out=items.map(i=>({판:i.label,...(store.get(i.key)||{})})).filter(x=>x.score||x.memo);
  const txt=JSON.stringify(out,null,1); navigator.clipboard?.writeText(txt).then(()=>alert('메모를 복사했습니다. 대화창에 붙여 넣어 주세요.'),()=>prompt('복사해서 붙여 넣어 주세요',txt));};
tbl.innerHTML='<table><tr><th>판</th><th>만든 방법</th><th>분량</th><th>대비</th><th>나열</th><th>선언</th><th>번역투</th><th>점수</th></tr>'+items.map(i=>`<tr><td><a class="pick" data-k="${i.key}">${esc(i.label)}</a></td><td>${esc(i.desc)}</td><td class="n">${i.m['분량'].toLocaleString()}</td><td class="n">${i.m['대비']}</td><td class="n">${i.m['나열']}</td><td class="n">${i.m['선언']}</td><td class="n">${i.m['번역투']}</td><td class="n">${(store.get(i.key)||{}).score||''}</td></tr>`).join('')+'</table>';
tbl.querySelectorAll('a.pick').forEach(a=>a.onclick=()=>{R.value=a.dataset.k;draw();scrollTo({top:0,behavior:'smooth'})});
draw();
</script></body></html>"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(PAGE.replace("__DATA__", data), encoding="utf-8")
print(f"{OUT} · 판 {len(items)}개")
