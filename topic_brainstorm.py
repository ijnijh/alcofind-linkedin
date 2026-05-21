"""1단계 — 주제 브레인스토밍 (창의성·다양성 강화 버전).

핵심 개선:
  · 한국 음주측정 산업의 주제 풀 7개 영역을 LLM에 명시적으로 시드
  · 회사 트랙(글로벌)용 별도 풀 — 미국·호주·중동·인도·아세안 규제·시장
  · 후킹 전략 8종 명시 — 5개 후보가 서로 다른 전략으로
  · IID(시동잠금장치)에만 회귀하지 않도록 차단
  · 각 후보에 THEME_AREA + HOOK_STRATEGY 라벨 강제 → 다양성 자동 검증
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


# ==========================================================
# 주제 풀 — LLM에 시드되는 다양한 영역
# ==========================================================

KOREA_THEME_POOL = dedent("""
    한국 음주측정 산업의 7개 주제 영역. 5개 후보는 가급적 서로 다른 영역에서 샘플링:

    [영역1] 규제·법령 (IID 외에도 다양함)
      · 산업안전보건법·중대재해처벌법 — 작업자 음주 / 사업주 형사책임
      · 운수사업법·여객자동차법 — 택시·버스·트럭 사전 점검 의무
      · 어선원 및 어선원의 재해보상에 관한 법률 — 해상 안전
      · 항공보안법·철도안전법 — 항공·철도 종사자 음주 규정
      · 학교보건법·어린이 통학버스 안전 — 학교 차량 운전자
      · 노사 단체협약 — 자율 측정 합의·동의 절차
      · 군인사법·경찰공무원법 — 공직자 음주 관리

    [영역2] 미측정 시 발생하는 재정적·법적 리스크
      · 중대재해처벌법 — 사망사고 발생 시 사업주 1년 이상 징역
      · 산재보험금 지급 거부 / 요율 상승
      · 도급 구조 시 원청 안전관리 책임 확대 (산안법 63조 등)
      · KOSHA-MS·ISO 45001 인증 박탈
      · 사고 후 행정처분 (영업정지·면허취소)
      · 노사 분쟁 — 정직·해고 불복 소송, 부당해고 판결
      · 기업 보험 거부·보험요율 인상

    [영역3] 사고·사건 사례 (1차 출처 기반)
      · 음주 관련 산재 통계 (KOSHA 산업재해 현황 보고서)
      · 운수업 음주사고 — 시내버스·고속버스·택시
      · 건설현장 음주 추락·끼임·기계 충돌
      · 학교 버스·통학차 음주 사고
      · 항공·철도 종사자 음주 적발 사례

    [영역4] 운영·SOP 현장 케이스
      · 동의 절차 (개인정보 보호법 vs 안전 의무) — 충돌과 해결
      · 측정 시간·횟수 (출근 직전 vs 작업 중 무작위 vs 사고 후)
      · 양성 반응 처리 (격리 → 재측정 → 조사 → 노조 협상)
      · 데이터 보관·삭제·열람 권한
      · 도급·하청 적용 범위 (원청 의무 vs 하청 동의)
      · 야간·교대 근로자 적용

    [영역5] 기술·제품 트렌드
      · 클라우드 기록·감사 추적 (Audit trail)
      · 자동 인증 (얼굴 인식·지문·QR 매핑)
      · IoT 연동 (출입·시동 잠금·작업 차단)
      · 데이터 분석·패턴 인식
      · 모바일·무선 측정

    [영역6] 비교·인사이트
      · 글로벌 사례 (미국 DOT, 일본 운수업) vs 한국 — 한쪽 잘하는 것
      · 자율 도입 vs 의무화 — 효과 비교
      · 사후 처벌 vs 사전 관리 — ROI
      · 대기업 vs 중소기업 적용 격차
      · 사업주 시각 vs 안전관리자 시각

    [영역7] BD·휴먼 관점 (BD 노트 시리즈 한정)
      · 영업 5년 차 받는 같은 질문 3개
      · 결정권자 분포 — 안전팀장·구매·CFO·CEO 각각의 관심사
      · 도입 검토 단계별 거절 사유 패턴
      · 가격 협상 인사이트
