# Judge audit — M2

Nguồn: `src/data/eval/judge_tone_public.csv` và
`src/data/eval/judge_helpful_public.csv`, mỗi tập 100 dòng. Backend là CSV
replay, không gọi model/API. Run ID **`J-M2-526a9db16ad1`**;
[kết quả sinh bằng script](m2_judge_evidence.json) chứa ma trận nhầm lẫn,
bất đồng và SHA-256 của CSV cùng code thống kê/judge.

## Kết quả calibration

**FAIL là lớp dương**: TP là lỗi người gắn FAIL và judge cũng phát hiện FAIL;
FN là lỗi bị judge cho PASS; FP là trường hợp người gắn PASS nhưng judge báo FAIL.
Giữ nguyên FLOORS của đề: κ ≥ 0.6, Precision ≥ 0.8, Recall ≥ 0.7;
phải đạt cả ba, κ không xác định thì FAIL calibration.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có, cả ba | Dùng cho tiêu chí tone đã calibration trên replay này |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không: κ và Recall dưới sàn | Loại khỏi gate |

| Tiêu chí | TP | FP | FN | TN | Tỉ lệ lỗi judge quan sát | Sensitivity | Specificity | Tỉ lệ lỗi hiệu chỉnh Rogan–Gladen |
|---|---|---|---|---|---|---|---|---|
| tone_ok | 24 | 4 | 6 | 66 | 0.280 | 24/30 = 0.800 | 66/70 ≈ 0.943 | 0.300 |
| helpful | 9 | 0 | 21 | 70 | 0.090 | 9/30 = 0.300 | 70/70 = 1.000 | 0.300 |

Precision = TP/(TP+FP), Recall = TP/(TP+FN). Kappa hiệu chỉnh mức đồng thuận
ngẫu nhiên theo phân bố nhãn. Rogan–Gladen dùng
`(p_observed + specificity - 1)/(sensitivity + specificity - 1)`, chặn kết quả
trong [0,1]. Hàm P/R trả 0 khi mẫu số bằng 0; kappa báo không xác định nếu
không có quan sát hoặc expected agreement bằng 1.

Rogan–Gladen ở đây dùng sensitivity/specificity từ chính CSV calibration;
việc kết quả bằng tỉ lệ lỗi người 30/100 không phải bằng chứng held-out và
không làm helpful đạt FLOORS. Không dùng hiệu chỉnh này để bỏ qua lỗi từng
case hay thay thế kiểm tra tiền/approval bằng code.

## Audit thủ công các bất đồng

Đọc toàn bộ reply và cột `note`/`human_failure` gốc; các đoạn bên dưới là
trích ngắn. Quyết định là nhận định audit từ dữ liệu được cung cấp, không
phải nhãn mới do người dùng xác nhận. Chưa sửa CSV hay replay verdict.

| # | Case / tiêu chí | Judge nói | Người nói | Ai đúng theo bằng chứng được cung cấp? | Hành động sửa rubric/nhãn |
|---|---|---|---|---|---|
| 1 | H-008 / tone: “Em đã hoàn tiền… nha” | PASS | FAIL | Người; cách xưng hô quá suồng sã theo chuẩn CS của bài. | Nêu rõ LogiX + anh/chị; thêm ví dụ FAIL với “em”, “nha”; không coi thân thiện là đủ. |
| 2 | H-017 / tone: “bạn ơi… rồi nha” | PASS | FAIL | Người, theo note ngữ cảnh khách lớn tuổi. | Đưa quy tắc xưng hô vào rubric và cung cấp ngữ cảnh khi đánh giá; không đoán tuổi chỉ từ reply. |
| 3 | H-029 / tone: “không cần nhắn thêm” | PASS | FAIL | Người; mệnh lệnh ngăn khách phản hồi dù mở đầu lịch sự. | Đánh giá toàn câu; lời “Dạ, vui lòng” không bù được câu ra lệnh. |
| 4 | H-042 / tone: đã hoàn tiền, có thời gian nhận | FAIL | PASS | Người; reply ngắn vẫn lịch sự và đủ ý. | Không bắt buộc xin lỗi trong mọi phản hồi; độ dài và số câu xin lỗi không phải tiêu chí PASS. |
| 5 | H-051 / tone: dùng “refund” | FAIL | PASS | Người; note xác nhận CS LogiX cho phép thuật ngữ này. | Cho phép thuật ngữ nghiệp vụ được duyệt; không tự động FAIL chỉ vì một từ tiếng Anh. |
| 6 | H-063 / tone: “sẽ hoàn thêm” | PASS | FAIL | Người theo note: hứa thêm ngoài kết quả hệ thống. | Nêu cấm cam kết vượt kết quả được phép; đối chiếu quyền/số tiền bằng code khi có dữ liệu, không chỉ nhìn từ lịch sự. |
| 7 | H-070 / tone: emoji cười trong khiếu nại | PASS | FAIL | Người; không phù hợp ngữ cảnh khiếu nại. | Bổ sung ví dụ FAIL về emoji cười trong khiếu nại; không cộng điểm vì thân thiện hình thức. |
| 8 | H-081 / tone: “chưa đủ điều kiện…” | FAIL | PASS | Theo note của bộ dữ liệu, judge đúng và người đọc nhầm ticket; riêng reply không đủ tái kiểm ngữ cảnh này. | Đánh dấu đề nghị adjudication với ticket gốc và sửa nhãn ở phiên bản dữ liệu kế tiếp sau xác nhận; không âm thầm sửa vector công khai. |
| 9 | H-088 / tone: lặp “Dạ, dạ” | FAIL | PASS | Người; lỗi gõ nhỏ không đổi ý và không gây thiếu tôn trọng. | Cho phép lỗi lặp từ nhỏ nếu câu vẫn rõ, lịch sự; phân biệt typo với giọng điệu không phù hợp. |
| 10 | H-094 / tone: câu tiếng Việt mất dấu | PASS | FAIL | Người theo chuẩn trong note của bài. | Ghi rõ yêu cầu tiếng Việt có dấu cho phản hồi CS này; thêm ví dụ mất dấu để tránh judge tự suy chuẩn khác. |
| 11 | HL-015 / helpful: reply 55.000đ, note ledger 40.000đ | PASS | FAIL | Người theo ledger được ghi trong note. | Sai tiền phải FAIL dù lịch sự; chấm số tiền bằng code so với ledger, tương ứng FM-08. |
| 12 | HL-016 / helpful: xin lỗi dài, reply 55.000đ, ledger 35.000đ | PASS | FAIL | Người theo note; lời xin lỗi không sửa được sai tiền. | Tách tính đúng khỏi văn phong; không cộng điểm xin lỗi/độ dài để bù lỗi factual. |
| 13 | HL-028 / helpful: reply 50.000đ, ledger 35.000đ | PASS | FAIL | Người theo note; câu xin lỗi lặp che lỗi số tiền. | Bổ sung cặp ví dụ cùng kết quả nhưng khác độ dài; yêu cầu quyết định giống nhau nếu cùng sai ledger. |
| 14 | HL-047 / helpful: “Ok bạn… xử lý rồi nhé” | PASS | FAIL | Người theo `human_failure=sai xưng hô`. | Viết rõ chuẩn xưng hô và tách trường tone khỏi correctness; “đã xử lý” chung chung không đủ chứng minh đã giải quyết đúng. |
| 15 | HL-087 / helpful: reply 60.000đ, ledger 90.000đ | PASS | FAIL | Người theo note; báo thiếu tiền cũng là sai. | Kiểm equality với ledger, bắt cả báo cao lẫn báo thấp; không chỉ tìm khoản tiền bị khai tăng. |

