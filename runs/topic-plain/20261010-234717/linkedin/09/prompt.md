아래 [원문]을 재료로 사내 뉴스레터(SK E&S 직원 대상, 대부분 개발자가 아닌 사무·현장 직군) 칼럼을 한 편 쓰려고 합니다. 제목은 나중에 따로 정합니다. 지금은 이 원문으로 무슨 이야기를 할 수 있는지만 정리해 주세요.

출력 형식(이 두 줄 머리만 쓰고 다른 설명은 붙이지 마세요):
있었던 일: <원문 속 사람이 실제로 겪거나 한 일. 사실과 숫자는 원문에 있는 그대로, 두세 문장>
할 말: <그 일에서 우리 직원이 가져갈 것 한 가지를, 옆자리 동료에게 말하듯 평범한 평서문 한 문장으로>

지킬 것: 원문의 문장을 그대로 옮기지 않습니다. 원문에 없는 사실·수치·경험을 지어내지 않습니다. 원문이 가장 하고 싶은 말을 붙잡고, 사소한 세부에 매달리지 않습니다.

파일을 만들거나 명령을 실행하지 말고 답변으로만 주세요.

=== [원문] ===
New research note from , Cheryl Wu, , and me. (Chiefly Parker!) We find that *half* of SWE-bench Verified solutions from Sonnet 3.5-to-4.5 generation AIs *which are graded as passing* are rejected by project maintainers.In our set-up, 4 maintainers from scikit-learn, Sphinx, and pytest (25% of SWE-bench repos) review 296 AI PRs (from 19% of SWE-bench Verified issues; solutions on these issues have pass rates representative of SWE-Bench verified) from 's benchmarking hub.Maintainers are blinded to human vs AI. They review PRs on github (but without CI + ignoring test requirements).We adjust for noise in merge decisions by using the proportion of original human solutions which these same maintainers would approve for merging into main.Repo maintainer feedback suggests that a meaningful chunk of rejections are due to core functionality failures, not merely code quality issues.Note that we think it's plausible that better elicitation could decrease the gap between pass rates from automated grader vs. repo maintainers, and that in our set-up AIs and humans aren't working under identical conditions (AIs can't iterate on maintainer feedback).The takeaway here is an AI classic: benchmarks don't tell the full story.Naive interpretation of SWE-bench Verified scores as ~"% of solutions solving issues to real-world standard" would overestimate AI agent capabilities (at least without more elicitation/feedback).