""").strip()


GLOBAL_THEME_POOL = dedent("""
    글로벌 alcohol-safety 산업의 7개 주제 영역.
    타겟 시장: United States · Australia · GCC (UAE/Saudi/Qatar) · India · ASEAN. Europe is excluded.

    [Area 1] Regulatory pulse — multi-jurisdiction
      · US: DOT 49 CFR Part 40, FMCSA, SAMHSA, OSHA
      · Australia: Safe Work Australia, fitness-for-work standards
      · GCC: UAE MOHRE labor reform, Saudi HRSD, Qatar Wage Protection
      · India: DGFASLI, Factories Act, BIS standards, Petroleum Rules
      · ASEAN: Singapore MOM, Malaysia DOSH, Thailand DLPW, Vietnam MOLISA

    [Area 2] Financial / legal risks of NOT testing
      · OSHA fines · Australian SafeWork penalties · GCC labor court rulings
      · Insurance underwriting changes (premium adjustments based on testing practice)
      · Procurement disqualification — fleet contracts requiring documented testing
      · Class-action exposure (US)
      · Brand reputation in safety-sensitive sectors (oil & gas, aviation, mining)

    [Area 3] Industry-specific adoption
      · Fleet: Tier-1 US carriers, Australian long-haul, GCC bus operators
      · Construction: Saudi NEOM-scale projects, Indian metro rail
      · Oil & Gas: ADNOC, Aramco, Indian ONGC, ASEAN PETRONAS
      · Mining: Australian iron ore, Indonesian coal
      · Aviation ground crews · Maritime crews

    [Area 4] Operational evidence / case studies
      · Pre-shift random testing vs post-incident — incident rate change
      · Data integrity audit trail (what regulators ask for)
      · Multi-jurisdiction operators dealing with conflicting rules
      · Anonymous case from Korea as one data point (no self-promotion)

    [Area 5] Tech / product trends
      · Cloud-based audit trails
      · Biometric authentication (face / fingerprint / QR mapping)
      · IoT integration (access control, ignition lock, machine lockout)
      · API for HR / fleet management systems
      · Edge analytics for real-time risk scoring

    [Area 6] Market / commercial signals
      · Tender language: "audit trail", "data export format", "record retention"
      · Insurance underwriter requirements
      · Distributor margin trends in target regions
      · OEM vs branded — buyer behavior shift
      · Korea OEM export readiness (gentle, factual)

    [Area 7] Comparative analysis (Korea as one data point)
      · Korea vs US: prevention frameworks
      · Korea vs Australia: workplace alcohol standards
      · Korea OEM capability vs ASEAN local manufacturing
""").strip()


HOOK_STRATEGIES = dedent("""
    후킹 전략 8종 — 5개 후보는 가급적 서로 다른 전략으로:

    A) 충격 데이터 — "X%가 음주 연관 — 보고서엔 안 나옵니다"
    B) 현장 인용 — "안전관리자가 이렇게 말했습니다: '...'"
    C) 의외 케이스 — "음주측정 도입 후 사고가 늘었습니다. 왜?"
    D) 정보 격차 — "사업주가 모르는 산안법 X조 — 미측정의 진짜 책임"
    E) 비교/대조 — "미국은 사후 처벌, 한국은? 5년 안에 바뀝니다"
    F) 질문 후킹 — "음주측정기 도입했는데 왜 보험료가 그대로일까?"
    G) 시간 압박 — "2026년 X 개정 D-180일 — 운수사 무엇을 준비해야"
    H) 미신 파괴 — "음주측정은 '운전기사'만의 일이라는 오해"
""").strip()


FORBIDDEN_PATTERNS = dedent("""
    금지 패턴 (반드시 피할 것):
    · 식상한 일반론 ("음주측정의 중요성", "안전이 우선")
    · 자기 칭찬 형용사 ("최고의", "혁신적", "유일한")
    · IID(시동잠금장치)에만 집중 — 이미 다른 포스트에서 다뤘다고 가정. 5개 중 최대 1개만 IID 허용.
    · 같은 후킹 각도 반복
    · "최초·유일·최대" 절대 단언 (calibrated 표현 사용)
    · CLAIM HYGIENE 위반 (검증되지 않은 사실 단언)
""").strip()


SERIES_SPECIALTY = {
    "현장노트": "익명화된 케이스 + 1인칭 인용 + 실패담 우선. 사람 중심. 데이터는 보조.",
    "산업 인사이트": "1차 출처(KOSHA·고용노동부·통계청·법령) + 통계 + 규제 분석. 데이터·정책 톤.",
    "BD 노트": "BD 5년차 휴먼 인사이트, 영업 일화, 짧고 가볍게, 자조적 유머 허용.",
    "Industry Pulse": "글로벌 분석가 톤. 5개 jurisdiction (US·AU·GCC·India·ASEAN) 중 1~2개에 집중. Korea는 한 데이터 포인트.",
    "Company News": "보도자료 톤 (LinkedIn 친화). 회사 이벤트·인증·파트너십·신제품·전시 — 단, 자기 칭찬 금지.",
}


BRAINSTORM_SYSTEM = dedent("""
    당신은 김진호(DA Tech / ALCOFIND BD 리더)의 LinkedIn 콘텐츠 전략가입니다.
    음주측정·산업안전 분야 한국 최고 수준의 후킹 카피라이터처럼 사고하세요.
    안전한 일반론으로 회귀하지 마세요 — 매번 5개 후보가 서로 완전히 다른 각도여야 합니다.

    리드젠 (Lead Gen) vs 디맨드젠 (Demand Gen) 균형:
    · 리드젠 = DM·미팅·자료요청을 직접 유도하는 실행 콘텐츠 (2~3개)
    · 디맨드젠 = 카테고리 인식·시장 교육·장기 신뢰 자산 (2~3개)
