"""데이터 핸드오프 — 2인 개인 PC 체제에서 운영 데이터를 교대 시점에 안전하게 이관.

원칙 (기획서 11장): 데이터(data/)는 항상 한 PC에서만 '활성'이다.
  - 내보내기(export): data/ 전체를 zip으로 묶고(명세 포함) 이 PC를 '이관됨'으로 표시
  - 받기(receive):   zip 검증 → 기존 data/ 백업 → 교체 → 이 PC를 '활성'으로 표시
  - 쓰기 가드: '이관됨' 상태에서는 수집·추출 등 DB 쓰기 작업이 실행을 거부한다
    (두 PC의 데이터가 갈라지는 사고를 규율이 아니라 코드로 차단)

사용: make handoff  /  make receive FILE=경로
"""
from __future__ import annotations

import json
import shutil
import socket
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ROOT  # noqa: E402

DATA_DIR = ROOT / "data"
STATE_FILE_NAME = ".handoff_state"          # data/ 안에 위치 (데이터와 함께 이동하지 않도록 zip에서 제외)
HANDOFF_DIR = ROOT / "handoff"


def state_path() -> Path:
    return DATA_DIR / STATE_FILE_NAME


def get_state() -> str:
    """'active' | 'handed_off' | 'empty'"""
    if not (DATA_DIR / "pipeline.db").exists():
        return "empty"
    if not state_path().exists():
        return "active"  # 표식 없는 기존 데이터는 활성으로 간주 (기존 사용자 호환)
    return json.loads(state_path().read_text(encoding="utf-8")).get("state", "active")


def set_state(state: str, note: str = "") -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state_path().write_text(json.dumps({
        "state": state, "host": socket.gethostname(),
        "at": datetime.now().isoformat(timespec="seconds"), "note": note,
    }, ensure_ascii=False, indent=1), encoding="utf-8")


def ensure_active(task_name: str) -> None:
    """쓰기 작업 진입점에서 호출. 이관됨 상태면 중단시킨다."""
    st = get_state()
    if st == "handed_off":
        info = json.loads(state_path().read_text(encoding="utf-8"))
        raise SystemExit(
            f"[중단] 이 PC의 데이터는 {info.get('at')}에 이관됨 상태입니다.\n"
            f"'{task_name}' 같은 쓰기 작업은 현재 활성 PC에서 실행해야 합니다.\n"
            f"이 PC를 다시 활성화하려면 상대방의 /handoff 파일을 make receive로 받으세요."
        )


def counts() -> dict:
    conn = sqlite3.connect(DATA_DIR / "pipeline.db")
    c = {}
    for table in ["documents", "claims", "internal_docs", "articles"]:
        try:
            c[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.OperationalError:
            c[table] = 0
    conn.close()
    return c


def export() -> int:
    st = get_state()
    if st == "empty":
        print("data/에 데이터가 없습니다 — 내보낼 것이 없습니다.")
        return 1
    if st == "handed_off":
        print("이미 이관됨 상태입니다. 이중 내보내기를 중단합니다 (사고 방지).")
        return 1

    manifest = {"exported_at": datetime.now().isoformat(timespec="seconds"),
                "host": socket.gethostname(), "counts": counts()}
    HANDOFF_DIR.mkdir(exist_ok=True)
    out = HANDOFF_DIR / f"pipeline-data-{datetime.now():%Y%m%d-%H%M}.zip"

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(DATA_DIR.rglob("*")):
            if path.is_file() and path.name != STATE_FILE_NAME:
                zf.write(path, path.relative_to(DATA_DIR))
        zf.writestr("HANDOFF_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=1))

    set_state("handed_off", note=f"exported to {out.name}")
    c = manifest["counts"]
    print(f"내보내기 완료: {out}")
    print(f"  문서 {c['documents']} / claim {c['claims']} / 내부 {c['internal_docs']} / 아티클 {c['articles']}")
    print("이 PC는 '이관됨' 상태가 되어 쓰기 작업이 잠깁니다.")
    print("→ 이 파일을 상대방에게 전달하고, 상대 PC에서 make receive FILE=<경로> 를 실행하세요.")
    return 0


def receive(zip_path_str: str) -> int:
    zip_path = Path(zip_path_str)
    if not zip_path.exists():
        print(f"파일이 없습니다: {zip_path}")
        return 1

    with zipfile.ZipFile(zip_path) as zf:
        try:
            manifest = json.loads(zf.read("HANDOFF_MANIFEST.json"))
        except KeyError:
            print("핸드오프 파일이 아닙니다 (명세 누락). /handoff로 만든 zip인지 확인하세요.")
            return 1

        # 기존 data/ 백업 후 교체
        if DATA_DIR.exists() and any(DATA_DIR.iterdir()):
            backup = ROOT / f"data_backup_{datetime.now():%Y%m%d-%H%M}"
            shutil.move(str(DATA_DIR), str(backup))
            print(f"기존 data/는 {backup.name}/ 로 백업했습니다 (검증 후 삭제 가능).")
        DATA_DIR.mkdir(parents=True)
        zf.extractall(DATA_DIR)
        (DATA_DIR / "HANDOFF_MANIFEST.json").unlink(missing_ok=True)

    actual = counts()
    expected = manifest["counts"]
    ok = actual == expected
    set_state("active", note=f"received {zip_path.name} from {manifest.get('host')}")
    print(f"받기 완료 (보낸 PC: {manifest.get('host')}, {manifest.get('exported_at')})")
    for k in expected:
        mark = "OK" if actual.get(k) == expected[k] else "불일치!"
        print(f"  {k}: 명세 {expected[k]} / 실제 {actual.get(k)}  {mark}")
    if not ok:
        print("[경고] 건수 불일치 — 전달 중 파일 손상 가능. 상대에게 재내보내기를 요청하세요.")
        return 1
    print("이 PC가 '활성'이 되었습니다. 수집·추출·/draft를 여기서 실행하세요.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "receive":
        raise SystemExit(receive(sys.argv[2]) if len(sys.argv) > 2 else print("사용: receive <zip경로>") or 1)
    raise SystemExit(export())
