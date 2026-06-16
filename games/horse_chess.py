from typing import List, Dict, Any, Optional
import random
from core.minigame_base import MinigameBase, GameMode, GameState, Player

# ──────────────────────────────────────────────────────────────────────────
# Hằng số mô hình bàn cờ cá ngựa (Ludo) chuẩn
#
# Mỗi quân cờ được mô tả bằng số bước `steps` đã đi tính từ ô xuất phát:
#   - steps == -1            : còn trong chuồng (chưa ra), cần tung 6 để ra
#   - 0  <= steps <= 50      : đang trên đường chung (52 ô)
#   - 51 <= steps <= 56      : đang trên đường về đích riêng (6 ô)
#   - steps == 56            : đã về đích (hoàn thành)
#
# Vị trí tuyệt đối trên đường chung của quân màu p tại bước s (0..50):
#       abs = (START_OFFSETS[p] + s) % 52
# Hai quân khác màu "gặp nhau" (ăn quân) khi có cùng abs và ô đó không an toàn.
# ──────────────────────────────────────────────────────────────────────────

TRACK_LEN = 52          # số ô trên đường chung
LAST_TRACK_STEP = 50    # bước cuối còn nằm trên đường chung (ô ngay trước lối vào đích)
HOME_LEN = 6            # số ô của đường về đích riêng
FINISH_STEP = 56        # = LAST_TRACK_STEP + HOME_LEN; tung đúng để về đích

# Ô xuất phát của 4 màu, cách đều nhau 13 ô trên đường chung
START_OFFSETS = [0, 13, 26, 39]

# Ô an toàn (không bị ăn): 4 ô xuất phát + 4 ô "sao" (cách ô xuất phát 8 ô)
SAFE_CELLS = set(START_OFFSETS) | {(off + 8) % TRACK_LEN for off in START_OFFSETS}


# Board coordinates for a standard 15x15 Ludo board.
# Player order: blue (left), red (top), green (right), yellow (bottom).
BOARD_SIZE = 15
PLAYER_SYMBOLS = ["B", "R", "G", "Y"]
EMPTY_CELL = " "
CENTER_CELL = "*"
TRACK_CELL = "."
SAFE_CELL = "S"

TRACK_COORDS = [
    (6, 1), (6, 2), (6, 3), (6, 4), (6, 5),
    (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6),
    (0, 7), (0, 8),
    (1, 8), (2, 8), (3, 8), (4, 8), (5, 8),
    (6, 9), (6, 10), (6, 11), (6, 12), (6, 13), (6, 14),
    (7, 14), (8, 14),
    (8, 13), (8, 12), (8, 11), (8, 10), (8, 9),
    (9, 8), (10, 8), (11, 8), (12, 8), (13, 8), (14, 8),
    (14, 7), (14, 6),
    (13, 6), (12, 6), (11, 6), (10, 6), (9, 6),
    (8, 5), (8, 4), (8, 3), (8, 2), (8, 1), (8, 0),
    (7, 0), (6, 0),
]

HOME_LANE_COORDS = {
    0: [(7, col) for col in range(1, 7)],
    1: [(row, 7) for row in range(1, 7)],
    2: [(7, col) for col in range(13, 7, -1)],
    3: [(row, 7) for row in range(13, 7, -1)],
}

YARD_COORDS = {
    0: [(1, 1), (1, 3), (3, 1), (3, 3)],
    1: [(1, 11), (1, 13), (3, 11), (3, 13)],
    2: [(11, 11), (11, 13), (13, 11), (13, 13)],
    3: [(11, 1), (11, 3), (13, 1), (13, 3)],
}

if len(TRACK_COORDS) != TRACK_LEN:
    raise ValueError("TRACK_COORDS must contain exactly 52 cells")


