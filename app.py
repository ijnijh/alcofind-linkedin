"""ALCOFIND LinkedIn 작성앱 — 2단계 워크플로우.

Step 1) 주제 합의 — 방향성 입력 → Claude가 5개 후보 제시 → 사용자 선택/수정 → 확정
Step 2) 본문 + 이미지 자동 생성 — 제목 + 한·영 병기 본문 + 브랜드 이미지

운영:
  · 개인 (김진호, 한국어 먼저) 주 2회 — 화·목 09:00 — 한국 국내 시장
  · 회사 (ALCOFIND, 영문 먼저) 주 1회 — 수 10:00 KST — 미국·호주·중동·인도·아세안

두 트랙 모두 한·영 병기 출력. 두 축: 리드젠 + 디맨드젠.

실행: streamlit run app.py
"""
import json
import os
from datetime import datetime

import streamlit as st

from pathlib import Path

from config import (
    COMPANY_SERIES,
    COMPANY_TARGET_MARKET,
    DEFAULT_MODEL_LABEL,
    HISTORY_DIR,
    IMAGE_SIZES,
    MODELS,
    OUT_DIR,
    PERSONAL_SERIES,
    PERSONAL_TARGET_MARKET,
    ROOT,
)
from chat_refine import call_refine
from image_renderer import (
    render_hook_card,
    render_question_card,
    render_quote_card,
    render_split_card,
    render_stat_card,
)
from llm_client import (
    call_claude,
    compose_post,
    estimate_cost_krw,
    has_api_key,
    parse_response,
)
from prompt_builder import build_prompt
from topic_brainstorm import build_brainstorm_prompt, parse_brainstorm


st.set_page_config(
    page_title="ALCOFIND LinkedIn 작성앱",
    page_icon="🟢",
    layout="wide",
)


# ===================== 비밀번호 게이트 =====================
# 동작: APP_PASSWORD가 secrets/env에 설정되어 있으면 진입 시 비밀번호 요구.
# 둘 다 없으면 게이트 자체를 패스 (로컬 개발 시 편의).
def _get_app_password() -> str:
    """env > st.secrets 순으로 읽기."""
    p = (os.environ.get("APP_PASSWORD") or "").strip()
    if p:
        return p
    try:
        return (st.secrets.get("APP_PASSWORD") or "").strip()
    except Exception:
        return ""


def _password_gate() -> bool:
    """비밀번호 통과 여부. 통과 시 True 반환하며 화면 그대로, 미통과 시 입력 화면 표시 후 False."""
    pw = _get_app_password()
    if not pw:
        return True  # 비밀번호 설정 안 됨 — 게이트 없음 (로컬 개발용)

    if st.session_state.get("_auth_ok"):
        return True

    # 게이트 화면
    st.markdown("# 🔒 ALCOFIND LinkedIn 작성앱")
    st.caption("비공개 도구입니다. 비밀번호를 입력하세요.")
    with st.form("auth_form", clear_on_submit=False):
        attempt = st.text_input("비밀번호", type="password")
        ok = st.form_submit_button("진입", type="primary", use_container_width=True)
    if ok:
        if attempt == pw:
            st.session_state["_auth_ok"] = True
            st.rerun()
        else:
            st.error("비밀번호가 일치하지 않습니다.")
    return False


if not _password_gate():
    st.stop()


# ===================== 세션 상태 =====================
SS = st.session_state
SS.setdefault("api_key_session", "")
SS.setdefault("p_step", 1)  # 개인 트랙 현재 단계 (1=주제 / 2=생성)
SS.setdefault("c_step", 1)  # 회사 트랙 현재 단계
SS.setdefault("p_candidates", None)
SS.setdefault("c_candidates", None)
SS.setdefault("p_selected", None)  # 확정된 주제 dict
SS.setdefault("c_selected", None)
SS.setdefault("p_result", None)
SS.setdefault("c_result", None)


# ===================== 상단 =====================
st.title("ALCOFIND LinkedIn 작성앱")
st.caption(
    "Step 1 주제 합의 → Step 2 제목·본문·이미지 자동 생성. "
    "두 트랙 모두 한·영 병기 (개인=한글 먼저, 회사=영문 먼저). 리드젠 + 디맨드젠 두 축."
)


