"""창간호 ②: 읽기 전용 DB 검색, 외부 claim 후보만 저장."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from db import connect
from search.semantic import hybrid_search

root = Path(__file__).resolve().parents[1]
conn = connect()
conn.execute('SET TRANSACTION READ ONLY')
queries = ['AI 성과 측정 지표', 'AI 자기 평가 성과 기록', 'AI 생산성 자기 보고 측정', 'AI 성과 평가 품질 검토']
result = {'branches': {}}
for branch, tiers in [('practice', ['T2','T3','T4']), ('research', ['T1','T2'])]:
    hits = {}
    for query in queries:
        for row in hybrid_search(query, tiers=tiers, limit=30, conn=conn):
            key = row['id']
            if key not in hits:
                hits[key] = dict(row, queries=[])
            hits[key]['queries'].append(query)
    result['branches'][branch] = list(hits.values())
result['theory'] = [dict(r) for r in conn.execute("""SELECT c.id,c.claim_text,c.stance,c.evidence_type,c.from_summary,
 d.title AS document_title,d.source_id,d.tier,d.url FROM claims c JOIN documents d ON d.id=c.document_id
 WHERE c.evidence_type='theory' AND COALESCE(c.from_summary,0)=0
 AND (d.title ILIKE '%Kerr%' OR d.title LIKE '%보상%' OR d.title LIKE '%탤런트십%' OR d.title LIKE '%의사결정 과학%')""").fetchall()]
result['internal_metadata'] = [dict(r) for r in conn.execute("SELECT id,title,security,api_eligible,effective_date FROM internal_docs WHERE id IN (?,?)", ('policies/2026-ai-task-guide.md','leadership-messages/2026-06-이천포럼-패널토의.md')).fetchall()]
conn.close()
path = root / 'content/evidence/ai-yearend-what-counts-search.json'
path.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str), encoding='utf-8')
print(json.dumps({'counts': {k:len(v) for k,v in result['branches'].items()}, 'theory':len(result['theory']), 'internal':result['internal_metadata']},ensure_ascii=False,default=str))
