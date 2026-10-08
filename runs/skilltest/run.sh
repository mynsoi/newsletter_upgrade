#!/usr/bin/env bash
# 사용: run.sh <워크트리이름> <단계> <지시문파일> [claude 추가 옵션...]
# 결과: $T/<워크트리>/<단계>.jsonl(전체 기록) · <단계>.md(최종 답) · <단계>.tools.txt(부른 도구·스킬)
T=$(cd "$(dirname "$0")" && pwd); W=/home/hwjoo/01-projects/2026/mentoring/skens/mentor-lab-wt
wt=$1; st=$2; pf=$3; shift 3
mkdir -p "$T/$wt"; cd "$W/$wt" || exit 1
start=$(date +%s)
claude -p --model opus --output-format stream-json "$@" --verbose --no-session-persistence "$(cat "$pf")" < /dev/null > "$T/$wt/$st.jsonl" 2> "$T/$wt/$st.err"
code=$?
python3 -I - "$T/$wt/$st" <<'PY'
import json,sys
base=sys.argv[1]; res=''; tools=[]
for line in open(base+'.jsonl',encoding='utf-8'):
    try: e=json.loads(line)
    except Exception: continue
    if e.get('type')=='result': res=e.get('result') or ''
    if e.get('type')=='assistant':
        for c in e.get('message',{}).get('content',[]):
            if c.get('type')=='tool_use':
                i=c.get('input',{}); tools.append(c['name']+' '+json.dumps({k:(str(v)[:80]) for k,v in i.items()},ensure_ascii=False))
open(base+'.md','w',encoding='utf-8').write(res)
open(base+'.tools.txt','w',encoding='utf-8').write('\n'.join(tools)+'\n')
PY
echo "$wt/$st exit=$code $(( $(date +%s)-start ))s chars=$(wc -m < "$T/$wt/$st.md") tools=$(grep -c . "$T/$wt/$st.tools.txt")"
