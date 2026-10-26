"""Supabase(main 파이프라인 DB)의 문서를 작업실 원문으로 받아 온다.

원천은 DB다. 작업실은 지금까지처럼 sources/originals/<사이트>/NNNN.md 파일을 읽고,
이 스크립트가 DB 문서를 그 모양(머리말 + 원문 그대로)으로 내려 둔다. 받아 온 파일은 git에 넣지 않는다
(.gitignore — 저작권 있는 원문이라 저장소에 올리지 않는다). 경영일기(infuture, 문체 참고)는 그대로 git에 있다.

  python3 -I scripts/db_sources.py --status                      범위 안 DB 문서 수 · 받아 둔 수 (소스별)
  python3 -I scripts/db_sources.py --sync [--since 2026-08-01] [--source hbr ...] [--limit N]
  python3 -I scripts/db_sources.py --sync --prune                범위에서 빠진 문서(반려 등)의 파일을 지움 — 카드가 있는 원문은 남김

범위: sources/db_scope.json (소스 목록 · 최소 글자 수 · 요약문/반려 제외).
본문은 documents.body 그대로 쓴다. claims(main이 문서에서 뽑은 주장)는 원문을 대신하지 않는다 — 글은 언제나 원문 전체로 쓴다.
DB는 읽기 전용 트랜잭션으로만 연다. 연결 문자열은 환경변수 DATABASE_URL에서만 읽고 어디에도 쓰지 않는다.

번호표 공유(2026-10-26): 원문 번호(NNNN)는 받은 순서대로 매겨져 PC마다 달랐다 — 주제 지도·글 설정이 git으로
공유되니 다른 PC에서는 엉뚱한 원문을 가리켰다. 그래서 한 PC(db_scope.json의 "index_owner" = 그 PC의 컴퓨터 이름)만
번호를 매기고, 번호표를 sources/db_index.shared.json(git)으로 올린다.
  · 기준 PC(owner)   — 지금처럼 받고 번호를 매긴 뒤 공유 번호표가 바뀌었으면 커밋·push(운영 브랜치, wiki.push)
  · 다른 PC(follower) — 공유 번호표대로 파일을 다시 쓰고 남는 파일은 지운다. 공유 번호표에 아직 없는 새 원문은
                        받지 않는다(기준 PC가 번호를 매겨 올릴 때까지 — 작업실이 6시간마다 받는다)
  · index_owner가 비었거나 공유 번호표가 아직 없으면 예전처럼 이 PC가 번호를 매긴다(공유 없음)
sources/db_index.json(git 밖)은 PC마다 쓰는 번호표 그대로 — 같은 이름을 git에 넣으면 다른 PC의 pull이 막힌다.
"""
import argparse
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
ORIG = SRC / "originals"
SCOPE = SRC / "db_scope.json"
INDEX = SRC / "db_index.json"  # doc_id → originals/<사이트>/NNNN.md (git 밖)
SHARED = SRC / "db_index.shared.json"  # 기준 PC의 번호표 — git으로 공유, 다른 PC는 이 번호를 따른다(2026-10-26)
DOC_CARDS = SRC / "doc_cards.json"  # 자동 카드(main document_cards, Sonnet 5.5)를 받아 둔 것 — wiki.doc_cards()가 읽는다(git 밖)
STYLE_ONLY = {"infuture"}  # wiki.STYLE_ONLY와 같음 — DB 문서가 이 이름으로 들어오지 않게


def scope():
    return json.loads(SCOPE.read_text(encoding="utf-8"))


def index():
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}


def this_pc():
    return (os.environ.get("COMPUTERNAME") or socket.gethostname()).strip()


def role(sc):
    """owner(번호를 매기고 공유) · follower(공유 번호를 따름) · solo(공유 없음, 예전 동작)"""
    owner = str(sc.get("index_owner") or "").strip()
    if not owner:
        return "solo"
    return "owner" if owner.lower() == this_pc().lower() else "follower"


