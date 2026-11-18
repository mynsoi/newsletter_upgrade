"""참고 원문 보관 — 「유정식의 경영일기」 본문을 git 대신 Supabase에 두고, 작업실이 받아 파일로 내려 둔다 (2026-11-18).

저장소가 Public이라 저작권 있는 원문은 git에 올리지 않는다. 경영일기 본문(문체·제목 참고)만 git에 남아 있던 것을
다른 원문처럼 옮겼다. 원천은 Supabase reference_files 표(pipeline/migrations/012), 작업실은 지금까지처럼
sources/originals/infuture/p*.md 파일을 읽는다. 분석 결과(_structure.json · _style_guide.md · _title_pairs.json 등)는 git에 그대로 있다.

  python3 -I scripts/style_refs.py --status   DB에 있는 수 · 이 PC에 있는 수 · 서로 다른 파일
  python3 -I scripts/style_refs.py --pull     DB → 파일 (없거나 다른 파일만 쓴다. 이 PC의 파일을 지우지는 않는다)
  python3 -I scripts/style_refs.py --push     파일 → DB (새 파일·바뀐 파일만 올린다. DB의 행을 지우지는 않는다)

- 받기는 저절로 된다: Supabase 받기(db_sources.py --sync)가 끝에 --pull과 같은 일을 하고, 쓰기(column_pipeline)가
  참고 글 파일을 못 찾으면 그 자리에서 한 번 받는다.
- 올리기는 손으로 한다: 경영일기 새 글을 받은 뒤(column_pipeline.py --fetch-infuture <번호>) --push.
- 본문은 화면·로그에 찍지 않는다(경로와 글자 수만). 파일 내용은 바이트 그대로 오간다(줄바꿈 포함).
DB 연결 문자열은 환경변수 DATABASE_URL에서만 읽는다.
"""
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
# 묶음마다 옮기는 파일(sources/ 기준). 여기 있는 것은 .gitignore로 git 밖이다.
COLLECTIONS = {
    "infuture": ["originals/infuture/p*.md", "originals/infuture/snap/*.txt",
                 "originals/infuture/_archive.txt", "originals/infuture/_bodies.raw.txt"],
}
TABLE = "reference_files"


def connect(write=False):
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None
    import psycopg
    c = psycopg.connect(url, prepare_threshold=None)  # Supabase 풀러(트랜잭션 모드)는 prepared statement를 못 씀
    c.read_only = not write
    return c


def local():
    """이 PC의 파일 → {sources/ 기준 경로: (묶음, 바이트)}"""
    out = {}
    for name, pats in COLLECTIONS.items():
        for pat in pats:
            for f in sorted(SRC.glob(pat)):
                if f.is_file():
                    out[f.relative_to(SRC).as_posix()] = (name, f.read_bytes())
    return out


def sha(b):
    return hashlib.sha256(b).hexdigest()


def has_table(c):
    return bool(c.execute(f"SELECT to_regclass('public.{TABLE}')").fetchone()[0])


def safe(path):
    """DB에서 온 경로가 sources/ 안인지 — 밖을 가리키면 쓰지 않는다."""
    f = (SRC / path).resolve()
    return f if SRC.resolve() in f.parents else None


def pull(quiet=False):
    """DB → 파일. 없거나 내용이 다른 파일만 쓴다 → 쓴 파일 수(받을 수 없으면 None)."""
    c = connect()
    if c is None:
        if not quiet:
            print("참고 원문: DATABASE_URL이 없어 받지 않음")
        return None
    with c:
        if not has_table(c):
            if not quiet:
                print(f"참고 원문: Supabase에 {TABLE} 표가 아직 없음 — 건너뜀")
            return None
        have = {p: sha(b) for p, (_, b) in local().items()}
        todo = [p for p, s in c.execute(f"SELECT path, sha256 FROM {TABLE}").fetchall() if have.get(p) != s]
        n = 0
        for i in range(0, len(todo), 50):
            for path, body in c.execute(f"SELECT path, body FROM {TABLE} WHERE path = ANY(%s)", (todo[i:i + 50],)).fetchall():
                f = safe(path)
                if f is None:
                    continue
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(body.encode("utf-8"))
                n += 1
    if not quiet or n:
        print(f"참고 원문: 받음 {n}" + (f" · 그대로 {len(have)}" if not n else ""))
    return n


def push():
    """파일 → DB. 새 파일·바뀐 파일만 올린다."""
    files = local()
    c = connect(write=True)
    if c is None:
        sys.exit("DATABASE_URL이 없습니다.")
    with c:
        if not has_table(c):
            sys.exit(f"Supabase에 {TABLE} 표가 없습니다 — pipeline/에서 make init(마이그레이션 012)을 먼저 적용하세요.")
        there = dict(c.execute(f"SELECT path, sha256 FROM {TABLE}").fetchall())
        new = upd = 0
        for path, (name, b) in files.items():
            s = sha(b)
            if there.get(path) == s:
                continue
            try:
                text = b.decode("utf-8")
            except UnicodeDecodeError:
                print("  건너뜀(UTF-8 아님):", path)
                continue
            if "\x00" in text:
                print("  건너뜀(널 문자):", path)
                continue
            c.execute(f"""INSERT INTO {TABLE} (path, collection, body, sha256) VALUES (%s, %s, %s, %s)
                          ON CONFLICT (path) DO UPDATE SET collection = EXCLUDED.collection, body = EXCLUDED.body,
                              sha256 = EXCLUDED.sha256, updated_at = CURRENT_TIMESTAMP""", (path, name, text, s))
            new, upd = new + (path not in there), upd + (path in there)
        c.commit()
    print(f"참고 원문: 올림 새 파일 {new} · 바뀐 파일 {upd} · 그대로 {len(files) - new - upd} · 이 PC 파일 {len(files)}")


def status():
    files = {p: sha(b) for p, (_, b) in local().items()}
    c = connect()
    if c is None:
        sys.exit("DATABASE_URL이 없습니다.")
    with c:
        if not has_table(c):
            sys.exit(f"Supabase에 {TABLE} 표가 아직 없음")
        there = dict(c.execute(f"SELECT path, sha256 FROM {TABLE}").fetchall())
        size = c.execute(f"SELECT coalesce(sum(length(body)), 0) FROM {TABLE}").fetchone()[0]
    only_here = sorted(set(files) - set(there))
    only_db = sorted(set(there) - set(files))
    diff = sorted(p for p in files if p in there and files[p] != there[p])
    print(f"DB {len(there)}개({size:,}자) · 이 PC {len(files)}개 · 같음 {len(set(files) & set(there)) - len(diff)}")
    for label, xs in (("이 PC에만(--push)", only_here), ("DB에만(--pull)", only_db), ("내용 다름", diff)):
        if xs:
            print(f"  {label} {len(xs)}:", ", ".join(xs[:6]) + (" …" if len(xs) > 6 else ""))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--pull"]:
        pull()
    elif a[:1] == ["--push"]:
        push()
    elif a[:1] == ["--status"]:
        status()
    else:
        print(__doc__)
