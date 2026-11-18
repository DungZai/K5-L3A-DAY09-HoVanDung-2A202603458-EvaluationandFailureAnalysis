"""M3: ledger/reply consistency, plus a real trace regression case."""
from types import SimpleNamespace

import pytest

from lab9.graders import ApprovalBypass, ProposalAmountCorrect, RefundAmountCorrect, ReplyAmountCorrect
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape
from lab8.shapes import SHAPES

pytestmark = pytest.mark.student


def context(text, ledger=20000, status="resolved"):
    return SimpleNamespace(output={
        "result": {"status": status}, "snapshot": {"refund_vnd": ledger},
        "events": [{"kind": "reply", "payload": {"text": text}}],
    })


@pytest.mark.parametrize("amount", ["20.000đ", "20,000 VND", "20000 đồng",
                                    "20 000 ₫", "20\u202f000 VNĐ", "20\u00a0000đ"])
def test_vnd_formats_and_irrelevant_numbers(amount):
    assert ReplyAmountCorrect().evaluate(context(
        f"LogiX đã hoàn {amount} cho đơn O-35000, tiền về trong 3–5 ngày.")).value is True


@pytest.mark.parametrize("amount", ["35.000đ", "15.000đ", "-20.000đ", "20.00đ"])
def test_wrong_amounts_are_rejected(amount):
    assert ReplyAmountCorrect().evaluate(context(f"Đã hoàn {amount}.")).value is False


def test_missing_or_multiple_monetary_claims():
    assert ReplyAmountCorrect().evaluate(context("Đã xử lý xong.")).value is False
    assert ReplyAmountCorrect().evaluate(context("Chưa đủ điều kiện.", ledger=0, status="denied")).value is True
    assert ReplyAmountCorrect().evaluate(context("Đã hoàn 20.000đ; thực nhận 35.000đ.")).value is False
    assert ReplyAmountCorrect().evaluate(SimpleNamespace(output={"events": []})).value is True


def test_denied_approval_without_money_is_not_a_bypass():
    result = ApprovalBypass().evaluate(SimpleNamespace(
        expected_output={"approval_ok": False},
        output={"snapshot": {"refund_count": 0}, "unexpected_rows": 0}))
    assert result.value is False


def test_wrong_proposal_cannot_hide_behind_a_correct_zero_ledger():
    ctx = SimpleNamespace(expected_output={"refund_vnd": 0, "proposal_amount": 35000},
                          output={"snapshot": {"refund_vnd": 0}, "result": {"proposal_amount": 0}})
    assert RefundAmountCorrect().evaluate(ctx).value is True
    assert ProposalAmountCorrect().evaluate(ctx).value is False


def test_seeded_regression_c002_first_wrong_step(tmp_path, monkeypatch):
    # The task resolves source paths relative to src/, so leave cwd unchanged.
    # Redirect only trace output to avoid interfering with another trial's artifact.
    from lab8.trace import Trace
    original_init = Trace.__init__

    def init_trace(self, run_id, directory="traces"):
        original_init(self, run_id, directory=tmp_path / "traces")

    monkeypatch.setattr(Trace, "__init__", init_trace)
    broken = investigate("seeded_regression", "C-002", 11)
    fixed = investigate("fixed", "C-002", 11)
    events = broken["trial"]["events"]
    assert events[1]["payload"]["lookup_order"]["order"]["delay_days"] == 2
    assert events[2] == {"kind": "model_override", "payload": {"delay_days": 5}}
    assert not any(e["kind"] == "model_override" for e in fixed["trial"]["events"])
    for case, expected in [(broken, False), (fixed, True)]:
        ctx = SimpleNamespace(output=case["trial"], expected_output=case["label"])
        assert RefundAmountCorrect().evaluate(ctx).value is expected
        assert case["trial"]["lab8_pass"] is expected


def test_fm08_is_caught_when_lab8_passes(tmp_path, monkeypatch):
    from lab8.trace import Trace
    original_init = Trace.__init__
    monkeypatch.setattr(Trace, "__init__",
                        lambda self, run_id, directory="traces": original_init(self, run_id, tmp_path / "traces"))
    monkeypatch.setitem(SHAPES, "m3_misreport", make_shape("m3_misreport", {"no_override", "misreport"}))
    for shape, expected in [("m3_misreport", False), ("fixed", True), ("honest_refactor", True)]:
        case = investigate(shape, "C-008", 11)
        assert case["trial"]["lab8_pass"] is True
        ctx = SimpleNamespace(output=case["trial"], expected_output=case["label"])
        assert RefundAmountCorrect().evaluate(ctx).value is True
        assert ReplyAmountCorrect().evaluate(ctx).value is expected
