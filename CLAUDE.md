# Minigame Discord Bot - CLAUDE.md

Dự án bot Discord để chơi minigame với cấu trúc OOP cho phép mở rộng dễ dàng.

## 📋 Tóm Tắt Dự Án

- **Thư mục**: E:\Minigame
- **Ngôn ngữ**: Python 3.10+
- **Database**: Supabase (PostgreSQL)
- **Game đầu tiên**: Cờ Cá Ngựa (Horse Chess/Ludo)

## 🏗️ Cấu Trúc Thư Mục

```
minigame/
├── core/
│   └── minigame_base.py       # Base class cho all minigames
├── games/
│   └── horse_chess.py         # Game cờ cá ngựa (40 ô, 4 quân/người)
├── bot/
│   └── discord_bot.py         # Discord bot + slash commands
├── database/
│   ├── supabase_manager.py    # Quản lý Supabase CRUD
│   └── schema.sql             # SQL schema (3 tables)
├── config/
│   └── settings.py            # Load .env variables
├── main.py                    # Entry point
└── requirements.txt           # discord.py, supabase, python-dotenv
```

## 🎮 Game Hiện Có

### Cờ Cá Ngựa (Horse Chess)
- **File**: `games/horse_chess.py`
- **Quy tắc**:
  - 4 quân cờ/người chơi, 40 ô bảng + 4 ô nhà
  - Tung xúc xắc (1-6) để di chuyển
  - Tung được 6 = chơi tiếp (tối đa 3 lần liên tiếp)
  - Ăn quân đối thủ ở vị trí cùng (quân bị ăn về nhà)
  - Quân cờ chưa ra khỏi nhà phải tung được 6 lần đầu

- **3 chế độ chơi**:
  - `single`: 1 người + 1 bot
  - `double`: 1 người + 2 bots
  - `triple`: 1 người + 3 bots

- **AI Bot**: Chiến lược greedy
  - Ưu tiên: đưa quân ra khỏi nhà → quân gần vào nhà nhất
  - Dễ thay đổi bằng cách sửa `get_bot_move()` trong game class

## 💻 Slash Commands

Tất cả dùng `/` (slash commands), không dùng prefix `!`.

| Command | Mô tả |
|---------|-------|
| `/horsechess mode:[1 Bot\|2 Bots\|3 Bots]` | Bắt đầu game |
| `/stats [member]` | Xem stats của người chơi |
| `/leaderboard [game]` | Xem top 10 người chơi |

**Lựa chọn quân cờ**: Dùng UI buttons (Quân 0, 1, 2, 3) trong trò chơi, không cần lệnh.

## 🔧 Cài Đặt & Chạy

### 1. Chuẩn Bị Môi Trường

```bash
pip install -r requirements.txt
cp .env.example .env
```

### 2. Cấu Hình `.env`

```
DISCORD_TOKEN=your_bot_token
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_anon_key
```

Lấy từ:
- **Discord Token**: Discord Developer Portal → Applications → Your Bot → Token
- **Supabase URL + Key**: Project Settings → API

### 3. Tạo Database Tables

Chạy `database/schema.sql` trong Supabase SQL Editor (3 tables: game_sessions, game_states, moves).

### 4. Chạy Bot

```bash
python main.py
```

Bot sẽ tự động sync slash commands khi khởi động.

## 📚 Thêm Game Mới

Thêm game mới rất đơn giản nhờ base class `MinigameBase`:

### 1. Tạo Game Class

```python
# games/your_game.py
from core.minigame_base import MinigameBase, GameMode, Player
from typing import List, Dict, Any

class YourGame(MinigameBase):
    async def initialize_game(self) -> None:
        # Init game state
        pass
    
    async def make_move(self, player_idx: int, move: Any) -> bool:
        # Execute move, return True if valid
        pass
    
    async def get_game_state(self) -> Dict[str, Any]:
        # Return current state as dict
        pass
    
    async def is_game_over(self) -> bool:
        # Check win condition
        pass
    
    async def get_winner(self) -> Player:
        # Return winner
        pass
    
    async def get_bot_move(self, player_idx: int) -> Any:
        # Bot AI logic
        pass
```

### 2. Thêm Slash Command

