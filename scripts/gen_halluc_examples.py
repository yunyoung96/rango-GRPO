#!/usr/bin/env python3
"""덤프한 환각 사례를 **md 조각**으로 만든다 (toggle + 왼쪽 색선).

프롬프트 전문을 사람이 옮겨 적으면 반드시 틀린다. JSON 에서 바로 만든다.
사용: python3 scripts/gen_halluc_examples.py /tmp/halluc_cases2.json [원인들] > frag.md
"""
import json
import re
import sys

BAR = ('<blockquote style="border-left:4px solid #4a9eff; padding-left:1em; '
       'margin-left:0">')
CAUSE_TITLE = {
    "A": "A. 주입 재료 자체가 없다 — 인덱스에도 검색 결과에도 없음",
    "B": "B. 검색 결과에는 있는데 프롬프트에 안 실렸다",
    "C": "C. 주입 재료는 있는데 **씨앗이 닿지 않는다**",
    "D": "D. 씨앗은 닿는데 예산·캡에 밀렸다",
}


def render(case, n):
    d = case["diag"][0]
    nm = d["name"]
    cause = case["cause"]
    vp = case["vp"].rstrip()
    tgt = case["target"]
    seeds = "·".join(d["seed_sources"]) if d["seed_sources"] else "**어디에도 없음**"
    rank = d["rank"] if d["rank"] else "검색 100개 안에 없음"
    out = []
    out.append(f'<details>')
    out.append(f'<summary><b>사례 {n} — <code>{nm}</code> '
               f'({d["kind"]}) · 원인 {cause[0]}</b></summary>')
    out.append('')
    out.append(BAR)
    out.append('')
    out.append(f'**파일** `{case["file"]}`  ·  **idx** `{case["idx"]}`')
    out.append('')
    out.append('**① 모델이 보는 프롬프트 — 전문** (2048토큰 절단 **후** = 실제 입력)')
    out.append('')
    out.append('```')
    out.append(vp)
    out.append('```')
    out.append('')
    out.append('**② gold tactic** (모델이 맞혀야 하는 것)')
    out.append('')
    out.append('```coq')
    out.append(tgt)
    out.append('```')
    out.append('')
    out.append(f'**③ 진단** — 위 프롬프트 어디에도 `{nm}` 이 없다.')
    out.append('')
    out.append('| 항목 | 값 |')
    out.append('|---|---|')
    out.append(f'| 선언 종류 | `{d["kind"]}` |')
    out.append(f'| rango 풀에서 빠지는 종류인가 | '
               f'{"**예** — 검색 후보에 애초에 안 들어간다" if d["pool_excluded"] else "아니오"} |')
    out.append(f'| 검색 100개 중 순위 | {rank} |')
    out.append(f'| `func_defs` 에 정의 재료가 있나 | '
               f'{"**있다**" if d["in_index"] else "없다"} |')
    out.append(f'| 주입 가능한 형태인가(`pick_def`) | '
               f'{"예" if d["pickable"] else "아니오"} |')
    out.append(f'| 씨앗이 닿는 출처 | {seeds} |')
    out.append(f'| 프로젝트 내 tactic 사용 | {d["uses"]}회 · {d["files"]}개 파일 |')
    out.append('')
    if d.get("defn"):
        out.append(f'**④ 참고 — 인덱스에 있는 정의문** (넣을 재료는 있었다)')
        out.append('')
        out.append('```coq')
        out.append(re.sub(r"\s+", " ", d["defn"])[:400])
        out.append('```')
        out.append('')
    out.append('</blockquote>')
    out.append('</details>')
    out.append('')
    return "\n".join(out)


if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    # 인덱스로 직접 고르기: `python3 gen.py cases.json idx:3,24,4,2`
    if len(sys.argv) > 2 and sys.argv[2].startswith("idx:"):
        for n, k in enumerate(int(x) for x in sys.argv[2][4:].split(",")):
            print(render(d["cases"][k], n + 1))
        sys.exit(0)
    want = (sys.argv[2] if len(sys.argv) > 2 else "ABCD")
    per = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    cnt = {}
    n = 0
    for cse in d["cases"]:
        c = cse["cause"][0]
        if c not in want or cnt.get(c, 0) >= per:
            continue
        if len(cse["vp"]) > 7000:          # 너무 긴 것은 건너뛴다(가독성)
            continue
        cnt[c] = cnt.get(c, 0) + 1
        n += 1
        print(render(cse, n))