def shared():
    return json.loads(SHARED.read_text(encoding="utf-8")) if SHARED.exists() else None


def dump(idx):
    return json.dumps(idx, ensure_ascii=False, indent=0) + "\n"


def publish_shared(idx, push=True):
    """기준 PC — 공유 번호표가 바뀌었으면 쓰고 커밋·push. 반환: 바뀌었는지."""
    text = dump(idx)
    if SHARED.exists() and SHARED.read_text(encoding="utf-8") == text:
        return False
    SHARED.write_text(text, encoding="utf-8")
    rel = SHARED.relative_to(ROOT).as_posix()
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    git("add", "--", rel)
    if git("diff", "--cached", "--quiet", "--", rel).returncode:
        r = git("commit", "-m", f"원문 번호표: {len(idx)}편 (기준 PC {this_pc()})", "--", rel)
        if r.returncode:
            print("공유 번호표 커밋 실패 — " + (r.stderr or r.stdout).strip(), flush=True)
            return True
        if push:
            sys.path.insert(0, str(ROOT / "scripts"))
            import wiki as W
            W.push()  # 실패하면 커밋은 이 PC에 남아 다음 push 때 올라간다(wiki.push가 알림)
    return True


def connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL이 없습니다 — main 파이프라인과 같은 Supabase 연결 문자열을 환경변수로 두세요(파일에 쓰지 않음).")
    try:
        import psycopg
    except ImportError:
        sys.exit("psycopg가 없습니다 — pip install \"psycopg[binary]\"")
    c = psycopg.connect(url, prepare_threshold=None)  # Supabase 풀러(트랜잭션 모드)는 prepared statement를 못 씀
    c.read_only = True  # 첫 트랜잭션 전에 — 이 연결의 모든 트랜잭션이 읽기 전용
    return c


def where(sc, since=None, only=None):
    ids = [s for s in sc["sources"] if not only or s in only]
    cond = ["source_id = ANY(%s)", "length(body) >= %s"]
    args = [ids, sc.get("min_chars", 800)]
    if sc.get("exclude_rejected", True):
        cond.append("status <> 'rejected'")
    if sc.get("exclude_summary_only", True):
        cond.append("coalesce(summary_only, 0) = 0")
    if since:
        cond.append("coalesce(published_at, collected_at::date) >= %s")
        args.append(since)
    return " AND ".join(cond), args


def one_line(v):
    v = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", str(v or ""), flags=re.S)  # bain-insights 제목의 CDATA 껍질
    return re.sub(r"\s+", " ", v).strip().replace("---", "—")  # 머리말 안에 ---가 있으면 split("---", 2)로 읽는 쪽이 깨진다


def url_line(v):
    return re.sub(r"\s+", "", str(v or "")).replace("---", "%2D%2D%2D")  # 주소 속 ---는 같은 뜻의 퍼센트 인코딩으로


def render(r, sc):
    doc_id, source_id, tier, url, title, author, published, body = r
    name = sc["sources"].get(source_id, {}).get("name", source_id)
    head = [
        "---",
        f"url: {url_line(url)}",
        f"title: {one_line(title)}",
        f"author: {one_line(author)}",
        f"date: {published.isoformat() if published else ''}",
        f"site_name: {name}",
        f"tier: {tier}",
        f"doc_id: {doc_id}",
        "from: supabase",
        "---",
        "",
    ]
    return "\n".join(head) + (body or "").strip() + "\n"


def next_no(site, used):
    d = ORIG / site
    nums = [int(f.stem) for f in d.glob("[0-9]*.md") if f.stem.isdigit()] if d.exists() else []
    nums += [int(Path(p).stem) for p in used if p.startswith(f"originals/{site}/")]
    return max(nums, default=0) + 1


COLS = "id, source_id, tier, url, title, author, published_at, body"


def file_doc_id(f):
    """받아 둔 원문 파일 머리말의 doc_id — 파일이 없거나 머리말에 없으면 None."""
    if not f.exists():
        return None
    with f.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if line.startswith("doc_id: "):
                return line[8:].strip()
            if i > 12:
                return None
    return None


