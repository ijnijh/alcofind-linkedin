"""ALCOFIND 브랜드 이미지 카드 렌더러 — 시각적 후킹 강화 버전.

5종 템플릿:
  · Bold Hook   — 큰 텍스트 + 강조 단어 컬러 + 도트 패턴 액센트
  · Editorial Quote — 매거진 풍 큰 따옴표 그래픽 + 화자 + 사선 액센트
  · Stat Spotlight — 큰 숫자 + 도넛 차트 모티프 + 화살표
  · Split Statement — 좌측 컬러 블록 라벨 + 우측 본문 (매거진 분할)
  · Big Question  — 큰 물음표 + 짧은 질문 + 작은 답 (위트·후킹용)
"""
from __future__ import annotations

import random
import re
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import BRAND, FONT_BOLD, FONT_REGULAR


def _font(size: int, bold: bool = True):
    """폰트 경로 안전 로드. 경로 비었거나 못 열면 PIL 기본 폰트 fallback (한글 깨질 수 있음)."""
    path = FONT_BOLD if bold else FONT_REGULAR
    if path:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


def _font_bold(size: int):
    """편의 함수 — bold 폰트 안전 로드."""
    return _font(size, bold=True)


def _font_regular(size: int):
    """편의 함수 — regular 폰트 안전 로드."""
    return _font(size, bold=False)


# ===================== Color helpers =====================
def _hex(c: str):
    return tuple(int(c.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))


P_PRIMARY   = _hex(BRAND["primary"])
P_SECONDARY = _hex(BRAND["secondary"])
P_ACCENT    = _hex(BRAND["accent"])
P_HIGHLIGHT = _hex(BRAND["highlight"])
P_ALERT     = _hex(BRAND["alert"])
P_COOL      = _hex(BRAND["cool"])
P_INK       = _hex(BRAND["ink"])
P_WHITE     = _hex(BRAND["white"])
P_MUTED     = _hex(BRAND["muted"])
P_PAPER     = _hex(BRAND["paper"])


# ===================== Text helpers =====================
def _wrap(text: str, font, draw, max_width: int):
    """한글·영문 혼용 줄바꿈."""
    out = []
    for para in text.split("\n"):
        if " " in para:
            words = para.split(" ")
            cur = ""
            for w in words:
                cand = (cur + " " + w).strip()
                if draw.textlength(cand, font=font) <= max_width:
                    cur = cand
                else:
                    if cur:
                        out.append(cur)
                    cur = w
            if cur:
                out.append(cur)
        else:
            cur = ""
            for ch in para:
                if draw.textlength(cur + ch, font=font) <= max_width:
                    cur += ch
                else:
                    if cur:
                        out.append(cur)
                    cur = ch
            if cur:
                out.append(cur)
    return out


def _fit_font(text, draw, max_w, max_h, max_size, bold=True, min_size=22, line_pad=14):
    size = max_size
    while size >= min_size:
        f = _font(size, bold=bold)
        lines = _wrap(text, f, draw, max_w)
        total = len(lines) * (size + line_pad)
        if total <= max_h:
            return f, lines, size, total
        size -= 4
    f = _font(min_size, bold=bold)
    lines = _wrap(text, f, draw, max_w)
    total = len(lines) * (min_size + line_pad)
    return f, lines, min_size, total


# ===================== Graphic helpers =====================
def _dot_pattern(draw, x, y, w, h, color, spacing=22, radius=2):
    for px in range(x, x + w, spacing):
        for py in range(y, y + h, spacing):
            draw.ellipse(
                [px - radius, py - radius, px + radius, py + radius], fill=color
            )


def _diagonal_stripes(draw, x, y, w, h, color, spacing=24, thickness=4):
    for i in range(-h, w + h, spacing):
        draw.line([(x + i, y + h), (x + i + h, y)], fill=color, width=thickness)


