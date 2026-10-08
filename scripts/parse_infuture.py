"""「유정식의 경영일기」 글 페이지 스냅샷에서 본문을 원문 그대로 뽑는다.

사용: python3 parse_infuture.py <snap/pNNN.txt> <제목> > <pNNN.md>
- 스냅샷 트리의 text·table 노드 중 가장 긴 한국어 덩어리를 본문으로 본다(본문은 shadow DOM 안에 있어 일반 innerText로는 안 잡힘).
- 날짜·호수는 "YYYY년 M월 D일 (No. N)" 머리에서 읽고, 본문은 그 뒤부터 "(끝)"까지 + 참고 표기.
- 텍스트는 바꾸지 않는다(빈 줄 정리만).
"""
import json
import re
import sys

path, title = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""
k = re.search(r"p(\d+)\.txt$", path).group(1)
blobs = []
for line in open(path, encoding="utf-8"):
    m = re.match(r'\s*- (?:text|table|cell|generic|paragraph)(?: \[ref=[^\]]+\])?:\s*"(.*)"\s*$', line)
    if not m:
        continue
    s = m.group(1)
    try:
        s = json.loads('"' + s + '"')
    except Exception:
        s = s.replace("\\n", "\n")
    blobs.append(s)
# "(No. N)" 머리부터 "(끝)"이 든 조각까지 문서 순서대로 잇고, 뒤따르는 "*참고" 조각까지 붙인다
si = next((i for i, b in enumerate(blobs) if re.search(r"\(No\. ?\d+\)", b)), 0)
ei = next((i for i in range(si, len(blobs)) if "(끝)" in blobs[i]), len(blobs) - 1)
tail = [b for b in blobs[ei + 1:ei + 4] if b.strip().startswith("*참고")]
text = "\n\n".join(blobs[si:ei + 1] + tail)
m = re.search(r"(\d{4})년 (\d{1,2})월 (\d{1,2})일\s*\(No\. ?(\d+)\)", text)
date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""
issue = m.group(4) if m else ""
body = text[m.end():] if m else text
end = body.find("(끝)")
ref = ""
if end != -1:
    rest = body[end + 3:]
    rm = re.search(r"\*\s*참고[^\n]*(?:\n(?!\*)[^\n]+){0,3}", rest)
    ref = rm.group(0).strip() if rm else ""
    body = body[: end + 3]
body = re.sub(r"[ \t]+\n", "\n", body)
body = re.sub(r"\n{3,}", "\n\n", body).strip()
if title and body.startswith(title):
    body = body[len(title):].strip()
n = len(re.sub(r"\s", "", body))
print(f"---\nurl: https://infuture.stibee.com/p/{k}\ntitle: {title!r}\ndate: {date}\nissue: '{issue}'\n"
      f"chars_no_space: {n}\nhas_end_mark: {end != -1}\nreference: {ref!r}\n---\n\n{body}\n")
