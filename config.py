"""브랜드 상수 + 개인·회사 시리즈 정의."""
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
HISTORY_DIR = ROOT / "history"
OUT_DIR.mkdir(exist_ok=True)
HISTORY_DIR.mkdir(exist_ok=True)

# .env 자동 로드 (있을 때만). 환경변수가 이미 설정돼 있으면 그것이 우선.
load_dotenv(ROOT / ".env", override=False)

# 사용 가능 모델 — 라벨 → 모델 ID
MODELS = {
    "Sonnet 4.6 (권장 · 균형)": "claude-sonnet-4-6",
    "Haiku 4.5 (빠르고 저렴)": "claude-haiku-4-5-20251001",
    "Opus 4.7 (최고 품질)": "claude-opus-4-7",
}
DEFAULT_MODEL_LABEL = "Sonnet 4.6 (권장 · 균형)"

BRAND = {
    "name_kr": "ALCOFIND",
    "name_full": "DA Tech · ALCOFIND",
    "primary": "#1B4D2B",       # 다크그린 (코어)
    "secondary": "#4F7A52",     # 보조그린
    "accent": "#F4E8D0",        # 베이지 (따뜻한 액센트)
    "highlight": "#FFC857",     # 옐로우 (강조·시선유도)
    "alert": "#E63946",         # 코랄 (위급·반전)
    "cool": "#5B8FB9",          # 블루 (데이터·신뢰)
    "ink": "#0F1A11",           # 본문 잉크 블랙
    "white": "#FFFFFF",
    "muted": "#8B9C8E",
    "paper": "#FAF7F0",         # 종이톤 (에디토리얼 배경용)
}

FONT_REGULAR = "C:/Windows/Fonts/malgun.ttf"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"

# ===========================================================
# 개인 트랙 — 한국 국내 시장, 김진호 1인칭 화자
# 출력 = 한국어 먼저 + 영문 보조 (한·영 병기)
# ===========================================================
PERSONAL_TARGET_MARKET = "한국 국내 시장 — 안전관리자·구매팀·운수·건설·제조 의사결정자"
PERSONAL_VOICE = "김진호 (DA Tech BD 리더) 1인칭. '제가', '저는', '제가 만난 분이' 등. 회사를 대표하지 않는 개인 관점."

PERSONAL_SERIES = {
    "현장노트": {
        "label": "현장노트",
        "primary_lang": "ko",
        "goal_axis": "리드젠 (Lead Gen) — 직접 DM·미팅 유도",
        "audience": PERSONAL_TARGET_MARKET,
        "structure": "후킹(1~3줄) → 상황(4~6줄) → 시도와 실수(5~8줄, 중요) → 무엇이 달라졌나(4~6줄) → 다음에 시도한다면(3~4줄) + CTA",
        "tone": "현장 기록자 톤. 자랑·광고 X. 의외성·실패담을 앞에 배치.",
        "cta_default": "비슷한 상황이라면 DM 주세요. 30분 통화로 SOP 초안 같이 정리합니다.",
        "hashtags_ko": ["#현장노트", "#산업안전", "#음주측정", "#안전관리"],
        "hashtags_en": ["#FieldNote", "#WorkplaceAlcohol", "#OccupationalSafety", "#Korea"],
    },
    "산업 인사이트": {
        "label": "산업 인사이트",
        "primary_lang": "ko",
        "goal_axis": "디맨드젠 (Demand Gen) — 카테고리 인식 확장, 장기 신뢰",
        "audience": PERSONAL_TARGET_MARKET + " · 정책 관련자",
        "structure": "도입(데이터·통계 1줄) → 문제 정의 → 3가지 관점/사례 → 결론·전망 → 토론 유도 CTA",
        "tone": "데이터 기반. 단언보다 관점 제시. 1차 출처 인용 필수(KOSHA·고용노동부·통계청).",
        "cta_default": "여러분 현장에서는 어떻게 보시나요? 댓글로 의견 부탁드립니다.",
        "hashtags_ko": ["#산업안전", "#음주측정", "#안전관리법", "#KOSHA"],
        "hashtags_en": ["#OccupationalSafety", "#WorkplaceAlcohol", "#Regulation", "#Korea"],
    },
    "BD 노트": {
        "label": "BD 노트",
        "primary_lang": "ko",
        "goal_axis": "디맨드젠 (Demand Gen) — 신뢰·휴먼 터치",
        "audience": "동종 BD · 잠재 고객 · 산업 종사자",
        "structure": "관찰 1줄 → 짧은 일화 → 일반화된 교훈 1줄 → 가벼운 토론 유도",
        "tone": "솔직하고 가벼움. 자조적 유머 허용. 짧게.",
        "cta_default": "여러분 경험은 어떠셨나요? 비슷한 사례 있으면 댓글 부탁드립니다.",
        "hashtags_ko": ["#B2B영업", "#BD", "#음주측정기"],
        "hashtags_en": ["#B2BSales", "#BusinessDevelopment", "#FieldNotes"],
    },
}