```python
# bot/discord_bot.py
from games.your_game import YourGame

class MinigameBot(commands.Cog):
    @app_commands.command(name="yourgame")
    async def start_your_game(self, interaction: discord.Interaction, 
                              mode: str = "single"):
        game_mode = mode_map.get(mode.lower(), GameMode.SINGLE_PLAYER)
        game_id = await self.create_game(interaction, game_mode)
        game = YourGame(game_id, game_mode, players)
        await game.initialize_game()
        self.active_games[game_id] = game
        # ... rest of game_loop logic
```

### 3. (Tùy chọn) Tạo Database Entries

Nếu game mới cần bảng riêng, thêm vào `schema.sql` và run migration.

## 📊 Database Schema

### game_sessions
```
- id: SERIAL PRIMARY KEY
- game_id: VARCHAR UNIQUE (8 chars)
- game_name: VARCHAR (Horse Chess, etc.)
- players: TEXT[] (names array)
- mode: VARCHAR (single_player, two_bots, three_bots)
- status: VARCHAR (in_progress, finished)
- winner: VARCHAR
- created_at: TIMESTAMP
- finished_at: TIMESTAMP (nullable)
- final_state: JSONB
```

### game_states
```
- id: SERIAL PRIMARY KEY
- game_id: VARCHAR UNIQUE FK
- state: JSONB (full game state snapshot)
- updated_at: TIMESTAMP
```

### moves
```
- id: SERIAL PRIMARY KEY
- game_id: VARCHAR FK
- player_name: VARCHAR
- move_data: JSONB {piece_id, dice_value, ...}
- created_at: TIMESTAMP
```

## ⚙️ Cấu Hình Ứng Dụng

File: `config/settings.py`

| Biến | Giá Trị | Mô Tả |
|------|--------|-------|
| `DISCORD_TOKEN` | từ .env | Bot token |
| `SUPABASE_URL` | từ .env | Database URL |
| `SUPABASE_KEY` | từ .env | Anon key |
| `GAME_TIMEOUT` | 300 | Timeout (giây) cho người chơi |
| `BOT_DELAY` | 1 | Delay (giây) trước bot chơi |
| `MAX_PLAYERS_PER_GAME` | 4 | Max players (Horse Chess = 4) |

## 🤖 Bot Architecture

### Flow: Game Loop

```
1. User: /horsechess mode:1 Bot
   ↓
2. create_game() → init HorseChessGame instance
   ↓
3. game_loop():
   - Get current player
   - If human: wait for button click, execute move
   - If bot: auto-move after delay
   - Save state to DB
   - Check win condition
   - Loop until winner
   ↓
4. finish_game() → save result to DB
```

### Key Classes

- **MinigameBase** (`core/minigame_base.py`): Abstract base, định nghĩa interface
- **HorseChessGame** (`games/horse_chess.py`): Implement Horse Chess logic
- **MinigameBot** (`bot/discord_bot.py`): Cog chứa slash commands + game loop
- **SupabaseManager** (`database/supabase_manager.py`): DB CRUD wrapper

## 🐛 Debugging Tips

### Bot không sync commands
- Kiểm tra stdout: `📝 Đã sync X slash commands`
- Nếu không, kiểm tra bot intents: `intents.message_content = True`
- Restart bot để force sync

### Game không lưu
- Kiểm tra Supabase RLS policies (enable for public access)
- Check Network tab → Supabase API calls
- Log queries trong `supabase_manager.py`

### Timeout xảy ra
- Tăng `GAME_TIMEOUT` trong settings nếu người chơi chậm
- Kiểm tra view timeout handling trong `_wait_for_player_move()`

## 📝 Files Tài Liệu

- **README.md**: Quick start + feature overview
- **GAME_RULES.md**: Luật chơi Cờ Cá Ngựa chi tiết
- **SLASH_COMMANDS.md**: Reference cho tất cả commands + examples
- **SETUP_GUIDE.md**: Step-by-step setup từ 0 (deprecated, dùng CLAUDE.md)

## 🚀 Next Steps / TODO

- [ ] Thêm game mới (Caro, Đoán số, v.v.)
- [ ] Cải thiện AI bot (minimax, heuristics)
- [ ] Multi-player (real players, không chỉ bot)
- [ ] Achievements/badges system
- [ ] Admin commands (reset stats, ban players)
- [ ] Voice channel integration?

## 📞 Contact / Support

- Discord Bot Token issue: Check Developer Portal, regenerate if needed
- Supabase issue: Check project status, RLS policies
- Game logic bug: Trace through `horse_chess.py` logic
