"""LinkedIn 본문 생성용 구조화 프롬프트 빌더.

두 트랙 모두 한·영 병기 출력:
  · 개인 트랙(primary_lang='ko'): 한국어 먼저, 영문은 KO 참고 → EN 참고 순서
  · 회사 트랙(primary_lang='en'): 영문 먼저, 한국어는 EN 참고 → KO 참고 순서

화자 입장:
  · 개인 = 김진호 1인칭 (현장 BD)
  · 회사 = ALCOFIND / we (회사 공식)

타겟 시장:
  · 개인 = 한국 국내
  · 회사 = 미국 · 호주 · 중동 · 인도 · 아세안 (유럽 제외)
"""
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


SYSTEM_NOTE = dedent("""
    당신은 김진호(DA Tech / ALCOFIND BD 리더)의 개인 LinkedIn 계정과
    DA Tech / ALCOFIND 회사 페이지의 카피라이터입니다.

    최종 목적: 인바운드 리드 확보 (개인 = 국내 / 회사 = 영어권 글로벌).
    주제의 큰 두 축: 리드젠(Lead Gen) · 디맨드젠(Demand Gen).

    공통 원칙:
    1. **포스트는 [TITLE] 한 줄로 시작 → 빈 줄 → [HOOK].**
       LinkedIn은 제목 필드가 없으므로 본문 최상단 한 줄이 헤드라인 역할.
       제목 길이: 한국어 12~28자 / 영문 8~14 words.
    2. LinkedIn 미리보기 컷(첫 ~210자) 안에서 후킹을 완성.
    3. 광고 톤 금지. 의외성·실패담·데이터·인용을 앞에 배치.
    4. 자기 칭찬 형용사("best", "혁신적", "유일한") 금지.
    5. 본문 상단 3블록에 제품명·모델명 노출 금지 (CTA 직전에만 가능).
    6. CTA는 '대화 초대' 톤. 강매 X.
    7. 해시태그 3~5개를 본문 마지막에 (해당 언어용).
    8. 본문 분량 — **간결 우선**:
       · 한국어 본문 = 840~1,260자
       · 영문 본문   = 700~1,050 characters
       · 분량을 채우려고 늘리지 말 것.
    9. **요약 헤더 표기 — "TL;DR" 사용 금지**.
       영문은 **"Key takeaways"** 또는 **"Three quick reads"**,
       한국어는 **"핵심 요약"** 또는 **"한눈에 보기"** 를 사용.
    10. **CLAIM HYGIENE — 사실 주장 위생 (매우 중요)**:
        a. "최초", "유일", "최대", "가장 먼저"와 같은 절대적 단언은 **사용자 입력의 [추가 데이터 / 1차 출처]에 명시되어 있을 때만** 허용.
        b. 명시된 출처가 없으면 calibrated language로:
           · "한국은 아시아 최초의 IID 시행국" ❌
           · "한국은 2024년 IID 의무화를 시행 — 아시아권에서는 비교적 이른 시기" ⭕
           · "Korea is the first in Asia to mandate IID" ❌
           · "Korea's 2024 IID mandate is among the earlier in Asia (per public records)" ⭕
        c. 통계·수치·연도·관할 기관명은 입력에 명시된 것만 사용. 추정·재구성 금지.
        d. 명시 안 된 비교·서열·시장 점유율 주장 금지.
        e. 의심스러우면 단언 대신 질문형 또는 "publicly reported" 같은 외부참조 톤으로.
    11. **[FACTS_TO_VERIFY] 출력 블록 — 게시 전 검증 체크리스트**:
        본문에 등장하는 사실 주장 중 **김진호 님이 게시 전 1차 출처로 확인해야 할 항목**을
        bullet으로 정리. 만약 본문에 검증 필요 사실이 0개면 "(없음 — 모든 주장이 입력 출처에 근거)" 라고 명시.

    **한·영 병기 규칙** — 두 트랙 모두 한·영 출력하되 순서가 다르다:
    · 개인 트랙: PRIMARY = 한국어 (게시용), SECONDARY = 영문 (보조·검수용)
    · 회사 트랙: PRIMARY = 영문 (게시용), SECONDARY = 한국어 (검수용)

    각 섹션은 PRIMARY를 먼저, SECONDARY를 그 아래에 출력한다.
""").strip()


