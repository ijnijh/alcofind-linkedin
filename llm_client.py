"""Anthropic Claude API 호출 + 응답 파싱.

응답 형식 — prompt_builder가 강제하는 섹션 마커:
  한글 트랙: [TITLE] [HOOK] [BODY] [CTA] [HASHTAGS] [IMAGE_HOOK] [INTENT_NOTE]
  영문 트랙: [TITLE · EN] [TITLE · KO 참고] [HOOK · EN] [HOOK · KO 참고]
             [BODY · EN] [BODY · KO 참고] [CTA · EN] [CTA · KO 참고]
             [HASHTAGS] [IMAGE_HOOK · EN] [IMAGE_HOOK · KO 참고] [INTENT_NOTE]
"""
import os
import re
from typing import Optional

from prompt_builder import SYSTEM_NOTE


# [KEY] ~ 다음 [KEY] 또는 문자열 끝까지 (DOTALL로 줄바꿈 포함)
SECTION_RE = re.compile(
    r"\[([^\]\n]+)\]\s*\n(.*?)(?=\n\[[^\]\n]+\]|\Z)",
    re.DOTALL,
)


def _key_from_secrets() -> str:
    """Streamlit secrets에서 키 읽기 (배포 환경)."""
    try:
        import streamlit as st
        return (st.secrets.get("ANTHROPIC_API_KEY") or "").strip()
    except Exception:
        return ""


def get_api_key() -> str:
    """우선순위: env (.env로딩됨) → Streamlit secrets."""
    env = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if env:
        return env
    return _key_from_secrets()


def has_api_key() -> bool:
    return bool(get_api_key())


def call_claude(
    user_prompt: str,
    model: str = "claude-sonnet-4-6",
    api_key: Optional[str] = None,
    max_tokens: int = 4096,
) -> str:
    """Claude API 호출. api_key 명시되지 않으면 env → secrets 순으로 자동 탐색."""
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError("anthropic 패키지가 설치되지 않았습니다.") from e

    effective = (api_key or "").strip() or get_api_key()
    client = Anthropic(api_key=effective) if effective else Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_NOTE,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(
        block.text for block in resp.content if hasattr(block, "text")
    )
    return text


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl > 0:
            t = t[first_nl + 1 :]
    if t.rstrip().endswith("```"):
        t = t.rstrip()[:-3].rstrip()
    return t


def parse_response(text: str) -> dict[str, str]:
    """[KEY] 블록 추출. 키 트림, 값 트림."""
    text = _strip_code_fences(text)
    out: dict[str, str] = {}
    for m in SECTION_RE.finditer(text):
        out[m.group(1).strip()] = m.group(2).strip()
    return out


def compose_post(sections: dict[str, str], primary_lang: str) -> dict[str, str]:
    """파싱된 섹션을 (게시용·검수용·이미지·메타)로 묶어 반환.

    primary_lang: 'ko' (개인 트랙) 또는 'en' (회사 트랙)
    PRIMARY = 게시용, SECONDARY = 검수용
    섹션 마커는 prompt_builder의 정의와 정확히 일치해야 한다.
    """
    if primary_lang == "ko":
        # 개인 트랙 — 한국어 게시용 / 영문 참고
        primary_blocks = [
            sections.get("TITLE · KO", ""),
            sections.get("HOOK · KO", ""),
            sections.get("BODY · KO", ""),
            sections.get("CTA · KO", ""),
            sections.get("HASHTAGS · KO", ""),
        ]
        secondary_blocks = [
            sections.get("TITLE · EN 참고", ""),
            sections.get("HOOK · EN 참고", ""),
            sections.get("BODY · EN 참고", ""),
            sections.get("CTA · EN 참고", ""),
            sections.get("HASHTAGS · EN 참고", ""),
        ]
        return {
            "primary_lang": "ko",
            "secondary_lang": "en",
            "title_post": sections.get("TITLE · KO", ""),
            "title_ref": sections.get("TITLE · EN 참고", ""),
            "post": "\n\n".join(b for b in primary_blocks if b),
            "reference": "\n\n".join(b for b in secondary_blocks if b),
            "image_hook": sections.get("IMAGE_HOOK · KO", ""),
            "image_hook_ref": sections.get("IMAGE_HOOK · EN 참고", ""),
            "intent_note": sections.get("INTENT_NOTE", ""),
        }
    # 회사 트랙 — 영문 게시용 / 한국어 참고
    primary_blocks = [
        sections.get("TITLE · EN", ""),
        sections.get("HOOK · EN", ""),
        sections.get("BODY · EN", ""),
        sections.get("CTA · EN", ""),
        sections.get("HASHTAGS · EN", ""),
    ]
    secondary_blocks = [
        sections.get("TITLE · KO 참고", ""),
        sections.get("HOOK · KO 참고", ""),
        sections.get("BODY · KO 참고", ""),
        sections.get("CTA · KO 참고", ""),
        sections.get("HASHTAGS · KO 참고", ""),
    ]
    return {
        "primary_lang": "en",
        "secondary_lang": "ko",
        "title_post": sections.get("TITLE · EN", ""),
        "title_ref": sections.get("TITLE · KO 참고", ""),
        "post": "\n\n".join(b for b in primary_blocks if b),
        "reference": "\n\n".join(b for b in secondary_blocks if b),
        "image_hook": sections.get("IMAGE_HOOK · EN", ""),
        "image_hook_ref": sections.get("IMAGE_HOOK · KO 참고", ""),
        "intent_note": sections.get("INTENT_NOTE", ""),
        "facts_to_verify": sections.get("FACTS_TO_VERIFY", ""),
        "image_keywords": sections.get("IMAGE_KEYWORDS", ""),
    }


def estimate_cost_krw(model: str, est_in_tok: int = 2000, est_out_tok: int = 1500) -> float:
    """대략적인 호출 비용 (₩). 1 USD ≈ 1,380 KRW 가정. 실제 청구는 다를 수 있음."""
    rates = {
        # USD per 1M tokens (Anthropic 공식 가격 기반 추정)
        "claude-sonnet-4-6": (3.0, 15.0),
        "claude-haiku-4-5-20251001": (0.80, 4.0),
        "claude-opus-4-7": (15.0, 75.0),
    }
    rate = rates.get(model, (3.0, 15.0))
    usd = (est_in_tok / 1_000_000) * rate[0] + (est_out_tok / 1_000_000) * rate[1]
    return usd * 1380
