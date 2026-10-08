#!/usr/bin/env bash
S=$(cd "$(dirname "$0")" && pwd)
runA(){ d=$S/astra-$1; mkdir -p $d; s=$(date +%s); ( cd $d && codex exec -m gpt-6-astra -C $d --skip-git-repo-check -s read-only --ephemeral --color never -o $d/output.md "$(cat $S/$1.prompt.md)" < /dev/null > $d/run.log 2>&1 ); echo "astra-$1 exit=$? $(( $(date +%s)-s ))s" >> $S/status.txt; }
runC(){ d=$S/claude-$1; mkdir -p $d; s=$(date +%s); ( cd $d && claude -p --model opus --tools "" --strict-mcp-config --no-session-persistence "$(cat $S/$1.prompt.md)" < /dev/null > $d/output.md 2> $d/run.log ); echo "claude-$1 exit=$? $(( $(date +%s)-s ))s" >> $S/status.txt; }
: > $S/status.txt
runA S1-revise & runA S2-rerun & runC S1-revise & wait
echo ALLDONE >> $S/status.txt
