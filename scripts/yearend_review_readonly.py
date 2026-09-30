"""선택 후보 원문 문단 대조. DB 변경·원문 파일 저장 없음."""
import json, os, re, sys
import psycopg
from psycopg.rows import dict_row
with psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row, connect_timeout=15) as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    for row in conn.execute('''SELECT c.id,c.claim_text,c.metric,c.from_summary,d.id AS document_id,
        d.title,d.url,d.body FROM claims c JOIN documents d ON d.id=c.document_id
        WHERE c.id=ANY(%s)''',(sys.argv[1:],)).fetchall():
        body=row.pop('body') or ''
        paragraphs=body.split('\n')
        selected=[p for p in paragraphs if re.search(r'measur|evaluat|self.report|review|quality|judg|12.2|32%|검증|측정|설명|기여|평가|성과|보상',p,re.I)]
        row['body_length']=len(body)
        row['review_passages']='\n'.join(selected)[:14000] if selected else body[:6000]
        print(json.dumps(row,ensure_ascii=False,default=str))
