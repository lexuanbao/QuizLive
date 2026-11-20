# Tranh luận cách tính điểm

Ba agent tranh luận hai vòng. Lead chốt. Tài liệu này ghi lại lập luận, điểm
yếu tự thừa nhận, phản biện chéo, kết luận và cả những phương án thua.

## 1. Bối cảnh

- 5 câu, mỗi câu 4 lựa chọn, 20 giây, tiếng Việt.
- Host chiếu trên máy chiếu, người chơi dùng điện thoại, không tài khoản.
- Dưới 50 người chơi. Sai hoặc không trả lời: 0 điểm.
- Server đo thời gian, không tin đồng hồ trình duyệt.
- INV-1: điểm một người luôn bằng `SUM(answers.points)`, không có cột điểm
  cộng dồn.
- INV-2: mỗi người một lần mỗi câu, gửi lần hai trả 409 và không đổi điểm.
- INV-3: khi status là `lobby` hoặc `question`, không response nào chứa
  `correct_index` hay `explanation`.

## 2. Ba đề xuất

**A — Đúng là được điểm như nhau.** 1000 điểm mỗi câu đúng, sai 0. Không phụ
thuộc tốc độ.

**B — Nhanh hơn nhiều điểm hơn.** Giữ công thức hiện tại: đúng =
`1000 - 25*t`, t là số giây trọn từ lúc câu mở tới lúc server nhận, kẹp 0..20.
Sai 0. Đúng ngay 1000, đúng giây cuối 500.

**C — Thưởng chuỗi đúng liên tiếp.** Nền `600 + 400*(1 - t/20)`, cộng thưởng
chuỗi vào `points` của câu tương ứng: +200 cho câu đúng thứ 2 liên tiếp,
+300 cho câu thứ 3, +500 cho câu thứ 4-5. Trần 1500/câu, 6500/ván.

## 3. Vòng 1 — lập luận và tự phê bình

### A

Lập luận mạnh:

- Thứ hạng bằng số câu đúng, đọc được ngay trên máy chiếu. Năm câu chỉ có sáu
  mức điểm, không phải giải thích công thức giữa ván.
- Loại bỏ bất công hạ tầng. Người chơi dùng wifi quán hoặc 4G chập chờn; B
  tính 25 điểm/giây thì jitter 400ms mất 10 điểm mỗi câu, 50 điểm cả ván.
  Không tài khoản nghĩa là không có kênh khiếu nại.
- Không phạt người suy nghĩ. Sản phẩm có phần giải thích đáp án, tức mục tiêu
  là hiểu bài, không phải bấm liều.
- INV-1 và INV-2 dễ bảo vệ: `points` chỉ thuộc {0, 1000}.
- Giữ người chơi ở lại. B có thể tạo khoảng cách 2500 sau năm câu.

Tự nhận điểm yếu:

- Chí mạng: hòa hàng loạt. Năm câu nhị phân chỉ cho sáu mức điểm; với 50
  người, mức 5/5 thường có 3-8 người. Bảng chung cuộc đầy đồng hạng.
- Không có động lực trả lời sớm. Ai cũng chờ giây 19; 50 request dồn vào một
  giây, dễ timeout.
- Năm câu ngang trọng số, không thưởng được câu khó hơn.
- A thất bại khi cần đúng một người thắng, hoặc khi cả phòng giỏi ngang nhau.

Phản biện B và C:

- B đo độ trễ mạng chứ không đo kiến thức. Đoán mò trong 2 giây ăn 950, suy
  nghĩ 15 giây ăn 625. Chênh 500 điểm ở câu một không gỡ nổi trong bốn câu
  còn lại. B còn phải định nghĩa chính xác "câu mở" là lúc broadcast hay lúc
  client render.
- C phạt kép: sai câu một mất điểm câu đó và mất hệ số bốn câu sau. Với ván
  năm câu, đứt chuỗi ở câu ba làm câu bốn, năm vô nghĩa. `points` của câu bốn
  phụ thuộc câu một đến ba nên muốn audit phải replay toàn bộ.

### B

Lập luận mạnh:

- Giải thích được trong một câu trên màn hình host: "nhanh hơn 1 giây được
  thêm 25 điểm". Ván chỉ 3-4 phút, người chơi không có thời gian đọc luật.
- Nén thời gian chết. 20 giây × 5 câu là 100 giây chờ nếu mọi người ngồi hết
  giờ. B khiến người chơi bấm sớm, nhịp game không bị chết.
- Thang 500-1000 đủ rộng nhưng không tuyệt đối: đúng chậm vẫn hơn sai rất
  nhiều. Điểm là hàm của đúng một answer nên INV-1 thỏa tự nhiên.
- Với dưới 50 người, khoảng cách này đủ tách top 5 mà không chốt ván từ câu 2.

Tự nhận điểm yếu:

