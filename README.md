# Minigame Discord Bot

Bot Discord để chơi minigame với cấu trúc hướng đối tượng (OOP), dễ mở rộng. Game đầu tiên: **Cờ Cá Ngựa** với 3 chế độ chơi (1/2/3 bots).

## 🚀 Khởi Động Nhanh

```bash
pip install -r requirements.txt
cp .env.example .env
# Chỉnh sửa .env với Discord token + Supabase keys
python main.py
```

Trong Discord: `/horsechess mode:1 Bot`

> **Yêu cầu**: Python 3.10+ (đã kiểm thử trên 3.14). Trên Python 3.13+, gói `audioop-lts` được discord.py tự động cài kèm để thay thế module `audioop` đã bị gỡ khỏi stdlib.

## 🎮 Tính Năng

- **Cờ Cá Ngựa**: 4 quân/người, 52 ô đường chung, 6 ô về đích riêng mỗi người, xúc xắc, ăn quân
- **3 chế độ**: 1 bot / 2 bots / 3 bots
- **Slash commands**: `/horsechess`, `/stats`, `/leaderboard`
- **Nút tương tác**: Nhấn nút để di chuyển quân cờ
- **Database**: Supabase lưu trữ phiên chơi, nước đi và thống kê

## ⚙️ Cấu Hình

Tạo file `.env` từ `.env.example`:

```
DISCORD_TOKEN=your_bot_token
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_anon_key
```

- **Discord Token**: Discord Developer Portal → Applications → Your Bot → Token
- **Supabase URL + Key**: Project Settings → API

Sau đó chạy `database/schema.sql` trong Supabase SQL Editor để tạo 3 bảng (`game_sessions`, `game_states`, `moves`).

> Chi tiết cài đặt, kiến trúc và hướng dẫn thêm game mới: xem [CLAUDE.md](CLAUDE.md).

---

# 💻 Slash Commands

Tất cả dùng `/` (slash commands), không dùng prefix `!`. Lệnh tự động sync khi bot khởi động; gõ `/` để bật autocomplete. Tham số tùy chọn có thể bỏ trống.

### `/horsechess` — Bắt đầu trò chơi Cờ Cá Ngựa

| Tham số | Giá trị | Mô tả |
|---------|--------|-------|
| `mode` | `1 Bot` / `2 Bots` / `3 Bots` | Chế độ chơi (bắt buộc) |

**Ví dụ**: `/horsechess mode:1 Bot`

Khi đến lượt bạn, nhấn nút **Quân 1/2/3/4** để di chuyển quân cờ tương ứng.

### `/stats` — Xem thống kê người chơi

| Tham số | Giá trị | Mô tả |
|---------|--------|-------|
| `member` | @user (tùy chọn) | Người dùng cần xem thống kê (mặc định: bạn) |

**Ví dụ**: `/stats` hoặc `/stats member:@User1`
**Output**: Tổng trận, Thắng, Tỷ lệ thắng (%)

### `/leaderboard` — Xem bảng xếp hạng

| Tham số | Giá trị | Mô tả |
|---------|--------|-------|
| `game` | Tên trò chơi (tùy chọn) | Trò chơi cần xem (mặc định: tất cả) |

**Ví dụ**: `/leaderboard` hoặc `/leaderboard game:Horse Chess`
**Output**: 10 người chơi đứng đầu theo số trận thắng

---

# 🐴 Cờ Cá Ngựa — Luật Chơi

## 🎯 Mục Tiêu

Đưa tất cả 4 quân cờ từ chuồng xuất phát, đi hết đường chung và vào đường về đích riêng; người đầu tiên đưa đủ 4 quân về đích sẽ thắng.

## 👥 Người Chơi

- 2-4 người chơi, 4 quân cờ/người
- **3 chế độ**: single (1 bot), double (2 bots), triple (3 bots)

## 🎲 Cách Chơi

**Quân cờ chưa ra khỏi chuồng**
- Bắt đầu ở vị trí -1 (trong chuồng)
- **Phải tung được 6** để ra khỏi chuồng → xuất hiện ở vị trí 0

**Quân cờ trên đường chung**
- Tung xúc xắc, di chuyển quân cờ **bằng số ô được tung**
- Có thể chọn quân cờ nào để di chuyển (nếu có nhiều cách)
- **Tung được 6**: Chơi tiếp một lần nữa (tối đa 3 lần liên tiếp)

**Quân cờ về đích**
- Sau khi đi hết đường chung, quân đi vào **đường về đích riêng gồm 6 ô**
- Phải tung đúng số để về ô đích cuối cùng; nếu tung quá số cần thiết thì quân đó không được đi
- *Ví dụ*: quân còn cách đích 2 bước, tung 2 → về đích; tung 3 → không hợp lệ

## ⚔️ Ăn Quân

Quân cờ của bạn **cùng vị trí** với quân đối thủ → **bạn ăn nó**:
- Quân bị ăn về chuồng (vị trí -1)
- Chiến lược: ăn quân bot để làm chậm tiến độ của họ

## 💡 Mẹo

1. Ưu tiên ăn quân bot → làm họ chậm lại
2. Tập trung đưa một quân về đích trước, rồi chuyển qua quân khác
3. Tung được 6 = may mắn → dùng để ăn quân hoặc tiến xa
4. Chú ý vị trí bot → tránh để họ ăn quân bạn

## ❓ FAQ

**Q: Tôi tung 3 nhưng không có quân nào có thể di chuyển?**
A: Nếu quân còn trong chuồng thì phải tung 6 mới ra được. Nếu quân gần đích nhưng tung quá số cần thiết, quân đó cũng không được đi.

**Q: Tung 6 ba lần, có được chơi lần thứ 4 không?**
A: Không! Tối đa 3 lần liên tiếp tung được 6.

**Q: Quân gần đích nhưng tôi tung lớn hơn số bước cần thiết thì sao?**
A: Nước đi đó không hợp lệ. Bạn phải tung đúng số bước còn thiếu để quân về đích.

**Q: Làm sao biết thắng?**
A: Tất cả 4 quân về đích = bạn thắng. Bot sẽ thông báo: 🎉 Người thắng!

---

**Timeout**: 5 phút/lượt (nếu hết giờ thì bỏ qua lượt).
