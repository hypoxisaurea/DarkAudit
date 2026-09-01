"""
Structured UI Representation 추출
--------------------------------
화면에서 **모든** UI 요소를 뽑아 Rule Engine 이 소비할 수 있는 형태로 만든다.

capture.py 가 뽑는 것은 "패턴이 걸린 요소"뿐이라 정답 라벨 생성용이다.
Rule Engine 은 화면 전체를 보고 스스로 위험을 찾아야 하므로 별도 추출이 필요하다.

이 파일이 만들어내는 구조가 곧 Team A 와 합의할 UI Schema 의 초안이다.
문서로 먼저 정의하려다 보류했으나, 실제로 규칙을 돌려보면 어떤 필드가
반드시 필요한지 확정되므로 구현을 통해 스키마를 확정한다.

사용
    python extract_ui.py --config configs/ins-001-risky.json
    python extract_ui.py --all
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 390, "height": 844}

# 의미 있는 요소만 추출한다. 레이아웃용 래퍼까지 넣으면 노이즈가 커진다.
EXTRACT_JS = r"""
() => {
  // --- 색상 유틸 ---------------------------------------------------------
  const rgb = (s) => {
    const m = (s || '').match(/[\d.]+/g);
    if (!m) return null;
    return { r: +m[0], g: +m[1], b: +m[2], a: m.length > 3 ? +m[3] : 1 };
  };
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  // 배경이 투명하면 부모를 거슬러 올라가 실제 배경을 찾는다
  const bgOf = (el) => {
    let n = el;
    while (n && n !== document.documentElement) {
      const c = rgb(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.05) return c;
      n = n.parentElement;
    }
    return { r: 255, g: 255, b: 255, a: 1 };
  };
  const contrast = (fg, bg) => {
    if (!fg || !bg) return null;
    const a = lum(fg), b = lum(bg);
    return +(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05))).toFixed(2);
  };
  const saturation = (c) => {
    if (!c) return 0;
    const mx = Math.max(c.r, c.g, c.b), mn = Math.min(c.r, c.g, c.b);
    return mx === 0 ? 0 : +((mx - mn) / mx).toFixed(3);
  };

  // --- 요소 식별자 (capture.py 와 동일 규칙) -----------------------------
  const daId = (el) => {
    const tag = el.tagName.toLowerCase();
    const cls = (el.className || '').toString().trim().split(/\s+/)
                  .filter(Boolean).sort().join('.');
    const txt = (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 24);
    const path = [];
    let n = el;
    while (n && n !== document.body && path.length < 4) {
      path.push(n.tagName.toLowerCase()); n = n.parentElement;
    }
    const raw = [path.reverse().join('>'), cls, txt].join('|');
    let h = 0;
    for (let i = 0; i < raw.length; i++) { h = (h * 31 + raw.charCodeAt(i)) | 0; }
    return tag + '-' + (h >>> 0).toString(36);
  };

  // --- 요소 유형 판정 ----------------------------------------------------
  const typeOf = (el) => {
    const c = (el.className || '').toString();
    if (c.includes('btn')) return 'button';
    if (c.includes('box')) return 'checkbox';
    if (c.includes('accordion')) return 'accordion';
    if (c.includes('badge')) return 'badge';
    if (c.includes('bulk')) return 'link';
    if (c.includes('price') || c.includes('rate')) return 'price';
    if (el.tagName === 'BUTTON') return 'button';
    if (el.tagName === 'A') return 'link';
    return 'text';
  };

  const W = document.body.scrollWidth, H = document.body.scrollHeight;
  const SEL = 'button, a, .btn, .box, .opt, .card, .badge, .price, .rate, '
            + '.accordion, .bulk, .note, .risk-notice, h2, .sub, .t, .d, .p, .k, .v';

  const out = [];
  document.querySelectorAll(SEL).forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return;

    const cs = getComputedStyle(el);
    const fg = rgb(cs.color);
    const bg = bgOf(el);
    const own = rgb(cs.backgroundColor);
    const text = (el.innerText || '').trim().replace(/\s+/g, ' ');

    // 애니메이션 여부 — DA-13(감각조작) 판정의 핵심 신호
    const animated = cs.animationName !== 'none' && cs.animationName !== '';

    out.push({
      element_id: daId(el),
      element_type: typeOf(el),
      text: text.slice(0, 120) || null,
      bbox: [ +(r.x / W).toFixed(4), +(r.y / H).toFixed(4),
              +(r.width / W).toFixed(4), +(r.height / H).toFixed(4) ],
      state: {
        checked: el.classList.contains('on') || null,
        disabled: el.disabled || null,
      },
      computed_style: {
        font_size: parseFloat(cs.fontSize),
        font_weight: parseInt(cs.fontWeight) || null,
        color: cs.color,
        background_color: cs.backgroundColor,
        opacity: parseFloat(cs.opacity),
        contrast_ratio: contrast(fg, bg),
        saturation: saturation(own && own.a > 0.05 ? own : fg),
        area_ratio: +((r.width * r.height) / (W * H)).toFixed(5),
        animated: animated,
        filled: !!(own && own.a > 0.05),
      },
      // 다크패턴 주입 마커. Rule Engine 은 이 값을 보지 않는다(정답 누출 방지).
      _injected: el.getAttribute('data-da') || null,
    });
  });

  return { viewport: { width: W, height: H }, elements: out };
}
"""


def extract(cfg: dict, html_root: Path, out_root: Path) -> dict:
    flow_id = cfg["flow_id"]
    html_dir = html_root / flow_id
    out_dir = out_root / flow_id
    out_dir.mkdir(parents=True, exist_ok=True)

    screens = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        for html in sorted(html_dir.glob("*.html")):
            idx = int(html.stem)
            page.goto(html.resolve().as_uri())
            page.wait_for_timeout(200)
            data = page.evaluate(EXTRACT_JS)
            screens.append({
                "screen_index": idx,
                "viewport": data["viewport"],
                "elements": data["elements"],
            })
        browser.close()

    doc = {
        "schema_version": "0.1",
        "flow_id": flow_id,
        "flow_type": cfg.get("flow_type", "join"),
        "sector": cfg.get("sector"),
        "screens": screens,
    }
    (out_root / f"{flow_id}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return doc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--html", default="../synthetic/html")
    ap.add_argument("--out", default="../synthetic/ui")
    args = ap.parse_args()

    cfgs = sorted(Path("configs").glob("*.json")) if args.all else [Path(args.config)]
    for c in cfgs:
        cfg = json.loads(c.read_text(encoding="utf-8"))
        doc = extract(cfg, Path(args.html), Path(args.out))
        n = sum(len(s["elements"]) for s in doc["screens"])
        print(f"{doc['flow_id']:<16} 화면 {len(doc['screens'])}  요소 {n}")


if __name__ == "__main__":
    main()