- Chí mạng: phạt oan độ trễ mạng. 300-800ms mất 8-20 điểm mỗi câu, 50-100
  điểm cả ván, đủ đổi thứ hạng. Đây là bất công hệ thống, không phải kỹ năng.
- Thưởng cả may mắn: người bấm ở giây 0 để lấy 1000 thường là đoán mò.
- Tốc độ lấn kiến thức: đúng 4 câu chậm được 2000, đúng 3 câu nhanh được
  3000. Đúng nhiều hơn vẫn thua.
- Bậc thang giây trọn: cách 0,9 giây có thể cùng điểm, cách 1,1 giây khác 25.
- B thất bại khi trong phòng có người wifi và người 4G.

Phản biện A và C:

- A công bằng nhưng làm phẳng game. Muốn phá hòa phải tie-break bằng thời
  gian, tức là B trá hình nhưng giấu đi. Tệ hơn: không ai có lý do bấm sớm,
  cả phòng chờ hết 20 giây.
- C có chuỗi tối đa 5 câu, nên câu 1 quan trọng bất cân xứng. Sai một câu sớm
  là mất gần hết ván, người chơi mất động lực ở câu 2-5 và thoát. C khó giải
  thích trong 20 giây và dễ vi phạm tinh thần INV-1 nếu tính điểm dựa trên
  lịch sử.

### C

Lập luận mạnh:

- Năm câu là quá ngắn để may mắn tự san bằng. Với B, chậm 8 giây ở câu 1 là
  mất 200 điểm, gần như không gỡ được.
- Thưởng chuỗi tạo ra thứ khiến câu 4, câu 5 còn đáng xem: một cuộc rượt đuổi
  có thể đảo chiều.
- Nền nén 400 đặt tốc độ xuống dưới kiến thức nhưng vẫn giữ tốc độ.
- Chuỗi là tín hiệu "mình đang làm tốt" mà không cần tài khoản hay lịch sử.
- INV-1 nguyên vẹn: thưởng là phép cộng vào `points` của chính dòng `answers`
  đó, không cột mới. INV-2 còn được bảo vệ tốt hơn vì lần gửi thứ hai trả 409
  thì thưởng không thể cộng hai lần.

Tự nhận điểm yếu:

- Chí mạng: sai câu 1 là trần điểm tụt 1000-1300. Ván kết thúc sau 20 giây
  đầu; 40 người còn lại chơi cho có.
- Người vào muộn ở câu 2-3 không bao giờ có chuỗi, và không có tài khoản để bù.
- Chuỗi là trạng thái ẩn. Không hiển thị thì người chơi nhận điểm mà không
  hiểu vì sao; hiển thị thì thêm phức tạp.
- Thưởng chuỗi thưởng cho sự ổn định, không thưởng cho hiểu bài.
- Điểm phình 5000 lên 6500, khó đọc trên màn chiếu.

Phản biện A và B:

- A làm câu 5 vô nghĩa, top 5 là năm dòng giống nhau, 50 request dồn giây 19.
  A công bằng nhưng không phải một trò chơi.
- B biến ván quiz thành cuộc đua đọc chữ và độ trễ mạng. Server đo thời gian
  là đúng, nhưng nó đo luôn 4G của người ngồi góc phòng. Ba người nhanh nhất
  thắng mọi ván; màn host nhàm từ ván thứ hai.

## 4. Vòng 2 — phản biện chéo

### A

- Chấp nhận đòn mạnh nhất: A thiếu cơ chế tạo ra người thắng; nếu tie-break
  bằng thời gian thì A đúng là B trá hình. Đây là điểm yếu chí mạng.
- Không chấp nhận rằng tốc độ phải nằm trong điểm. A chỉ cần một tie-break
  không dựa trên tốc độ, hoặc một tie-break công khai.
- B sửa bằng miễn 2 giây và hệ số 15. Miễn 2 giây không xử lý jitter vì jitter
  là phương sai, không phải độ lệch cố định. Hệ số 15 nén thang còn 700-1000,
  tức B tiến gần A mà vẫn thưởng đoán mò ở giây 0. Sửa xong thì không còn là B.
- C tự nhận sai câu 1 là ván kết thúc. Nhượng bộ 150/200/300 làm chuỗi gần
  như vô hại, tức xóa lý do tồn tại của C. "Chuỗi ẩn trong points" khiến người
  chơi không hiểu điểm mình.
- Nếu A bị loại, A chọn C, vì C đặt tốc độ dưới kiến thức và lỗi của C là lỗi
  tham số, sửa được; lỗi của B là lỗi cấu trúc, sửa là mất B.
- Phương án dung hòa của A: đúng 1000, cộng thưởng tốc độ thô +100 nếu t ≤ 5
  giây, +50 nếu 5-12 giây. Trần 1100/câu. Tie-break: số câu đúng, rồi số câu
  đúng nhanh, rồi đồng hạng công khai.

