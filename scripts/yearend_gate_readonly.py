"""창간호 사전 점검용 읽기 전용 조회. 원문과 비밀값은 파일에 저장하지 않는다."""
import json
import os
import psycopg
from psycopg.rows import dict_row

IDS = ['1A08D5245FB22192CB864355CEA', '1A0A2E2B877A137D8A90648806A',
       '1A06B774F00C9C201DE9F384C0C', '1A061210902EC955B670CEEE43E',
       '1A09783ED66AD6D197BAAFED53D']
with psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row, connect_timeout=15) as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    rows = conn.execute('''SELECT c.id,c.document_id,c.claim_text,c.evidence_type,c.stance,
        c.metric,c.from_summary,d.source_id,d.tier,d.title,d.url,d.published_at,d.body
        FROM claims c JOIN documents d ON d.id=c.document_id WHERE c.id=ANY(%s)''', (IDS,)).fetchall()
    for row in rows:
        print(json.dumps(row,ensure_ascii=False,default=str))
    rows = conn.execute('''SELECT c.id,c.claim_text,c.evidence_type,c.stance,c.metric,c.from_summary,
        d.source_id,d.tier,d.title,d.url,d.published_at
        FROM claims c JOIN documents d ON d.id=c.document_id
        WHERE d.source_id='ms-worklab' AND (c.claim_text LIKE %s OR c.claim_text LIKE %s)
        ORDER BY c.id''', ('%보상%', '%뒤처%')).fetchall()
    print('MS_CANDIDATES', json.dumps(rows,ensure_ascii=False,default=str))
