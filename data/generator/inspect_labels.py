"""
DarkAudit Label Inspector
-------------------------
Gold Set 검수를 눈으로 할 수 있게 만든다.

  1) 스크린샷 위에 라벨 bbox 를 그려 검수 시트를 생성한다.
     related_elements 는 점선으로 구분해 primary 와 헷갈리지 않게 한다.
  2) 유형별 인스턴스 분포를 출력한다.
     인스턴스가 3건 미만인 유형은 Recall 이 사실상 0/1 밖에 못 가지므로 경고한다.

사용
    python inspect_labels.py                 # 전체
    python inspect_labels.py --flow dep-001-risky
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LABELS_DIR = Path("../synthetic/labels")
SHOTS_DIR = Path("../synthetic/screenshots")
OUT_DIR = Path("../synthetic/review")

PRIMARY_COLOR = (220, 38, 38)      # 빨강 — primary
RELATED_COLOR = (37, 99, 235)      # 파랑 — related
MIN_INSTANCES = 3                  # 유형별 최소 확보 목표


def _font(size: int):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _draw_box(draw, box, w, h, color, text, dashed=False, scale=1):
    """정규화 bbox 를 실제 픽셀로 되돌려 그린다."""
    x, y, bw, bh = box
    x0, y0 = x * w, y * h
    x1, y1 = x0 + bw * w, y0 + bh * h

    if dashed:
        step, on = 9 * scale, True
        for cx in range(int(x0), int(x1), step):
            if on:
                draw.line([cx, y0, min(cx + step, x1), y0], fill=color, width=2 * scale)
                draw.line([cx, y1, min(cx + step, x1), y1], fill=color, width=2 * scale)
            on = not on
        on = True
        for cy in range(int(y0), int(y1), step):
            if on:
                draw.line([x0, cy, x0, min(cy + step, y1)], fill=color, width=2 * scale)
                draw.line([x1, cy, x1, min(cy + step, y1)], fill=color, width=2 * scale)
            on = not on
    else:
        draw.rectangle([x0, y0, x1, y1], outline=color, width=3 * scale)

    font = _font(15 * scale)
    tw = draw.textlength(text, font=font)
    ty = max(0, y0 - 21 * scale)
    draw.rectangle([x0, ty, x0 + tw + 10 * scale, ty + 20 * scale], fill=color)
    draw.text((x0 + 5 * scale, ty + 2 * scale), text, fill="white", font=font)


def build_sheet(doc: dict) -> Path:
    """Flow 하나를 가로로 이어붙인 검수 시트를 만든다."""
    flow_id = doc["flow_id"]

    # 화면별로 그릴 라벨을 모은다
    per_screen = collections.defaultdict(list)
    flow_labels = []
    for lb in doc["labels"]:
        if lb["label_unit"] == "element":
            per_screen[lb["primary"]["screen_index"]].append(lb)
        elif lb["label_unit"] == "screen":
            per_screen[lb["screen_index"]].append(lb)
        else:
            flow_labels.append(lb)

    images = []
    for sc in doc["screens"]:
        idx = sc["screen_index"]
        img = Image.open(SHOTS_DIR / Path(sc["image"])).convert("RGB")
        scale = round(img.width / sc["viewport"]["width"]) or 1
        draw = ImageDraw.Draw(img)

        for lb in per_screen.get(idx, []):
            if lb["label_unit"] != "element":
                continue
            _draw_box(draw, lb["primary"]["bbox"], img.width, img.height,
                      PRIMARY_COLOR, lb["rule_id"], scale=scale)
            for rel in lb.get("related_elements", []):
                _draw_box(draw, rel["bbox"], img.width, img.height,
                          RELATED_COLOR, f"{lb['rule_id']} rel", dashed=True, scale=scale)

        # 화면 번호와 flow 단위 라벨 표시용 머리글
        head = 46 * scale
        canvas = Image.new("RGB", (img.width, img.height + head), "white")
        canvas.paste(img, (0, head))
        d = ImageDraw.Draw(canvas)
        tags = [l["rule_id"] for l in flow_labels if idx in l.get("screen_indices", [])]
        cap = f"S{idx}" + (f"   flow: {', '.join(tags)}" if tags else "")
        d.text((10 * scale, 12 * scale), cap, fill=(20, 20, 20), font=_font(20 * scale))
        images.append(canvas)

    w = sum(i.width for i in images)
    h = max(i.height for i in images)
    sheet = Image.new("RGB", (w, h), "white")
    x = 0
    for i in images:
        sheet.paste(i, (x, 0))
        x += i.width

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet.thumbnail((2400, 2400))
    out = OUT_DIR / f"{flow_id}.jpg"
    sheet.save(out, quality=88)
    return out


def distribution(docs: list[dict]) -> None:
    inst = collections.Counter()
    flows = collections.defaultdict(set)

    for d in docs:
        for lb in d["labels"]:
            inst[lb["rule_id"]] += 1
            flows[lb["rule_id"]].add(d["flow_id"])

    print("\n유형별 인스턴스 분포")
    print(f"{'ID':<8}{'인스턴스':>8}{'Flow수':>8}   상태")
    print("-" * 44)
    for rid in sorted(inst):
        n = inst[rid]
        flag = "" if n >= MIN_INSTANCES else f"  부족 (목표 {MIN_INSTANCES})"
        print(f"{rid:<8}{n:>8}{len(flows[rid]):>8}{flag}")

    short = [r for r, n in inst.items() if n < MIN_INSTANCES]
    print(f"\n총 {sum(inst.values())}건 / {len(inst)}개 유형")
    if short:
        print(f"보충 필요: {', '.join(sorted(short))}")
        print("→ config 를 추가해 해당 유형이 포함된 Flow 를 늘린다.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow", help="특정 flow_id 만 처리")
    args = ap.parse_args()

    docs = []
    for f in sorted(LABELS_DIR.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if args.flow and d["flow_id"] != args.flow:
            continue
        docs.append(d)

    for d in docs:
        if not d["labels"]:
            print(f"{d['flow_id']:<18} 라벨 없음 (clean) — 시트 생략")
            continue
        out = build_sheet(d)
        print(f"{d['flow_id']:<18} 라벨 {len(d['labels'])}건 → {out}")

    distribution(docs)


if __name__ == "__main__":
    main()
