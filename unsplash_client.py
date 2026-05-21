"""Unsplash API 클라이언트 — 키워드로 무료 고품질 사진 검색·다운로드.

발급: https://unsplash.com/developers
무료 한도: 시간당 50회 (개발) → 신청 시 5000회/시간 (Production).
김진호 님 운영(주 3건)에는 충분.

키 설정 우선순위: 환경변수 > Streamlit Secrets > .env
키 이름: UNSPLASH_ACCESS_KEY
"""
from __future__ import annotations

import os
from io import BytesIO
from typing import Optional

import requests
from PIL import Image


def get_unsplash_key() -> str:
    """우선순위: env → Streamlit secrets."""
    k = (os.environ.get("UNSPLASH_ACCESS_KEY") or "").strip()
    if k:
        return k
    try:
        import streamlit as st
        return (st.secrets.get("UNSPLASH_ACCESS_KEY") or "").strip()
    except Exception:
        return ""


def has_unsplash_key() -> bool:
    return bool(get_unsplash_key())


def search_unsplash(
    query: str,
    orientation: str = "squarish",
    per_page: int = 10,
    timeout: int = 15,
) -> list[dict]:
    """Unsplash에서 키워드 검색. 결과 리스트(딕셔너리) 반환.

    orientation: 'landscape' | 'portrait' | 'squarish'
    """
    key = get_unsplash_key()
    if not key:
        raise RuntimeError(
            "UNSPLASH_ACCESS_KEY가 설정되지 않았습니다. "
            "https://unsplash.com/developers에서 발급 후 .env 또는 Streamlit Secrets에 추가하세요."
        )
    r = requests.get(
        "https://api.unsplash.com/search/photos",
        params={
            "query": query,
            "orientation": orientation,
            "per_page": per_page,
            "content_filter": "high",  # 산업·B2B 적합 필터
        },
        headers={
            "Authorization": f"Client-ID {key}",
            "Accept-Version": "v1",
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def download_photo(url: str, timeout: int = 30) -> Image.Image:
    """URL에서 사진 다운로드 → PIL Image."""
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return Image.open(BytesIO(r.content)).convert("RGB")


def trigger_download_ping(download_location: str) -> None:
    """Unsplash API 정책 준수 — 다운로드 사용 시 ping (rate에 영향 X)."""
    key = get_unsplash_key()
    if not key or not download_location:
        return
    try:
        requests.get(
            download_location,
            headers={"Authorization": f"Client-ID {key}"},
            timeout=5,
        )
    except Exception:
        pass


def get_photo_for_query(
    query: str,
    orientation: str = "squarish",
    index: int = 0,
) -> tuple[Image.Image, dict] | None:
    """편의 함수 — 키워드로 검색 → index번째 결과 다운로드.

    Returns: (PIL Image, photo metadata) or None if no results.
    metadata 안의 user.name·user.username·links.html은 크레딧 표시용.
    """
    results = search_unsplash(query, orientation=orientation, per_page=max(index + 1, 5))
    if not results:
        return None
    photo = results[min(index, len(results) - 1)]
    image_url = photo.get("urls", {}).get("regular") or photo.get("urls", {}).get("full")
    if not image_url:
        return None
    img = download_photo(image_url)
    # 다운로드 ping (Unsplash 정책)
    dl_link = photo.get("links", {}).get("download_location")
    if dl_link:
        trigger_download_ping(dl_link)
    return img, photo
