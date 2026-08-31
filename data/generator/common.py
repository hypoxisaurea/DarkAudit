"""
DarkAudit Generator — 공통 레이아웃

모든 업권 Flow 가 공유하는 뷰포트, 기본 스타일, 패턴별 주입 CSS, 화면 셸.
업권별 화면 정의는 flows/ 아래에 둔다.
"""

from __future__ import annotations

VIEWPORT_W = 390
VIEWPORT_H = 844


# ---------------------------------------------------------------- 공통 스타일

BASE_CSS = f"""
* {{ margin:0; padding:0; box-sizing:border-box;
     -webkit-font-smoothing:antialiased; }}
body {{
  width:{VIEWPORT_W}px; min-height:{VIEWPORT_H}px;
  font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;
  background:#fff; color:#1a1a1a; font-size:15px; line-height:1.5;
}}
.status  {{ height:44px; display:flex; align-items:center; justify-content:space-between;
           padding:0 18px; font-size:13px; font-weight:600; }}
.nav     {{ height:52px; display:flex; align-items:center; padding:0 16px;
           border-bottom:1px solid #eee; }}
.nav .back {{ font-size:20px; color:#444; margin-right:12px; }}
.nav .title {{ font-size:16px; font-weight:600; }}
.steps   {{ display:flex; gap:6px; padding:14px 18px 4px; }}
.step    {{ flex:1; height:3px; background:#e5e5e5; border-radius:2px; }}
.step.on {{ background:#1f4fd8; }}
.body    {{ padding:20px 18px 120px; }}
h2       {{ font-size:21px; font-weight:700; line-height:1.35; margin-bottom:6px; }}
.sub     {{ font-size:13px; color:#767676; margin-bottom:22px; }}
.card    {{ border:1px solid #e8e8e8; border-radius:12px; padding:16px; margin-bottom:12px; }}
.row     {{ display:flex; justify-content:space-between; align-items:center; padding:9px 0; }}
.row .k  {{ color:#666; font-size:14px; }}
.row .v  {{ font-weight:600; font-size:14px; }}
.hr      {{ height:1px; background:#eee; margin:10px 0; }}
.price   {{ font-size:26px; font-weight:800; letter-spacing:-0.4px; }}
.price .u{{ font-size:15px; font-weight:600; margin-left:2px; }}
.opt     {{ display:flex; align-items:flex-start; gap:11px; padding:14px 0; }}
.opt+.opt{{ border-top:1px solid #f2f2f2; }}
.box     {{ width:21px; height:21px; border:1.5px solid #c8c8c8; border-radius:5px;
           flex-shrink:0; margin-top:1px; }}
.box.on  {{ background:#1f4fd8; border-color:#1f4fd8;
           background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3.4' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'/></svg>");
           background-size:15px; background-position:center; background-repeat:no-repeat; }}
.opt .t  {{ font-size:14.5px; font-weight:600; }}
.opt .d  {{ font-size:12.5px; color:#888; margin-top:3px; }}
.opt .p  {{ margin-left:auto; font-size:14px; font-weight:700; color:#1f4fd8;
           white-space:nowrap; padding-left:8px; }}
.note    {{ font-size:12px; color:#999; margin-top:10px; line-height:1.55; }}
.cta     {{ position:fixed; left:0; right:0; bottom:0; width:{VIEWPORT_W}px;
           padding:12px 18px 26px; background:#fff; border-top:1px solid #f0f0f0; }}
.btn     {{ display:block; width:100%; text-align:center; padding:16px;
           border-radius:12px; font-size:16px; font-weight:700; border:none; }}
.btn-pri {{ background:#1f4fd8; color:#fff; }}
.btn-sec {{ background:#f2f3f5; color:#555; }}
.pair    {{ display:flex; gap:9px; }}
.pair .btn {{ flex:1; }}
.rate    {{ font-size:30px; font-weight:800; letter-spacing:-0.6px; color:#1f4fd8; }}
.rate .u {{ font-size:17px; font-weight:700; margin-left:1px; }}
.accordion {{ display:flex; align-items:center; justify-content:space-between;
           border:1px solid #e8e8e8; border-radius:12px; padding:16px;
           font-size:14.5px; font-weight:600; color:#444; }}
.accordion .chev {{ color:#bbb; font-size:19px; }}
.bulk    {{ text-align:right; font-size:13px; color:#1f4fd8; font-weight:600;
           margin-top:10px; }}
.badge.hot {{ background:#fff1f0; color:#d92d20; }}
.badge   {{ display:inline-block; font-size:11.5px; font-weight:700; padding:4px 9px;
           border-radius:5px; background:#eef2ff; color:#1f4fd8; margin-bottom:10px; }}
"""

# 패턴별로 덧입히는 스타일. 이 CSS 가 적용되는지 여부가 곧 Risky/Clean 을 가른다.
PATTERN_CSS = {
    # DA-03 잘못된 계층구조 — 거절 선택지를 배경과 동화시키고 크기를 줄인다
    "DA-03": """
.pair .btn-sec { background:#fff; color:#bdbdbd; font-size:13px; font-weight:500;
                 padding:16px 4px; flex:0.48; }
""",
    # DA-07 숨겨진 정보 — 위험 고지를 작고 흐리게
    # (예적금 Flow 는 '자세히 보기 안에 접어두기' 형태를 함께 사용한다)
    "DA-07": """
.risk-notice { font-size:9.5px !important; color:#cfcfcf !important; line-height:1.35 !important; }
""",
    # DA-13 감각조작 — 특정 옵션만 점멸시켜 주의를 집중시킨다
    "DA-13": """
@keyframes daBlink { 0%,100%{background:#e8efff;} 50%{background:#fff;} }
.sense { animation:daBlink 1.1s infinite; border-radius:9px;
         margin:0 -8px; padding-left:8px; padding-right:8px; }
""",
}


# ---------------------------------------------------------------- 화면 정의
# 각 화면은 cfg(설정) 를 받아 HTML 조각을 반환한다.
# 패턴이 걸린 요소에는 data-da="DA-XX" 를 남긴다 → 캡처 시 bbox 자동 추출.


def _risk_attr(cfg: dict) -> str:
    """DA-07 이 켜졌을 때만 위험고지 요소에 추출용 태그를 남긴다."""
    return ' data-da="DA-07"' if "DA-07" in cfg.get("patterns", []) else ""


def _shell(idx: int, total: int, title: str, inner: str, cta: str, cfg: dict) -> str:
    on = "".join(PATTERN_CSS.get(r, "") for r in cfg.get("patterns", []))
    bars = "".join(
        f'<div class="step{" on" if i <= idx else ""}"></div>' for i in range(1, total + 1)
    )
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<style>{BASE_CSS}{on}</style></head><body>
<div class="status"><span>9:41</span><span>100%</span></div>
<div class="nav"><span class="back">&#8249;</span><span class="title">{title}</span></div>
<div class="steps">{bars}</div>
<div class="body">{inner}</div>
<div class="cta">{cta}</div>
</body></html>"""


