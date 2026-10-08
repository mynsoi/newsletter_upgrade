#!/usr/bin/env bash
D=$(cd "$(dirname "$0")" && pwd)
runA(){ d=$D/astra-$1-$2; mkdir -p $d; s=$(date +%s); ( cd $d && codex exec -m gpt-6-astra -C $d --skip-git-repo-check -s read-only --ephemeral --color never -o $d/output.md "$(cat $D/$1.prompt.md)" < /dev/null > $d/run.log 2>&1 ); echo "astra-$1-$2 exit=$? $(( $(date +%s)-s ))s" >> $D/status.txt; }
: > $D/status.txt; runA D1 a & runA D1 b & wait; echo ALLDONE >> $D/status.txt
