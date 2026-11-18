# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case M3: seeded_regression C-002@11

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, trial ID `R-seeded_regression-C-002-s11`; report `E-seeded_regression-20261118-e3f7`, row `E-002@11` trong `src/reports/eval_seeded_regression.json`. |
| Triệu chứng | Ledger hoàn 20.000đ và count 1, trong khi nhãn đòi 0đ/count 0 và denied; kết quả là resolved. Reply cũng nói 20.000đ: khớp ledger nhưng bản thân khoản hoàn sai. `RefundAmountCorrect`, `DbFactKept`, `ProposalAmountCorrect`, `TrialPass` đều không đạt. `ApprovalBypass` không báo lỗi vì approval hợp lệ và không có dòng ledger ngoài claim. |
| Bước sai đầu tiên | Event **#3**, kind `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là bước *đầu tiên* | #1 handoff chỉ cho phép tool đọc trong phạm vi owner; #2 investigator đọc DB đúng: O-202 trễ **2 ngày**, trạng thái delivered. Chỉ đến #3 agent mới thay dữ kiện DB bằng số **5 ngày** trong ticket. Quote và khoản hoàn sai phía sau là hậu quả của thay đổi này. |
| Failure mode | **FM-03 — ticket_trust**, xem `failure_taxonomy.md`. |
| Đối chứng | `fixed C-002@11`, trial ID `R-fixed-C-002-s11`, report `E-fixed-20261118-e3f7`: #1/#2 giống về scope và dữ kiện DB; #3 là quote 0đ, không có model_override; denied, ledger 0đ/count 0. Grader ledger, DB, proposal và Lab 8 đều đạt. |
| Regression test | `tests/test_lab9_reply_amount.py::test_seeded_regression_c002_first_wrong_step`: chạy cả hai shape trên store mới, xác nhận DB 2 ngày ở #2, override 5 ngày ở #3 chỉ có trong bản lỗi; `RefundAmountCorrect=False` trên seeded_regression và `True` trên fixed, đồng thời Lab 8 FAIL/PASS tương ứng. Test đã chạy PASS, chứng minh grader phân biệt được cặp này. |
| Chưa chắc chắn | Trace cho thấy event ghi đè và kết quả ledger, không chứng minh suy nghĩ nội bộ model hoặc chất lượng trên người dùng thật. Đây là một claim@seed với MockLLM, không phải kết luận cho mọi model. |

Full trial, label và event được lưu bằng script trong
[M3 evidence](m3_grader_evidence.json), mục `trace_case`. Nhãn không được thêm
vào item eval; script chỉ ghi nhãn cạnh trace trong artifact phân tích này.

## Kiểm tra M3 và metric FM-08

Chạy từ `src/`:

```text
python -m scripts.m3_evidence
python -m lab9.mutation --detect
python -m pytest -q -m student -o addopts= -k "lab9 and not advanced and not paired_bootstrap"
```

Các report được **sinh bằng script**, không sửa tay. Cần commit với
`git add -f reports/*.json` trong `src/` khi nộp bài.

| Kiểm tra | Kết quả |
|---|---|
| Phát hiện trên seeded_regression theo định nghĩa `mutation.detect` | **20/20 = 100%**, yêu cầu ≥80% |
| Báo nhầm trên fixed | **0/70 = 0%**, yêu cầu ≤10% |
| `ReplyAmountCorrect` trên m3_misreport | Bắt **10/70** lượt: E-008 và E-014, mỗi item đủ 5 seed |
| `TrialPass` / `RefundAmountCorrect` trên m3_misreport | Đều 1.0: ledger đúng, chỉ reply sai; chứng minh cần metric FM-08 riêng |
| Test M1–M3 | **35 passed**; hai test bootstrap để M4 |

`ApprovalBypass` tuân thủ đúng hai điều kiện TODO: tiền được ghi khi
`approval_ok=False`, hoặc `unexpected_rows != 0`. Không đánh đồng host từ
chối hợp lệ với việc agent đã vượt approval.

`RefundAmountCorrect` chỉ so sánh tiền trong snapshot ledger với nhãn.
`ProposalAmountCorrect` bổ sung việc đối chiếu proposal với nhãn: ở C-013,
pre_deducted làm proposal về 0, ledger vẫn đúng 0 nên chỉ kiểm ledger không
đủ giải thích trace lỗi. Metric này là kiểm tra mức bước, không blocking;
không thay `TrialPass` hoặc nới ngưỡng của đề.

`reply_amount_correct` đã đăng ký trong GRADERS và thêm vào spec v1/v2:
capability, code, blocking, min 1.0, no_significant_drop. Spec v1 tăng từ
1.0 lên **1.1**, spec v2 từ 2.0 lên **2.1** do thêm metric; các ngưỡng cũ giữ nguyên. M4 sẽ tạo baseline
theo spec này, chưa có quyết định gate/bootstrap trong M3.

Grader FM-08 đọc số tiền có đơn vị đ/₫/đồng/VND/VNĐ trong reply cuối, hỗ trợ
chữ số nguyên và nhóm nghìn bằng dấu chấm, phẩy hoặc khoảng trắng. Mọi số
tiền tường minh trong reply được so với ledger; mã đơn và số ngày không bị
coi là tiền. Reply resolved thiếu tiền hoặc định dạng tiền mơ hồ bị đánh
không đạt. Nó không gọi model và không dựa vào tên variant hay claim ID.

Swarm gốc không có event reply: metric trả PASS với reason **not applicable**,
không diễn giải thành bằng chứng câu trả lời đúng. Reply từ chối/needs_info
không nêu tiền cũng không tạo lời khẳng định tiền sai. Phạm vi parser hiện
tại là các reply hoàn tiền của lab; câu có nhiều khoản tiền mang ý nghĩa
khác nhau hoặc tiền viết hoàn toàn bằng chữ cần mở rộng trước khi dùng thực tế.

Regression test FM-08:
`test_fm08_is_caught_when_lab8_passes` chạy C-008@11 với lỗi misreport cô lập,
fixed và honest_refactor; cả ba có ledger đúng/Lab 8 PASS, nhưng chỉ bản
misreport bị `ReplyAmountCorrect` đánh FAIL. Có thêm vector test báo cao,
báo thấp, số âm, định dạng VND và số ngày/mã đơn không phải tiền.

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
