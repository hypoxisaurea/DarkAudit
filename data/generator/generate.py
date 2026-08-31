"""
DarkAudit Synthetic Financial UI Generator
------------------------------------------
금융상품 가입 Flow 화면을 HTML 로 생성한다.

핵심 설계
  - 화면 템플릿은 업권별로 하나. 어떤 다크패턴을 심을지는 설정으로 주입한다.
  - 따라서 Risky / Clean 쌍은 "설정만 다른" 상태가 구조적으로 보장된다.
  - 패턴이 걸린 요소에는 data-da 속성을 남긴다. capture.py 가 이 속성을 읽어
    bbox 를 자동 추출하므로 사람이 좌표를 찍지 않는다.

사용
    python generate.py --config configs/dep-001-risky.json
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

# 업권 → 화면 모듈. 새 업권은 flows/ 에 모듈을 추가하고 여기 한 줄만 등록한다.
FLOWS = {
    "insurance": "flows.insurance",
    "deposit": "flows.deposit",
}


def load_screens(sector: str):
    if sector not in FLOWS:
        raise SystemExit(f"지원하지 않는 업권: {sector} (가능: {', '.join(FLOWS)})")
    return importlib.import_module(FLOWS[sector]).SCREENS


def generate(cfg: dict, out_dir: Path) -> list[Path]:
    screens = load_screens(cfg["sector"])
    flow_dir = out_dir / cfg["flow_id"]
    flow_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for i, fn in enumerate(screens, start=1):
        path = flow_dir / f"{i:02d}.html"
        path.write_text(fn(cfg), encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="../synthetic/html")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    files = generate(cfg, Path(args.out))
    print(f"{cfg['flow_id']}  [{cfg['sector']}]  patterns={cfg['patterns'] or '없음(clean)'}  → {len(files)}화면")


if __name__ == "__main__":
    main()
