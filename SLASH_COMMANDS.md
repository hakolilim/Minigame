# Slash Commands Reference

## 🐴 Game

### `/horsechess`
**Bắt đầu trò chơi Cờ Cá Ngựa**

| Tham số | Giá trị | Mô tả |
|---------|--------|-------|
| `mode` | `1 Bot` / `2 Bots` / `3 Bots` | Chế độ chơi (bắt buộc) |

**Ví dụ**: `/horsechess mode:1 Bot`

**Cách chơi**: Khi đến lượt bạn, nhấn nút Quân 0/1/2/3 để di chuyển quân cờ tương ứng.

---

## 📊 Thống Kê

### `/stats`
**Xem thống kê người chơi**

| Tham số | Giá trị | Mô tả |
|---------|--------|-------|
| `member` | @user (optional) | User cần xem stats (default: bạn) |

**Ví dụ**:
- `/stats` → Xem của bạn
- `/stats member:@User1` → Xem của User1

**Output**: Total games, Wins, Win rate (%)

---

### `/leaderboard`
**Xem bảng xếp hạng**

| Tham số | Giá trị | Mô tả |
|---------|--------|-------|
| `game` | Game name (optional) | Game cần xem (default: all) |

**Ví dụ**:
- `/leaderboard` → Xem tất cả
- `/leaderboard game:Horse Chess` → Xem riêng Cờ Cá Ngựa

**Output**: Top 10 players ranked by wins

---

## 🎮 Gameplay

**Lượt chơi**:
1. Bot hiển thị xúc xắc (1-6)
2. Nếu lượt bạn: Nhấn nút Quân X
3. Nếu lượt bot: Bot tự chơi sau ~1 giây

**Buttons**: Quân 0, Quân 1, Quân 2, Quân 3 (di chuyển quân cờ tương ứng)

**Timeout**: 5 phút/lượt (nếu hết, bỏ qua lượt)

---

## 📝 Ghi Chú

- Slash commands tự động sync khi bot khởi động
- Dùng `/` để trigger autocomplete
- Tham số tùy chọn có thể bỏ trống

