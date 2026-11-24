# Trạng thái hiện tại

Đang ở: Bước 3 — sóng 2 và 3 xong về code, chờ chơi thử trên trình duyệt thật
Đã xong: sóng 0, 1, 2 (màn hình host và người chơi), 3 (`tests/game/`); 110 test xanh
Đang làm: người thật chơi thử một ván (máy chiếu + điện thoại) để chốt sóng 2
Quyết định vừa chốt: bằng điểm vẫn xếp hạng khác nhau (1, 2) vì SPEC không quy định; chờ người dùng quyết

---

## Ai được sửa file này

Khi làm một mình với một Claude: Claude cập nhật file này sau mỗi mảng việc.

Khi chạy agent team: **chỉ lead** sửa file này. Teammate xong việc thì báo
cho lead, lead ghi lại. Nhiều agent cùng sửa một file sẽ ghi đè lên nhau.

## Các sóng

| Sóng | Ai | Nội dung | Xong khi |
|---|---|---|---|
| 0 | Lead, một mình | Database, bảng, app tối thiểu, file trống cho mọi module | `/api/health` trả 200 |
| 1 | Người 1, 2, 3 cùng lúc | Luật chơi và điểm; trạng thái và bảng xếp hạng; sinh câu hỏi | Ba test invariant hết skip và xanh |
| 2 | Người 4, 5 cùng lúc | Màn hình host; màn hình người chơi | Chơi trọn một ván trên máy |
| 3 | Người 6 | Test chơi trọn ván qua API | `tests/game/` xanh |

## Nhật ký

### 2026-11-24 — lead — sóng 2 và 3 (3 agent song song)
Đã làm: lead viết trước `app.js` (api, poll, store, el, show) và `style.css`
(biến màu, `.choice-0..3`) để hai agent frontend không sửa chung file.
Người 4 viết `host.html`, Người 5 viết `play.html` (mỗi trang tự chứa
`<style>` và `<script>`), Người 6 viết `tests/game/` (6 test: trọn 5 câu khớp
điểm tính tay, 409 lần hai, hết giờ, 403, 404). Lead sửa: nút "Câu tiếp" bị
poll bật lại khi đang gửi; người chơi bấm lúc câu vừa đóng (409
`question_closed`) bị tính là đã chọn. Kiểm tra: `pytest tests` 110 passed;
`node --check` hai script; chạy trọn một ván qua HTTP thật với mock.
Quyết định: frontend chưa mở bằng trình duyệt thật — sóng 2 chỉ coi là xong
khi người chơi thử. Bằng điểm thì rank theo thứ tự `views._ranking` (1, 2).
Người tiếp theo cần biết: `backend.app` gọi `db.init_db()` lúc import, nên
fixture `tests/game` xoá `backend.app` khỏi `sys.modules` mỗi test; chuyển
`init_db()` vào lifespan sẽ bền hơn. Đổi thiết bị giữa ván thì màn hình người
chơi không biết đã chọn gì (server không trả lựa chọn) và hiện "Hết giờ".

### 2026-11-24 — lead — chốt sóng 1, chuẩn bị sóng 2 và 3
Đã làm: kiểm tra sóng 1 — `game.py`, `scoring.py`, `views.py`, `generator.py`,
`routes_game.py`, `routes_state.py` đã có logic thật, không còn stub.
`pytest tests`: 104 passed (3 invariant, còn lại unit). Sửa helper `_answer()`
trong `tests/unit/test_game.py` (thừa tham số `choice_index`, làm 4 test đỏ).
Thêm hook PreToolUse `.claude/hooks/protect-invariants.ps1` chặn lệnh shell
ghi/xoá/đổi tên trong `tests/invariants/`; hook SessionStart in file này.
Quyết định: thời gian mỗi câu là 20 giây (`game.QUESTION_SECONDS`,
`scoring.MAX_SECONDS`). Mock câu hỏi bằng `QUESTIONS_SOURCE=mock`.
Người tiếp theo cần biết: frontend hiện chỉ là placeholder (`host.html`,
`play.html`, `app.js`, `style.css`). Sóng 2: Người 4 làm màn hình host, Người 5
làm màn hình người chơi; cả hai chỉ gọi API theo CONTRACT, poll `/state`, không
sửa backend. Hai người dùng chung `app.js`/`style.css` dễ ghi đè nhau — nên tách
`host.js` và `play.js`. Sóng 3: Người 6 viết `tests/game/` chạy trọn một ván qua
API với mock, không cần chờ sóng 2.

### 2026-11-21 — lead — sóng 0 phần nền
Đã làm: `backend/db.py` và `backend/schema.sql` tạo 4 bảng đúng cột trong
CONTRACT; `backend/app.py` có `/api/health`, phục vụ `/`, `/play`, `/static`;
file rỗng kèm chữ ký hàm dùng chung cho `game.py`, `scoring.py`,
`routes_game.py`, `views.py`, `routes_state.py`, `generator.py`; frontend
placeholder. `pytest tests/invariants`: 3 skipped vì `POST /api/rooms` chưa
viết; app import được, `/api/health` trả 200.
Quyết định: schema giữ đúng cột CONTRACT, không thêm cột; `answers` có
`UNIQUE(question_id, player_id)`; không có cột điểm cộng dồn. Router rỗng đã
gắn sẵn trong app.py để người sau không phải sửa app.py. Hàm dùng chung chỉ là
stub `raise NotImplementedError`, chưa có logic chơi.
Người tiếp theo cần biết: Người 1 thêm route vào `routes_game.py`, Người 2 vào
`routes_state.py`, Người 3 viết `generator.generate`; không sửa `app.py`,
`db.py`, `schema.sql`. Máy chưa có Python nên đã cài Python 3.12 và tạo
`.venv`; chạy test bằng `.\.venv\Scripts\python.exe -m pytest tests/invariants`.
Docker chưa dùng được vì WSL2/Virtual Machine Platform chưa bật.

<!-- Mục mới thêm lên trên cùng. Viết ngắn, không dán code.

### <ngày> — <ai> — <việc gì>
Đã làm:
Quyết định:
Người tiếp theo cần biết:
-->
