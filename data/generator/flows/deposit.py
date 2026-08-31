"""
은행 예·적금 가입 Flow — 5화면

보험 Flow 와의 차이가 이 Flow 의 존재 이유다.

  DA-15  보험은 가격이 오르지만 예적금은 금리가 내려간다.
         Rule Base 의 rate_deterioration_across_screens 를 검증하는 유일한 데이터.
  DA-07  보험은 '작고 흐리게', 예적금은 '자세히 보기 안에 접어두기'.
         같은 규칙의 다른 관찰 형태.
  DA-05  '최대 연 4.5%' 에 근거가 없는 형태. 보험 Flow 에는 없던 유형.

가이드라인 원문이 DA-15 의 예시로 제시한 것도 예·적금 화면이다.
"""

from __future__ import annotations

from common import _risk_attr, _shell


def screen_1(cfg: dict) -> str:
    """상품 안내 — DA-15 의 유인 금리, DA-05 의 근거 없는 최상급 표현."""
    p = cfg["patterns"]
    risk = _risk_attr(cfg)
    base, top = cfg["base_rate"], cfg["top_rate"]

    if "DA-15" in p:
        # 최고 이율만 단독 표시. 기본금리와 도달 조건을 알 수 없다.
        rate_block = f"""
      <div class="rate" data-da="DA-15">연 {top}<span class="u">%</span></div>
      <div class="note">세전 이자율 기준</div>"""
    else:
        rate_block = f"""
      <div class="rate">연 {base}~{top}<span class="u">%</span></div>
      <div class="note">기본금리 연 {base}%에 우대조건 충족 시 최대 연 {top}%가
      적용됩니다. 우대조건은 다음 화면에서 확인하실 수 있습니다.</div>"""

    if "DA-05" in p:
        claim = '<span class="badge hot" data-da="DA-05">업계 최고 수준 금리</span>'
    else:
        claim = '<span class="badge">정기적금</span>'

    inner = f"""
    {claim}
    <h2>든든모아 정기적금</h2>
    <div class="sub">12개월 · 월 최대 50만원</div>
    <div class="card">{rate_block}</div>
    <div class="card">
      <div class="row"><span class="k">가입기간</span><span class="v">12개월</span></div>
      <div class="hr"></div>
      <div class="row"><span class="k">월 납입한도</span><span class="v">50만원</span></div>
      <div class="hr"></div>
      <div class="row"><span class="k">이자지급</span><span class="v">만기일시지급</span></div>
    </div>
    <div class="risk-notice note"{risk}>이 예금은 예금자보호법에 따라 예금보험공사가
    보호하되, 보호 한도는 본 은행에 있는 모든 예금보호대상 금융상품의 원금과
    소정의 이자를 합하여 1인당 최고 5천만원입니다.</div>"""
    return _shell(1, 5, "적금 가입", inner, '<button class="btn btn-pri">가입 시작하기</button>', cfg)


def screen_2(cfg: dict) -> str:
    """우대조건 — DA-07 을 '접어두기' 형태로 구현."""
    p = cfg["patterns"]
    top, base = cfg["top_rate"], cfg["base_rate"]

    conds = [
        ("급여이체 실적", "6개월 이상", "+0.8"),
        ("당행 신용카드 사용", "월 30만원 이상", "+0.7"),
        ("마케팅 정보 수신 동의", "가입 기간 중 유지", "+0.5"),
        ("첫 거래 고객", "당행 예적금 최초 가입", "+0.5"),
    ]

    if "DA-07" in p:
        # 우대조건 전체를 접어 두고, 클릭해야만 확인 가능
        body = f"""
    <div class="card">
      <div class="row"><span class="k">기본금리</span><span class="v">연 {base}%</span></div>
      <div class="hr"></div>
      <div class="row"><span class="k">최고금리</span><span class="v">연 {top}%</span></div>
    </div>
    <div class="accordion" data-da="DA-07">
      <span>우대조건 자세히 보기</span><span class="chev">&#8250;</span>
    </div>
    <div class="note">우대조건 미충족 시 기본금리가 적용됩니다.</div>"""
    else:
        rows = "".join(
            f"""<div class="opt"><div class="box"></div>
        <div><div class="t">{n}</div><div class="d">{d}</div></div>
        <div class="p">{v}%p</div></div>"""
            for n, d, v in conds
        )
        body = f"""
    <div class="card">
      <div class="row"><span class="k">기본금리</span><span class="v">연 {base}%</span></div>
    </div>
    <div class="card">{rows}</div>
    <div class="note">해당하는 우대조건을 모두 충족하면 최대 연 {top}%가 적용됩니다.
    충족하지 못한 조건이 있으면 그만큼 금리가 낮아집니다.</div>"""

    inner = f"""
    <h2>우대조건을 확인해 주세요</h2>
    <div class="sub">조건 충족 여부에 따라 금리가 달라집니다</div>
    {body}"""
    return _shell(2, 5, "우대조건", inner, '<button class="btn btn-pri">다음</button>', cfg)


