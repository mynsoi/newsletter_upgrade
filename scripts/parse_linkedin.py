"""LinkedIn 게시물 페이지 스냅샷(aside snapshot tree)에서 작성자·날짜·본문·반응 수를 원문 그대로 뽑는다.

사용: python3 parse_linkedin.py <스냅샷.txt> > <원문.md>
- "주요 콘텐츠" 영역의 첫 게시물만 본다(사이드바의 열람자 정보는 쓰지 않는다).
- 본문은 바꾸지 않는다(요약·재구성 없음).
"""
import json
import re
import sys

src = open(sys.argv[1], encoding="utf-8").read().splitlines()
url = next((l[5:].strip() for l in src if l.startswith("URL: ")), "")


def unq(s):
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s.replace("\\n", "\n")


start = next((i for i, l in enumerate(src) if 'region "주요 콘텐츠"' in l), None)
if start is None:
    sys.exit("주요 콘텐츠 영역 없음")
author = headline = date = reactions = reposts = ""
body = []
in_body = False
for l in src[start + 1:]:
    if re.match(r"^  - (complementary|contentinfo)", l):
        break
    if not author and (m := re.match(r'\s*- link "(.+?)(?:•.*)?" \[ref=', l)) and "프로필 보기" not in l and m.group(1).strip():
        author = m.group(1).strip()
        continue
    if author and not headline and not in_body and (m := re.match(r'\s*- text: "(.*)"\s*$', l)):
        headline = unq(m.group(1))
        continue
    if not date and (m := re.match(r'\s*- text: "(.+?)\s*•\s*"', l)):
        date = m.group(1)
        continue
    if "게시물에 대한 관리 메뉴 열기" in l:
        in_body = True
        continue
    if (m := re.match(r'\s*- button "반응 버튼[^"]*" \[ref=[^\]]+\]: "([\d,]+)"', l)):
        reactions = m.group(1)
        in_body = False
        continue
    if (m := re.match(r'\s*- button "퍼가기" \[ref=[^\]]+\]: "([\d,]+)"', l)):
        reposts = m.group(1)
        break
    if in_body:
        if (m := re.match(r'\s*- text: "(.*)"\s*$', l)):
            body.append(unq(m.group(1)))
        elif (m := re.match(r'\s*- link "해시태그[^"]*" \[ref=[^\]]+\]: "(.*)"', l)):
            body.append(unq(m.group(1)))

print(f"---\nurl: {url}\nauthor: {author}\nheadline: {headline!r}\ndate: {date}\n"
      f"reactions: '{reactions}'\nreposts: '{reposts}'\n---\n")
print(" ".join(body).strip())
