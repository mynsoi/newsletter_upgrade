"""사람 검수 카드와 원문 대조를 거친 창간호 후보의 증거 묶음 저장."""
import collections, json, os
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

selection = {
 '1A06A16BEBF1A02A2043025D9DC': ('practice','본인 기여 설명','전문가의 역량 진단 제안. 세 기준을 검증된 평가 척도로 단정하지 않는다.'),
 '1A06A16BA8A6407FD4AB5BD513C': ('practice','성과와 역량 분리','산출물의 완성도만으로 역량 향상을 확정하지 않는 논거. 개인의 기여가 없다는 뜻은 아니다.'),
 '1A061447941878283655B257E9A': ('practice','개인·팀 측정 단위','분석 도구 판매 기업의 해석·제안. 측정 편향의 실험적 입증으로 소개하지 않는다.'),
 '1A0927045D10A41AA91C2378D78': ('practice','재작업 함께 집계','기업 블로그에 소개된 한 팀의 코드 되돌림 사례. 일반 직무의 효과 크기로 전이하지 않는다. 다른 팀의 처리량 증가와 같은 표본처럼 묶지 않는다.'),
 '1A0614108BF4446FFCF82657E85': ('practice','사용 여부와 평가의 연결','Deloitte 분석의 관찰. 모든 조직 또는 우리 제도가 사용량을 보상한다는 증거가 아니다.'),
 '1A061210902EC955B670CEEE43E': ('practice','함정 단락 전용','McKinsey 인터뷰의 전문가 관찰. 계량 조사나 고사용자의 실제 보상 불이익으로 서술 금지.'),
 '1A06A2202EF5E6CFCF61B8561C7': ('practice','함정 단락 전용','WorkLab의 설문 인식. 65%와 13%는 다른 문항이며 차이를 개인별 보상 실패율로 계산하지 않는다. 원래 묶음6의 누락 ID 확정은 아님.'),
 '1A06A3BA7C533B7A15258E936FF': ('research','품질 개선 가능성','T1 전이 표시 필요: BCG 지식근로자의 제한된 실험 과제. 연간 직무성과·국내 사내 평가에 같은 효과가 난다고 일반화하지 않는다.'),
 '1A06A3BA8791EA9D6D780E3609C': ('research','과제별 효과 차이','T1 전이 표시 필요: 같은 연구의 복잡한 관리 과제 결과. 품질과 정확성을 별도로 확인하자는 편집 제안의 배경이며 사내 평가 방식의 효과 검증이 아니다.'),
 '1A0607D6166105B12314EE09346': ('theory','무엇을 왜 측정하는가','Boudreau·Ramstad 개념 틀. 새 측정법의 인과적 효과 근거가 아니다.'),
 '1A0607DAD9B5D0F0C4D495A031B': ('theory','함정 단락 전용','Kerr 사례 기반 개념 논문. AI 사용량 보상이 왜곡을 일으켰다는 사내 실증으로 단정하지 않는다.'),
}
with psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row,connect_timeout=15) as conn:
 conn.execute('SET TRANSACTION READ ONLY')
 rows=conn.execute('''SELECT c.id,c.claim_text AS text,c.metric,c.stance,c.evidence_type,c.from_summary,
 c.document_id,d.title AS doc,d.source_id AS source,d.tier,d.url,d.published_at
 FROM claims c JOIN documents d ON d.id=c.document_id WHERE c.id=ANY(%s)''',(list(selection),)).fetchall()
 assert len(rows)==len(selection)
 assert all(r['from_summary']==0 for r in rows)
 for r in rows:
  r['branch'],r['role'],r['caution']=selection[r['id']]
 sources=sorted({r['source'] for r in rows})
 branches={b:{'count':sum(r['branch']==b for r in rows),'sources':sorted({r['source'] for r in rows if r['branch']==b})} for b in ['practice','research','theory']}
 data={'topic':'AI로 일한 한 해, 무엇을 세어야 하나','slug':'ai-yearend-what-counts','collected_at':'2026-09-30',
 'status':'angle_selection_pending','search_note':'hybrid_search: 실무 T2,T3,T4 / 연구 T1,T2 각 4개 질의, limit=30. from_summary 제외. 동일 문서 관련 claim과 검수 완료 이론 카드 별도 확인. 검색 후보 전체는 search.json, 문서별 관련 후보는 targeted.json.',
 'branches':branches,'conditions':{'independent_sources':sources,'independent_sources_count':len(sources),'stances':dict(collections.Counter(r['stance'] for r in rows)),'t1_t2_count':sum(r['tier'] in ['T1','T2'] for r in rows),'from_summary_count':0,'verdict':'② 후보 풀 조건 통과. 본문 실사용 기준 검증은 집필 후 별도.'},
 'theory_lenses':[{'card':'knowledge/theories/kerr-folly-of-rewarding-a.md','status':'reviewed','reviewed_by':'이소민','role':'함정 단락'}, {'card':'knowledge/theories/boudreau-ramstad-decision-science.md','status':'reviewed','reviewed_by':'이소민','role':'측정 목적'}],
 'independence_note':'T1 실증 2개 claim은 동일한 BCG 실험 1편이다. 서로 다른 연구 2건으로 세지 않는다. 독립 출처 수는 source_id 집계이며 이론 2장도 theory-canon 1곳으로 센다. 실무 기업 블로그와 컨설팅 분석은 독립적 효과 검증으로 취급하지 않는다.',
 'external_validity_flags':['T1 두 claim에서 사내 측정·서술 제안으로 넘어가는 문장에 <!-- external-validity: T1 claim ID; 연구 범위; 사내 적용은 편집 제안 --> 표시 예정.','BCG 과제 실험의 효과를 우리 조직의 성과 수치·연간 평가 타당도로 전이하지 않는다.','자기보고 과장 연구(논리 추론·학생 표본)를 이번 논지의 직접 증거로 채택하지 않는다.'],
 'excluded':[{'id':'1A09270426C2548B53EC2326710','reason':'3~5배 claim은 원문의 서로 다른 수치 범위를 단순 배수로 표현. 동일 조건 직접 비교 연구 확인 안 되어 제외.'},{'id':'1A06A3C383E3775C6A022164A5C','reason':'논리 추론 실험의 과대평가를 연말 자기평가로 전이하지 않음.'},{'id':'1A061410B73C0097A2017D587E2','reason':'절반 수치는 원문에서 재인용. 1차 조사 방법 미대조로 수치 채택 보류.'}],
 'claims':rows}
 Path('content/evidence/ai-yearend-what-counts.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
 print(json.dumps({'branches':branches,'conditions':data['conditions']},ensure_ascii=False))
