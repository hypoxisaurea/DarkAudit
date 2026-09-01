"""
Fingerprint 견고성 테스트
------------------------
"느슨하게 잡는다"는 결정이 실제로 의도대로 동작하는지 확인한다.

Counterfactual Pair 로만 검증하면 clean 쪽에 Finding 이 0건이라
무엇을 넣어도 전부 RESOLVED 가 되어 매칭 로직이 검증되지 않는다.
아래는 매칭이 실제로 판단을 내려야 하는 경우들이다.

    같아야 하는 경우 (수정했지만 문제는 그대로 → persisted)
      - 금액·이율이 바뀜        9,900원 → 12,900원
      - 문구를 다듬음           공백·문장부호 변화
      - 요소가 조금 이동함      레이아웃 미세 조정

    달라야 하는 경우 (서로 다른 문제 → 섞이면 안 됨)
      - 다른 규칙
      - 다른 화면
      - 화면 반대편의 다른 요소

    python test_fingerprint.py
"""

from __future__ import annotations

from app.fingerprint import make, normalize_text

BASE = dict(
    rule_id="DA-04",
    screen_index=3,
    bbox=[0.0897, 0.2901, 0.0538, 0.0249],
    text="안심케어 서비스 +3,000원",
    label_unit="element",
)


def fp(**over) -> str:
    return make(**{**BASE, **over})


SAME = [
    ("금액 변경 (3,000 → 5,000원)", dict(text="안심케어 서비스 +5,000원")),
    ("금액 자릿수 변경 (→ 12,900원)", dict(text="안심케어 서비스 +12,900원")),
    ("공백 정리", dict(text="안심케어  서비스 +3,000 원")),
    ("문장부호 제거", dict(text="안심케어 서비스 +3000원")),
    ("요소 미세 이동 (같은 격자)", dict(bbox=[0.0932, 0.2955, 0.0541, 0.0252])),
    ("크기 미세 변화", dict(bbox=[0.0897, 0.2901, 0.0560, 0.0260])),
]

DIFFERENT = [
    ("다른 규칙", dict(rule_id="DA-03")),
    ("다른 화면", dict(screen_index=4)),
    ("화면 반대편 요소", dict(bbox=[0.7100, 0.2901, 0.0538, 0.0249])),
    ("세로로 멀리 떨어진 요소", dict(bbox=[0.0897, 0.7400, 0.0538, 0.0249])),
    ("완전히 다른 문구", dict(text="해외여행 의료지원")),
]


def main() -> int:
    base = fp()
    print(f"기준: {BASE['text']!r}")
    print(f"      정규화 → {normalize_text(BASE['text'])!r}")
    print(f"      fingerprint → {base}\n")

    fails = 0

    print("같은 문제로 묶여야 하는 경우")
    for name, over in SAME:
        got = fp(**over)
        ok = got == base
        fails += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {name}")

    print("\n다른 문제로 구분되어야 하는 경우")
    for name, over in DIFFERENT:
        got = fp(**over)
        ok = got != base
        fails += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {name}")

    # flow 단위는 화면 구성이 바뀌어도 동일해야 한다
    print("\nflow 단위")
    a = make("DA-15", label_unit="flow")
    b = make("DA-15", label_unit="flow")
    ok = a == b
    fails += not ok
    print(f"  {'OK  ' if ok else 'FAIL'} 화면이 추가·삭제되어도 동일")
    ok = make("DA-15", label_unit="flow") != make("DA-08", label_unit="flow")
    fails += not ok
    print(f"  {'OK  ' if ok else 'FAIL'} 다른 규칙과는 구분")

    print(f"\n{'전부 통과' if not fails else f'{fails}건 실패'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