def _arrow(draw, x1, y1, x2, y2, color, thickness=10, head=22):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=thickness)
    # 화살촉 — 수평 화살표 가정
    if x2 >= x1:
        draw.polygon(
            [(x2, y2 - head), (x2 + head, y2), (x2, y2 + head)], fill=color
        )
    else:
        draw.polygon(
            [(x2, y2 - head), (x2 - head, y2), (x2, y2 + head)], fill=color
        )


def _donut(draw, cx, cy, r, color, ring_w=24, fill_pct=0.7):
    """도넛 — 외곽 원 + 안쪽 흰 원 + 일부 강조."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    inner_r = r - ring_w
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=P_WHITE)
    # 작은 강조 점 (도넛 위)
    angle = -90  # 12시 방향
    import math
    ax = cx + int(r * math.cos(math.radians(angle)))
    ay = cy + int(r * math.sin(math.radians(angle)))
    draw.ellipse([ax - 12, ay - 12, ax + 12, ay + 12], fill=P_HIGHLIGHT)


def _underline(draw, x, y, w, color, thickness=8):
    draw.rectangle([(x, y), (x + w, y + thickness)], fill=color)


def _highlight_word(draw, x, y, text, font, fg, bg):
    """단어 뒤에 사각형 액센트 + 글자."""
    tw = int(draw.textlength(text, font=font))
    th = font.size
    pad_x, pad_y = 8, 4
    draw.rectangle(
        [(x - pad_x, y - pad_y), (x + tw + pad_x, y + th + pad_y)],
        fill=bg,
    )
    draw.text((x, y), text, fill=fg, font=font)
    return tw


# 강조 단어 추출 — 따옴표 안 단어, 영문 대문자 단어, 숫자
HIGHLIGHT_PATTERNS = [
    r"['\"]([^'\"]+)['\"]",            # 따옴표 안
    r"\b(\d+(?:[\.,]\d+)?%?)",          # 숫자(±%)
    r"\b([A-Z]{2,}[A-Z0-9-]*)\b",       # 대문자 약어 (DOT, SAMHSA 등)
]


def _find_highlights(text: str):
    """텍스트에서 강조할 토큰(span) 목록."""
    spans = []
    for pat in HIGHLIGHT_PATTERNS:
        for m in re.finditer(pat, text):
            spans.append((m.start(), m.end()))
    # 중복 제거
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s < merged[-1][1]:
            continue
        merged.append((s, e))
    return merged


def _draw_text_with_emphasis(draw, x, y, text, font, base_color, accent_color):
    """한 줄 텍스트에서 강조 토큰만 색을 다르게 칠해서 그린다."""
    spans = _find_highlights(text)
    cursor = 0
    cx = x
    for s, e in spans:
        # 일반 부분
        if cursor < s:
            chunk = text[cursor:s]
            draw.text((cx, y), chunk, fill=base_color, font=font)
            cx += int(draw.textlength(chunk, font=font))
        # 강조 부분
        token = text[s:e]
        draw.text((cx, y), token, fill=accent_color, font=font)
        cx += int(draw.textlength(token, font=font))
        cursor = e
    if cursor < len(text):
        chunk = text[cursor:]
        draw.text((cx, y), chunk, fill=base_color, font=font)


# ===================== Template 1: Bold Hook =====================
def render_hook_card(
    hook_text: str,
    series_tag: str = "Field Note",
    brand_line: str = "DA Tech · ALCOFIND",
    author: str = "",
    size=(1080, 1080),
) -> bytes:
    W, H = size
    img = Image.new("RGB", size, P_PRIMARY)
    d = ImageDraw.Draw(img)

    # 배경 그래픽 — 우측 하단 도트 패턴 + 좌측 상단 사선 코너
    _dot_pattern(d, W - 380, H - 380, 360, 360, P_SECONDARY, spacing=26, radius=3)
    # 좌상단 사선 액센트 블록
    d.polygon([(0, 0), (160, 0), (0, 160)], fill=P_HIGHLIGHT)
    # 우상단 작은 액센트 블록
    d.rectangle([(W - 60, 0), (W, 60)], fill=P_ACCENT)

    # 시리즈 태그 (상단) + underline
    tag_font = _font_bold(30)
    d.text((80, 100), series_tag.upper(), fill=P_HIGHLIGHT, font=tag_font)
    tag_w = d.textlength(series_tag.upper(), font=tag_font)
    _underline(d, 80, 140, int(tag_w), P_HIGHLIGHT, thickness=4)

    # Hook — 강조 단어 컬러 처리하면서 fit
    margin_x = 80
    avail_w = W - margin_x * 2 - 40
    avail_h = H - 400
    font, lines, fsize, total_h = _fit_font(
        hook_text, d, avail_w, avail_h,
        max_size=86, bold=True, min_size=38, line_pad=16,
    )
    y = (H - total_h) // 2 - 20
    for ln in lines:
        _draw_text_with_emphasis(d, margin_x, y, ln, font, P_WHITE, P_HIGHLIGHT)
        y += fsize + 16

    # 하단 브랜드 라인
    foot_b = _font_bold(28)
    foot_r = _font_regular(24)
    if author.strip():
        d.text((80, H - 130), brand_line, fill=P_ACCENT, font=foot_b)
        d.text((80, H - 90), author, fill=P_WHITE, font=foot_r)
    else:
        d.text((80, H - 110), brand_line, fill=P_ACCENT, font=foot_b)
    # 하단 액센트 라인
    _underline(d, 80, H - 50, 120, P_HIGHLIGHT, thickness=6)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ===================== Template 2: Editorial Quote =====================
def render_quote_card(
    quote: str,
    attribution: str = "현장 안전관리자",
    brand_line: str = "DA Tech · ALCOFIND",
    size=(1080, 1080),
) -> bytes:
    W, H = size
    img = Image.new("RGB", size, P_PAPER)
    d = ImageDraw.Draw(img)

    # 상단 굵은 컬러 바 (다크그린)
    d.rectangle([(0, 0), (W, 22)], fill=P_PRIMARY)
    # 하단 가는 라인 + 옐로우 액센트
    d.rectangle([(0, H - 10), (W, H)], fill=P_PRIMARY)
    d.rectangle([(0, H - 10), (W // 3, H)], fill=P_HIGHLIGHT)

    # 큰 따옴표 그래픽 — 두 개의 굵은 점 + 디자인된 quote
    qx, qy = 70, 80
    qsize = 80
    d.ellipse([qx, qy, qx + qsize, qy + qsize], fill=P_PRIMARY)
    d.ellipse([qx + qsize + 24, qy, qx + 2 * qsize + 24, qy + qsize], fill=P_PRIMARY)
    # 점 내부에 흰 작은 점 (꼬리)
    d.polygon(
        [
            (qx + qsize // 2, qy + qsize),
            (qx + qsize // 2 - 14, qy + qsize + 32),
            (qx + qsize // 2 + 14, qy + qsize + 4),
        ],
        fill=P_PRIMARY,
    )
    d.polygon(
        [
            (qx + qsize + 24 + qsize // 2, qy + qsize),
            (qx + qsize + 24 + qsize // 2 - 14, qy + qsize + 32),
            (qx + qsize + 24 + qsize // 2 + 14, qy + qsize + 4),
        ],
        fill=P_PRIMARY,
    )

    # 인용문 — 강조 단어 컬러
    margin_x = 90
    avail_w = W - margin_x * 2
    avail_h = H - 460
    font, lines, fsize, total_h = _fit_font(
        quote, d, avail_w, avail_h,
        max_size=66, bold=True, min_size=30, line_pad=16,
    )
    y = 280
    for ln in lines:
        _draw_text_with_emphasis(d, margin_x, y, ln, font, P_INK, P_ALERT)
        y += fsize + 16

    # 화자 — 좌측에 짧은 다크그린 라인 + 텍스트
    attr_font = _font_bold(30)
    _underline(d, margin_x, H - 140, 56, P_PRIMARY, thickness=4)
    d.text((margin_x + 72, H - 155), attribution, fill=P_PRIMARY, font=attr_font)

    # 브랜드 라인 — 우측 하단
    brand_f = _font_bold(22)
    bw = d.textlength(brand_line, font=brand_f)
    d.text((W - bw - 80, H - 70), brand_line, fill=P_MUTED, font=brand_f)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ===================== Template 3: Stat Spotlight =====================
def render_stat_card(
    stat: str,
    caption: str,
    source: str = "",
    brand_line: str = "DA Tech · ALCOFIND",
    size=(1080, 1080),
) -> bytes:
    W, H = size
    img = Image.new("RGB", size, P_WHITE)
    d = ImageDraw.Draw(img)

    # 배경 좌측에 큰 도넛 모티프 (희미하게)
    _donut(d, cx=180, cy=180, r=140, color=P_HIGHLIGHT, ring_w=28)

    # 우측 상단 작은 작은 도트 클러스터
    _dot_pattern(d, W - 240, 60, 180, 140, P_SECONDARY, spacing=24, radius=3)

    # 상하단 브랜드 바
    d.rectangle([(0, 0), (W, 14)], fill=P_PRIMARY)
    d.rectangle([(0, H - 14), (W, H)], fill=P_PRIMARY)

    # Stat — 거대 폰트, primary 컬러
    stat_size = 280
    if len(stat) > 5:
        stat_size = 220
    if len(stat) > 8:
        stat_size = 160
    if len(stat) > 12:
        stat_size = 120
    sf = _font_bold(stat_size)
    bbox = d.textbbox((0, 0), stat, font=sf)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    ink_center_y = int(H * 0.38)
    draw_x = (W - text_w) // 2 - bbox[0]
    draw_y = ink_center_y - text_h // 2 - bbox[1]
    # 그림자 효과 (살짝 옅게)
    d.text((draw_x + 6, draw_y + 6), stat, fill=P_ACCENT, font=sf)
    d.text((draw_x, draw_y), stat, fill=P_PRIMARY, font=sf)
    stat_bottom = draw_y + bbox[3]

    # 화살표 액센트 — 숫자 아래
    arrow_y = stat_bottom + 40
    _arrow(d, W // 2 - 60, arrow_y, W // 2 + 60, arrow_y, P_ALERT, thickness=10, head=22)

    # Caption
    margin_x = 100
    avail_w = W - margin_x * 2
    cap_font, cap_lines, cap_fsize, cap_total = _fit_font(
        caption, d, avail_w, 240,
        max_size=44, bold=True, min_size=22, line_pad=10,
    )
    y = arrow_y + 80
    for ln in cap_lines:
        lw = d.textlength(ln, font=cap_font)
        _draw_text_with_emphasis(
            d, (W - int(lw)) // 2, y, ln, cap_font, P_INK, P_ALERT
        )
        y += cap_fsize + 10

    # 출처
    if source:
        srcf = _font_regular(22)
        txt = f"source · {source}" if all(ord(c) < 128 for c in source) else f"출처 · {source}"
        sw = d.textlength(txt, font=srcf)
        d.text(((W - int(sw)) // 2, H - 90), txt, fill=P_MUTED, font=srcf)

    # 브랜드
    bf = _font_bold(22)
    bw = d.textlength(brand_line, font=bf)
    d.text(((W - int(bw)) // 2, H - 55), brand_line, fill=P_PRIMARY, font=bf)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ===================== Template 4: Split Statement =====================
def render_split_card(
    label: str,
    statement: str,
    brand_line: str = "DA Tech · ALCOFIND",
    size=(1080, 1080),
) -> bytes:
    """좌측 컬러 블록(짧은 라벨/태그) + 우측 본문(메시지). 매거진 분할."""
    W, H = size
    img = Image.new("RGB", size, P_WHITE)
    d = ImageDraw.Draw(img)

    # 좌측 컬러 블록 — 다크그린
    LEFT_W = int(W * 0.36)
    d.rectangle([(0, 0), (LEFT_W, H)], fill=P_PRIMARY)
    # 그 위에 옐로우 코너
    d.polygon([(0, 0), (90, 0), (0, 90)], fill=P_HIGHLIGHT)
    # 좌측에 사선 패턴 (희미하게)
    _diagonal_stripes(d, 0, H - 280, LEFT_W, 280, P_SECONDARY, spacing=28, thickness=3)

    # 라벨 — 회전된 큰 텍스트는 PIL 복잡, 그냥 큰 텍스트 + 줄바꿈
    lf, lab_lines, lab_size, lab_total = _fit_font(
        label, d, LEFT_W - 80, H - 320,
        max_size=72, bold=True, min_size=32, line_pad=10,
    )
    ly = (H - lab_total) // 2
    for ln in lab_lines:
        d.text((40, ly), ln, fill=P_HIGHLIGHT, font=lf)
        ly += lab_size + 10
    # 좌측 하단 작은 underline
    _underline(d, 40, H - 80, 80, P_HIGHLIGHT, thickness=6)

    # 우측 본문 영역
    RIGHT_X = LEFT_W + 60
    right_w = W - RIGHT_X - 60
    sf, st_lines, st_size, st_total = _fit_font(
        statement, d, right_w, H - 280,
        max_size=58, bold=True, min_size=28, line_pad=14,
    )
    sy = (H - st_total) // 2 - 20
    for ln in st_lines:
        _draw_text_with_emphasis(d, RIGHT_X, sy, ln, sf, P_INK, P_PRIMARY)
        sy += st_size + 14

    # 우측 하단 브랜드 + 액센트
    _underline(d, RIGHT_X, H - 100, 60, P_PRIMARY, thickness=6)
    bf = _font_bold(24)
    d.text((RIGHT_X, H - 80), brand_line, fill=P_PRIMARY, font=bf)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ===================== Template 5: Big Question =====================
def render_question_card(
    question: str,
    micro_answer: str = "",
    brand_line: str = "DA Tech · ALCOFIND",
    size=(1080, 1080),
) -> bytes:
    """큰 물음표 + 짧은 질문 + (선택) 작은 답. 위트·후킹용."""
    W, H = size
    img = Image.new("RGB", size, P_ACCENT)
    d = ImageDraw.Draw(img)

    # 배경 — 우측에 거대한 ? 그래픽
    qmf = _font_bold(720)
    qm_text = "?"
    qm_bbox = d.textbbox((0, 0), qm_text, font=qmf)
    qm_w = qm_bbox[2] - qm_bbox[0]
    qm_h = qm_bbox[3] - qm_bbox[1]
    # 우측 가장자리 살짝 잘리도록 배치
    d.text(
        (W - qm_w + 40 - qm_bbox[0], (H - qm_h) // 2 - 40 - qm_bbox[1]),
        qm_text,
        fill=P_HIGHLIGHT,
        font=qmf,
    )

    # 좌상단 라벨
    tag_font = _font_bold(26)
    d.text((70, 80), "ALCOFIND · INDUSTRY PULSE", fill=P_PRIMARY, font=tag_font)
    _underline(d, 70, 116, 100, P_PRIMARY, thickness=4)

    # 질문 — 좌측 상단 강조
    qf, q_lines, q_size, q_total = _fit_font(
        question, d, int(W * 0.62), 420,
        max_size=78, bold=True, min_size=34, line_pad=14,
    )
    y = 200
    for ln in q_lines:
        _draw_text_with_emphasis(d, 70, y, ln, qf, P_INK, P_ALERT)
        y += q_size + 14

    # 마이크로 답 — 작은 박스
    if micro_answer:
        ans_box_y = max(y + 40, int(H * 0.66))
        af_size = 30
        af = _font_regular(af_size)
        a_lines = _wrap(micro_answer, af, d, int(W * 0.58))
        box_h = len(a_lines) * (af_size + 8) + 36
        d.rectangle([(60, ans_box_y), (60 + int(W * 0.6), ans_box_y + box_h)], fill=P_WHITE)
        # 좌측 박스에 컬러 라인
        d.rectangle([(60, ans_box_y), (68, ans_box_y + box_h)], fill=P_PRIMARY)
        ay = ans_box_y + 18
        for ln in a_lines:
            d.text((86, ay), ln, fill=P_INK, font=af)
            ay += af_size + 8

    # 브랜드 라인 하단
    bf = _font_bold(26)
    d.text((70, H - 90), brand_line, fill=P_PRIMARY, font=bf)
    _underline(d, 70, H - 52, 60, P_HIGHLIGHT, thickness=6)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ===================== Template 6: Photo Hook (Unsplash 사진 + 오버레이) =====================
def render_photo_hook_card(
    hook_text: str,
    photo: Image.Image,
    series_tag: str = "Field Note",
    brand_line: str = "DA Tech · ALCOFIND",
    author: str = "",
    photo_credit: str = "",
    size=(1080, 1080),
) -> bytes:
    """실제 사진(Unsplash) + 그라데이션 + 후킹 텍스트 오버레이.

    photo: PIL Image (Unsplash에서 다운받은 것)
    photo_credit: 크레딧 줄 (예: "Photo by Hanson Lu on Unsplash")
    """
    W, H = size
    # 1) 사진을 W×H로 cover crop (비율 유지, 잘림)
    pw, ph = photo.size
    scale = max(W / pw, H / ph)
    new_size = (int(pw * scale), int(ph * scale))
    photo = photo.resize(new_size, Image.LANCZOS)
    px = (new_size[0] - W) // 2
    py = (new_size[1] - H) // 2
    img = photo.crop((px, py, px + W, py + H))

    d = ImageDraw.Draw(img, "RGBA")

    # 2) 어두운 그라데이션 — 상단 가벼움, 하단 강하게 (가독성)
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    # 상단 60%는 살짝, 하단 40%는 진하게
    for y in range(H):
        if y < H * 0.4:
            alpha = int(60 * (1 - y / (H * 0.4)))  # 상단 살짝
        elif y < H * 0.6:
            alpha = 40
        else:
            t = (y - H * 0.6) / (H * 0.4)
            alpha = int(40 + 200 * t)  # 하단 진하게
        gd.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), grad)
    d = ImageDraw.Draw(img, "RGBA")

    # 3) 상단 좌측에 시리즈 태그 (배경 박스)
    tag_font = _font_bold(28)
    tag_text = series_tag.upper()
    tw = int(d.textlength(tag_text, font=tag_font))
    th = 36
    d.rectangle([(60, 60), (60 + tw + 28, 60 + th + 16)], fill=P_PRIMARY)
    # 우측에 옐로우 액센트 막대
    d.rectangle([(60 + tw + 28, 60), (60 + tw + 38, 60 + th + 16)], fill=P_HIGHLIGHT)
    d.text((74, 68), tag_text, fill=P_HIGHLIGHT, font=tag_font)

    # 4) Hook — 화면 하단 30~70% 영역에 큰 텍스트 + 강조
    margin_x = 80
    avail_w = W - margin_x * 2 - 20
    avail_h = int(H * 0.42)
    font, lines, fsize, total_h = _fit_font(
        hook_text, d, avail_w, avail_h,
        max_size=84, bold=True, min_size=42, line_pad=14,
    )
    y = int(H * 0.58) - 20
    for ln in lines:
        _draw_text_with_emphasis(d, margin_x, y, ln, font, P_WHITE, P_HIGHLIGHT)
        y += fsize + 14

    # 5) 하단 브랜드 + 작성자
    foot_b = _font_bold(26)
    foot_r = _font_regular(22)
    if author.strip():
        d.text((80, H - 130), brand_line, fill=P_ACCENT, font=foot_b)
        d.text((80, H - 95), author, fill=P_WHITE, font=foot_r)
    else:
        d.text((80, H - 110), brand_line, fill=P_ACCENT, font=foot_b)
    _underline(d, 80, H - 55, 80, P_HIGHLIGHT, thickness=6)

    # 6) Unsplash 크레딧 (작게, 우하단)
    if photo_credit:
        cr_font = _font_regular(14)
        cw = int(d.textlength(photo_credit, font=cr_font))
        d.text((W - cw - 20, H - 24), photo_credit, fill=(255, 255, 255, 200), font=cr_font)

    buf = BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


# ===================== Template 7: Photo Quote =====================
def render_photo_quote_card(
    quote: str,
    photo: Image.Image,
    attribution: str = "현장 안전관리자",
    brand_line: str = "DA Tech · ALCOFIND",
    photo_credit: str = "",
    size=(1080, 1080),
) -> bytes:
    """사진 위에 흰색 인용 박스 — 매거진 풍."""
    W, H = size
    pw, ph = photo.size
    scale = max(W / pw, H / ph)
    new_size = (int(pw * scale), int(ph * scale))
    photo = photo.resize(new_size, Image.LANCZOS)
    px = (new_size[0] - W) // 2
    py = (new_size[1] - H) // 2
    img = photo.crop((px, py, px + W, py + H)).convert("RGBA")

    # 살짝 어둡게
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 70))
    img = Image.alpha_composite(img, dark)
    d = ImageDraw.Draw(img, "RGBA")

    # 흰 인용 박스 (가운데, 폭 70%)
    box_w = int(W * 0.78)
    box_x = (W - box_w) // 2
    # 임시 박스 높이 측정용 폰트
    qf = _font_bold(54)
    lines = _wrap(quote, qf, d, box_w - 80)
    # 너무 길면 폰트 줄임
    while len(lines) > 6 and qf.size > 32:
        qf = _font_bold(qf.size - 4)
        lines = _wrap(quote, qf, d, box_w - 80)
    box_h = 140 + len(lines) * (qf.size + 14) + 100
    box_y = (H - box_h) // 2

    # 박스 + 그림자
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle([(box_x + 10, box_y + 14), (box_x + box_w + 10, box_y + box_h + 14)],
                 fill=(0, 0, 0, 80))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([(box_x, box_y), (box_x + box_w, box_y + box_h)], fill=P_WHITE)
    # 좌측 컬러 라인
    d.rectangle([(box_x, box_y), (box_x + 10, box_y + box_h)], fill=P_PRIMARY)

    # 큰 따옴표 그래픽
    q_big = _font_bold(120)
    d.text((box_x + 40, box_y + 10), '"', fill=P_PRIMARY, font=q_big)

    # 인용문
    y = box_y + 130
    for ln in lines:
        _draw_text_with_emphasis(d, box_x + 50, y, ln, qf, P_INK, P_ALERT)
        y += qf.size + 14

    # 화자
    attr_font = _font_bold(24)
    d.text((box_x + 50, box_y + box_h - 70), "— " + attribution, fill=P_PRIMARY, font=attr_font)

    # 하단 브랜드 (사진 위)
    brand_f = _font_bold(22)
    bw = int(d.textlength(brand_line, font=brand_f))
    d.text(((W - bw) // 2, H - 50), brand_line, fill=P_WHITE, font=brand_f)

    # 크레딧
    if photo_credit:
        cr_font = _font_regular(13)
        cw = int(d.textlength(photo_credit, font=cr_font))
        d.text((W - cw - 18, H - 22), photo_credit, fill=(255, 255, 255, 200), font=cr_font)

    buf = BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()
