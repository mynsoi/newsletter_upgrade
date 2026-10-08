"""Threads 글 페이지 스냅샷(aside snapshot tree)에서 작성자 본문과 이어지는 글만 원문 그대로 뽑는다.

사용: python3 parse_threads.py <스냅샷.txt> > <원문.md>
- 첫 줄 "URL: ..."에서 작성자 핸들을 읽는다.
- "칼럼 본문" 영역의 글 블록을 위에서부터 읽고, 작성자 블록이 이어지는 동안만 본문을 모은다.
- 텍스트는 바꾸지 않는다(요약·재구성 없음).
"""
import json
import re
import sys

src = open(sys.argv[1], encoding="utf-8").read().splitlines()
url = next((l[5:].strip() for l in src if l.startswith("URL: ")), "")
m = re.search(r"/@([^/]+)/post/", url)
author = m.group(1) if m else ""

TEXT = re.compile(r'^(\s*)- text: "(.*)"\s*$')
LINK = re.compile(r'^(\s*)- link "(.*?)"(?: \[ref=[^\]]+\])?(?::\s*"(.*)")?\s*$')
BLOCK = re.compile(r"^  - generic \[ref=[^\]]+\]:\s*$")


def unq(s):
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s.replace("\\n", "\n")


# "칼럼 본문" 영역 이후만 본다
start = next((i for i, l in enumerate(src) if 'region "칼럼 본문"' in l), 0)
blocks, cur = [], None
for l in src[start + 1:]:
    if BLOCK.match(l):
        cur = {"author": None, "date": None, "lines": [], "counts": []}
        blocks.append(cur)
        continue
    if cur is None:
        continue
    lm = LINK.match(l)
    if lm:
        name, val = lm.group(2), lm.group(3)
        if cur["author"] is None and name and not name.startswith("http") and " " not in name and "님" not in name:
            cur["author"] = name
        elif cur["date"] is None and (dm := re.match(r"(\d{4})년 (\d{1,2})월 (\d{1,2})일", name or "")):
            cur["date"] = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
        elif name and ("." in name or name.startswith("http")):
            cur["lines"].append(f"[링크] {name}")
        continue
    tm = TEXT.match(l)
    if tm:
        t = unq(tm.group(2))
        if re.fullmatch(r"[\d.,만천]+", t.strip()):
            cur["counts"].append(t.strip())
        elif t.strip() in {"AI Threads", "인기순", "활동 보기", "작성자", "답글 보기"} or re.fullmatch(r"\d+/\d+", t.strip()):
            continue
        else:
            cur["lines"].append(t)

chain, later = [], []
for b in blocks:
    if b["author"] == author and not later and (not chain or chain[-1] is blocks[blocks.index(b) - 1]):
        chain.append(b)
    elif b["author"] == author:
        later.append(b)
    elif chain and not later:
        later.append(None)  # 표식: 다른 사람 블록이 끼어듦
later = [b for b in later if b]

first = chain[0] if chain else {"date": "", "counts": []}
c = first["counts"] + ["", "", "", ""]
print(f"---\nurl: {url}\nauthor: '@{author}'\ndate: {first['date']}\n"
      f"likes: '{c[0]}'\nreplies: '{c[1]}'\nreposts: '{c[2]}'\nshares: '{c[3]}'\n"
      f"posts_in_chain: {len(chain)}\n---\n")
for i, b in enumerate(chain, 1):
    print(f"## {i}/{len(chain)}\n")
    print("\n".join(b["lines"]).strip() + "\n")
for b in later:
    print(f"## 작성자 답글 ({b['date']})\n")
    print("\n".join(b["lines"]).strip() + "\n")
