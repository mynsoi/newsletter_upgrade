import json, os, sys
import psycopg
from psycopg.rows import dict_row
with psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row,connect_timeout=15) as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    rows=conn.execute('''SELECT c.id,c.claim_text,c.metric,c.stance,c.evidence_type,c.from_summary,
        c.document_id,d.title AS document_title,d.source_id,d.tier,d.url,d.published_at
        FROM claims c JOIN documents d ON d.id=c.document_id WHERE c.document_id IN
        (SELECT document_id FROM claims WHERE id=ANY(%s)) AND COALESCE(c.from_summary,0)=0''',(sys.argv[1:],)).fetchall()
    from pathlib import Path
    Path('content/evidence/ai-yearend-what-counts-targeted.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    for r in rows: print(r['id'],r['source_id'],r['stance'],r['claim_text'])
    ids=['policies/2026-ai-task-guide.md','leadership-messages/2026-06-이천포럼-패널토의.md']
    meta=conn.execute('SELECT id,security,api_eligible FROM internal_docs WHERE id=ANY(%s)',(ids,)).fetchall()
    if len(meta)!=2 or any(r['api_eligible']!=1 for r in meta):
        raise SystemExit('STOP: internal gate failed')
    for r in conn.execute('SELECT id,effective_date,body FROM internal_docs WHERE id=ANY(%s) AND api_eligible=1',(ids,)).fetchall():
        print('INTERNAL',json.dumps(r,ensure_ascii=False,default=str))