# ===========================================================
# 회사 트랙 — 영어권 글로벌 시장, ALCOFIND 공식 화자
# 타겟 지역: 미국 · 호주 · 중동(GCC) · 인도 · 아세안 (유럽 제외)
# 출력 = 영문 먼저 + 한글 검수용 (한·영 병기)
# ===========================================================
COMPANY_TARGET_MARKET = (
    "English-speaking markets: United States, Australia, Middle East (GCC: UAE/Saudi/Qatar), "
    "India, ASEAN (Singapore, Malaysia, Thailand, Vietnam, Indonesia, Philippines). "
    "Europe is explicitly excluded from this track."
)
COMPANY_VOICE = (
    "ALCOFIND / DA Tech company voice — third-person 'ALCOFIND' or first-person plural 'we'. "
    "Never first-person singular 'I'. Avoid Korea-centric framing; treat Korea as one regional data point only."
)

COMPANY_SERIES = {
    "Industry Pulse": {
        "label": "Industry Pulse",
        "primary_lang": "en",
        "goal_axis": "Demand Gen — category education, long-term trust building in target markets",
        "audience": (
            "Distributors, OEM procurement, fleet EHS leads, occupational safety consultants in "
            "US · AU · Middle East (GCC) · India · ASEAN"
        ),
        "structure": (
            "TL;DR (3 bullets, ≤80 chars each) → The signal (regulation/ruling/market move with primary source) "
            "→ Why it matters across target regions → ALCOFIND's read (2–3 points, neutral analyst tone) "
            "→ What to watch next → Open invitation CTA"
        ),
        "tone": (
            "Neutral analyst. Cite primary sources (US DOT, OSHA, SAMHSA, Australia Safe Work, "
            "UAE MOHRE, Saudi HRSD, India DGFASLI, Singapore MOM, Malaysia DOSH, etc.). "
            "No product pitch. Calibrated language — never 'the best/only/revolutionary'."
        ),
        "cta_default": (
            "ALCOFIND publishes a quarterly alcohol-safety brief covering US, AU, GCC, India, and "
            "ASEAN. Reply or DM 'BRIEF' to be added to the distribution list."
        ),
        "hashtags_en": ["#WorkplaceAlcohol", "#FleetSafety", "#AlcoholTesting", "#OccupationalSafety", "#ALCOFIND"],
        "hashtags_ko": ["#ALCOFIND", "#글로벌시장", "#음주측정"],
    },
    "Company News": {
        "label": "Company News",
        "primary_lang": "en",
        "goal_axis": "Lead Gen — trigger distributor/OEM/partnership inbound from target markets",
        "audience": (
            "Existing & prospective distributors, OEM buyers, certification bodies, and EHS-tech "
            "procurement teams across US · AU · GCC · India · ASEAN"
        ),
        "structure": (
            "Headline fact (one line) → Context (why now, why this matters in target regions) "
            "→ Concrete impact (what changes for partners / customers / market) "
            "→ Next step or DM-friendly CTA"
        ),
        "tone": (
            "Press-release register adapted to LinkedIn. Short paragraphs. Substantiate claims with "
            "data, certifications (UL/FCC, RCM-AU, SASO, BIS, PSB-SG), named partners (when permitted), "
            "or independent validation. No marketing adjectives."
        ),
        "cta_default": (
            "Distribution, OEM, and partnership inquiries for US · AU · GCC · India · ASEAN: "
            "DM or visit alcofind.com. Press inquiries: press@alcofind.com."
        ),
        "hashtags_en": ["#ALCOFIND", "#DATech", "#BreathalyzerTechnology", "#SafetyTech", "#OEMPartner"],
        "hashtags_ko": ["#ALCOFIND", "#DATech", "#수출", "#OEM"],
    },
}

# 이미지 사이즈 옵션 (LinkedIn 친화적)
IMAGE_SIZES = {
    "정사각 (1080×1080) — 피드 최적": (1080, 1080),
    "가로 (1200×627) — 링크 카드형": (1200, 627),
}