def write_doc(r, rel, sc):
    """원문 파일 하나 — 내용이 같으면 건드리지 않는다. 반환: 새로 썼는지."""
    f = SRC / rel
    text = render(r, sc)
    if f.exists() and f.read_bytes().decode("utf-8") == text:
        return False
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(text.encode("utf-8"))  # 줄바꿈은 LF 그대로 (Windows에서도)
    return True


def sync(since=None, only=None, limit=None, prune=False, push=True):
    sc = scope()
    rl = role(sc)
    sh = shared() if rl == "follower" else None
    if rl == "follower" and sh is None:
        print("공유 번호표(sources/db_index.shared.json)가 아직 없음 — 기준 PC가 올릴 때까지 이 PC 번호로 받는다", flush=True)
    follow = sh is not None
    before = index()
    idx = dict(sh) if follow else before  # 따르는 PC: 번호표를 통째로 기준 PC 것으로
    w, args = where(sc, since, only)
    sql = f"SELECT {COLS} FROM documents WHERE {w} ORDER BY published_at DESC NULLS LAST, id"
    if limit:
        sql += f" LIMIT {int(limit)}"
    new = upd = moved = waiting = 0
    seen = set()
    cards = ROOT / "wiki" / "cards.json"
    carded = set(json.loads(cards.read_text(encoding="utf-8")).keys()) if cards.exists() else set()
    with connect() as c:
        for r in c.execute(sql, args):
            doc_id, site = r[0], r[1]
            if site in STYLE_ONLY:
                continue
            seen.add(doc_id)
            rel = idx.get(doc_id)
            if follow:
                if not rel:  # 기준 PC가 아직 번호를 매기지 않은 새 원문 — 기다린다
                    waiting += 1
                    continue
            else:
                if rel and rel.split("/")[1] != site and rel.removeprefix("originals/").removesuffix(".md") not in carded:
                    # DB에서 소스가 바뀐 문서(수기 등록 → 정식 소스, scripts/remap_manual.py) — 새 소스 폴더로 옮긴다.
                    # 주제 지도 카드가 이미 있는 원문은 카드가 옛 경로를 가리키니 그대로 둔다.
                    (SRC / rel).unlink(missing_ok=True)
                    rel = None
                    moved += 1
                if not rel:
                    rel = f"originals/{site}/{next_no(site, idx.values()):04d}.md"
                    idx[doc_id] = rel
                    new += 1
            upd += write_doc(r, rel, sc)
        gone = []
        if follow:
            # 기준 PC 번호표에는 있는데 이번 범위 조회에 안 걸린 원문(범위 밖이 됐지만 주제 지도 카드가 있어 남긴 것 등) —
            # 파일이 없으면 id로 받아 둔다. 주제 지도가 가리키는데 파일이 없으면 작업실 상태 응답이 멈춘다.
            # 파일이 있어도 다른 글(이 PC 옛 번호)이면 같은 처리
            lack = [d for d, rel in idx.items() if d not in seen and file_doc_id(SRC / rel) != d]
            if lack and not (since or only or limit):
                for r in c.execute(f"SELECT {COLS} FROM documents WHERE id = ANY(%s)", (lack,)):
                    upd += write_doc(r, idx[r[0]], sc)
            # 이 PC 번호에만 있던 파일은 지운다(같은 글이 기준 번호로 다시 써졌다). 번호표 밖의 파일은 건드리지 않는다
            keep = set(idx.values())
            for rel in set(before.values()) - keep:
                (SRC / rel).unlink(missing_ok=True)
                gone.append(rel)
        elif prune and not since and not only and not limit:
            w_all, a_all = where(sc)
            alive = {x[0] for x in c.execute(f"SELECT id FROM documents WHERE {w_all}", a_all)}
            for doc_id, rel in list(idx.items()):
                k = rel.removeprefix("originals/").removesuffix(".md")
                if doc_id not in alive and k not in carded:
                    (SRC / rel).unlink(missing_ok=True)
                    del idx[doc_id]
                    gone.append(rel)
        INDEX.write_text(dump(idx), encoding="utf-8")
        sync_cards(c, idx)
    shared_note = ""
    if rl == "owner":
        shared_note = " · 공유 번호표 올림" if publish_shared(idx, push) else " · 공유 번호표 그대로"
    elif follow:
        shared_note = f" · 기준 PC 번호표 따름(기다리는 새 원문 {waiting})"
    print(f"받음: 새 문서 {new} · 다시 씀 {upd} · 범위 안 {len(seen)}" + (f" · 소스 바뀜 {moved}" if moved else "")
          + (f" · 지움 {len(gone)}" if prune or follow else "") + shared_note)


