from pathlib import Path

from app.domain.errors import AdultVerificationRequiredError
from app.infrastructure.crawlers.yes24.parser import extract_search_candidate_urls, parse_detail_page


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "html"


def test_extract_search_candidate_urls():
    html = (FIXTURE_DIR / "yes24_search.html").read_text(encoding="utf-8")
    urls = extract_search_candidate_urls(html, limit=5)
    assert urls == [
        "https://www.yes24.com/product/goods/1111",
        "https://www.yes24.com/product/goods/2222",
    ]


def test_parse_detail_page():
    html = (FIXTURE_DIR / "yes24_detail.html").read_text(encoding="utf-8")
    result = parse_detail_page(html, "https://www.yes24.com/product/goods/126011284")
    assert result.book.isbn == "9791130671017"
    assert result.book.title == "쉬프팅"
    assert result.book.author == "범유진"
    assert result.book.publisher == "다산책방"
    assert result.book.category == "청소년 소설"
    assert result.book.page_count == "220쪽"
    assert result.book.book_size == "135*210*15mm"
    assert result.cover_image_url == "https://image.yes24.com/goods/126011284/XL"
    assert result.detail_image_url == "https://image.yes24.com/momo/TopCate/shift.jpg"


def test_parse_detail_page_detects_adult_gate():
    html = "<html><body><div>성인 인증이 필요한 상품입니다.</div></body></html>"
    try:
        parse_detail_page(html, "https://www.yes24.com/product/goods/999")
        raise AssertionError("Expected AdultVerificationRequiredError")
    except AdultVerificationRequiredError as exc:
        assert exc.code == "adult_verification_required"


def test_parse_detail_page_prefers_actual_detail_section_over_duplicate_infoset_id():
    html = """
    <html>
      <body>
        <h2 class="gd_name">미스터 마켓 2021</h2>
        <div class="gd_pubArea">
          <span class="gd_auth"><a href="#">이한영</a></span>
          <span class="gd_pub"><a href="#">페이지2북스</a></span>
          <span class="gd_date">2020년 12월 30일</span>
        </div>
        <div class="gd_imgArea"><div class="gd_img"><img class="gImg" src="https://image.yes24.com/goods/95563770/XL"></div></div>
        <div id="infoset_goodsCate"><div class="infoSetCont_wrap"><a href="#">국내도서</a><a href="#">경제 경영</a></div></div>
        <table id="infoset_specific">
          <tr><th>ISBN13</th><td>9791190977036</td></tr>
          <tr><th>쪽수, 무게, 크기</th><td>368쪽 | 580g | 152*225*20mm</td></tr>
        </table>
        <div class="gd_infoTbArea"><table class="gd_infoTb"><tr><th>정가</th><td>18,500원</td></tr><tr><th>판매가</th><td>16,650원</td></tr></table></div>

        <div id="infoset_chYes" class="gd_infoSet">
          <div class="tm_infoSet"><h4 class="tit_txt">채널예스 기사</h4></div>
          <div class="infoSetCont_wrap">
            <img src="https://image.yes24.com/images/chyes24/b/e/7/4/be74a664f5c8ed3cbedec61eebe6ea47.png" alt="채널예스 기사 썸네일">
          </div>
        </div>

        <div id="infoset_chYes" class="gd_infoSet">
          <div class="tm_infoSet"><h4 class="tit_txt">상세 이미지</h4></div>
          <div class="infoSetCont_wrap">
            <div class="infoWrap_txt">
              <img data-original="https://image.yes24.com/momo/TopCate3227/MidCate008/322676575.jpg" src="https://image.yes24.com/momo/Noimg_XL.jpg" alt="상세 이미지 1">
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    result = parse_detail_page(html, "https://www.yes24.com/product/goods/95563770")

    assert result.detail_image_url == "https://image.yes24.com/momo/TopCate3227/MidCate008/322676575.jpg"
