"""Render the v2 eval-card section from Advanced/Expert evidence."""
from pathlib import Path

from lab9.eval import load_spec


def section(evidence):
    spec = load_spec(Path(evidence["spec"]))
    metrics = evidence["metrics"]
    text = f"""
## v2 — Advanced / Expert

Baseline `{evidence['baseline']}`, eval-set SHA `{evidence['manifest']['eval_set_sha']}`,
{evidence['manifest']['items']} item × {len(evidence['manifest']['seeds'])} seed;
metric spec {spec['metric_spec_version']}. v2 gồm v1 và adversarial pack gốc,
không sửa pack/variant/trap. Labels v2 tách khỏi item. Report nằm trong
`src/reports/baseline_v2.json`, `src/reports/v2/`; bằng chứng tổng hợp
`src/reports/advanced_evidence.json` do `scripts.advanced_evidence` sinh.

| Shape | pass_rate | pass_hat_5 | reply_amount_correct | Metric/slice bị chặn |
|---|---|---|---|---|
"""
    for name, values in metrics.items():
        why = ", ".join(evidence["decisions"][name]["blocked"]) or "merge"
        text += f"| {name} | {values['pass_rate']} | {values['pass_hat_5']} | {values['reply_amount_correct']} | {why} |\n"
    text += "\n### Sàn và A/A\n\n"
    floor = next(m["threshold"]["min"] for m in spec["metrics"] if m["id"] == "pass_hat_5")
    text += (f"A/A dùng hai bộ seed 11/22/33/44/55 và 66/77/88/99/110, cùng swarm. "
             f"Cả hai có pass_hat_5={metrics['swarm']['pass_hat_5']}, mọi Δ=0. "
             f"Chọn sàn blocking pass_hat_5={floor}, thấp hơn mức của cả hai run và có khoảng đệm "
             "lớn hơn độ dao động quan sát (0). Sàn nằm ngoài dải nhiễu quan sát, không được chọn bằng cách khớp tên mutant.\n\n"
             "```text\n" + evidence["aa_output"] + "```\n\n"
             "Với model thật, các lần sinh có thể thay đổi dù cùng cấu hình, nên dải A/A có thể rộng hơn 0; "
             "cần đo nhiều lần và đặt biên chấp nhận có khoảng đệm phù hợp với dải đó. "
             "pass@k là xác suất ít nhất một lượt đạt, pass^k là xác suất cả k lượt đạt, "
             "tính bằng tổ hợp không hoàn lại trên từng item rồi trung bình. "
             "Không dùng pass@k cao để thay cho độ ổn định pass^k.\n\n")
    text += "### Slice nào bắt lỗi nào\n\n"
    text += "| Slice | Floor | Metric | Blocking |\n|---|---|---|---|\n"
    for s in spec["slices"]:
        text += f"| {s['name']} | {s['min']} | {s['metric']} | {s['blocking']} |\n"
    text += ("\n`money_movement` chặn slice_regression: proposal cộng clause sai trên claim có tiền, "
             "trong khi trung bình toàn tập vẫn có thể qua sàn. `adversarial` bảo vệ các prompt tấn công; "
             "`denial` kiểm việc giữ quyết định từ chối. Slice dùng tag từ nhãn, khóa với baseline, "
             "và bootstrap theo item. `pass_hat_5` chặn flaky_regression. "
             "Metric reply/ledger bắt FM-08 độc lập với Lab 8 pass_rate.\n\n"
             "### Mutation và integrity\n\n```text\n" + evidence["mutation_output"] + "```\n\n"
             "```text\n" + evidence["traps_output"] + "```\n\n")
    text += "| Trap | Gate CLI cuối |\n|---|---|\n"
    for name, output in evidence["trap_gate_outputs"].items():
        text += f"| {name} | {output.strip().splitlines()[-1]} |\n"
    quiet = evidence["quiet_validation"]
    text += ("\nIntegrity kiểm cả PR và baseline: evaluator_failures, giá trị thiếu/NaN/inf, "
             "đủ tích item×seed và không trùng cặp, giữ nguyên slice, tính lại aggregate từ row. "
             "Ratchet chống bỏ metric/slice, tắt blocking, bỏ no_significant_drop hoặc nới ngưỡng "
             "trên cùng eval-set version. Test bổ sung bao phủ dòng trùng giữ nguyên số dòng và "
             "evaluator_failures trên report xanh — hai dạng trap ẩn được gợi ý trong CHECKPOINTS.\n\n"
             f"Biến thể validation không ghi model_override vẫn bị chặn: db_fact_kept={quiet['metrics']['db_fact_kept']}, "
             f"blocked={quiet['blocked']}. Đây là kiểm chứng bổ sung, không thay test ẩn của giảng viên.\n\n"
             "### Coverage và giới hạn v2\n\n")
    text += "| FM | Số item v2 |\n|---|---|\n"
    for fm, count in sorted(evidence["coverage"].items()):
        text += f"| {fm} | {count} |\n"
    text += ("\nMỗi FM bị adversarial pack tấn công có ít nhất 3 item. FM-09 có ba trace "
             "đối chứng C-110/C-113/C-114: quyền truy cập bị từ chối và escalated, không có khoản hoàn. "
             "Đó là bằng chứng hàng rào hoạt động, không khẳng định baseline đã rò dữ liệu principal.\n\n"
             "Năm seed không đủ phát hiện ổn định một bug xác suất 1/3; không hạ sàn cho tới khi bắt được "
             "một bug hiếm. Chưa có held-out thật, chưa chạy model thật; các test/variant/trap ẩn chỉ có "
             "ở giảng viên. Integrity không chứng minh một report giả hoàn toàn nhất quán là thật; "
             "CI vẫn cần chạy lại agent, kiểm provenance và dùng baseline/spec được bảo vệ. "
             "Parser FM-08 hiện không hiểu mọi cách diễn đạt tiền bằng chữ hoặc nhiều khoản tiền khác mục đích.\n")
    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
