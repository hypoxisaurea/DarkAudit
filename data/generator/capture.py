"""
DarkAudit Capture & Auto-label
------------------------------
생성된 HTML 을 렌더링해 스크린샷을 저장하고, 동시에 정답 라벨을 만든다.

핵심은 bbox 를 사람이 찍지 않는다는 점이다.
화면을 우리가 생성했으므로 패턴이 걸린 요소에 data-da 속성이 남아 있고,
브라우저에서 getBoundingClientRect() 로 정확한 좌표를 얻을 수 있다.
좌표는 화면 크기로 나눠 0~1 정규화해 저장한다.

주의: 여기서 나오는 라벨은 "우리가 심은 것"이다.
      의도치 않게 발생한 패턴은 포함되지 않으므로 Gold Set 검수로 보완한다.

사용
    python capture.py --config configs/ins-001-risky.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 390, "height": 844}

# Rule Base 의 label_unit / related_required 와 일치해야 한다.
# 생성기가 심을 수 있는 유형만 기술한다.
RULE_META = {
    "DA-03": {"unit": "element", "type": "button",   "severity": "HIGH"},
    "DA-05": {"unit": "element", "type": "text",     "severity": "HIGH"},
    "DA-04": {"unit": "element", "type": "checkbox", "severity": "HIGH"},
    "DA-07": {"unit": "element", "type": "text",     "severity": "HIGH"},
    "DA-12": {"unit": "element", "type": "button",   "severity": "REVIEW"},
    "DA-13": {"unit": "element", "type": "text",     "severity": "REVIEW"},
    "DA-15": {"unit": "flow",    "type": None,       "severity": "HIGH"},
}

# related 가 필수인 유형은 상대 요소를 어떻게 찾을지 지정한다.
# selector 는 primary 요소를 기준으로 한 형제/이웃 탐색이다.
RELATED_OF = {
    "DA-03": ".btn-sec",   # 강조된 가입 버튼 ↔ 억제된 거절 버튼
}

# related 를 primary 와 같은 selector 로 못 찾는 경우를 위한 예외 처리는
# 규칙이 늘어나면 별도 모듈로 분리한다.

EXTRACT_JS = """
() => {
  const out = [];
  document.querySelectorAll('[data-da]').forEach(el => {
    const r = el.getBoundingClientRect();
    out.push({
      rule_id: el.getAttribute('data-da'),
      bbox: [r.x, r.y, r.width, r.height],
      text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 60)
    });
  });
  return out;
}
"""

RELATED_JS = """
(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return { bbox: [r.x, r.y, r.width, r.height], text: (el.innerText || '').trim().slice(0, 60) };
}
"""


def _norm(bbox: list[float], w: int, h: int) -> list[float]:
    """절대 픽셀 → 0~1 정규화. 해상도가 달라도 임계값이 동일하게 걸리도록."""
    x, y, bw, bh = bbox
    return [round(x / w, 4), round(y / h, 4), round(bw / w, 4), round(bh / h, 4)]


def capture(cfg: dict, html_root: Path, shot_root: Path, label_root: Path) -> dict:
    flow_id = cfg["flow_id"]
    html_dir = html_root / flow_id
    shot_dir = shot_root / flow_id
    shot_dir.mkdir(parents=True, exist_ok=True)

    screens, labels = [], []
    flow_hits: dict[str, list[int]] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)

        for html in sorted(html_dir.glob("*.html")):
            idx = int(html.stem)
            page.goto(html.resolve().as_uri())
            # 애니메이션(DA-13 점멸)이 특정 프레임에 걸리지 않도록 잠시 대기
            page.wait_for_timeout(250)

            shot = shot_dir / f"{idx:02d}.png"
            page.screenshot(path=str(shot), full_page=True)

            dims = page.evaluate(
                "() => ({w: document.body.scrollWidth, h: document.body.scrollHeight})"
            )
            screens.append({
                "screen_index": idx,
                "image": f"{flow_id}/{idx:02d}.png",
                "viewport": {"width": dims["w"], "height": dims["h"]},
            })

            for hit in page.evaluate(EXTRACT_JS):
                rid = hit["rule_id"]
                meta = RULE_META[rid]

                if meta["unit"] == "flow":
                    flow_hits.setdefault(rid, []).append(idx)
                    continue

                label = {
                    "rule_id": rid,
                    "label_unit": "element",
                    "primary": {
                        "screen_index": idx,
                        "bbox": _norm(hit["bbox"], dims["w"], dims["h"]),
                        "text": hit["text"] or None,
                        "element_type": meta["type"],
                    },
                    "related_elements": [],
                    "severity": meta["severity"],
                    "mitigated": False,
                }
                if label["primary"]["text"] is None:
                    del label["primary"]["text"]

                if rid in RELATED_OF:
                    rel = page.evaluate(RELATED_JS, RELATED_OF[rid])
                    if rel:
                        label["related_elements"].append({
                            "screen_index": idx,
                            "bbox": _norm(rel["bbox"], dims["w"], dims["h"]),
                            "text": rel["text"],
                            "element_type": "button",
                        })

                labels.append(label)

        browser.close()

    for rid, idxs in flow_hits.items():
        labels.append({
            "rule_id": rid,
            "label_unit": "flow",
            "screen_indices": sorted(idxs),
            "severity": RULE_META[rid]["severity"],
            "mitigated": False,
        })

    doc = {
        "schema_version": "1.0",
        "flow_id": flow_id,
        "variant": cfg["variant"],
        "pair_id": cfg["pair_id"],
        "sector": cfg["sector"],
        "flow_type": cfg["flow_type"],
        "screens": screens,
        "labels": sorted(labels, key=lambda x: x["rule_id"]),
        "deferred": [],
    }

    label_root.mkdir(parents=True, exist_ok=True)
    (label_root / f"{flow_id}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return doc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--html", default="../synthetic/html")
    ap.add_argument("--shots", default="../synthetic/screenshots")
    ap.add_argument("--labels", default="../synthetic/labels")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    doc = capture(cfg, Path(args.html), Path(args.shots), Path(args.labels))

    print(f"{doc['flow_id']}  화면 {len(doc['screens'])}장  라벨 {len(doc['labels'])}건")
    for l in doc["labels"]:
        if l["label_unit"] == "element":
            b = l["primary"]["bbox"]
            rel = f"  related={len(l['related_elements'])}" if l["related_elements"] else ""
            print(f"  {l['rule_id']}  S{l['primary']['screen_index']}  bbox={b}{rel}")
        else:
            print(f"  {l['rule_id']}  screens={l['screen_indices']}  (flow)")


if __name__ == "__main__":
    main()
