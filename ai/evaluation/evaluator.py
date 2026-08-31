"""Evaluate analyzer output against JSONL golden cases."""

import json
from dataclasses import dataclass
from pathlib import Path

from .metrics import precision_recall_f1


@dataclass(slots=True)
class EvaluationResult:
    cases: int
    precision: float
    recall: float
    f1: float


class Evaluator:
    def evaluate_labels(self, predicted: list[set[str]], expected: list[set[str]]) -> EvaluationResult:
        if len(predicted) != len(expected):
            raise ValueError("Predicted and expected case counts differ")
        scores = [precision_recall_f1(p, e) for p, e in zip(predicted, expected)]
        if not scores:
            return EvaluationResult(0, 0.0, 0.0, 0.0)
        return EvaluationResult(len(scores), *(sum(row[i] for row in scores) / len(scores) for i in range(3)))

    @staticmethod
    def load_golden(path: str | Path) -> list[dict]:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]