# ===================== 사이드바 =====================
with st.sidebar:
    st.markdown("### 🔑 Anthropic API")
    env_key_ok = has_api_key()
    session_key = SS.api_key_session
    if env_key_ok:
        st.success("✅ API 키 등록됨 (.env)")
        st.caption("다음 실행에서도 자동 로드됩니다 — 다시 입력할 필요 없음")
        effective_key = None
    elif session_key:
        st.success("✅ API 키 등록됨 (세션)")
        effective_key = session_key
    else:
        st.warning("⚠️ API 키 없음 — 한 번만 등록하면 끝")
        st.markdown(
            "**가장 빠른 방법**: 아래에 키를 붙여넣으면 `.env`에 자동 저장 → 다음부터는 묻지 않음."
        )
        key_in = st.text_input(
            "Anthropic API 키 (sk-ant-...)",
            type="password",
            key="api_key_paste",
            help="입력 즉시 .env에 저장됩니다. 한 번만 하면 영구.",
        )
        if key_in:
            k = key_in.strip()
            if k.startswith("sk-ant-api"):
                # .env 영구 저장 + 환경변수에도 즉시 반영
                env_path = ROOT / ".env"
                env_path.write_text(
                    f"ANTHROPIC_API_KEY={k}\n", encoding="utf-8"
                )
                import os as _os
                _os.environ["ANTHROPIC_API_KEY"] = k
                SS.api_key_session = k
                st.success("✅ .env에 영구 저장됨 — 다음부터 자동 로드")
                st.rerun()
            else:
                st.error("키는 'sk-ant-api'로 시작해야 합니다.")
        with st.expander("다른 방법: 바탕화면 아이콘"):
            st.caption(
                "키를 클립보드에 복사한 후, 바탕화면 "
                "`ALCOFIND_LinkedIn_START.bat`을 더블클릭하면 "
                "자동으로 .env에 저장됩니다."
            )
        effective_key = ""

    can_generate = env_key_ok or bool(SS.api_key_session)

    st.markdown("### 🤖 모델")
    model_label = st.selectbox(
        "본문 생성 모델",
        list(MODELS.keys()),
        index=list(MODELS.keys()).index(DEFAULT_MODEL_LABEL),
    )
    model_id = MODELS[model_label]
    st.caption(f"호출당 예상 비용: ₩{estimate_cost_krw(model_id):.0f}")

    st.markdown("---")
    st.markdown("### 🟢 운영 리듬")
    st.markdown(
        """
| 트랙 | 화자 | 빈도 | 슬롯 |
|---|---|---|---|
| 개인 | 김진호 1인칭 | 주 2 | 화·목 09:00 |
| 회사 | ALCOFIND 공식 | 주 1 | 수 10:00 KST |

**타겟 시장**
- 개인: 한국 국내
- 회사: US · AU · GCC · India · ASEAN

**두 축**: 리드젠 + 디맨드젠
**병기 순서**: 개인=한글 먼저 / 회사=영문 먼저
        """
    )
    st.markdown("---")
    st.caption(f"`{OUT_DIR}`\n`{HISTORY_DIR}`")


