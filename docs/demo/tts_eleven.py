"""시연 영상 2차 내레이션 음성 — ElevenLabs로 문장마다 <챕터>-<번호>.mp3를 만든다 (11/4 사용자: 우리 녹음 대신 일레븐랩스 더빙)

사용: py -3 -X utf8 -I docs/demo/tts_eleven.py --voices                 # 쓸 수 있는 목소리 목록(이름 · voice_id)
      py -3 -X utf8 -I docs/demo/tts_eleven.py --voice <voice_id> [--model eleven_multilingual_v2] [--only 1,5] [--out _workspace/demo/tts-eleven]
  그다음: py -3 -X utf8 -I docs/demo/edit.py --r2 --audio _workspace/demo/tts-eleven --out r2-v3
- 키는 ELEVENLABS_API_KEY — 이 셸에 없으면 Windows 사용자 환경변수에서 읽는다. 값은 출력하지 않는다.
- 글은 docs/demo/narration-r2.json의 읽는 표기(둘째 칸, 없으면 자막 글). 같은 챕터의 앞뒤 문장을 previous_text·next_text로 넘겨 억양을 잇는다.
- 이미 있는 파일은 건너뛴다(--force면 다시) — 글자 수만큼 크레딧이 든다. 대본 글이 ElevenLabs 서버로 간다.
- 회사망 SSL 검사 때문에 Windows 인증서 저장소(truststore)를 쓴다 — 검증을 끄지 않는다.
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import truststore

truststore.inject_into_ssl()

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:]
API = "https://api.elevenlabs.io/v1"


def opt(name, default):
    return args[args.index(name) + 1] if name in args else default


VOICE = opt("--voice", "")
MODEL = opt("--model", "eleven_multilingual_v2")
OUT = ROOT / opt("--out", "_workspace/demo/tts-eleven")
ONLY = {x for x in opt("--only", "").split(",") if x}
FORCE = "--force" in args


def key():
    k = os.environ.get("ELEVENLABS_API_KEY", "")
    if not k and sys.platform == "win32":
        k = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetEnvironmentVariable('ELEVENLABS_API_KEY','User')"],
                           capture_output=True, text=True).stdout.strip()
    if not k:
        sys.exit("ELEVENLABS_API_KEY가 없습니다 — Windows 사용자 환경변수에 넣어 주세요")
    return k


def call(path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None, method="POST" if body else "GET",
                                 headers={"xi-api-key": key(), "Content-Type": "application/json", "Accept": "audio/mpeg" if body else "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    if "--voices" in args:
        for v in json.loads(call("/voices"))["voices"]:
            lab = v.get("labels") or {}
            print(f"{v['voice_id']}  {v['name']}  ({', '.join(x for x in (lab.get('gender'), lab.get('age'), lab.get('accent'), v.get('category')) if x)})")
        return
    if not VOICE:
        sys.exit("--voice <voice_id>가 필요합니다 (목록은 --voices)")
    narr = json.loads((ROOT / "docs" / "demo" / "narration-r2.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    chars = 0
    for n, rows in narr.items():
        if not n.isdigit() or (ONLY and n not in ONLY):
            continue
        texts = [r[1] if len(r) > 1 else r[0] for r in rows]
        for k, text in enumerate(texts, 1):
            f = OUT / f"{n}-{k}.mp3"
            if f.exists() and not FORCE:
                continue
            body = {"text": text, "model_id": MODEL,
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.15, "use_speaker_boost": True},
                    "previous_text": texts[k - 2] if k > 1 else None, "next_text": texts[k] if k < len(texts) else None}
            f.write_bytes(call(f"/text-to-speech/{VOICE}?output_format=mp3_44100_128", body))
            chars += len(text)
            print(f"  {f.name}  {text[:30]}…", flush=True)
    print(f"끝 → {OUT} · 이번에 보낸 글 {chars}자")


if __name__ == "__main__":
    main()
