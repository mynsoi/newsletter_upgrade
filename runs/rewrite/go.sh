#!/usr/bin/env bash
R=$(cd "$(dirname "$0")" && pwd)
runA(){ d=$R/astra-$1; mkdir -p $d; s=$(date +%s); ( cd $d && codex exec -m gpt-6-astra -C $d --skip-git-repo-check -s read-only --ephemeral --color never -o $d/output.md "$(cat $R/$1.prompt.md)" < /dev/null > $d/run.log 2>&1 ); echo "astra-$1 exit=$? $(( $(date +%s)-s ))s $(wc -m < $d/output.md 2>/dev/null)" >> $R/status.txt; }
runC(){ d=$R/claude-$1; mkdir -p $d; s=$(date +%s); ( cd $d && claude -p --model opus --tools "" --strict-mcp-config --no-session-persistence "$(cat $R/$1.prompt.md)" < /dev/null > $d/output.md 2> $d/run.log ); echo "claude-$1 exit=$? $(( $(date +%s)-s ))s $(wc -m < $d/output.md 2>/dev/null)" >> $R/status.txt; }
runK(){ d=$R/claude-R5; mkdir -p $d; s=$(date +%s); ( cd /home/hwjoo/01-projects/2026/mentoring/skens/mentor-lab-wt/base && claude -p --model opus --tools "Skill,Read,Glob" --permission-mode bypassPermissions --output-format stream-json --verbose --no-session-persistence "$(cat $R/R5.prompt.md)" < /dev/null > $d/out.jsonl 2> $d/run.log ); python3 -I -c "
import json
r='';t=[]
for l in open('$d/out.jsonl',encoding='utf-8'):
    try:e=json.loads(l)
    except: continue
    if e.get('type')=='result': r=e.get('result') or ''
    if e.get('type')=='assistant':
        for c in e['message'].get('content',[]):
            if c.get('type')=='tool_use': t.append(c['name']+' '+str(c.get('input',{}).get('skill') or c.get('input',{}).get('file_path','')))
open('$d/output.md','w',encoding='utf-8').write(r); open('$d/tools.txt','w',encoding='utf-8').write('\n'.join(t))"; echo "claude-R5 $(( $(date +%s)-s ))s $(wc -m < $d/output.md)" >> $R/status.txt; }
: > $R/status.txt
for r in R1 R2 R3 R4; do runA $r & runC $r & done; runK & wait
echo ALLDONE >> $R/status.txt
