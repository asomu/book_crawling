from __future__ import annotations

from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pydantic import ValidationError

from app.domain.enums import Site
from app.domain.errors import AdultVerificationRequiredError, SelectorChangedError
from app.domain.schemas import BookPayload, FetchBookResult


YES24_BASE_URL = "https://www.yes24.com"
ADULT_GATE_MARKERS = (
    "성인 인증",
    "성인인증",
    "본인인증",
    "19세 미만",
    "청소년 이용불가",
    "19세 이상",
)


def extract_search_candidate_urls(html: str, limit: int = 5) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("#yesSchList li .item_img a[href], #yesSchList li .item_info a.gd_name[href]"):
        href = anchor.get("href")
        if not href:
            continue
        absolute = urljoin(YES24_BASE_URL, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        urls.append(absolute)
        if len(urls) >= limit:
            break
    return urls


def has_adult_gate(html: str) -> bool:
    return any(marker in _visible_text(html) for marker in ADULT_GATE_MARKERS)


def looks_like_search_redirect_page(html: str, current_url: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    has_results = bool(soup.select("#yesSchList li"))
    return "Main/default.aspx" in current_url and title == "예스24" and not has_results


def parse_detail_page(html: str, product_url: str) -> FetchBookResult:
    if has_adult_gate(html):
        raise AdultVerificationRequiredError(
            "성인인증이 필요한 도서입니다. 현재 v2는 익명 수집만 지원하므로 이 항목은 건너뜁니다."
        )
    soup = BeautifulSoup(html, "html.parser")

    title = _text_or_meta(soup, "h2.gd_name", "meta[name='title']")
    if not title:
        raise SelectorChangedError("Could not parse the Yes24 title selector.")

    category_links = soup.select("#infoset_goodsCate .infoSetCont_wrap a")
    category = category_links[-1].get_text(strip=True) if category_links else ""

    description = ""
    meta_description = soup.select_one("meta[name='description']")
    if meta_description:
        description = meta_description.get("content", "").strip()

    author = _first_text(soup.select(".gd_pubArea .gd_auth a, .gd_pubArea .gd_auth"))
    publisher = _first_text(soup.select(".gd_pubArea .gd_pub a, .gd_pubArea .gd_pub"))
    published_date = _first_text(soup.select(".gd_pubArea .gd_date"))

    rows = _table_rows(soup.select("#infoset_specific tr"))
    page_count = ""
    book_size = ""
    isbn = ""
    for header, value in rows:
        if header == "쪽수, 무게, 크기":
            parts = [part.strip() for part in value.split("|")]
            if parts:
                page_count = parts[0]
            if len(parts) >= 3:
                book_size = parts[2]
        elif header == "ISBN13":
            isbn = value.strip()
        elif header == "발행일" and not published_date:
            published_date = value.strip()

    if not isbn:
        raise SelectorChangedError("Could not parse ISBN13 from the Yes24 detail table.")

    price_rows = _table_rows(soup.select(".gd_infoTbArea .gd_infoTb tr"))
    price_original = ""
    price_sale = ""
    for header, value in price_rows:
        if header == "정가":
            price_original = value.replace("원", "").strip()
        elif header == "판매가":
            price_sale = value.replace("원", "").strip().split("(")[0].strip()

    cover_image = ""
    cover = soup.select_one(".gd_imgArea .gd_img img.gImg")
    if cover:
        cover_image = cover.get("src", "").strip()

    detail_image = _extract_detail_image(soup)

    try:
        book = BookPayload(
            isbn=isbn,
            site=Site.YES24,
            title=title,
            author=author,
            publisher=publisher,
            description=description,
            category=category,
            price_original=price_original,
            price_sale=price_sale,
            published_date=published_date,
            page_count=page_count,
            book_size=book_size,
            product_url=product_url,
        )
    except ValidationError as exc:
        raise SelectorChangedError(f"Parsed Yes24 detail page failed validation: {exc}") from exc
    return FetchBookResult(book=book, cover_image_url=cover_image or None, detail_image_url=detail_image or None)


def _text_or_meta(soup: BeautifulSoup, selector: str, meta_selector: str) -> str:
    node = soup.select_one(selector)
    if node:
        return node.get_text(strip=True)
    meta = soup.select_one(meta_selector)
    if meta:
        return meta.get("content", "").strip().split("|")[0]
    return ""


def _first_text(nodes: Iterable) -> str:
    for node in nodes:
        text = node.get_text(" ", strip=True)
        if text:
            return text.replace(" 저", "").strip()
    return ""


def _table_rows(rows: Iterable) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for row in rows:
        header = row.select_one("th")
        value = row.select_one("td")
        if not header or not value:
            continue
        parsed.append((header.get_text(strip=True), value.get_text(" ", strip=True)))
    return parsed


def _extract_detail_image(soup: BeautifulSoup) -> str:
    detail_sections = []
    for section in soup.select("div.gd_infoSet, div[id='infoset_chYes']"):
        title = section.select_one(".tm_infoSet .tit_txt")
        if title and "상세 이미지" in title.get_text(" ", strip=True):
            detail_sections.append(section)

    for section in detail_sections:
        image_url = _first_valid_image_url(
            section.select(".infoWrap_txt img[data-original], .infoWrap_txt img[src], img[data-original], img[src]")
        )
        if image_url:
            return image_url

    image_url = _first_valid_image_url(
        soup.select("#infoset_chYes .infoWrap_txt img[data-original], #infoset_chYes .infoWrap_txt img[src]")
    )
    if image_url:
        return image_url

    return _first_valid_image_url(
        soup.select("img[alt*='상세 이미지'][data-original], img[alt*='상세 이미지'][src]")
    )


def _first_valid_image_url(images: Iterable) -> str:
    for image in images:
        url = (image.get("data-original") or image.get("src") or "").strip()
        if not url or "Noimg" in url:
            continue
        return url
    return ""


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)
