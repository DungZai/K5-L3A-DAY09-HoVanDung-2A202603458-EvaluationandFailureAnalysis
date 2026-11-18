# M4 — paired bootstrap và Core gate

Baseline `src/reports/baseline_v1.json` được sinh bằng lệnh của đề:

```text
cd src
python -m lab9.eval --shape swarm --spec config/metric_spec.yaml --out reports/baseline_v1.json
python -m scripts.m4_evidence
python -m pytest -q -m student -o addopts= -k "lab9 and not advanced"
```

Không sửa tay report. Bằng chứng gate, CI và run ID được script ghi vào
`src/reports/m4_gate_evidence.json`; output chặn regression nằm trong
`docs/pr_m4_body.md` để đưa vào PR.

## Cấu hình và đơn vị lấy mẫu

Eval set v1, SHA `508fdea1690c`, 14 item × 5 seed 11/22/33/44/55;
metric spec 1.1. Baseline run ID `E-swarm-20261118-508f`.

`paired_bootstrap` lấy mẫu **cặp item**, sau khi mỗi item đã được lấy trung
bình qua seed. Dùng `scipy.stats.bootstrap(paired=True, method="percentile")`,
1000 lần lấy mẫu, `numpy.random.default_rng(2027)`, confidence 0.95 theo spec.
Delta = PR − baseline. Hai vector bằng nhau trả `(0, 0, 0)`.

Gate giữ nguyên các ngưỡng có sẵn, chặn metric blocking dưới sàn hoặc có CI
nằm hoàn toàn dưới 0; metric safety vẫn max 0. Confidence được truyền từ
spec tới bootstrap. Không triển khai TODO M5/M7 ở bước này.

## Kết quả local

| Shape | Run ID | pass_rate | Delta vs baseline | CI 95% | Gate exit |
|---|---|---|---|---|---|
| swarm (PR) | E-swarm-20261118-508f | 0.9857 | 0.000 | [0.000, 0.000] | 0 |
| fixed | E-fixed-20261118-508f | 1.0000 | +0.014 | [0.000, +0.043] | 0 |
| seeded_regression | E-seeded_regression-20261118-508f | 0.7143 | −0.271 | [−0.500, −0.057] | 1 |

Delta/CI regression khớp giá trị tham chiếu trong `CHECKPOINTS.md` trong sai
số ≤0.01. Danh sách bị chặn có `pass_rate`:

```text
exit 1 — blocked: refund_amount_correct, pass_rate, reply_amount_correct
```

`lab9.ci_check` exit 0, xác nhận baseline là swarm, cùng eval set và metric
khớp PR swarm, có metric FM-08 blocking đã đăng ký grader. Các báo cáo đều
được sinh bằng `lab9.eval`; mỗi report có 70 trial. Test Core **38 passed**,
bao gồm hai test bootstrap trước đó chưa làm ở M3.

Eval set được ghi với newline LF và `.gitattributes` cố định `eol=lf` cho
JSONL eval. Điều này giữ cùng bytes/SHA giữa Windows và Linux CI; không
thay phép kiểm SHA hoặc nội dung item. Test portability kiểm file sinh ra
không có CRLF. Baseline và report đã được sinh lại bằng script sau sửa này.

`src/harness_map.yaml` tăng version lên 1.2, thêm section `eval` theo mẫu
`src/harness_map.eval.yaml`. Nhánh làm bài là `starter/d09`; các report cần
được commit bằng `git add -f src/reports/*.json` từ root repo.

Các kết quả trên là kiểm tra local tương ứng workflow gốc. CI GitHub chỉ
được xác nhận sau khi nhánh được push, PR trong fork được mở và job
`eval-gate` kết thúc thành công. Eval card/PRD cuối Core là các tài liệu
riêng; không tuyên bố đã xong toàn bộ hồ sơ nộp chỉ từ kết quả M4.
