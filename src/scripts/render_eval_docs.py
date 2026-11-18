"""Generate the Core eval card and PRD tables directly from script-produced reports.

Run from src/: python -m scripts.render_eval_docs
An optional v2 section is appended when reports/advanced_evidence.json exists.
"""
import hashlib
import json
from pathlib import Path
import subprocess

from lab9.eval import load_spec, per_item
from lab9.stats import paired_bootstrap


ROOT = Path("..")
OWNER = "Hồ Văn Dũng — tác giả bài / eval owner"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def main():
    spec = load_spec()
    base = read("reports/baseline_v1.json")
    fixed, broken = read("reports/eval_fixed.json"), read("reports/eval_seeded_regression.json")
    judge = read("../docs/m2_judge_evidence.json")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    revision = commit + (" + working tree tại thời điểm sinh tài liệu" if dirty else "")
    fingerprints = {str(path): hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
                    for path in map(Path, ("lab9/graders.py", "lab9/stats.py", "lab9/gate.py"))}
    metrics = "| Metric | Ngưỡng trong spec | Blocking | Baseline | Fixed | Regression |\n|---|---|---|---|---|---|\n"
    for metric in spec["metrics"]:
        mid = metric["id"]
        threshold = json.dumps(metric.get("threshold", {}), ensure_ascii=False)
        metrics += f"| {mid} | `{threshold}` | {'có' if metric.get('blocking') else 'không'} | {base['metrics'].get(mid)} | {fixed['metrics'].get(mid)} | {broken['metrics'].get(mid)} |\n"
    comparisons = "| Shape | Run ID | pass_rate Δ (PR − baseline) | CI 95% |\n|---|---|---|---|\n"
    bs = spec["bootstrap"]
    for rep in (fixed, broken):
        a, b = per_item(rep, "pass_rate"), per_item(base, "pass_rate")
        keys = sorted(a)
        d, lo, hi = paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                    n_resamples=bs["n_resamples"], rng=bs["rng"], confidence=bs["confidence"])
        comparisons += f"| {rep['shape']} | {rep['run_id']} | {d:+.3f} | [{lo:+.3f}, {hi:+.3f}] |\n"
    tone, helpful = judge["results"]["tone"], judge["results"]["helpful"]
    m = base["manifest"]
    scope = ("Pilot offline: ticket hoàn phí ship do giao trễ hoặc bồi thường hàng hỏng, "
             "mỗi lượt một claim thuộc owner; thiếu mã đơn thì hỏi thêm, trái quyền thì escalated. "
             "Tiền chịu giới hạn approval, paid amount, entitlement và lịch sử hoàn theo host; "
             "không tự tạo approval. Ngoài phạm vi: khách thật, thanh toán thật, gom nhiều đơn, tranh chấp pháp lý.")
    limits = ("MockLLM không đại diện cho model thật; tập v1 nhỏ nên CI rộng, chỉ bắt hồi quy lớn; "
              "judge chỉ replay CSV công khai, chưa có held-out mới hoặc dữ liệu người dùng thật. "
              "Metric FM-08 không áp dụng cho swarm gốc không có reply; parser hiện kiểm tiền VND "
              "tường minh trong reply cuối. Key anchor riêng chỉ giảng viên mới đối chiếu được.")
    fm = "| FM | Grader | Loại | Lý do |\n|---|---|---|---|\n"
    for code, graders, why in [
        ("FM-01", "SecretLeak", "quét secret/PII theo nhãn"),
        ("FM-02", "TrialPass, ReplyAmountCorrect; ApprovalBypass", "kiểm trạng thái/ledger; chỉ báo bypass khi thật sự ghi tiền trái phép"),
        ("FM-03", "DbFactKept, RefundAmountCorrect, ProposalAmountCorrect", "DB là nguồn dữ kiện, kiểm thêm outcome nếu không có override event"),
        ("FM-04", "ProposalAmountCorrect, RefundAmountCorrect", "host cap có thể che proposal cộng/làm tròn sai"),
        ("FM-05", "ProposalAmountCorrect, RefundAmountCorrect", "bắt trừ lịch sử hai lần"),
        ("FM-06", "TrialPass, ProposalAmountCorrect, RefundAmountCorrect", "bắt hậu quả dùng clause sai hiệu lực"),
        ("FM-07", "ApprovalBypass, TrialPass", "phát hiện unexpected ledger rows"),
        ("FM-08", "ReplyAmountCorrect", "đối chiếu tiền reply và ledger"),
    ]:
        fm += f"| {code} | {graders} | code | {why} |\n"
    card = f"""# Eval card — LogiX-VN refund agent

Sinh bằng `python -m scripts.render_eval_docs`; số liệu lấy từ report, không nhập tay.

- **Baseline run ID:** `{base['run_id']}`; **eval set SHA:** `{m['eval_set_sha']}`.
- **Code / grader revision:** `{revision}`; report manifest Python `{m['python']}`.
- **SHA-256 source UTF-8/LF:** `{json.dumps(fingerprints)}`.
- **Eval set:** {m['eval_set']} ({m['items']} item × {len(m['seeds'])} seed), nguồn lab8_public; labels riêng `{spec['labels']}`.
- **Metric spec:** {spec['metric_spec_version']}; **seeds:** {m['seeds']}.
- **Gate owner:** {OWNER}.
- **Phạm vi:** {scope}

## Metric, ngưỡng và kết quả v1

{metrics}
Các cột lần lượt thuộc run `{base['run_id']}`, `{fixed['run_id']}`, `{broken['run_id']}`.

## Paired bootstrap v1

{comparisons}
Lấy mẫu cặp item sau khi trung bình qua seed, {bs['n_resamples']} resample, rng={bs['rng']}, confidence={bs['confidence']}, method={bs['method']}.
Gate swarm/fixed exit 0; seeded_regression exit 1, có pass_rate trong danh sách chặn.
CI Core đã xanh: [workflow run](https://github.com/DungZai/K5-L3A-DAY09-HoVanDung-2A202603458-EvaluationandFailureAnalysis/actions/runs/44227867007).

## Judge và trace case

Run `{judge['run_id']}`: tone κ={tone['kappa']}, P={tone['precision']}, R={tone['recall']} đạt sàn; helpful κ={helpful['kappa']}, P={helpful['precision']}, R={helpful['recall']} không đạt, loại khỏi gate. [Audit](judge_audit.md).
[Trace case](trace_case.md): C-002@11, event #3 model_override thay DB 2 ngày bằng ticket 5 ngày; regression test `test_seeded_regression_c002_first_wrong_step` bắt bản lỗi và cho fixed qua.

## Giới hạn và versioning

{limits}

Thêm/thay item hoặc nhãn → tăng eval_set_version và sinh baseline mới. Đổi metric/ngưỡng → tăng metric_spec_version; cùng eval-set version chỉ được siết ngưỡng. Metric spec v1 tăng 1.0→1.1 khi thêm metric M3; không đổi tính năng agent.
"""
    advanced = Path("reports/advanced_evidence.json")
    if advanced.exists():
        from scripts.render_v2_docs import section
        card += section(read(advanced))
    write("docs/eval_card.md", card)
    prd = f"""# PRD v1.1 — LogiX-VN refund agent

Sinh bằng `python -m scripts.render_eval_docs` từ report v1. v1.1 bổ sung tiêu chí đánh giá và release gate, không đổi tính năng v1.0.

## 1. Thay đổi so với v1.0

Thay tiêu chí demo thủ công bằng metric/spec có ngưỡng và report có run ID; ánh xạ rủi ro sang failure taxonomy và code grader. Revision generator `{commit}`.

## 2. Phạm vi pilot

{scope}
Môi trường đo: MockLLM, {m['items']} item × {len(m['seeds'])} seed; chưa pilot trên người dùng thật.

## 3. Định nghĩa chạy đúng

Baseline `{base['run_id']}`, SHA `{m['eval_set_sha']}`, metric spec {spec['metric_spec_version']}.

{metrics}
"Giảm có ý nghĩa" là CI {bs['confidence'] * 100:g}% của Δ (PR − baseline) nằm hoàn toàn dưới 0. Giá trị safety là số lần vi phạm; capability là tỉ lệ đạt. Metric nonblocking chỉ cảnh báo, không tự ý dùng làm lý do chặn release.

{comparisons}
## 4. Failure mode → grader

{fm}
Tiền/approval luôn chấm bằng code. Judge chỉ dùng cho tiêu chí đã qua calibration: tone dùng được trong phạm vi replay; helpful bị loại, xem [judge audit](judge_audit.md).

## 5. Cổng release và trách nhiệm

```text
python -m lab9.gate --pr reports/eval_<shape>.json --baseline reports/baseline_v1.json
```

Eval owner: {OWNER}. Gate exit 1 thì không merge; owner đọc metric/trace, sửa nguyên nhân rồi chạy lại, không sửa report hay nới sàn. Baseline hiện được sinh trên nhánh làm bài theo hướng dẫn lab, sẽ nằm trên main khi merge PR; chưa xác nhận branch protection được cấu hình. CI so SHA và baseline với chính swarm chạy lại. Phát hành thực tế cần baseline từ nhánh được bảo vệ.

Ngoại lệ: phải có người chịu trách nhiệm sản phẩm và eval owner phê duyệt rõ trong PR; bài lab này không thực hiện waiver để bỏ qua gate. Workflow xanh chưa phải phê duyệt dùng tiền thật.

## 6. Bằng chứng còn thiếu / rủi ro mở

{limits}

## 7. Khi nào lên v1.2

Thêm/thay dữ liệu → tăng eval_set_version và sinh baseline. Đổi metric/ngưỡng → tăng metric_spec_version, ghi lý do; không nới sàn trên cùng eval-set version. M5–M7 dùng eval set v2, được mô tả riêng trong [eval card](eval_card.md).

## Phê duyệt

| Vai trò | Người phụ trách | Trạng thái |
|---|---|---|
| Product | Chưa chỉ định cho triển khai thực tế | Chưa phê duyệt pilot thực tế |
| Eval owner | {OWNER} | Bằng chứng kỹ thuật từ report/CI; không thay chữ ký phê duyệt của người dùng |
"""
    write("docs/PRD_v1.1.md", prd)
    print("generated docs/eval_card.md and docs/PRD_v1.1.md from reports")


if __name__ == "__main__":
    main()
