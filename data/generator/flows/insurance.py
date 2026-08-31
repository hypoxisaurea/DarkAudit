"""보험 가입 Flow — 5화면"""

from __future__ import annotations

from common import PATTERN_CSS, _risk_attr, _shell  # noqa: F401


def screen_1(cfg: dict) -> str:
    """상품 확인 — DA-15(순차공개 가격) 의 최초 표시가가 여기서 정해진다."""
    p = cfg["patterns"]
    risk = _risk_attr(cfg)
    # DA-15 risky: 최저가만 단독 표시 / clean: 범위 + 변동 고지
    if "DA-15" in p:
        price_block = f"""
      <div class="price" data-da="DA-15">월 {cfg['base_price']:,}<span class="u">원</span></div>
      <div class="note">보험료는 가입조건에 따라 산출됩니다.</div>"""
    else:
        price_block = f"""
      <div class="price">월 {cfg['base_price']:,}~{cfg['final_price']:,}<span class="u">원</span></div>
      <div class="note">선택하시는 특약과 부가서비스에 따라 최종 보험료가
      달라질 수 있습니다. 다음 단계에서 항목별 금액을 확인하실 수 있습니다.</div>"""

    if "DA-05" in p:
        claim = '<span class="badge hot" data-da="DA-05">업계 최저 보험료</span>'
    else:
        claim = '<span class="badge">간편심사</span>'

    inner = f"""
    {claim}
    <h2>든든안심 실손의료비보험</h2>
    <div class="sub">30세 여성 · 표준형 기준</div>
    <div class="card">{price_block}</div>
    <div class="card">
      <div class="row"><span class="k">보장기간</span><span class="v">100세 만기</span></div>
      <div class="hr"></div>
      <div class="row"><span class="k">납입기간</span><span class="v">20년납</span></div>
      <div class="hr"></div>
      <div class="row"><span class="k">가입금액</span><span class="v">5,000만원</span></div>
    </div>
    <div class="risk-notice note"{risk}>본 보험은 예금자보호법에 따라 보호되지 않는 상품이며,
    중도 해지 시 해약환급금이 납입한 보험료보다 적거나 없을 수 있습니다.
    자세한 사항은 약관을 확인하시기 바랍니다.</div>"""
    return _shell(1, 5, "보험 가입", inner, '<button class="btn btn-pri">가입 시작하기</button>', cfg)


def screen_2(cfg: dict) -> str:
    """특약 선택"""
    inner = """
    <h2>특약을 선택해 주세요</h2>
    <div class="sub">필요한 보장만 골라 담을 수 있습니다</div>
    <div class="card">
      <div class="opt"><div class="box on"></div>
        <div><div class="t">질병입원의료비</div><div class="d">필수 가입 항목</div></div>
        <div class="p">포함</div></div>
      <div class="opt"><div class="box on"></div>
        <div><div class="t">상해입원의료비</div><div class="d">필수 가입 항목</div></div>
        <div class="p">포함</div></div>
      <div class="opt"><div class="box"></div>
        <div><div class="t">비급여 도수치료</div><div class="d">연간 350만원 한도</div></div>
        <div class="p">+1,200원</div></div>
    </div>"""
    return _shell(2, 5, "특약 선택", inner, '<button class="btn btn-pri">다음</button>', cfg)


def screen_3(cfg: dict) -> str:
    """부가서비스 — DA-04(사전선택) · DA-13(감각조작) 이 여기 걸린다."""
    p = cfg["patterns"]
    on = " on" if "DA-04" in p else ""
    da4 = ' data-da="DA-04"' if "DA-04" in p else ""
    sense = " sense" if "DA-13" in p else ""
    da13 = ' data-da="DA-13"' if "DA-13" in p else ""

    # DA-04 clean 일 때만 전체해제 컨트롤을 노출 (mitigating_checks 대응)
    bulk = "" if "DA-04" in p else '<div class="note">선택하신 항목만 보험료에 합산됩니다.</div>'

    inner = f"""
    <h2>부가서비스를 확인해 주세요</h2>
    <div class="sub">가입 후에도 변경하실 수 있습니다</div>
    <div class="card">
      <div class="opt{sense}"{da13}><div class="box{on}"{da4}></div>
        <div><div class="t">안심케어 서비스</div>
        <div class="d">24시간 건강상담 · 병원 예약대행</div></div>
        <div class="p">+3,000원</div></div>
      <div class="opt"><div class="box"></div>
        <div><div class="t">해외여행 의료지원</div>
        <div class="d">해외 체류 중 의료비 지원</div></div>
        <div class="p">+1,500원</div></div>
    </div>
    {bulk}"""
    return _shell(3, 5, "부가서비스", inner, '<button class="btn btn-pri">다음</button>', cfg)


def screen_4(cfg: dict) -> str:
    """보험료 확인 — DA-15 의 가격 변동이 드러나는 지점."""
    p = cfg["patterns"]
    total = cfg["final_price"] if "DA-04" in p else cfg["base_price"]
    da15 = ' data-da="DA-15"' if "DA-15" in p else ""

    extra = ""
    if "DA-04" in p:
        extra = """
      <div class="hr"></div>
      <div class="row"><span class="k">안심케어 서비스</span><span class="v">3,000원</span></div>"""

    inner = f"""
    <h2>최종 보험료를 확인해 주세요</h2>
    <div class="sub">아래 금액으로 매월 자동이체됩니다</div>
    <div class="card">
      <div class="price"{da15}>월 {total:,}<span class="u">원</span></div>
    </div>
    <div class="card">
      <div class="row"><span class="k">기본 보험료</span><span class="v">{cfg['base_price']:,}원</span></div>{extra}
      <div class="hr"></div>
      <div class="row"><span class="k">합계</span><span class="v">{total:,}원</span></div>
    </div>"""
    return _shell(4, 5, "보험료 확인", inner, '<button class="btn btn-pri">가입 신청</button>', cfg)


def screen_5(cfg: dict) -> str:
    """최종 확인 — DA-03(계층구조) · DA-12(감정적 언어) 가 여기 걸린다."""
    p = cfg["patterns"]
    risk = _risk_attr(cfg)
    if "DA-12" in p:
        decline, da12 = "혜택을 포기하고 나가기", ' data-da="DA-12"'
    else:
        decline, da12 = "가입하지 않기", ""
    da3 = ' data-da="DA-03"' if "DA-03" in p else ""

    inner = f"""
    <h2>가입 내용을 확인해 주세요</h2>
    <div class="sub">확인 후 가입이 완료됩니다</div>
    <div class="card">
      <div class="row"><span class="k">상품</span><span class="v">든든안심 실손의료비</span></div>
      <div class="hr"></div>
      <div class="row"><span class="k">계약자</span><span class="v">홍길동</span></div>
      <div class="hr"></div>
      <div class="row"><span class="k">납입방법</span><span class="v">자동이체</span></div>
    </div>
    <div class="risk-notice note"{risk}>청약 후 15일 이내 청약철회가 가능하며,
    보험금 지급사유 발생 시 약관에 따라 지급이 제한될 수 있습니다.</div>"""

    cta = f"""<div class="pair">
      <button class="btn btn-sec"{da12}>{decline}</button>
      <button class="btn btn-pri"{da3}>가입 완료하기</button>
    </div>"""
    return _shell(5, 5, "가입 확인", inner, cta, cfg)


SCREENS = [screen_1, screen_2, screen_3, screen_4, screen_5]
