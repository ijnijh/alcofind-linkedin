"""1단계 — 주제 브레인스토밍.

사용자 방향성(키워드·관심사·최근 이슈)을 입력하면
Claude가 5개의 주제 후보를 제안한다.
각 후보에는 다음이 포함된다:
  · TITLE 안 (8~14 words 영문 또는 12~28자 한글)
  · 목적 축 — 리드젠 / 디맨드젠
  · 핵심 인사이트 (1~2줄)
  · 후킹 안 (한 줄)
  · 시장 핏 — 어느 타겟 세그먼트에 가장 잘 맞는지
"""
from __future__ import annotations

import re
from textwrap import dedent
from typing import Optional

from config import (
    COMPANY_SERIES,
    COMPANY_TARGET_MARKET,
    COMPANY_VOICE,
    PERSONAL_SERIES,
    PERSONAL_TARGET_MARKET,
    PERSONAL_VOICE,
)


BRAINSTORM_SYSTEM = dedent("""
    당신은 김진호(DA Tech / ALCOFIND BD 리더)의 LinkedIn 콘텐츠 전략가입니다.
    사용자가 제시한 방향성에 따라 곧바로 작성 착수 가능한 주제 후보 5개를 만들어 주세요.

    각 후보는 반드시 두 축 중 하나에 명확하게 속해야 합니다:
    · 리드젠 (Lead Gen) — DM·미팅·자료요청을 직접 유도하는 실행적 콘텐츠
    · 디맨드젠 (Demand Gen) — 카테고리 인식 확장 / 시장 교육 / 장기 신뢰 자산

    후보 다양화 규칙:
    · 5개 중 리드젠 2~3개, 디맨드젠 2~3개로 균형
    · 후킹 각도가 서로 겹치지 않도록 (실패담 / 데이터 / 규제 / 비교 / 케이스 등 다양화)
    · 자기 칭찬 형용사·광고 톤 금지
""").strip()


def build_brainstorm_prompt(
    track: str,
    series_key: str,
    direction: str,
    avoid: Optional[str] = None,
) -> str:
    """주제 브레인스토밍용 프롬프트."""
    is_personal = track == "personal"
    series = (PERSONAL_SERIES if is_personal else COMPANY_SERIES)[series_key]
    voice = PERSONAL_VOICE if is_personal else COMPANY_VOICE
    market = PERSONAL_TARGET_MARKET if is_personal else COMPANY_TARGET_MARKET
    primary_lang = series["primary_lang"]
    title_format = (
        "한국어 12~28자 (영문 8~14 words 영문 보조 라벨 포함)"
        if primary_lang == "ko"
        else "English 8~14 words (한국어 12~28자 보조 라벨 포함)"
    )

    parts = [
        BRAINSTORM_SYSTEM,
        "",
        "---",
        "",
        "## 컨텍스트",
        "",
        f"- 트랙: **{'개인 (김진호 1인칭)' if is_personal else 'DA Tech / ALCOFIND 회사 페이지'}**",
        f"- 시리즈: **{series['label']}**",
        f"- 타겟 시장: {market}",
        f"- 화자 입장: {voice}",
        f"- 시리즈 기본 목적 축: {series['goal_axis']}",
        "",
        "## 사용자 방향성",
        "",
        direction.strip() or "(별도 방향성 없음 — 시리즈 정체성에 맞게 자유롭게 제안)",
    ]
    if avoid:
        parts += ["", f"## 피해야 할 주제 / 각도", "", avoid.strip()]

    parts += [
        "",
        "## 출력 형식 (필수)",
        "",
        f"5개 후보를 아래 형식으로 정확히 출력하세요. 각 후보 사이는 빈 줄로 구분.",
        f"TITLE 라인 길이: {title_format}",
        "",
        "```",
        "[#1]",
        "TITLE: <한 줄 헤드라인>",
        "AXIS: <리드젠 or 디맨드젠>",
        "INSIGHT: <1~2줄 핵심 인사이트>",
        "HOOK: <후킹 안 한 줄>",
        "FIT: <어느 타겟 세그먼트에 가장 잘 맞는지 한 줄>",
        "",
        "[#2]",
        "TITLE: ...",
        "(이하 동일하게 #5까지)",
        "```",
        "",
        "모든 후보를 출력한 후, 마지막에 한국어 한 단락(3줄 이내)으로 ",
        "왜 이 5개를 선정했는지 — 어떤 다양성과 균형을 추구했는지 — 설명하세요.",
        "이 단락의 시작에 [SELECTION_NOTE] 마커를 넣어 파싱 가능하게 하세요.",
    ]
    return "\n".join(parts)


# 후보 블록 추출 — [#N] ~ 다음 [#] 또는 [SELECTION_NOTE] 또는 EOF
CANDIDATE_RE = re.compile(
    r"\[#(\d+)\]\s*\n(.*?)(?=\n\[#\d+\]|\n\[SELECTION_NOTE\]|\Z)",
    re.DOTALL,
)
NOTE_RE = re.compile(r"\[SELECTION_NOTE\]\s*\n(.*?)\Z", re.DOTALL)
FIELD_RE = re.compile(r"^(TITLE|AXIS|INSIGHT|HOOK|FIT)\s*:\s*(.+?)$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        nl = t.find("\n")
        if nl > 0:
            t = t[nl + 1 :]
    if t.rstrip().endswith("```"):
        t = t.rstrip()[:-3].rstrip()
    return t


def parse_brainstorm(text: str) -> dict:
    text = _strip_fences(text)
    candidates = []
    for m in CANDIDATE_RE.finditer(text):
        idx = int(m.group(1))
        body = m.group(2)
        fields = {k: v.strip() for k, v in FIELD_RE.findall(body)}
        candidates.append(
            {
                "idx": idx,
                "title": fields.get("TITLE", ""),
                "axis": fields.get("AXIS", ""),
                "insight": fields.get("INSIGHT", ""),
                "hook": fields.get("HOOK", ""),
                "fit": fields.get("FIT", ""),
            }
        )
    candidates.sort(key=lambda c: c["idx"])
    note_match = NOTE_RE.search(text)
    selection_note = note_match.group(1).strip() if note_match else ""
    return {"candidates": candidates, "selection_note": selection_note}