# ===================== Step 1: 주제 합의 =====================
def render_step1(track: str, series_dict: dict, key_prefix: str):
    """방향성 → 후보 5개 → 선택/수정 → 확정."""
    track_kr = "개인" if track == "personal" else "회사"

    col1, col2 = st.columns([1, 1])
    with col1:
        series_key = st.selectbox(
            "시리즈",
            list(series_dict.keys()),
            key=f"{key_prefix}_s1_series",
        )
        s = series_dict[series_key]
        st.caption(f"📌 {s['goal_axis']}")
        st.caption(f"👥 {s['audience']}")

    with col2:
        st.markdown(
            f"**타겟 시장**  \n{PERSONAL_TARGET_MARKET if track == 'personal' else COMPANY_TARGET_MARKET}"
        )

    direction = st.text_area(
        "방향성 / 키워드 / 최근 이슈 (자유 형식, 비워두면 시리즈 정체성대로 자유롭게 제안)",
        key=f"{key_prefix}_s1_dir",
        height=120,
        placeholder=(
            "예: 산안법 개정 흐름, 자율 도입 케이스, 데이터 무결성"
            if track == "personal"
            else "ex) US DOT 2024 update, ASEAN fleet adoption, GCC labor reform, India BIS certification trends"
        ),
    )
    avoid = st.text_input(
        "(선택) 피하고 싶은 각도 / 이미 다룬 주제",
        key=f"{key_prefix}_s1_avoid",
        placeholder="예: 지난 주에 다룬 토픽, 너무 일반적인 진단 등",
    )

    btn_col1, btn_col2 = st.columns([3, 1])
    with btn_col1:
        gen_topics = st.button(
            "💡 Step 1 — 주제 후보 5개 받기",
            type="primary",
            use_container_width=True,
            disabled=not can_generate,
            key=f"{key_prefix}_s1_gen",
        )
    with btn_col2:
        if SS[f"{key_prefix}_candidates"]:
            if st.button("🔄 다시 받기", key=f"{key_prefix}_s1_retry"):
                SS[f"{key_prefix}_candidates"] = None
                st.rerun()

    if gen_topics:
        prompt = build_brainstorm_prompt(track, series_key, direction, avoid or None)
        with st.spinner(f"Claude {model_label}이(가) 주제 5개 브레인스토밍 중... (8~15초)"):
            try:
                raw = call_claude(prompt, model=model_id, api_key=effective_key or None)
                parsed = parse_brainstorm(raw)
            except Exception as e:
                st.error(f"❌ 호출 실패: {e}")
                return
        if not parsed["candidates"]:
            st.error("후보 파싱 실패. 다시 시도해주세요.")
            with st.expander("원본 응답"):
                st.code(raw)
            return
        SS[f"{key_prefix}_candidates"] = {
            "series_key": series_key,
            "direction": direction,
            "raw": raw,
            "parsed": parsed,
        }
        st.rerun()

    # ---- 후보 표시 + 선택 ----
    cands_state = SS[f"{key_prefix}_candidates"]
    if cands_state:
        st.markdown("---")
        st.markdown("### 📚 주제 후보 5개 — 하나 선택하거나 수정하세요")
        if cands_state["parsed"]["selection_note"]:
            with st.expander("🧠 선정 노트 (5개를 왜 이렇게 골랐는지)"):
                st.write(cands_state["parsed"]["selection_note"])

        # 라디오 선택
        cand_list = cands_state["parsed"]["candidates"]
        labels = []
        for c in cand_list:
            axis_emoji = "🎯" if "리드" in c["axis"] else "📡"
            labels.append(f"#{c['idx']} {axis_emoji} {c['axis']} — {c['title']}")
        choice_idx = st.radio(
            "후보 선택",
            range(len(cand_list)),
            format_func=lambda i: labels[i],
            key=f"{key_prefix}_s1_choice",
        )
        chosen = cand_list[choice_idx]

        # === 라디오 선택이 바뀌면 수정 입력 필드를 새 후보 값으로 강제 리셋 ===
        prev_key = f"{key_prefix}_s1_prev_choice"
        edit_topic_key = f"{key_prefix}_s1_edit_topic"
        edit_insight_key = f"{key_prefix}_s1_edit_insight"
        if SS.get(prev_key, -1) != choice_idx:
            SS[edit_topic_key] = chosen["title"]
            SS[edit_insight_key] = chosen["insight"]
            SS[prev_key] = choice_idx

        # 카드 표시 — 현재 선택된 후보의 모든 정보
        with st.container(border=True):
            st.markdown(f"**📌 TITLE 안 (#{chosen['idx']})**  \n{chosen['title']}")
            st.markdown(f"**🎯 목적 축**  \n{chosen['axis']}")
            st.markdown(f"**💡 핵심 인사이트**  \n{chosen['insight']}")
            st.markdown(f"**🎣 후킹 안**  \n{chosen['hook']}")
            st.markdown(f"**👥 시장 핏**  \n{chosen['fit']}")

        st.markdown("##### 수정 (필요 시 — 그대로 두면 위 카드 값으로 진행)")
        # value 파라미터 없이 — session_state(위에서 리셋함)가 입력값을 결정
        edit_topic = st.text_input(
            "주제 / 제목",
            key=edit_topic_key,
        )
        edit_insight = st.text_area(
            "핵심 인사이트",
            key=edit_insight_key,
            height=80,
        )

        confirm = st.button(
            f"✅ #{chosen['idx']} 주제로 확정 → Step 2로 이동",
            type="primary",
            use_container_width=True,
            key=f"{key_prefix}_s1_confirm",
        )
        if confirm:
            SS[f"{key_prefix}_selected"] = {
                "series_key": cands_state["series_key"],
                "topic": (edit_topic or chosen["title"]).strip(),
                "insight": (edit_insight or chosen["insight"]).strip(),
                "hook_hint": chosen["hook"],
                "axis": chosen["axis"],
                "fit": chosen["fit"],
                "chosen_idx": chosen["idx"],
            }
            SS[f"{key_prefix}_step"] = 2
            st.rerun()