### B

- Chấp nhận đòn mạnh nhất: B chưa định nghĩa "câu mở". Nếu t tính từ lúc
  server broadcast, người mạng chậm nhận câu muộn hơn trong khi đồng hồ đã
  chạy. B đo độ trễ chứ không đo phản xạ. Đây là điểm yếu chí mạng.
- Không chấp nhận kết luận "bỏ tốc độ hoàn toàn": lỗi nằm ở tham số, không ở
  cơ chế.
- A: tie-break bằng tổng thời gian phản hồi chính là B nhưng giấu; điểm hiển
  thị bằng nhau nên người chơi không hiểu vì sao thua. Bonus +100 trong 5 giây
  quá nhỏ, chỉ chia 3-8 người hòa thành 2-3 nhóm.
- C: hạ thưởng còn 150/200/300 thì chuỗi gần như vô nghĩa, mất đúng cái "cuộc
  rượt đuổi" C hứa. 6500 điểm trên máy chiếu buộc người chơi làm phép trừ.
- Nếu B bị loại, B chọn A, vì INV đơn giản nhất và không loại ai khỏi ván.
- Phương án dung hòa của B: `700 + 300*(1 - max(0, t-2)/18)`. Đúng ngay 1000,
  giây cuối 700. Miễn 2 giây đầu, chênh tối đa 300/câu, 1500/ván.

### C

- Chấp nhận đòn "phạt kép": sai câu 1 mất 1000 điểm câu đó và khoảng 1300
  thưởng của bốn câu sau. Không phải vì con số, mà vì hành vi: người chơi hiểu
  điều đó sau câu 1 và bỏ điện thoại. C giết phần lớn phòng trong 20 giây đầu.
- Không chấp nhận cáo buộc "INV-1 khó kiểm chứng". Điểm vẫn ghi vào đúng dòng
  `answers`, `SUM` vẫn đúng. Cái mất là một dòng không còn tự giải thích.
- A: tie-break tổng thời gian là đưa tốc độ vào cửa sau, lần này vô hình. Hai
  người 5/5, người thắng do 4G. Bonus +100 trong 5 giây còn tệ hơn: dựng một
  vách đúng giây thứ 5.
- B: miễn 2 giây nuốt 300-800ms nhưng nuốt luôn cả đoán mò giây 0; hệ số 15
  nén thang còn 700-1000, tức B sửa lỗi của mình bằng cách nhận lỗi của A.
- Nếu C bị loại, C chọn B, vì hòa là lỗi sản phẩm nặng hơn thiên lệch. 50-100
  điểm độ trễ mỗi ván nhỏ hơn khoảng cách một câu.
- Phương án dung hòa của C: nền phẳng 1000, thưởng chuỗi chỉ mở từ câu 3,
  +100 ở câu 3, +200 ở câu 4-5, trần +300 cả ván, ghi thẳng vào `points`.
  Xếp hạng: `SUM(points)` giảm dần, hòa thì `SUM(t)` tăng dần.

## 5. Kết luận

**Chọn B, nhưng chặn biên tốc độ.** Cụ thể:

- Đúng: `1000 - 8*t`, t là số giây trọn từ lúc câu mở tới lúc server nhận,
  kẹp 0..20.
- Sai hoặc không trả lời: 0.
- Đúng ngay: 1000. Đúng ở giây cuối: 840.
- Hòa điểm: xếp theo tổng thời gian trả lời tăng dần, công bố trước ván. Đây
  là tie-break hiển thị, không phải điểm.

Vì sao chọn B và sửa hệ số:

- Giữ được lợi ích của B: có áp lực thời gian, có tie-break tự nhiên, ván
  không chết ở giây 19.
- Sửa được lỗi chí mạng của B. Với 5 câu, biên tốc độ mỗi câu là 160 điểm,
  cả ván là 800. Một câu đúng thấp nhất được 840, tức **một câu đúng luôn
  đáng hơn toàn bộ chênh lệch tốc độ của cả ván**. Hệ quả: người đúng nhiều
  hơn luôn xếp trên; tốc độ chỉ quyết định giữa những người cùng số câu đúng.
- Kiểm tra: 5 câu đúng chậm = 4200, 4 câu đúng nhanh = 4000. 4 câu đúng chậm
  = 3360, 3 câu đúng nhanh = 3000. Đúng nhiều hơn luôn thắng.
- Hệ số 8 là mức đơn giản, integer, vẫn dưới ngưỡng 200. Nếu để 10 thì 5 câu
  đúng chậm (4000) chỉ hòa 4 câu đúng nhanh (4000); nếu để trên 10 thì đúng
  nhiều hơn có thể thua.
