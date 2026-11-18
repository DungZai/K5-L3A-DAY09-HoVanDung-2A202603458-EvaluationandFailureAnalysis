"""M2 edge cases: reject invalid inputs and preserve FAIL-positive semantics."""
import pytest

from lab9 import stats
from lab9.judge import calibrate
from pathlib import Path

pytestmark = pytest.mark.student


def test_all_confusion_cells_and_empty_precision():
    assert stats.confusion(["FAIL", "PASS", "FAIL", "PASS"],
                           ["FAIL", "FAIL", "PASS", "PASS"]) == dict(tp=1, fp=1, fn=1, tn=1)
    assert stats.precision_recall([], []) == (0.0, 0.0)
    assert stats.precision_recall(["FAIL"], ["PASS"]) == (0.0, 0.0)


@pytest.mark.parametrize("human,judge", [(["FAIL"], []), (["UNKNOWN"], ["PASS"])])
def test_confusion_rejects_invalid_labels(human, judge):
    with pytest.raises(ValueError):
        stats.confusion(human, judge)


def test_kappa_extremes_and_empty_sample():
    assert stats.cohen_kappa(["PASS", "FAIL"], ["PASS", "FAIL"]) == 1.0
    assert stats.cohen_kappa(["PASS", "FAIL"], ["FAIL", "PASS"]) == -1.0
    assert stats.cohen_kappa(["PASS", "FAIL"], ["PASS", "PASS"]) == 0.0
    with pytest.raises(ValueError):
        stats.cohen_kappa([], [])
    with pytest.raises(ValueError):
        stats.cohen_kappa(["FAIL"] * 3, ["FAIL"] * 3)


@pytest.mark.parametrize("rates", [(0.5, 0.5, 0.5), (0.5, 0.2, 0.3),
                                   (-0.1, 0.8, 0.9), (0.5, float("nan"), 0.9),
                                   (float("inf"), 0.8, 0.9)])
def test_rogan_gladen_rejects_invalid_calibration(rates):
    with pytest.raises(ValueError):
        stats.rogan_gladen(*rates)


def test_rogan_gladen_upper_clip_and_perfect_judge():
    assert stats.rogan_gladen(1.0, 0.8, 0.9) == 1.0
    assert stats.rogan_gladen(0.3, 1.0, 1.0) == pytest.approx(0.3)


def test_helpful_is_rejected_for_missing_failures():
    result = calibrate(Path("data/eval/judge_helpful_public.csv"))
    assert result["passed"] is False
    assert result["confusion"]["fn"] > result["confusion"]["tp"]
    assert result["recall"] < 0.7
