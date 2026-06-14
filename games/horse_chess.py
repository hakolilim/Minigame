from typing import List, Dict, Any, Optional, Tuple
import random
import asyncio
from core.minigame_base import MinigameBase, GameMode, GameState, Player

class HorseChessGame(MinigameBase):
    """
    Game Cờ Cá Ngựa (Ludo-like game)
    - Mỗi người chơi có 4 quân cờ
    - Bảng 40 ô
    - Tung xúc xắc để di chuyển
    - Quân cờ vào nhà sau khi đi được 40 ô
    """

    def __init__(self, game_id: str, mode: GameMode, players: List[Player]):
        super().__init__(game_id, "Horse Chess", mode, players)
        self.board_size = 40
        self.pieces_per_player = 4

        # Trạng thái bảng: {player_idx: {piece_id: position}}
        self.board_state: Dict[int, Dict[int, int]] = {}

        # Số ô đã đi của mỗi quân cờ để vào nhà
        self.home_positions: Dict[int, Dict[int, int]] = {}

        # Số lần tung xúc xắc liên tiếp
        self.consecutive_sixes = 0
        self.max_consecutive_sixes = 3

        # Bảng điểm
        self.scores: Dict[int, int] = {}

    async def initialize_game(self) -> None:
        """Khởi tạo trò chơi cờ cá ngựa"""
        self.state = GameState.IN_PROGRESS

        for i in range(len(self.players)):
            self.board_state[i] = {}
            self.home_positions[i] = {}
            self.scores[i] = 0

            # Mỗi người chơi bắt đầu với 4 quân cờ ở vị trí -1 (chưa ra khỏi nhà)
            for piece_id in range(self.pieces_per_player):
                self.board_state[i][piece_id] = -1
                self.home_positions[i][piece_id] = 0

        await self.record_move({'event': 'game_started', 'players': [p.name for p in self.players]})

    async def roll_dice(self) -> int:
        """Tung xúc xắc (1-6)"""
        return random.randint(1, 6)

    async def can_piece_move(self, player_idx: int, piece_id: int, dice_value: int) -> bool:
        """Kiểm tra xem quân cờ có thể di chuyển không"""
        current_pos = self.board_state[player_idx][piece_id]

        # Quân cờ chưa ra khỏi nhà phải tung được 6
        if current_pos == -1:
            return dice_value == 6

        # Nếu quân cờ vào nhà rồi
        if current_pos >= self.board_size:
            home_pos = self.home_positions[player_idx][piece_id]
            new_home_pos = home_pos + dice_value
            return new_home_pos <= 4  # Nhà có 4 ô

        return True

    async def move_piece(self, player_idx: int, piece_id: int, dice_value: int) -> bool:
        """Di chuyển quân cờ"""
        if not await self.can_piece_move(player_idx, piece_id, dice_value):
            return False

        current_pos = self.board_state[player_idx][piece_id]

        # Quân cờ chưa ra khỏi nhà
        if current_pos == -1:
            self.board_state[player_idx][piece_id] = 0
        # Quân cờ đã vào nhà
        elif current_pos >= self.board_size:
            home_pos = self.home_positions[player_idx][piece_id]
            self.home_positions[player_idx][piece_id] = home_pos + dice_value
        # Quân cờ trên bảng
        else:
            new_pos = current_pos + dice_value

            # Quân cờ vào nhà
            if new_pos >= self.board_size:
                self.board_state[player_idx][piece_id] = self.board_size
                self.home_positions[player_idx][piece_id] = 0
            else:
                self.board_state[player_idx][piece_id] = new_pos

                # Ăn quân của người khác
                await self._capture_opponent_pieces(player_idx, new_pos)

        return True

    async def _capture_opponent_pieces(self, player_idx: int, position: int) -> None:
        """Ăn quân của người khác tại vị trí này"""
        for i in range(len(self.players)):
            if i != player_idx:
                for piece_id in self.board_state[i]:
                    if self.board_state[i][piece_id] == position:
                        # Quân bị ăn về nhà
                        self.board_state[i][piece_id] = -1
                        self.home_positions[i][piece_id] = 0

    async def make_move(self, player_idx: int, move: Dict[str, Any]) -> bool:
        """
        Thực hiện nước đi
        move = {'piece_id': int, 'dice_value': int}
        """
        piece_id = move['piece_id']
        dice_value = move['dice_value']

        if piece_id not in self.board_state[player_idx]:
            return False

        success = await self.move_piece(player_idx, piece_id, dice_value)

        if success:
            await self.record_move({
                'piece_id': piece_id,
                'dice_value': dice_value,
                'position': self.board_state[player_idx][piece_id]
            })

            # Nếu tung được 6, tiếp tục lượt
            if dice_value != 6:
                await self.switch_turn()
                self.consecutive_sixes = 0
            else:
                self.consecutive_sixes += 1
                if self.consecutive_sixes >= self.max_consecutive_sixes:
                    await self.switch_turn()
                    self.consecutive_sixes = 0

        return success

    async def get_valid_moves(self, player_idx: int, dice_value: int) -> List[Dict[str, Any]]:
        """Lấy tất cả nước đi hợp lệ"""
        valid_moves = []

        for piece_id in range(self.pieces_per_player):
            if await self.can_piece_move(player_idx, piece_id, dice_value):
                valid_moves.append({'piece_id': piece_id, 'dice_value': dice_value})

        return valid_moves

    async def get_game_state(self) -> Dict[str, Any]:
        """Lấy trạng thái hiện tại của trò chơi"""
        return {
            'board_state': self.board_state,
            'home_positions': self.home_positions,
            'current_player': self.players[self.current_turn_player_idx].name,
            'current_player_idx': self.current_turn_player_idx,
            'scores': self.scores,
            'game_state': self.state.value
        }

    async def is_game_over(self) -> bool:
        """Kiểm tra xem trò chơi có kết thúc"""
        for player_idx in range(len(self.players)):
            all_pieces_in_home = True
            for piece_id in range(self.pieces_per_player):
                if self.board_state[player_idx][piece_id] != self.board_size:
                    all_pieces_in_home = False
                    break

            if all_pieces_in_home:
                # Kiểm tra tất cả quân cờ đã vào nhà hoàn toàn
                all_in_final_home = all(
                    self.home_positions[player_idx][pid] == 4
                    for pid in range(self.pieces_per_player)
                )
                if all_in_final_home:
                    return True

        return False

    async def get_winner(self) -> Player:
        """Lấy người thắng"""
        for player_idx in range(len(self.players)):
            if all(self.board_state[player_idx][pid] == self.board_size and
                   self.home_positions[player_idx][pid] == 4
                   for pid in range(self.pieces_per_player)):
                return self.players[player_idx]

        return None

    async def get_bot_move(self, player_idx: int) -> Dict[str, Any]:
        """Bot tính toán nước đi"""
        # Tung xúc xắc
        dice_value = await self.roll_dice()

        # Lấy nước đi hợp lệ
        valid_moves = await self.get_valid_moves(player_idx, dice_value)

        if not valid_moves:
            return {'piece_id': -1, 'dice_value': dice_value}

        # Chiến lược đơn giản: ưu tiên đưa quân cờ ra khỏi nhà
        pieces_at_home = [m for m in valid_moves if
                          self.board_state[player_idx][m['piece_id']] == -1]

        if pieces_at_home:
            return random.choice(pieces_at_home)

        # Ngoài ra, chọn quân cờ gần vào nhà nhất
        furthest_piece = max(
            valid_moves,
            key=lambda m: self.board_state[player_idx][m['piece_id']]
        )

        return furthest_piece