# ===================== Step 2: 생성 =====================
def render_step2(track: str, series_dict: dict, key_prefix: str):
    track_kr = "개인" if track == "personal" else "회사"
    selected = SS[f"{key_prefix}_selected"]
    if not selected:
        st.warning("Step 1에서 주제를 먼저 확정해주세요.")
        if st.button("← Step 1로", key=f"{key_prefix}_s2_back_empty"):
            SS[f"{key_prefix}_step"] = 1
            st.rerun()
        return

    series_key = selected["series_key"]
    s = series_dict[series_key]

    # === 상단 큰 돌아가기 버튼 ===
    nav1, nav2, nav3 = st.columns([1, 1, 1])
    with nav1:
        if st.button(
            "⬅️ Step 1로 돌아가기 (주제 다시 선택)",
            key=f"{key_prefix}_s2_back_top",
            use_container_width=True,
        ):
            SS[f"{key_prefix}_step"] = 1
            SS[f"{key_prefix}_result"] = None
            st.rerun()
    with nav2:
        if st.button(
            "🔄 같은 주제로 본문만 다시 생성",
            key=f"{key_prefix}_s2_regen",
            use_container_width=True,
            help="확정 주제는 그대로, 본문/이미지만 새 결과로",
        ):
            SS[f"{key_prefix}_result"] = None
            st.rerun()
    with nav3:
        if st.button(
            "🆕 처음부터 새로 (주제 후보도 새로 받기)",
            key=f"{key_prefix}_s2_fresh",
            use_container_width=True,
        ):
            SS[f"{key_prefix}_step"] = 1
            SS[f"{key_prefix}_selected"] = None
            SS[f"{key_prefix}_candidates"] = None
            SS[f"{key_prefix}_result"] = None
            st.rerun()

    st.markdown("---")

    # 확정 주제 요약 카드
    with st.container(border=True):
        st.markdown(f"#### 📌 {selected['topic']}")
        st.caption(f"🎯 {selected['axis']}  ·  시리즈: {s['label']}")
        st.markdown(f"**핵심 인사이트**  \n{selected['insight']}")

    st.markdown("##### 보강 입력 (선택)")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        anon_case = st.text_area(
            "익명화된 케이스 / 사실",
            key=f"{key_prefix}_s2_case",
            height=80,
            placeholder="예: 운수업 300대 fleet 검측 누락률 23%→4%",
        )
    with col_b:
        extra_facts = st.text_area(
            "추가 데이터 / 1차 출처",
            key=f"{key_prefix}_s2_facts",
            height=80,
            placeholder="예: KOSHA 2024, US DOT Part 40, Australia Safe Work 2025",
        )
    cta_override = st.text_input(
        "CTA 직접 지정 (비우면 시리즈 기본값)",
        key=f"{key_prefix}_s2_cta",
        placeholder=s["cta_default"][:60] + ("..." if len(s["cta_default"]) > 60 else ""),
    )

    st.markdown("##### 🖼️ 브랜드 이미지")
    icol1, icol2, icol3 = st.columns([1, 1, 1])
    with icol1:
        img_template = st.selectbox(
            "템플릿",
            [
                "Hook 카드 — 후킹 한 줄 + 강조 컬러",
                "Quote 카드 — 매거진 풍 인용",
                "Stat 카드 — 큰 숫자 + 도넛",
                "Split 카드 — 매거진 분할 (라벨+본문)",
                "Question 카드 — 거대 ? + 위트",
            ],
            key=f"{key_prefix}_s2_imgtype",
        )
    with icol2:
        img_size_label = st.selectbox(
            "사이즈",
            list(IMAGE_SIZES.keys()),
            key=f"{key_prefix}_s2_imgsize",
        )
    with icol3:
        img_series_tag = st.text_input(
            "시리즈 태그",
            value=s["label"],
            key=f"{key_prefix}_s2_imgtag",
        )
    img_size = IMAGE_SIZES[img_size_label]

    # 입력 변수 초기화
    img_hook_override = quote_attr = stat_text = stat_caption = stat_source = ""
    split_label = split_statement = question_q = question_a = ""

    if img_template.startswith("Hook"):
        img_hook_override = st.text_input(
            "이미지 후킹 직접 입력 (비우면 LLM IMAGE_HOOK 자동 사용)",
            key=f"{key_prefix}_s2_imghook",
            help='따옴표 안 단어("...")는 자동으로 옐로우 강조됩니다.',
        )
    elif img_template.startswith("Quote"):
        img_hook_override = st.text_input(
            "인용문 (비우면 IMAGE_HOOK 자동 사용)",
            key=f"{key_prefix}_s2_imghook",
        )
        quote_attr = st.text_input(
            "화자",
            value="현장 안전관리자" if track == "personal" else "On-site safety manager",
            key=f"{key_prefix}_s2_qattr",
        )
    elif img_template.startswith("Stat"):
        stat_text = st.text_input("핵심 숫자", key=f"{key_prefix}_s2_stat", placeholder="예: 23%")
        stat_caption = st.text_area("숫자 설명", key=f"{key_prefix}_s2_statcap", height=60)
        stat_source = st.text_input("출처", key=f"{key_prefix}_s2_statsrc")
    elif img_template.startswith("Split"):
        split_label = st.text_input(
            "좌측 라벨 (짧게, 1~3 단어)",
            key=f"{key_prefix}_s2_splitlabel",
            value="INDUSTRY PULSE" if track == "company" else "FIELD NOTE",
        )
        split_statement = st.text_area(
            "우측 본문 (한 줄 강한 선언, 비우면 IMAGE_HOOK 자동 사용)",
            key=f"{key_prefix}_s2_splitstate",
            height=80,
        )
    else:  # Question
        question_q = st.text_area(
            "질문 (비우면 IMAGE_HOOK 자동 사용)",
            key=f"{key_prefix}_s2_qq",
            height=60,
        )
        question_a = st.text_area(
            "마이크로 답 (선택)",
            key=f"{key_prefix}_s2_qa",
            height=60,
            placeholder="예: 핵심 답을 한두 줄로",
        )

    author_line = "김진호 / DA Tech BD 리더" if track == "personal" else ""

    st.markdown("---")
    gen = st.button(
        f"✨ Step 2 — 제목 + 본문 + 이미지 자동 생성",
        type="primary",
        use_container_width=True,
        disabled=not can_generate,
        key=f"{key_prefix}_s2_gen",
    )

    if gen:
        prompt = build_prompt(
            track=track,
            series_key=series_key,
            topic=selected["topic"],
            key_insight=selected["insight"],
            cta_override=cta_override or None,
            anonymized_case=anon_case or None,
            extra_facts=extra_facts or None,
            goal_axis=selected["axis"],
        )
        with st.spinner(f"Claude {model_label}이(가) 본문 생성 중... (8~20초)"):
            try:
                raw = call_claude(prompt, model=model_id, api_key=effective_key or None)
                sections = parse_response(raw)
                composed = compose_post(sections, s["primary_lang"])
            except Exception as e:
                st.error(f"❌ 호출 실패: {e}")
                return
        if not composed["post"]:
            st.error("응답 파싱 실패. 원본 응답을 확인하세요.")
            with st.expander("원본 응답"):
                st.code(raw)
            return

        img_bytes = _render_chosen_image(
            img_template=img_template,
            composed=composed,
            selected=selected,
            series_label=s["label"],
            img_series_tag=img_series_tag,
            author_line=author_line,
            img_size=img_size,
            img_hook_override=img_hook_override,
            quote_attr=quote_attr,
            stat_text=stat_text,
            stat_caption=stat_caption,
            stat_source=stat_source,
            split_label=split_label,
            split_statement=split_statement,
            question_q=question_q,
            question_a=question_a,
        )

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_filename = f"{ts}_{track_kr}_{series_key.replace(' ', '').replace('/', '')}.png"
        (OUT_DIR / img_filename).write_bytes(img_bytes)

        history_entry = {
            "timestamp": ts,
            "track": track,
            "track_kr": track_kr,
            "series": series_key,
            "primary_lang": s["primary_lang"],
            "model": model_id,
            "selected_topic": selected,
            "extras": {"case": anon_case, "facts": extra_facts, "cta": cta_override},
            "image_template": img_template,
            "image_file": img_filename,
            "brainstorm_prompt": (SS[f"{key_prefix}_candidates"] or {}).get("raw", ""),
            "post_prompt": prompt,
            "raw_response": raw,
            "composed": composed,
        }
        (HISTORY_DIR / f"{ts}_{track_kr}.json").write_text(
            json.dumps(history_entry, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        SS[f"{key_prefix}_result"] = {
            "composed": composed,
            "img_bytes": img_bytes,
            "img_filename": img_filename,
            "primary_lang": s["primary_lang"],
            "raw": raw,
            "original_prompt": prompt,
            "chat_history": [],   # [(user_request, assistant_raw), ...]
            "image_args": {
                "img_template": img_template,
                "series_label": s["label"],
                "img_series_tag": img_series_tag,
                "author_line": author_line,
                "img_size": img_size,
                "img_hook_override": img_hook_override,
                "quote_attr": quote_attr,
                "stat_text": stat_text,
                "stat_caption": stat_caption,
                "stat_source": stat_source,
                "split_label": split_label,
                "split_statement": split_statement,
                "question_q": question_q,
                "question_a": question_a,
            },
            "selected": selected,
            "track": track,
            "series_key": series_key,
            "model_id": model_id,
            "effective_key": effective_key,
        }

    # ---- 결과 표시 ----
    result = SS[f"{key_prefix}_result"]
    if result:
        st.markdown("---")
        st.success(f"✅ 생성 완료 — `{result['img_filename']}`")
        _render_result(result)


def _render_chosen_image(
    img_template: str,
    composed: dict,
    selected: dict,
    series_label: str,
    img_series_tag: str,
    author_line: str,
    img_size,
    img_hook_override: str = "",
    quote_attr: str = "",
    stat_text: str = "",
    stat_caption: str = "",
    stat_source: str = "",
    split_label: str = "",
    split_statement: str = "",
    question_q: str = "",
    question_a: str = "",
) -> bytes:
    """선택된 템플릿으로 이미지 바이트 반환."""
    auto_hook = composed.get("image_hook") if composed else ""
    topic = selected.get("topic", "")

    if img_template.startswith("Hook"):
        hook = (img_hook_override or auto_hook or topic)[:100]
        return render_hook_card(
            hook,
            series_tag=img_series_tag or series_label,
            author=author_line,
            size=img_size,
        )
    if img_template.startswith("Quote"):
        quote = img_hook_override or auto_hook or topic
        return render_quote_card(
            quote,
            attribution=quote_attr or "현장",
            size=img_size,
        )
    if img_template.startswith("Stat"):
        return render_stat_card(
            stat_text or "?",
            stat_caption or topic,
            source=stat_source,
            size=img_size,
        )
    if img_template.startswith("Split"):
        return render_split_card(
            split_label or (img_series_tag or series_label).upper(),
            split_statement or auto_hook or topic,
            size=img_size,
        )
    # Question
    return render_question_card(
        question_q or auto_hook or topic,
        micro_answer=question_a,
        size=img_size,
    )


def _render_result(result: dict):
    composed = result["composed"]
    primary_lang = result["primary_lang"]
    img_bytes = result["img_bytes"]

    # 1) 제목
    st.markdown("### 📌 TITLE (게시용 헤드라인)")
    st.success(composed["title_post"])
    if composed["title_ref"]:
        st.caption(f"참고 번역: {composed['title_ref']}")

    # 2) 본문 — PRIMARY 먼저, SECONDARY는 탭
    st.markdown("### 📝 본문")
    primary_label = "🇰🇷 한국어 (게시용)" if primary_lang == "ko" else "🇬🇧 English (게시용)"
    secondary_label = "🇬🇧 English 참고" if primary_lang == "ko" else "🇰🇷 한국어 검수용"

    tab1, tab2 = st.tabs([primary_label, secondary_label])
    with tab1:
        st.text_area(
            "복사해서 LinkedIn에 붙여넣기",
            value=composed["post"],
            height=520,
            key="post_primary_out",
        )
        st.caption(f"분량: {len(composed['post'])}{'자' if primary_lang == 'ko' else ' chars'}")
    with tab2:
        st.text_area(
            "검수용 — 게시하지 마세요",
            value=composed["reference"],
            height=520,
            key="post_secondary_out",
        )

    # 🚨 사실 검증 체크리스트 — 게시 전 반드시 확인
    facts = composed.get("facts_to_verify", "").strip()
    if facts and facts not in ("(없음)", "(없음 — 모든 주장이 입력 출처에 근거)"):
        st.markdown("### 🚨 게시 전 검증 필요한 사실 주장")
        st.warning(
            "아래 항목은 본문에 사실로 단언된 주장입니다. "
            "**게시 전에 김진호 님이 1차 출처로 직접 확인**해주세요. "
            "할루시네이션 가능성이 있어 그대로 게시하면 신뢰도 타격 위험."
        )
        st.markdown(facts)
    elif facts:
        st.success("✅ 본문의 모든 사실 주장이 입력 출처에 근거합니다 (LLM 자체 판단)")

    if composed["intent_note"]:
        with st.expander("🧠 의도 노트 (검수용)"):
            st.write(composed["intent_note"])

    # 3) 이미지
    st.markdown("### 🖼️ 브랜드 이미지")
    img_c1, img_c2 = st.columns([1, 1])
    with img_c1:
        st.image(img_bytes)
    with img_c2:
        st.download_button(
            "PNG 다운로드",
            data=img_bytes,
            file_name=result["img_filename"],
            mime="image/png",
            use_container_width=True,
        )
        st.caption(f"`{result['img_filename']}`")
        if composed["image_hook"]:
            st.caption(f"IMAGE_HOOK: `{composed['image_hook']}`")
        if composed["image_hook_ref"]:
            st.caption(f"참고: {composed['image_hook_ref']}")

    # 4) 원본 응답 (디버그)
    with st.expander("🔍 원본 LLM 응답 (디버그)"):
        st.code(result["raw"], language="markdown")

    # 5) 채팅 수정 — 자연어 요청으로 본문·이미지 다듬기
    _render_refine_chat(result)


def _render_refine_chat(result: dict):
    """결과 영역 하단에 채팅 인터페이스. 자연어 수정 요청 → 새 결과로 갱신."""
    st.markdown("---")
    st.markdown("### 💬 수정 요청 — 자연어로 자유롭게")
    st.caption(
        "본문이나 톤이 마음에 안 들면 여기서 수정 요청하세요. "
        "예: \"본문 첫 문단을 더 강하게, IID 단언은 빼고\" / \"CTA를 더 가볍게\" / "
        "\"제목을 위트있게\" / \"숫자 케이스를 한국 운수업 사례로 바꿔서\""
    )

    # 1) 채팅 히스토리 표시
    history = result.get("chat_history", []) or []
    for user_msg, _assistant in history:
        with st.chat_message("user"):
            st.markdown(user_msg)
        with st.chat_message("assistant"):
            st.markdown("✅ 본문·이미지 갱신됨 (위 결과 영역에 반영)")

    # 2) 입력 받기
    if "effective_key" not in result:
        st.warning("API 키가 결과 메타에 없어 수정 호출이 불가합니다.")
        return

    user_request = st.chat_input("수정 요청 입력 (Enter로 전송)")
    if not user_request:
        return

    with st.chat_message("user"):
        st.markdown(user_request)

    with st.spinner("Claude가 수정 반영 중... (8~20초)"):
        try:
            new_raw = call_refine(
                original_user_prompt=result["original_prompt"],
                prior_assistant_text=result["raw"],
                user_request=user_request,
                model=result["model_id"],
                api_key=result.get("effective_key") or None,
                additional_history=history,  # 이전 라운드 누적
            )
            new_sections = parse_response(new_raw)
            new_composed = compose_post(new_sections, result["primary_lang"])
        except Exception as e:
            st.error(f"❌ 호출 실패: {e}")
            return

    if not new_composed["post"]:
        st.error("새 응답 파싱 실패.")
        with st.expander("원본 응답"):
            st.code(new_raw)
        return

    # 이미지도 재렌더링 (같은 템플릿·설정으로, 새 IMAGE_HOOK 반영)
    img_args = result["image_args"]
    new_img_bytes = _render_chosen_image(
        img_template=img_args["img_template"],
        composed=new_composed,
        selected=result["selected"],
        series_label=img_args["series_label"],
        img_series_tag=img_args["img_series_tag"],
        author_line=img_args["author_line"],
        img_size=img_args["img_size"],
        img_hook_override=img_args["img_hook_override"],
        quote_attr=img_args["quote_attr"],
        stat_text=img_args["stat_text"],
        stat_caption=img_args["stat_caption"],
        stat_source=img_args["stat_source"],
        split_label=img_args["split_label"],
        split_statement=img_args["split_statement"],
        question_q=img_args["question_q"],
        question_a=img_args["question_a"],
    )

    # 새 이미지 파일 저장 (덮어쓰기 X — 새 timestamp)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    track_kr = "개인" if result["track"] == "personal" else "회사"
    series_key = result["series_key"]
    new_filename = f"{ts}_{track_kr}_{series_key.replace(' ', '').replace('/', '')}_refined.png"
    (OUT_DIR / new_filename).write_bytes(new_img_bytes)

    # 결과 + 채팅 히스토리 갱신
    result["composed"] = new_composed
    result["img_bytes"] = new_img_bytes
    result["img_filename"] = new_filename
    result["raw"] = new_raw
    history.append((user_request, new_raw))
    result["chat_history"] = history

    # 히스토리 JSON 별도 저장 (수정 라운드 기록)
    refine_log = {
        "timestamp": ts,
        "track": result["track"],
        "track_kr": track_kr,
        "series": series_key,
        "user_request": user_request,
        "round_number": len(history),
        "new_image_file": new_filename,
        "new_raw_response": new_raw,
        "new_composed": new_composed,
    }
    (HISTORY_DIR / f"{ts}_{track_kr}_refine.json").write_text(
        json.dumps(refine_log, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    st.success(f"✅ 라운드 {len(history)} 반영 완료 — 위 결과·이미지 갱신됨")
    st.rerun()


# ===================== 메인 탭 =====================
tab_p, tab_c, tab_h = st.tabs(
    ["🧑 개인 포스팅 (주 2 · 한글 먼저)", "🏢 회사 페이지 (주 1 · 영문 먼저)", "📜 히스토리"]
)


def _step_header(track_kr: str, key_prefix: str):
    """Step 1 / Step 2 인디케이터."""
    step = SS[f"{key_prefix}_step"]
    confirmed = SS[f"{key_prefix}_selected"]
    s1 = "✅ Step 1 주제 합의" if step == 2 or confirmed else "🟢 **Step 1** 주제 합의"
    s2 = "🟢 **Step 2** 본문·이미지 생성" if step == 2 else ("⏳ Step 2" if not confirmed else "🟡 Step 2")
    st.markdown(f"<small>{s1}  →  {s2}</small>", unsafe_allow_html=True)


with tab_p:
    st.markdown(
        "##### 🎯 목적: 한국 국내 인바운드 리드 · 김진호 1인칭 · 한국어 게시용 + 영문 보조"
    )
    _step_header("개인", "p")
    if SS["p_step"] == 1:
        render_step1("personal", PERSONAL_SERIES, "p")
    else:
        render_step2("personal", PERSONAL_SERIES, "p")

with tab_c:
    st.markdown(
        "##### 🎯 Goal: Inbound leads from **US · AU · GCC · India · ASEAN** (Europe excluded) · ALCOFIND voice · English-first with Korean reference"
    )
    _step_header("회사", "c")
    if SS["c_step"] == 1:
        render_step1("company", COMPANY_SERIES, "c")
    else:
        render_step2("company", COMPANY_SERIES, "c")

with tab_h:
    st.markdown("### 최근 생성 이력 (최신순)")
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)
    if not files:
        st.info("아직 생성된 포스트가 없습니다.")
    else:
        for f in files[:30]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            ts = data.get("timestamp", "")
            ts_pretty = (
                f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}"
                if len(ts) >= 13
                else ts
            )
            composed = data.get("composed", {}) or {}
            sel = data.get("selected_topic", {}) or {}
            title = composed.get("title_post") or sel.get("topic", "")
            header = (
                f"{ts_pretty}  ·  "
                f"{data.get('track_kr', '?')}  ·  "
                f"{data.get('series', '')}  ·  "
                f"{title[:60]}"
            )
            with st.expander(header):
                hc1, hc2 = st.columns([2, 1])
                with hc1:
                    if sel:
                        st.markdown(f"**확정 주제**: {sel.get('topic', '')}")
                        st.markdown(f"**축**: {sel.get('axis', '')}")
                        st.markdown(f"**인사이트**: {sel.get('insight', '')}")
                    if composed.get("post"):
                        st.markdown("**게시용 본문**:")
                        st.text(composed["post"])
                    if composed.get("reference"):
                        with st.expander("참고 본문 (검수용)"):
                            st.text(composed["reference"])
                with hc2:
                    img_path = OUT_DIR / data.get("image_file", "")
                    if img_path.exists():
                        st.image(str(img_path))
                        st.download_button(
                            "PNG 다시 받기",
                            data=img_path.read_bytes(),
                            file_name=img_path.name,
                            mime="image/png",
                            key=f"hist_dl_{ts}",
                        )
