"""scripts/db_sources.py 번호표 공유 시험 — 가짜 DB, 임시 폴더(실제 sources/·Supabase는 건드리지 않음).

  python -m pytest tests/test_db_sources.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import db_sources as D  # noqa: E402


def row(doc_id, site="hbr", alive=True):
    return {"r": (doc_id, site, "T2", f"https://x/{doc_id}", f"제목 {doc_id}", "", None, f"본문 {doc_id} " * 5),
            "alive": alive}


class FakeConn:
    """db_sources가 부르는 쿼리 세 가지(범위 조회 · id로 조회 · 살아 있는 id)와 카드 표 확인만 흉내 낸다."""

    def __init__(self, docs):
        self.docs = docs

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, args=None):
        if "to_regclass" in sql:
            out = [(None,)]
        elif "WHERE id = ANY" in sql:
            out = [d["r"] for d in self.docs if d["r"][0] in args[0]]
        elif sql.startswith("SELECT id FROM"):
            out = [(d["r"][0],) for d in self.docs if d["alive"]]
        else:
            out = [d["r"] for d in self.docs if d["alive"] and d["r"][1] in args[0]]
        return Cur(out)


class Cur(list):
    def fetchone(self):
        return self[0]

    def fetchall(self):
        return list(self)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    src = tmp_path / "sources"
    (src / "originals").mkdir(parents=True)
    for name, val in {"ROOT": tmp_path, "SRC": src, "ORIG": src / "originals", "SCOPE": src / "db_scope.json",
                      "INDEX": src / "db_index.json", "SHARED": src / "db_index.shared.json",
                      "DOC_CARDS": src / "doc_cards.json"}.items():
        monkeypatch.setattr(D, name, val)
    monkeypatch.setenv("COMPUTERNAME", "MY-PC")
    git = lambda *a: subprocess.run(["git", *a], cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    git("init", "-q")
    git("config", "user.name", "t")
    git("config", "user.email", "t@t")

    def setup(docs, owner=None, local=None, shared=None, files=None):
        sc = {"sources": {"hbr": {"name": "HBR", "tier": "T2"}}, "min_chars": 10}
        if owner:
            sc["index_owner"] = owner
        D.SCOPE.write_text(json.dumps(sc), encoding="utf-8")
        if local is not None:
            D.INDEX.write_text(json.dumps(local), encoding="utf-8")
        if shared is not None:
            D.SHARED.write_text(json.dumps(shared), encoding="utf-8")
        for rel, doc_id in (files or {}).items():  # 이 PC에 이미 받아 둔 파일(옛 번호)
            f = src / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"---\nurl: x\ndoc_id: {doc_id}\n---\n옛 본문\n", encoding="utf-8")
        monkeypatch.setattr(D, "connect", lambda: FakeConn(docs))

    return {"src": src, "setup": setup, "git": git}


def doc_in(src, rel):
    return D.file_doc_id(src / rel)


def test_role():
    assert D.role({}) == "solo"
    assert D.role({"index_owner": ""}) == "solo"
    assert D.role({"index_owner": D.this_pc()}) == "owner"
    assert D.role({"index_owner": D.this_pc().lower()}) == "owner"
    assert D.role({"index_owner": "OTHER-PC"}) == "follower"


def test_solo_numbers_like_before_and_shares_nothing(env):
    env["setup"]([row("A"), row("B")])
    D.sync()
    idx = json.loads(D.INDEX.read_text(encoding="utf-8"))
    assert sorted(idx.values()) == ["originals/hbr/0001.md", "originals/hbr/0002.md"]
    assert not D.SHARED.exists()


def test_owner_publishes_shared_index_and_commits_once(env):
    env["setup"]([row("A"), row("B")], owner="MY-PC")
    D.sync(push=False)
    assert D.SHARED.read_text(encoding="utf-8") == D.INDEX.read_text(encoding="utf-8")
    log = env["git"]("log", "--oneline").stdout.splitlines()
    assert len(log) == 1 and "원문 번호표: 2편" in log[0]
    D.sync(push=False)  # 바뀐 것 없음 — 커밋 안 함
    assert len(env["git"]("log", "--oneline").stdout.splitlines()) == 1
    env["setup"]([row("A"), row("B"), row("C")], owner="MY-PC")
    D.sync(push=False)  # 새 원문 → 번호 매기고 다시 올림
    assert len(env["git"]("log", "--oneline").stdout.splitlines()) == 2
    assert json.loads(D.SHARED.read_text(encoding="utf-8"))["C"] == "originals/hbr/0003.md"


def test_follower_adopts_owner_numbers(env):
    src = env["src"]
    docs = [row("A"), row("B"), row("C", alive=False), row("D"), row("E")]
    # 이 PC 옛 번호: A=1, B=2, E=9 · 기준 PC: A=2, B=1, C=3(범위 밖이 됐지만 카드 때문에 남긴 글), E는 아직 없음
    local = {"A": "originals/hbr/0001.md", "B": "originals/hbr/0002.md", "E": "originals/hbr/0009.md"}
    shared = {"A": "originals/hbr/0002.md", "B": "originals/hbr/0001.md", "C": "originals/hbr/0003.md"}
    env["setup"](docs, owner="OTHER-PC", local=local, shared=shared,
                 files={"originals/hbr/0001.md": "A", "originals/hbr/0002.md": "B",
                        "originals/hbr/0009.md": "E", "originals/hbr/0003.md": "X"})
    D.sync(prune=True)
    assert doc_in(src, "originals/hbr/0001.md") == "B"
    assert doc_in(src, "originals/hbr/0002.md") == "A"
    assert doc_in(src, "originals/hbr/0003.md") == "C"  # 다른 글이 있던 자리 → id로 받아 다시 씀
    assert not (src / "originals/hbr/0009.md").exists()  # 이 PC 번호에만 있던 파일
    assert json.loads(D.INDEX.read_text(encoding="utf-8")) == shared  # D·E는 기준 PC가 번호를 매길 때까지 기다림
    assert "본문 A" in (src / "originals/hbr/0002.md").read_text(encoding="utf-8")
    assert env["git"]("log", "--oneline").stdout == ""  # 따르는 PC는 공유 번호표를 올리지 않는다
    assert json.loads(D.SHARED.read_text(encoding="utf-8")) == shared


def test_follower_without_shared_index_numbers_itself(env):
    env["setup"]([row("A")], owner="OTHER-PC")
    D.sync()
    assert json.loads(D.INDEX.read_text(encoding="utf-8")) == {"A": "originals/hbr/0001.md"}
    assert not D.SHARED.exists()