def screen_3(cfg: dict) -> str:
    """선택 서비스 — DA-04(마케팅 동의 사전선택) · DA-13(감각조작)."""
    p = cfg["patterns"]
    on = " on" if "DA-04" in p else ""
    da4 = ' data-da="DA-04"' if "DA-04" in p else ""
    sense = " sense" if "DA-13" in p else ""
    da13 = ' data-da="DA-13"' if "DA-13" in p else ""

    bulk = "" if "DA-04" in p else '<div class="bulk">전체선택 / 전체해제</div>'

    inner = f"""
    <h2>선택 항목을 확인해 주세요</h2>
    <div class="sub">동의하지 않아도 가입하실 수 있습니다</div>
    <div class="card">
      <div class="opt{sense}"{da13}><div class="box{on}"{da4}></div>
        <div><div class="t">마케팅 정보 수신 동의</div>
        <div class="d">상품·이벤트 안내 (선택)</div></div>
        <div class="p">우대 +0.5%p</div></div>
      <div class="opt"><div class="box"></div>
        <div><div class="t">개인정보 제3자 제공 동의</div>
        <div class="d">제휴사 서비스 안내 (선택)</div></div>
        <div class="p">선택</div></div>
    </div>
    {bulk}"""
    return _shell(3, 5, "선택 항목", inner, '<button class="btn btn-pri">다음</button>', cfg)


def screen_4(cfg: dict) -> str:
    """최종 조건 — DA-15 의 금리 하락이 여기서 드러난다."""
    p = cfg["patterns"]
    base, top = cfg["base_rate"], cfg["top_rate"]
    # 우대조건 중 마케팅 동의(+0.5) 만 충족한 상태를 가정
    applied = round(base + (0.5 if "DA-04" in p else 0.0), 1)
    da15 = ' data-da="DA-15"' if "DA-15" in p else ""

    extra = ""
    if "DA-04" in p:
        extra = """
      <div class="hr"></div>
      <div class="row"><span class="k">마케팅 동의 우대</span><span class="v">+0.5%p</span></div>"""

    inner = f"""
    <h2>적용 금리를 확인해 주세요</h2>
    <div class="sub">고객님께 실제 적용되는 금리입니다</div>
    <div class="card">
      <div class="rate"{da15}>연 {applied}<span class="u">%</span></div>
    </div>
    <div class="card">
      <div class="row"><span class="k">기본금리</span><span class="v">연 {base}%</span></div>{extra}
      <div class="hr"></div>
      <div class="row"><span class="k">미충족 우대조건</span><span class="v">{top - applied:.1f}%p</span></div>
      <div class="hr"></div>
      <div class="row"><span class="k">적용금리</span><span class="v">연 {applied}%</span></div>
    </div>"""
    return _shell(4, 5, "금리 확인", inner, '<button class="btn btn-pri">가입 신청</button>', cfg)


def screen_5(cfg: dict) -> str:
    """가입 확인 — DA-03(계층구조) · DA-12(감정적 언어)."""
    p = cfg["patterns"]
    risk = _risk_attr(cfg)
    if "DA-12" in p:
        decline, da12 = "우대금리를 포기할게요", ' data-da="DA-12"'
    else:
        decline, da12 = "가입하지 않기", ""
    da3 = ' data-da="DA-03"' if "DA-03" in p else ""

    inner = f"""
    <h2>가입 내용을 확인해 주세요</h2>
    <div class="sub">확인 후 가입이 완료됩니다</div>
    <div class="card">
      <div class="row"><span class="k">상품</span><span class="v">든든모아 정기적금</span></div>
      <div class="hr"></div>
      <div class="row"><span class="k">가입기간</span><span class="v">12개월</span></div>
      <div class="hr"></div>
      <div class="row"><span class="k">월 납입액</span><span class="v">300,000원</span></div>
    </div>
    <div class="risk-notice note"{risk}>만기 전 중도해지 시 약정 금리가 아닌
    중도해지이율이 적용되어 이자가 크게 줄어들 수 있습니다.</div>"""

    cta = f"""<div class="pair">
      <button class="btn btn-sec"{da12}>{decline}</button>
      <button class="btn btn-pri"{da3}>가입 완료하기</button>
    </div>"""
    return _shell(5, 5, "가입 확인", inner, cta, cfg)


SCREENS = [screen_1, screen_2, screen_3, screen_4, screen_5]