- Không chọn A: A công bằng nhưng làm phẳng game, hòa hàng loạt, không có
  động lực trả lời sớm. Tuy vậy, chính A là bên chỉ ra lỗi "tốc độ lấn kiến
  thức", và kết luận này giữ nguyên tắc của A: kiến thức quyết định thứ hạng,
  tốc độ chỉ phá hòa.
- Không chọn C: không thêm trạng thái chuỗi, không có cột điểm mới, không đổi
  chữ ký `scoring.points_for`, INV-1 vẫn là `SUM(answers.points)`.

Ảnh hưởng nếu chốt:

- `planning/SPEC.md` mục 4: đổi hệ số 25 thành 8; ví dụ "đúng ở giây cuối được
  500" thành 840.
- `backend/scoring.py`: đổi hằng số trong `points_for`; giữ nguyên chữ ký.
- Không đổi schema, không đổi API, không đổi ba test invariant.
- README vẫn đúng: trả lời càng nhanh càng nhiều điểm, chỉ khác là tốc độ
  không còn đủ để lấn một câu đúng.

## 6. Lập luận thua được giữ lại

### A thua vì

- Hòa hàng loạt và không có động lực trả lời sớm. A tự thừa nhận đây là điểm
  yếu chí mạng.
- Muốn phá hòa thì phải tie-break bằng thời gian, tức là đưa tốc độ vào cửa
  sau; nếu giấu thì tệ hơn B, nếu công khai thì không còn là A thuần.

Nhưng A đúng ở:

- Tốc độ không được phép khiến người đúng ít hơn thắng người đúng nhiều hơn.
  Đây là lý do hệ số bị hạ từ 25 xuống 8.
- Độ trễ mạng và thao tác đọc là bất công hệ thống, không phải kỹ năng.
- Một câu đúng nên đáng hơn toàn bộ chênh lệch tốc độ của ván. Kết luận dùng
  đúng tiêu chí này.

### C thua vì

- Snowball: sai câu 1 làm phần lớn phòng mất đường thắng ngay sau 20 giây.
- Người vào muộn không có chuỗi, không có cách bù.
- Chuỗi là trạng thái ẩn; hiển thị thì phức tạp, không hiển thị thì điểm vô
  nghĩa.
- Thêm một trạng thái phụ thuộc lịch sử vào cách tính điểm, trong khi sản phẩm
  chỉ có 5 câu và ưu tiên đơn giản.
- Điểm phình lên 6500, khó đọc trên màn chiếu.

Nhưng C đúng ở:

- Năm câu là quá ngắn để may mắn tự san bằng; một cơ chế tạo kịch tính ở câu
  4-5 là có giá trị.
- Chuỗi là tín hiệu tốt để người chơi biết mình đang làm tốt mà không cần tài
  khoản.
- Thưởng chuỗi vẫn có thể thỏa INV-1 nếu ghi vào `points` của dòng `answers`.
- Nếu vẫn muốn giữ phần hay của C, hiển thị chuỗi đúng như một thống kê trên
  màn host và điện thoại, không cộng điểm.

### Các phương án dung hòa bị loại

- **B với `700 + 300*(1 - max(0, t-2)/18)`.** Không đủ: 5 câu đúng chậm được
  3500, vẫn thua 4 câu đúng nhanh được 4000. Hệ số 15 vẫn để tốc độ lấn một
  câu đúng.
- **A với thưởng tốc độ thô (+100 nếu t ≤ 5, +50 nếu 5-12).** Thỏa nguyên tắc
  kiến thức, nhưng là công thức từng khúc, thêm hai mốc thời gian và một luật
  tie-break phức tạp. Không hơn B ở điểm nào đáng kể.
- **C với chuỗi chỉ từ câu 3 (+100/+200, trần 300).** Thỏa nguyên tắc kiến
  thức, nhưng vẫn thưởng cho người đang dẫn, vẫn thêm trạng thái chuỗi, và
  vẫn phải đổi `scoring.points_for`. Lợi ích kịch tính nhỏ hơn chi phí.
- **Tie-break bằng tổng thời gian của A.** Không bị loại; được giữ lại nhưng
  chỉ dùng khi điểm bằng nhau, và phải công bố trước ván. Nó không thay đổi
  điểm, chỉ thay đổi thứ tự hiển thị.

## 7. Việc cần làm sau (không sửa trong tài liệu này)

- Cập nhật `planning/SPEC.md` mục 4 theo công thức mới.
- Cập nhật hằng số trong `backend/scoring.py`.
- Thêm unit test cho các mốc: t = 0, t = 20, t bị kẹp, sai = 0.
- Giữ nguyên `tests/invariants/`: INV-1 vẫn đúng vì điểm vẫn là
  `SUM(answers.points)`.
- Nếu muốn giữ chuỗi như thống kê, thêm hiển thị ở frontend, không thêm điểm.
