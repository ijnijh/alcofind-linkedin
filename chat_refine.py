"""수정 요청 채팅 — 기존 결과를 사용자 자연어 요청으로 다듬는다.

호출 흐름:
  1) 사용자가 1차 [TITLE/HOOK/BODY/CTA/HASHTAGS/IMAGE_HOOK/...] 결과 받음
  2) 채팅창에 자연어 요청 입력 (예: "본문 첫 문단 더 강하게, IID 단언 표현 빼고")
  3) Claude에게 (system + 원래 prompt + 이전 응답 + 사용자 요청) 보냄
  4) 같은 마커 구조로 새 응답 받음 → 파싱 → 본문·이미지 갱신
  5) 라운드 누적 가능
"""
from __future__ import annotations

from textwrap import dedent

from llm_client import call_claude, parse_response
from prompt_builder import SYSTEM_NOTE


REFINE_INSTRUCTION = dedent("""
    아래는 김진호 님이 이전 응답에 대해 요청한 수정 사항입니다.
    같은 마커 구조([TITLE]·[HOOK]·[BODY]·[CTA]·[HASHTAGS]·[IMAGE_HOOK]·[FACTS_TO_VERIFY]·[INTENT_NOTE],
    또는 영문 트랙의 한·영 병기 마커)를 그대로 유지하면서 요청된 부분만 정확히 반영한 새 응답을 출력하세요.

    중요:
    · 사용자가 명시적으로 지목하지 않은 섹션은 가능한 한 이전 응답을 유지하세요 (불필요하게 다 바꾸지 마세요).
    · 분량·톤·CLAIM HYGIENE·해시태그·CTA 톤 등 시스템 원칙은 그대로 지킵니다.
    · [INTENT_NOTE]에는 이번 수정에서 무엇을 어떻게 바꿨는지 1~2줄로 설명하세요.
    · 마커 구조는 절대 깨지면 안 됩니다. 코드 펜스(```) 없이 마커만 출력해도 좋고, 펜스로 감싸도 됩니다.
""").strip()


def call_refine(
    original_user_prompt: str,
    prior_assistant_text: str,
    user_request: str,
    model: str = "claude-sonnet-4-6",
    api_key: str | None = None,
    additional_history: list[tuple[str, str]] | None = None,
) -> str:
    """수정 요청을 LLM에 보내고 새 응답을 받는다.

    additional_history: [(user_msg, assistant_resp), ...] 형식. 라운드가 누적된 경우.
    """
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError("anthropic 패키지가 필요합니다.") from e

    from llm_client import get_api_key
    effective = (api_key or "").strip() or get_api_key()
    client = Anthropic(api_key=effective) if effective else Anthropic()

    messages = [
        {"role": "user", "content": original_user_prompt},
        {"role": "assistant", "content": prior_assistant_text},
    ]
    if additional_history:
        for u, a in additional_history:
            messages.append({"role": "user", "content": u})
            messages.append({"role": "assistant", "content": a})

    refine_msg = REFINE_INSTRUCTION + "\n\n---\n\n## 김진호 님의 수정 요청\n\n" + user_request.strip()
    messages.append({"role": "user", "content": refine_msg})

    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_NOTE,
        messages=messages,
    )
    return "".join(b.text for b in resp.content if hasattr(b, "text"))


def parse_refined(text: str) -> dict[str, str]:
    """편의 래퍼 — llm_client.parse_response 그대로."""
    return parse_response(text)
