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

## 🎮 Tính Năng

- **Cờ Cá Ngựa**: 4 quân/người, 40 ô bảng, xúc xắc, ăn quân, nhà 4 ô
- **3 chế độ**: 1 bot / 2 bots / 3 bots
- **Slash commands**: `/horsechess`, `/stats`, `/leaderboard`
- **UI buttons**: Nhấn nút để di chuyển quân cờ
- **Database**: Supabase lưu trữ game sessions, moves, stats

## 📚 Tài Liệu

Xem chi tiết tại:
- **Cài đặt**: CLAUDE.md
- **Cách chơi**: GAME_RULES.md
- **Slash commands**: SLASH_COMMANDS.md
