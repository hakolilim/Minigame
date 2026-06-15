from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import asyncio

class GameMode(Enum):
    SINGLE_PLAYER = "single_player"  # 1 người + 1 bot
    TWO_BOTS = "two_bots"            # 1 người + 2 bot
    THREE_BOTS = "three_bots"        # 1 người + 3 bot

@dataclass
class Player:
    """Biểu diễn một người chơi"""
    id: str
    name: str
    is_bot: bool = False

class GameState(Enum):
    """Trạng thái của trò chơi"""
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    PAUSED = "paused"

class MinigameBase(ABC):
    """Lớp cơ sở cho tất cả minigame"""

    def __init__(self, game_id: str, game_name: str, mode: GameMode, players: List[Player]):
        self.game_id = game_id
        self.game_name = game_name
        self.mode = mode
        self.players = players
        self.state = GameState.WAITING
        self.current_turn_player_idx = 0
        self.history: List[Dict[str, Any]] = []

    @abstractmethod
    async def initialize_game(self) -> None:
        """Khởi tạo trò chơi"""
        pass

    @abstractmethod
    async def make_move(self, player_idx: int, move: Any) -> bool:
        """Thực hiện nước đi. Trả về True nếu hợp lệ"""
        pass

    @abstractmethod
    async def get_game_state(self) -> Dict[str, Any]:
        """Lấy trạng thái hiện tại của trò chơi"""
        pass

    @abstractmethod
    async def is_game_over(self) -> bool:
        """Kiểm tra xem trò chơi có kết thúc"""
        pass

    @abstractmethod
    async def get_winner(self) -> Player:
        """Lấy người thắng"""
        pass

    @abstractmethod
    async def get_bot_move(self, player_idx: int) -> Any:
        """Bot tự động tính toán nước đi. Ghi đè cho mỗi game"""
        pass

    async def get_current_player(self) -> Player:
        """Lấy người chơi hiện tại"""
        return self.players[self.current_turn_player_idx]

    async def switch_turn(self) -> None:
        """Chuyển lượt sang người chơi tiếp theo"""
        self.current_turn_player_idx = (self.current_turn_player_idx + 1) % len(self.players)

    async def record_move(self, move_data: Dict[str, Any]) -> None:
        """Ghi lại nước đi vào lịch sử"""
        move_data['turn'] = len(self.history)
        move_data['player'] = self.players[self.current_turn_player_idx].name
        self.history.append(move_data)

    async def play_bot_turn(self) -> bool:
        """Thực hiện lượt chơi của bot. Trả về True nếu bot thực sự di chuyển.

        Lưu ý: việc chuyển lượt (switch_turn) và ghi lịch sử do `make_move`
        của từng game tự xử lý — KHÔNG chuyển lượt thêm ở đây để tránh
        bị nhảy lượt (double switch).
        """
        current_player = await self.get_current_player()
        if not current_player.is_bot:
            return False

        move = await self.get_bot_move(self.current_turn_player_idx)
        return await self.make_move(self.current_turn_player_idx, move)