class HorseChessGame(MinigameBase):
    """
    Game Cờ Cá Ngựa (Ludo)
    - Mỗi người chơi có 4 quân cờ, bắt đầu trong chuồng
    - Đường chung 52 ô + đường về đích riêng 6 ô cho mỗi màu
    - Tung xúc xắc (1-6) để di chuyển; tung 6 để ra quân và được đi tiếp
    - Ăn quân đối thủ khi đáp đúng vị trí (trừ ô an toàn) -> quân đó về chuồng
    - Thắng khi cả 4 quân về đích
    """

    def __init__(self, game_id: str, mode: GameMode, players: List[Player]):
        super().__init__(game_id, "Horse Chess", mode, players)
        self.pieces_per_player = 4

        # steps[player_idx][piece_id] = số bước đã đi (-1..56)
        self.steps: Dict[int, Dict[int, int]] = {}

        # Số lần tung 6 liên tiếp (3 lần liên tiếp thì mất lượt)
        self.consecutive_sixes = 0
        self.max_consecutive_sixes = 3

        # Giá trị xúc xắc gần nhất (phục vụ hiển thị)
        self.last_dice: Optional[int] = None
        self.last_player_idx: Optional[int] = None

    async def initialize_game(self) -> None:
        """Khởi tạo trò chơi: tất cả quân ở trong chuồng (steps = -1)"""
        self.state = GameState.IN_PROGRESS

        for i in range(len(self.players)):
            self.steps[i] = {pid: -1 for pid in range(self.pieces_per_player)}

        await self.record_move({'event': 'game_started',
                                'players': [p.name for p in self.players]})

    # ── Xúc xắc & nước đi hợp lệ ────────────────────────────────────────────

    async def roll_dice(self) -> int:
        """Tung xúc xắc (1-6)"""
        return random.randint(1, 6)

    def absolute_position(self, player_idx: int, steps: int) -> Optional[int]:
        """Vị trí tuyệt đối trên đường chung (None nếu trong chuồng/đường về đích)"""
        if 0 <= steps <= LAST_TRACK_STEP:
            return (START_OFFSETS[player_idx % 4] + steps) % TRACK_LEN
        return None

    async def can_piece_move(self, player_idx: int, piece_id: int, dice_value: int) -> bool:
        """Kiểm tra quân cờ có thể di chuyển với số xúc xắc này không"""
        s = self.steps[player_idx][piece_id]

        # Đã về đích thì không đi nữa
        if s == FINISH_STEP:
            return False

        # Trong chuồng: chỉ ra được khi tung 6
        if s == -1:
            return dice_value == 6

        # Trên track / đường về đích: không được đi quá đích (phải tung đúng số)
        return s + dice_value <= FINISH_STEP

    async def get_valid_moves(self, player_idx: int, dice_value: int) -> List[Dict[str, Any]]:
        """Lấy tất cả nước đi hợp lệ cho số xúc xắc đã tung"""
        return [
            {'piece_id': pid, 'dice_value': dice_value}
            for pid in range(self.pieces_per_player)
            if await self.can_piece_move(player_idx, pid, dice_value)
        ]

    # ── Thực hiện nước đi ────────────────────────────────────────────────────

    async def _advance_turn(self, dice_value: int) -> None:
        """Quyết định chuyển lượt sau khi tung xúc xắc xong"""
        if dice_value == 6:
            self.consecutive_sixes += 1
            if self.consecutive_sixes >= self.max_consecutive_sixes:
                # Tung 6 ba lần liên tiếp -> mất lượt
                self.consecutive_sixes = 0
                await self.switch_turn()
            # else: được tung tiếp, giữ nguyên lượt
        else:
            self.consecutive_sixes = 0
            await self.switch_turn()

    async def pass_turn(self, dice_value: int) -> None:
        """Bỏ lượt khi không có nước đi hợp lệ (đã tung xúc xắc nhưng không đi được)"""
        self.last_dice = dice_value
        self.last_player_idx = self.current_turn_player_idx
        await self.record_move({'event': 'no_move', 'dice_value': dice_value})
        # Dù tung 6 mà không đi được vẫn mất lượt
        self.consecutive_sixes = 0
        await self.switch_turn()

    async def _capture_opponent_pieces(self, player_idx: int, abs_pos: int) -> List[Dict[str, int]]:
        """Ăn quân đối thủ tại vị trí tuyệt đối này. Trả về danh sách quân bị ăn."""
        captured = []
        if abs_pos in SAFE_CELLS:
            return captured  # ô an toàn: không ăn

        for i in range(len(self.players)):
            if i == player_idx:
                continue
            for pid in range(self.pieces_per_player):
                opp_abs = self.absolute_position(i, self.steps[i][pid])
                if opp_abs == abs_pos:
                    self.steps[i][pid] = -1  # về chuồng
                    captured.append({'player_idx': i, 'piece_id': pid})
        return captured

    async def make_move(self, player_idx: int, move: Dict[str, Any]) -> bool:
        """
        Thực hiện nước đi. move = {'piece_id': int, 'dice_value': int}
        - piece_id == -1: coi như không có nước đi -> bỏ lượt.
        Trả về True nếu quân thực sự di chuyển.
        """
        piece_id = move.get('piece_id', -1)
        dice_value = move['dice_value']

        # Không có nước đi -> bỏ lượt
        if piece_id == -1 or piece_id not in self.steps[player_idx]:
            await self.pass_turn(dice_value)
            return False

        if not await self.can_piece_move(player_idx, piece_id, dice_value):
            return False

        self.last_dice = dice_value
        self.last_player_idx = player_idx

        s = self.steps[player_idx][piece_id]
        new_steps = 0 if s == -1 else s + dice_value
        self.steps[player_idx][piece_id] = new_steps

        # Ăn quân nếu đáp xuống đường chung
        captured = []
        abs_pos = self.absolute_position(player_idx, new_steps)
        if abs_pos is not None:
            captured = await self._capture_opponent_pieces(player_idx, abs_pos)

        await self.record_move({
            'piece_id': piece_id,
            'dice_value': dice_value,
            'steps': new_steps,
            'captured': captured,
        })

        await self._advance_turn(dice_value)
        return True

    # ── Trạng thái & điều kiện thắng ─────────────────────────────────────────

    # Board rendering ---------------------------------------------------------

    def _blank_board(self) -> List[List[str]]:
        board = [[EMPTY_CELL * 2 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

        for idx, (row, col) in enumerate(TRACK_COORDS):
            board[row][col] = SAFE_CELL * 2 if idx in SAFE_CELLS else TRACK_CELL * 2

        for player_idx, coords in HOME_LANE_COORDS.items():
            symbol = PLAYER_SYMBOLS[player_idx]
            for number, (row, col) in enumerate(coords, start=1):
                board[row][col] = f"{symbol}{number}"

        for player_idx, coords in YARD_COORDS.items():
            symbol = PLAYER_SYMBOLS[player_idx]
            for row, col in coords:
                board[row][col] = f"{symbol}."

        board[7][7] = CENTER_CELL * 2
        return board

    def _put_piece(self, board: List[List[str]], row: int, col: int, token: str) -> None:
        current = board[row][col]
        if current.startswith(tuple(PLAYER_SYMBOLS)):
            board[row][col] = f"{current[0]}+"
        else:
            board[row][col] = token

    def _piece_coord(self, player_idx: int, piece_id: int, steps: int) -> tuple[int, int]:
        if steps == -1:
            return YARD_COORDS[player_idx % 4][piece_id]

        if 0 <= steps <= LAST_TRACK_STEP:
            abs_pos = self.absolute_position(player_idx, steps)
            return TRACK_COORDS[abs_pos]

        home_idx = min(steps - LAST_TRACK_STEP - 1, HOME_LEN - 1)
        return HOME_LANE_COORDS[player_idx % 4][home_idx]

    def render_board(self) -> str:
        """Hiển thị bàn cờ Cờ Cá Ngựa 15x15 trong Discord embed."""
        board = self._blank_board()
        occupied: Dict[tuple[int, int], List[str]] = {}

        for player_idx in range(len(self.players)):
            symbol = PLAYER_SYMBOLS[player_idx % 4]
            for piece_id, steps in self.steps[player_idx].items():
                coord = self._piece_coord(player_idx, piece_id, steps)
                occupied.setdefault(coord, []).append(f"{symbol}{piece_id + 1}")

        for (row, col), tokens in occupied.items():
            board[row][col] = tokens[0] if len(tokens) == 1 else f"{tokens[0][0]}+"

        rows = [" ".join(row).rstrip() for row in board]
        current_player = self.players[self.current_turn_player_idx].name
        dice = self.last_dice if self.last_dice is not None else "-"
        legend = "B=xanh dương, R=đỏ, G=xanh lá, Y=vàng | S=ô an toàn"
        return "```\n" + "\n".join(rows) + f"\n```\nLượt: {current_player} | Xúc xắc: {dice}\n{legend}"

    def pieces_finished(self, player_idx: int) -> int:
        """Số quân đã về đích của một người chơi"""
        return sum(1 for pid in range(self.pieces_per_player)
                   if self.steps[player_idx][pid] == FINISH_STEP)

    async def get_game_state(self) -> Dict[str, Any]:
        """Lấy trạng thái hiện tại (JSON-serializable)"""
        return {
            'steps': {str(i): {str(pid): self.steps[i][pid]
                               for pid in self.steps[i]} for i in self.steps},
            'current_player': self.players[self.current_turn_player_idx].name,
            'current_player_idx': self.current_turn_player_idx,
            'finished': {self.players[i].name: self.pieces_finished(i)
                         for i in range(len(self.players))},
            'last_dice': self.last_dice,
            'game_state': self.state.value,
        }

    async def is_game_over(self) -> bool:
        """Trò chơi kết thúc khi có người đưa cả 4 quân về đích"""
        return any(self.pieces_finished(i) == self.pieces_per_player
                   for i in range(len(self.players)))

    async def get_winner(self) -> Optional[Player]:
        """Lấy người thắng (None nếu chưa có)"""
        for i in range(len(self.players)):
            if self.pieces_finished(i) == self.pieces_per_player:
                return self.players[i]
        return None

    # ── AI Bot (chiến lược greedy) ───────────────────────────────────────────

    async def get_bot_move(self, player_idx: int) -> Dict[str, Any]:
        """
        Bot tung xúc xắc và chọn nước đi.
        Ưu tiên: ăn quân > đưa quân về đích > ra quân khỏi chuồng > đi xa nhất.
        Trả về {'piece_id': -1, 'dice_value': d} nếu không có nước đi.
        """
        dice_value = await self.roll_dice()
        valid_moves = await self.get_valid_moves(player_idx, dice_value)

        if not valid_moves:
            return {'piece_id': -1, 'dice_value': dice_value}

        def score(move: Dict[str, Any]) -> tuple:
            pid = move['piece_id']
            s = self.steps[player_idx][pid]
            new_steps = 0 if s == -1 else s + dice_value

            # Ưu tiên 1: ăn được quân đối thủ
            captures = 0
            abs_pos = self.absolute_position(player_idx, new_steps)
            if abs_pos is not None and abs_pos not in SAFE_CELLS:
                for i in range(len(self.players)):
                    if i == player_idx:
                        continue
                    for opp_pid in range(self.pieces_per_player):
                        if self.absolute_position(i, self.steps[i][opp_pid]) == abs_pos:
                            captures += 1

            reaches_home = 1 if new_steps == FINISH_STEP else 0   # ưu tiên 2: về đích
            leaves_yard = 1 if s == -1 else 0                     # ưu tiên 3: ra quân
            return (captures, reaches_home, leaves_yard, new_steps)

        return max(valid_moves, key=score)
