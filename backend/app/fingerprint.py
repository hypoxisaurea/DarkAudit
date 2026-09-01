"""
Finding Fingerprint
-------------------
v1 의 Finding 과 v2 의 Finding 을 "같은 문제"로 묶는 키를 만든다.
Regression Audit 이 성립하려면 이 매칭이 정확해야 한다.

설계 방침: 느슨하게(loose) 잡는다.

빡빡하게 잡으면(정확한 좌표 + 원문 텍스트) 서로 다른 문제가 섞일 일은 없지만,
문구를 조금만 다듬어도 "기존 문제 해결 + 새 문제 발생"으로 잡힌다.
담당자 입장에서는 고쳤는데 새 문제가 생겼다고 보고되는 셈이라 신뢰가 깨진다.

그래서 아래 세 가지를 의도적으로 무시한다.

  1. 정확한 좌표        → 0.1 단위 격자로 반올림
  2. 숫자               → 전부 마스킹
  3. 공백 / 대소문자    → 정규화

특히 숫자 마스킹이 중요하다. '월 9,900원' 체크박스가 '월 12,900원'으로 바뀌었다고
다른 문제가 되어서는 안 된다. DA-15 처럼 금액·이율이 바뀌는 규칙에서 필수적이다.

반대로 rule_id 와 screen_index 는 유지한다. 이것까지 뭉개면 서로 다른 화면의
다른 규칙이 하나로 섞인다.
"""

from __future__ import annotations

import hashlib
import re

# 위치 격자 크기. 0.1 이면 화면을 10x10 으로 나눈 칸 단위로 본다.
GRID = 0.1

# 텍스트 비교에 사용할 길이. 길수록 빡빡해진다.
TEXT_LEN = 24

_DIGITS = re.compile(r"\d[\d,._]*")   # 연속된 숫자 덩어리를 통째로 잡는다
_SPACES = re.compile(r"\s+")
_PUNCT = re.compile(r"[,.\u00b7:;!?~\-()\[\]]")


def normalize_text(text: str | None) -> str:
    """
    숫자를 마스킹하고 공백·문장부호를 제거한다.

    숫자는 **자릿수와 무관하게 하나의 토큰**으로 접는다.
    3,000 과 12,900 이 서로 다른 길이의 마스크가 되면 금액이 만 단위를 넘을 때
    다른 문제로 잡힌다. DA-15(순차공개 가격책정)가 정확히 이 상황이므로
    자릿수를 보존해서는 안 된다.

    공백도 축약이 아니라 제거한다. '+####원' 과 '+#### 원' 이 갈리면
    문구를 다듬은 것만으로 새 문제가 된다.
    """
    if not text:
        return ""
    t = text.strip().lower()
    t = _DIGITS.sub("#", t)      # 3,000 / 12,900 / 4.5 → 모두 '#'
    t = _PUNCT.sub("", t)
    t = _SPACES.sub("", t)       # 공백 완전 제거
    return t[:TEXT_LEN]


def bucket(value: float, grid: float = GRID) -> int:
    """정규화 좌표를 격자 칸 번호로 변환한다."""
    return int(value / grid)


def make(
    rule_id: str,
    *,
    screen_index: int | None = None,
    bbox: list[float] | None = None,
    text: str | None = None,
    label_unit: str = "element",
) -> str:
    """
    Finding fingerprint 를 만든다.

    label_unit 에 따라 재료가 다르다.
      element : rule_id + screen + 위치 격자 + 정규화 텍스트
      screen  : rule_id + screen
      flow    : rule_id  (Flow 전체에 걸린 문제라 위치가 없다)
    """
    parts: list[str] = [rule_id, label_unit]

    if label_unit == "element":
        parts.append(str(screen_index))
        if bbox:
            x, y, w, h = bbox
            # 좌상단 격자 + 크기 구간. 크기는 더 거칠게 본다.
            parts += [str(bucket(x)), str(bucket(y)), str(bucket(w, 0.2)), str(bucket(h, 0.2))]
        parts.append(normalize_text(text))

    elif label_unit == "screen":
        parts.append(str(screen_index))

    # flow / flow_pair 는 rule_id 만으로 식별한다.
    # 화면이 추가·삭제되어도 같은 문제로 추적되어야 하기 때문이다.

    raw = "|".join(parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{rule_id}:{digest}"


def from_label(label: dict) -> str:
    """라벨 JSON 한 건에서 fingerprint 를 만든다."""
    unit = label["label_unit"]
    if unit == "element":
        p = label["primary"]
        return make(
            label["rule_id"],
            screen_index=p["screen_index"],
            bbox=p.get("bbox"),
            text=p.get("text"),
            label_unit=unit,
        )
    if unit == "screen":
        return make(label["rule_id"], screen_index=label.get("screen_index"), label_unit=unit)
    return make(label["rule_id"], label_unit=unit)
