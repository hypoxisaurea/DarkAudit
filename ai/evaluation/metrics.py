"""Dependency-free multilabel evaluation metrics."""


def precision_recall_f1(predicted: set[str], expected: set[str]) -> tuple[float, float, float]:
    true_positive = len(predicted & expected)
    precision = true_positive / len(predicted) if predicted else float(not expected)
    recall = true_positive / len(expected) if expected else float(not predicted)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1
