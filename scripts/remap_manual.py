"""수기 등록(source_id='manual') 문서를 같은 발행처의 정식 소스로 옮긴다 — Supabase documents.source_id만 바꾼다.

  python3 -I scripts/remap_manual.py            미리보기 (바뀔 문서와 소스만 보여 줌)
  python3 -I scripts/remap_manual.py --apply    실행

문서 ID·본문·claim·인용 원장(article_sources)은 그대로라 연결이 끊기지 않는다. 등급(tier)이 매핑할 소스와 다르면 옮기지 않는다.
2026-10-20 결정 — 매핑하면 main 검증기의 참고자료에 기관명이 붙고(manual은 REF_NAME_SKIP), 월간 소스 리뷰의 인용 수가 발행처로 잡힌다.
맞는 소스가 없는 문서(Gallup·Equinor·SK AX·physicianleaders)는 manual로 둔다.
"""
import os
import re
import sys

import psycopg

# 주소 패턴 → 정식 소스 (tier는 main config/sources.yaml 기준)
MAP = [
    (r"^https://www\.deloitte\.com/us/en/insights/", "deloitte-insights", "T2"),
    (r"^https://joshbersin\.com/", "josh-bersin", "T2"),
    (r"^https://www\.microsoft\.com/en-us/worklab/", "ms-worklab", "T4"),
    (r"^https://www\.anthropic\.com/research/", "ai-lab-enterprise-reports", "T4"),
]


def main():
    apply = "--apply" in sys.argv
    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None) as c:
        c.read_only = not apply
        rows = c.execute("SELECT id, tier, url, left(title, 60) FROM documents WHERE source_id = 'manual' ORDER BY published_at DESC NULLS LAST").fetchall()
        moves = []
        for doc_id, tier, url, title in rows:
            hit = next(((sid, t) for pat, sid, t in MAP if re.search(pat, url or "")), None)
            if not hit:
                print(f"  그대로  {tier} {title}")
            elif hit[1] != tier:
                print(f"  건너뜀  {tier}≠{hit[1]} {title} → {hit[0]} (등급이 다름)")
            else:
                moves.append((doc_id, hit[0]))
                print(f"  옮김    {tier} {title} → {hit[0]}")
        if apply and moves:
            for doc_id, sid in moves:
                c.execute("UPDATE documents SET source_id = %s WHERE id = %s AND source_id = 'manual'", (sid, doc_id))
            c.commit()
        print(f"{'실행' if apply else '미리보기'} · 옮길 문서 {len(moves)}편 / manual {len(rows)}편")


if __name__ == "__main__":
    main()