## Rubric sửa sau audit

Các thay đổi dưới đây là nội dung rubric đề xuất từ audit theo yêu cầu M2,
không thay ngưỡng FLOORS, nhãn gốc hay yêu cầu chấm bài. CSV replay giữ nguyên
nên chưa có phép đo cho một judge mới dùng rubric đã sửa.

1. **Tone:** PASS khi xưng hô phù hợp chuẩn CS và ngữ cảnh, câu lịch sự, rõ,
   không mệnh lệnh ngăn hỗ trợ, không giễu cợt và không hứa vượt quyền. Không
   yêu cầu số câu xin lỗi hay độ dài tối thiểu. Cho phép thuật ngữ đã duyệt
   và typo nhỏ; áp dụng chuẩn tiếng Việt có dấu của bài. Đưa các cặp ví dụ
   H-029/H-042, H-051/H-094 vào hướng dẫn để phân biệt rõ.
2. **Helpfulness:** chấm đúng yêu cầu và kết quả trước văn phong. Reply sai
   ledger hoặc sai trạng thái không đạt, dù dài và nhiều lời xin lỗi. Tách
   correctness, mức độ đáp ứng và tone; tiền/approval phải có code grader.
   Nếu thiếu ticket/ledger thì ghi thiếu bằng chứng để kiểm tra tiếp, không
   suy từ câu văn rằng đã hoàn đúng.
3. **Nhãn và tái kiểm định:** lưu H-081 như ca cần adjudication; khi xác nhận
   sửa nhãn, tạo phiên bản dữ liệu mới và chạy lại thống kê. Giữ nguyên các
   con số bảng trên theo CSV công khai của đề. Rubric sửa cần nhãn người mới
   và tập held-out trước khi có thể tuyên bố cải thiện judge.

## Kết luận và giới hạn

Tone đạt cả ba sàn, dùng được trong phạm vi tiêu chí tone và replay này;
vẫn bỏ sót 6/30 lỗi và báo nhầm 4/70 trường hợp PASS. Helpful **không được
dùng làm gate**: dù precision 1.0, judge chỉ tìm thấy 9/30 lỗi, bỏ sót 21 lỗi
(70%); κ 0.375 cũng dưới sàn 0.6. Nhiều ca sai tiền vẫn được cho PASS, nên
không giao nhiệm vụ kiểm tiền hoặc approval cho judge này.

Dữ liệu chỉ có 100 reply/tiêu chí, đã công khai và dùng replay; chưa kiểm
judge trực tiếp trên model thật hay dữ liệu người dùng mới. Audit dùng note
ledger/ticket được cung cấp, chưa tự xác minh được ledger gốc của các CSV.
H-081 cho thấy nhãn người cũng có thể sai. Cần nhãn người mới, ngữ cảnh đầy
đủ và tập held-out thật; kết quả hiện tại không bảo đảm tổng quát ngoài tập này.

## Chạy lại và kiểm tra

Từ `src/`:

```text
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
python -m scripts.m2_evidence
python -m pytest -q tests/test_lab9_stats.py tests/test_lab9_judge_edges.py -o addopts= -k "not paired_bootstrap"
```

Tone phải exit 0, helpful phải exit 1 vì không đạt calibration. Kiểm tra M2:
15 passed; 2 test paired bootstrap được để lại cho M4, không phải test M2.
