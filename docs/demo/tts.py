"""시연 영상 내레이션 음성 — Microsoft 신경망 음성(edge-tts)으로 문장마다 <챕터>-<번호>.mp3를 만든다 (10/26 사용자: 비용 없이)

사용: py -3 -X utf8 -I docs/demo/tts.py [--voice ko-KR-SunHiNeural] [--rate +0%] [--only 1,9] [--out _workspace/demo/tts]
  그다음: py -3 -X utf8 -I docs/demo/edit.py --audio _workspace/demo/tts --out rough-v4
- 글은 docs/demo/narration.json의 TTS 글(둘째 칸, 없으면 자막 글).
- 회사망 SSL 검사 때문에 Windows 인증서 저장소(truststore)를 쓴다 — 검증을 끄지 않는다.
- 대본 글이 Microsoft 음성 서버로 간다.
"""
import asyncio
import json
import sys
from pathlib import Path

import truststore

truststore.inject_into_ssl()
import edge_tts  # noqa: E402 — truststore를 먼저 넣어야 한다

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:]


def opt(name, default):
    return args[args.index(name) + 1] if name in args else default


VOICE = opt("--voice", "ko-KR-SunHiNeural")
RATE = opt("--rate", "+0%")
OUT = ROOT / opt("--out", "_workspace/demo/tts")
ONLY = {x for x in opt("--only", "").split(",") if x}
NARR = json.loads((Path(__file__).parent / "narration.json").read_text(encoding="utf-8"))


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for ch, rows in NARR.items():
        if not ch.isdigit() or (ONLY and ch not in ONLY):
            continue
        for old in OUT.glob(f"{ch}-*.mp3"):
            old.unlink()
        for k, row in enumerate(rows, 1):
            text = row[1] if len(row) > 1 else row[0]
            f = OUT / f"{ch}-{k}.mp3"
            await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(f))
            print(f"{f.name} · {f.stat().st_size // 1024}KB · {text[:30]}", flush=True)


asyncio.run(main())