""").strip()


def build_brainstorm_prompt(
    track: str,
    series_key: str,
    direction: str,
    avoid: Optional[str] = None,
) -> str:
    """주제 브레인스토밍용 프롬프트 — 풀 시드 + 후킹 전략 + 다양성 강제."""
    is_personal = track == "personal"
    series = (PERSONAL_SERIES if is_personal else COMPANY_SERIES)[series_key]
    voice = PERSONAL_VOICE if is_personal else COMPANY_VOICE
    market = PERSONAL_TARGET_MARKET if is_personal else COMPANY_TARGET_MARKET
    primary_lang = series["primary_lang"]
    theme_pool = KOREA_THEME_POOL if is_personal else GLOBAL_THEME_POOL
    specialty = SERIES_SPECIALTY.get(series_key, "")
    title_format = (
        "한국어 12~28자"
        if primary_lang == "ko"
        else "English 8~14 words"
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
        f"- 시리즈 specialty: {specialty}",
        f"- 타겟 시장: {market}",
        f"- 화자 입장: {voice}",
        f"- 시리즈 기본 목적 축: {series['goal_axis']}",
        "",
        "## 사용 가능한 주제 풀 (서로 다른 영역에서 샘플링)",
        "",
        theme_pool,
        "",
        "## 후킹 전략",
        "",
        HOOK_STRATEGIES,
        "",
        "## 금지 패턴",
        "",
        FORBIDDEN_PATTERNS,
        "",
        "## 사용자 방향성",
        "",
        direction.strip() or "(별도 방향성 없음 — 위 풀에서 자율적으로, 가장 후킹력 높은 5개를 선정)",
    ]
    if avoid:
        parts += ["", "## 추가로 피해야 할 주제·각도", "", avoid.strip()]

    parts += [
        "",
        "## 출력 형식 (필수)",
        "",
        f"5개 후보를 아래 형식으로 정확히 출력. 각 후보 사이는 빈 줄로 구분.",
        f"TITLE 라인 길이: {title_format}",
        "",
        "**중요 — 다양성 강제**:",
        "· THEME_AREA는 5개 후보가 가급적 모두 달라야 함 (한국=영역1~7 중 / 글로벌=Area1~7 중)",
        "· HOOK_STRATEGY도 5개 후보가 가급적 모두 달라야 함 (A~H 중)",
        "· 리드젠 2~3 + 디맨드젠 2~3 분포 유지",
        "· IID 주제는 최대 1개로 제한",
        "",
        "```",
        "[#1]",
        "TITLE: <한 줄 헤드라인>",
        "AXIS: <리드젠 or 디맨드젠>",
        "THEME_AREA: <영역 번호와 이름, 예: '영역2 — 미측정 시 재정적·법적 리스크' 또는 'Area 3 — Industry-specific adoption'>",
        "HOOK_STRATEGY: <A~H 중 한 글자 + 짧은 설명, 예: 'D — 정보 격차'>",
        "INSIGHT: <1~2줄 핵심 인사이트>",
        "HOOK: <후킹 안 한 줄, 후킹 전략대로>",
        "FIT: <어느 타겟 세그먼트에 가장 잘 맞는지 한 줄>",
        "",
        "[#2]",
        "TITLE: ...",
        "(이하 동일하게 #5까지)",
        "```",
        "",
        "5개 후보 모두 출력한 후, 마지막에 한국어 한 단락(4줄 이내)으로",
        "왜 이 5개를 선정했는지 — 어떤 영역·후킹 전략·축의 다양성을 추구했는지 — 설명.",
        "이 단락의 시작에 [SELECTION_NOTE] 마커를 넣어 파싱 가능하게.",
    ]
    return "\n".join(parts)


# ==========================================================
# 응답 파싱
# ==========================================================

CANDIDATE_RE = re.compile(
    r"\[#(\d+)\]\s*\n(.*?)(?=\n\[#\d+\]|\n\[SELECTION_NOTE\]|\Z)",
    re.DOTALL,
)
NOTE_RE = re.compile(r"\[SELECTION_NOTE\]\s*\n(.*?)\Z", re.DOTALL)
FIELD_RE = re.compile(
    r"^(TITLE|AXIS|THEME_AREA|HOOK_STRATEGY|INSIGHT|HOOK|FIT)\s*:\s*(.+?)$",
    re.MULTILINE,
)


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
                "theme_area": fields.get("THEME_AREA", ""),
                "hook_strategy": fields.get("HOOK_STRATEGY", ""),
                "insight": fields.get("INSIGHT", ""),
                "hook": fields.get("HOOK", ""),
                "fit": fields.get("FIT", ""),
            }
        )
    candidates.sort(key=lambda c: c["idx"])
    note_match = NOTE_RE.search(text)
    selection_note = note_match.group(1).strip() if note_match else ""
    return {"candidates": candidates, "selection_note": selection_note}