def _series(track: str, key: str):
    return (PERSONAL_SERIES if track == "personal" else COMPANY_SERIES)[key]


def build_prompt(
    track: str,
    series_key: str,
    topic: str,
    key_insight: str,
    cta_override: Optional[str] = None,
    anonymized_case: Optional[str] = None,
    extra_facts: Optional[str] = None,
    goal_axis: Optional[str] = None,
) -> str:
    """주제와 인사이트로부터 본문 생성 프롬프트 빌드.

    goal_axis가 명시되면 시리즈 기본값을 오버라이드 (리드젠/디맨드젠 명시 강조).
    """
    s = _series(track, series_key)
    is_personal = track == "personal"
    voice = PERSONAL_VOICE if is_personal else COMPANY_VOICE
    market = PERSONAL_TARGET_MARKET if is_personal else COMPANY_TARGET_MARKET
    cta = (cta_override or "").strip() or s["cta_default"]
    axis = (goal_axis or "").strip() or s["goal_axis"]

    hashtags_primary = s["hashtags_ko"] if is_personal else s["hashtags_en"]
    hashtags_secondary = s["hashtags_en"] if is_personal else s["hashtags_ko"]

    lines = [
        SYSTEM_NOTE,
        "",
        "---",
        "",
        "## 이 포스트 작업 지시",
        "",
        f"- 트랙: **{'김진호 개인 계정' if is_personal else 'DA Tech / ALCOFIND 회사 페이지'}**",
        f"- 시리즈: **{s['label']}**",
        f"- 목적 축: **{axis}**",
        f"- 타겟 시장: {market}",
        f"- 화자 입장: {voice}",
        f"- 구조 가이드: {s['structure']}",
        f"- 톤 가이드: {s['tone']}",
        "",
        "### 입력 콘텐츠",
        f"- 주제: {topic}",
        f"- 핵심 인사이트 / 메시지: {key_insight}",
    ]
    if anonymized_case:
        lines.append(f"- 익명화된 케이스 / 사실: {anonymized_case}")
    if extra_facts:
        lines.append(f"- 추가 데이터 / 1차 출처: {extra_facts}")
    lines += [
        f"- 원하는 CTA: {cta}",
        f"- 해시태그 후보 (PRIMARY 언어): {' '.join(hashtags_primary)}",
        f"- 해시태그 후보 (SECONDARY 언어, 참고): {' '.join(hashtags_secondary)}",
        "",
    ]

    if is_personal:
        # PRIMARY = 한국어 (게시용), SECONDARY = 영문 (참고)
        lines += [
            "### 출력 형식 — **한·영 병기 / 한국어 먼저**",
            "",
            "각 섹션마다 KO(게시용)를 먼저, EN(참고)을 그 아래에. 의역해도 좋으나 의미·뉘앙스 보존.",
            "",
            "```",
            "[TITLE · KO]",
            "<한 줄 헤드라인 — 12~28자, 시리즈 + 토픽 요약>",
            "[TITLE · EN 참고]",
            "<영어 대응 번역>",
            "",
            "[HOOK · KO]",
            "<후킹 첫 줄 — 미리보기 컷 기준 210자 이내, 가장 자극적인 한 줄>",
            "[HOOK · EN 참고]",
            "<영어 대응 번역>",
            "",
            "[BODY · KO]",
            "<본문 — 구조 가이드 그대로, 840~1,260자>",
            "[BODY · EN 참고]",
            "<영어 대응 번역, 같은 문단 구조>",
            "",
            "[CTA · KO]",
            "<대화 초대 톤의 CTA 한두 줄>",
            "[CTA · EN 참고]",
            "<영어 대응 번역>",
            "",
            "[HASHTAGS · KO]",
            "<한국어 해시태그 3~5개>",
            "[HASHTAGS · EN 참고]",
            "<영어 해시태그 3~5개>",
            "",
            "[IMAGE_HOOK · KO]",
            "<이미지 카드용 한 줄 8~20자. 본문에서 가장 강한 한 문장의 압축판. 구체적 단어 사용, 추상어 X. 따옴표·숫자·고유명사를 포함해야 자동 컬러 강조됨>",
            "[IMAGE_HOOK · EN 참고]",
            "<영어 대응 번역, 8~16 chars>",
            "",
            "[IMAGE_KEYWORDS]",
            "<Unsplash 사진 검색용 영문 키워드 2~3개 단어, 콤마 구분. 본문 주제에 맞는 사진을 잘 찾도록 구체적 명사+상황. 예: 'construction worker safety helmet', 'industrial truck driver dashboard', 'office meeting team negotiation'. 사람·장소·도구 명사를 우선.>",
            "",
            "[FACTS_TO_VERIFY]",
            "<본문에 등장하는 사실 주장 중 게시 전 1차 출처로 확인 필요한 항목 bullet 정리. 없으면 '(없음)'>",
            "",
            "[INTENT_NOTE]",
            "<왜 이 후킹·구조·CTA를 택했는지 한국어로 3줄 이내 — 검수용>",
            "```",
        ]
    else:
        # PRIMARY = 영문 (게시용), SECONDARY = 한국어 (참고)
        lines += [
            "### 출력 형식 — **한·영 병기 / 영문 먼저**",
            "",
            "각 섹션마다 EN(게시용)을 먼저, KO(참고)를 그 아래에. EN은 자연스러운 비즈니스 영어로.",
            "Korea는 하나의 데이터 포인트로만 다루고, 글로벌 또는 타겟 지역 중심 프레이밍 우선.",
            "",
            "```",
            "[TITLE · EN]",
            "<English headline — 8~14 words, series tag + topic>",
            "[TITLE · KO 참고]",
            "<한국어 대응 번역>",
            "",
            "[HOOK · EN]",
            "<English hook — within ~180 chars, the most arresting opener>",
            "[HOOK · KO 참고]",
            "<한국어 대응 번역>",
            "",
            "[BODY · EN]",
            "<English body — follow the structure guide, target 700~1,050 chars>",
            "[BODY · KO 참고]",
            "<한국어 대응 번역, 같은 문단 구조>",
            "",
            "[CTA · EN]",
            "<English CTA, conversation-invite tone>",
            "[CTA · KO 참고]",
            "<한국어 대응 번역>",
            "",
            "[HASHTAGS · EN]",
            "<English hashtags 3~5개>",
            "[HASHTAGS · KO 참고]",
            "<한국어 해시태그 3~5개>",
            "",
            "[IMAGE_HOOK · EN]",
            "<8~16 chars/words, sharp English line for the brand card. Most arresting line of the body, compressed. Include quotes, numbers, or proper nouns for auto-color emphasis. Concrete words only — no abstractions.>",
            "[IMAGE_HOOK · KO 참고]",
            "<한국어 대응 번역, 8~20자>",
            "",
            "[IMAGE_KEYWORDS]",
            "<Unsplash photo search keywords — 2~3 English words, comma-separated. Choose concrete nouns (people + place + tool) matching the topic so Unsplash finds a fitting business-grade photo. Examples: 'construction site safety helmet', 'truck driver dashboard', 'corporate boardroom meeting', 'shipping port containers'.>",
            "",
            "[FACTS_TO_VERIFY]",
            "<본문(EN·KO 공통)에 등장하는 사실 주장 중 게시 전 1차 출처로 확인 필요한 항목을 한국어 bullet으로 정리. 없으면 '(없음)'>",
            "",
            "[INTENT_NOTE]",
            "<왜 이 후킹·구조·CTA를 택했는지 한국어로 3줄 이내 — 검수용>",
            "```",
        ]
    return "\n".join(lines)