def card_key(rel):
    return rel.removeprefix("originals/").removesuffix(".md")


def sync_cards(c, idx):
    """자동 카드 받기(2026-10-21) — 받아 둔 원문의 카드를 main document_cards에서 읽어 sources/doc_cards.json에 둔다.
    표가 아직 없으면(main 마이그레이션 009 적용 전) 건너뛴다. 카드 임베딩은 받지 않는다 — 검색은 Supabase에서 바로 한다(card_search.py)."""
    if not c.execute("SELECT to_regclass('public.document_cards')").fetchone()[0]:
        print("카드: Supabase에 document_cards 표가 아직 없음 — 건너뜀")
        return
    rows = c.execute("""SELECT document_id, thesis, episodes, material_type, model, prompt_version
                        FROM document_cards WHERE document_id = ANY(%s)""", (list(idx),)).fetchall()
    dc = json.loads(DOC_CARDS.read_text(encoding="utf-8")) if DOC_CARDS.exists() else {}
    live = {card_key(r) for r in idx.values()}
    gone = [k for k, v in dc.items() if v.get("from") == "supabase" and k not in live]  # 원문이 빠진 카드(반려 등)
    for k in gone:
        del dc[k]
    changed = 0
    for doc_id, thesis, eps, mt, model, pv in rows:
        eps = eps if isinstance(eps, list) else json.loads(eps or "[]")
        card = {"thesis": thesis, "episodes": eps, "material_type": mt or "", "model": model, "prompt_version": pv,
                "doc_id": doc_id, "from": "supabase"}
        k = card_key(idx[doc_id])
        if dc.get(k) != card:  # 시험에서 넣은 카드(--import-cards)도 진짜 카드가 오면 바뀐다
            dc[k] = card
            changed += 1
    DOC_CARDS.write_bytes(json.dumps(dc, ensure_ascii=False, indent=1).encode("utf-8"))
    print(f"카드: 받음 {len(rows)} · 새로·바뀜 {changed}" + (f" · 지움 {len(gone)}" if gone else "") + f" · 모두 {len(dc)}장")


def status():
    sc = scope()
    idx = index()
    w, args = where(sc)
    have = {}
    for rel in idx.values():
        have[rel.split("/")[1]] = have.get(rel.split("/")[1], 0) + 1
    with connect() as c:
        rows = c.execute(f"SELECT source_id, count(*) FROM documents WHERE {w} GROUP BY 1 ORDER BY 2 DESC", args).fetchall()
    print(f"{'소스':28} {'DB':>6} {'받음':>6}")
    for site, n in rows:
        print(f"{site:28} {n:>6} {have.get(site, 0):>6}")
    print(f"{'합계':28} {sum(n for _, n in rows):>6} {len(idx):>6}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--since")
    ap.add_argument("--source", nargs="+")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--prune", action="store_true")
    ap.add_argument("--no-push", action="store_true", help="기준 PC: 공유 번호표를 커밋만 하고 올리지 않는다")
    a = ap.parse_args()
    if a.sync:
        sync(a.since, a.source, a.limit, a.prune, push=not a.no_push)
    elif a.status:
        status()
    else:
        ap.print_help()
