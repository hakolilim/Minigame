import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, Optional
import uuid
from games.horse_chess import HorseChessGame
from core.minigame_base import GameMode, Player, GameState
from config.settings import DISCORD_TOKEN, BOT_DELAY, GAME_TIMEOUT
from database.supabase_manager import SupabaseManager
import asyncio

class MinigameBot(commands.Cog):
    """Cog quản lý các lệnh và phiên chơi minigame."""

    def __init__(self, bot: commands.Bot, db: SupabaseManager):
        self.bot = bot
        self.db = db
        self.active_games: Dict[str, HorseChessGame] = {}
        self.user_current_game: Dict[int, str] = {}  # user_id -> game_id

    async def create_game(self, interaction: discord.Interaction, mode: GameMode, human_members: list[discord.abc.User]) -> str:
        """Tạo một trò chơi Cờ Cá Ngựa mới."""
        game_id = str(uuid.uuid4())[:8]

        num_bots = {
            GameMode.NO_BOTS: 0,
            GameMode.SINGLE_PLAYER: 1,
            GameMode.TWO_BOTS: 2,
            GameMode.THREE_BOTS: 3,
        }.get(mode, 3)
        required_humans = 4 - num_bots

        if len(human_members) != required_humans:
            raise ValueError(f"Chế độ này cần {required_humans} người chơi thật và {num_bots} bot.")

        seen_user_ids = set()
        players = []
        for member in human_members:
            if member.bot:
                raise ValueError("Không thể chọn Discord bot làm người chơi thật.")
            if member.id in seen_user_ids:
                raise ValueError("Danh sách người chơi thật không được trùng nhau.")
            seen_user_ids.add(member.id)
            players.append(Player(id=str(member.id), name=member.name, is_bot=False))

        for i in range(num_bots):
            players.append(Player(id=f"bot_{i}", name=f"Bot {i + 1}", is_bot=True))

        game = HorseChessGame(game_id, mode, players)
        await game.initialize_game()

        self.active_games[game_id] = game
        for member in human_members:
            self.user_current_game[member.id] = game_id

        await self.db.create_game_session(
            game_id,
            "Horse Chess",
            [p.name for p in players],
            mode.value
        )

        return game_id

    @app_commands.command(name="horsechess", description="Bắt đầu trò chơi Cờ Cá Ngựa")
    @app_commands.describe(
        mode="Chế độ chơi theo số bot",
        player2="Người chơi thứ 2 (bắt buộc với 0/1/2 bot)",
        player3="Người chơi thứ 3 (bắt buộc với 0/1 bot)",
        player4="Người chơi thứ 4 (bắt buộc với 0 bot)",
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="0 Bot", value="zero"),
        app_commands.Choice(name="1 Bot", value="single"),
        app_commands.Choice(name="2 Bots", value="double"),
        app_commands.Choice(name="3 Bots", value="triple"),
    ])
    async def start_horse_chess(
        self,
        interaction: discord.Interaction,
        mode: str = "triple",
        player2: Optional[discord.User] = None,
        player3: Optional[discord.User] = None,
        player4: Optional[discord.User] = None,
    ):
        """Bắt đầu trò chơi Cờ Cá Ngựa."""
        mode_map = {
            'zero': GameMode.NO_BOTS,
            'single': GameMode.SINGLE_PLAYER,
            'double': GameMode.TWO_BOTS,
            'triple': GameMode.THREE_BOTS,
        }

        await interaction.response.defer()

        game_mode = mode_map.get(mode.lower(), GameMode.THREE_BOTS)
        human_members = [interaction.user]
        human_members.extend(member for member in (player2, player3, player4) if member is not None)

        try:
            game_id = await self.create_game(interaction, game_mode, human_members)
        except ValueError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return

        game = self.active_games[game_id]

        embed = discord.Embed(
            title="Horse Chess",
            color=discord.Color.blue()
        )
        embed.add_field(name="Game ID", value=game_id, inline=False)
        embed.add_field(name="Mode", value=game_mode.value, inline=False)
        player_list = "\n".join([f"{'[BOT]' if p.is_bot else '[USER]'} {p.name}" for p in game.players])
        embed.add_field(name="Players", value=player_list, inline=False)

        await interaction.followup.send(embed=embed)

        await self._game_loop(interaction, game_id)

    async def _game_loop(self, interaction: discord.Interaction, game_id: str) -> None:
        """Main game loop. Update one status message instead of sending new board messages."""
        game = self.active_games[game_id]
        channel = interaction.channel
        status_message: Optional[discord.Message] = None

        try:
            while not await game.is_game_over():
                current_player = await game.get_current_player()
                embed = self._build_board_embed(
                    game,
                    title=f"Lượt chơi: {current_player.name}",
                    color=discord.Color.green(),
                )

                if status_message is None:
                    status_message = await channel.send(embed=embed)
                else:
                    await status_message.edit(embed=embed, view=None)

                if current_player.is_bot:
                    await asyncio.sleep(BOT_DELAY)
                    await self._play_bot_turn_and_report(status_message, game)
                else:
                    await self._wait_for_player_move(interaction, game_id, status_message)

                try:
                    await self.db.save_game_state(game_id, await game.get_game_state())
                except Exception as db_error:
                    print(f"Không thể lưu trạng thái game {game_id}: {db_error}")
                await asyncio.sleep(1)

            winner = await game.get_winner()
            if winner:
                game.state = GameState.FINISHED
                embed = self._build_board_embed(
                    game,
                    title="Trò chơi kết thúc!",
                    description=f"Người thắng: {winner.name}",
                    color=discord.Color.gold(),
                )

                if status_message is None:
                    status_message = await channel.send(embed=embed)
                else:
                    await status_message.edit(embed=embed, view=None)

                await self.db.finish_game(game_id, winner.name, await game.get_game_state())

                del self.active_games[game_id]
                for player in game.players:
                    if not player.is_bot:
                        self.user_current_game.pop(int(player.id), None)

        except asyncio.TimeoutError:
            if status_message is not None:
                await status_message.edit(content="Trò chơi hết thời gian!", embed=None, view=None)
            else:
                await channel.send("Trò chơi hết thời gian!")

    def _build_board_embed(
        self,
        game: HorseChessGame,
        title: str,
        description: Optional[str] = None,
        color: Optional[discord.Color] = None,
    ) -> discord.Embed:
        """Build the shared board embed used by the single editable status message."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or discord.Color.blue(),
        )
        embed.add_field(name="Trạng thái bàn cờ", value=game.render_board(), inline=False)
        return embed

    async def _play_bot_turn_and_report(self, status_message: discord.Message, game: HorseChessGame) -> None:
        """Let a bot play and edit the shared status message with the result."""
        bot_idx = game.current_turn_player_idx
        bot_player = game.players[bot_idx]
        before_history_len = len(game.history)

        moved = await game.play_bot_turn()
        last_move = game.history[-1] if len(game.history) > before_history_len else {}
        dice_value = last_move.get('dice_value', game.last_dice)

        if moved:
            piece_id = last_move.get('piece_id', 0)
            description = f"{bot_player.name} tung **{dice_value}** và đi quân **{piece_id + 1}**."
            color = discord.Color.green()
        else:
            description = f"{bot_player.name} tung **{dice_value}** nhưng không có nước đi hợp lệ."
            color = discord.Color.orange()

        embed = self._build_board_embed(
            game,
            title="Lượt bot",
            description=description,
            color=color,
        )
        await status_message.edit(embed=embed, view=None)

    async def _wait_for_player_move(self, interaction: discord.Interaction, game_id: str, status_message: discord.Message) -> None:
        """Wait for a human player to roll and choose a piece on the shared status message."""
        game = self.active_games[game_id]
        current_player = await game.get_current_player()
        player_id = int(current_player.id)
        turn_done = asyncio.Event()
        rolled = False

        roll_view = discord.ui.View(timeout=GAME_TIMEOUT)
        roll_button = discord.ui.Button(
            label="Tung xúc xắc",
            style=discord.ButtonStyle.success,
            custom_id=f"roll_{game_id}",
        )
        roll_view.add_item(roll_button)

        roll_embed = self._build_board_embed(
            game,
            title=f"Lượt chơi: {current_player.name}",
            description="Bấm **Tung xúc xắc** để bắt đầu lượt của bạn.",
            color=discord.Color.blue(),
        )
        await status_message.edit(embed=roll_embed, view=roll_view)

        async def reject_wrong_user(button_interaction: discord.Interaction) -> bool:
            if button_interaction.user.id != player_id:
                await button_interaction.response.send_message("Không phải lượt của bạn!", ephemeral=True)
                return False
            return True

        async def roll_callback(button_interaction: discord.Interaction):
            nonlocal rolled
            if not await reject_wrong_user(button_interaction):
                return

            rolled = True
            dice_value = await game.roll_dice()
            valid_moves = await game.get_valid_moves(game.current_turn_player_idx, dice_value)
            roll_button.disabled = True

            if not valid_moves:
                await game.pass_turn(dice_value)
                no_move_embed = self._build_board_embed(
                    game,
                    title="Không có nước đi",
                    description=f"{current_player.name} tung **{dice_value}** nhưng không có quân nào đi được.",
                    color=discord.Color.orange(),
                )
                await button_interaction.response.edit_message(embed=no_move_embed, view=None)
                turn_done.set()
                roll_view.stop()
                return

            valid_piece_ids = {move['piece_id'] for move in valid_moves}
            move_view = discord.ui.View(timeout=GAME_TIMEOUT)

            async def move_callback(move_interaction: discord.Interaction):
                if not await reject_wrong_user(move_interaction):
                    return

                piece_id = int(move_interaction.data['custom_id'].split("_")[-1])
                if piece_id not in valid_piece_ids:
                    await move_interaction.response.send_message(
                        f"Quân này không đi được với xúc xắc {dice_value}.",
                        ephemeral=True,
                    )
                    return

                await game.make_move(game.current_turn_player_idx, {
                    'piece_id': piece_id,
                    'dice_value': dice_value,
                })

                move_embed = self._build_board_embed(
                    game,
                    title="Nước đi thành công",
                    description=f"{current_player.name} di chuyển quân **{piece_id + 1}**\nXúc xắc: **{dice_value}**",
                    color=discord.Color.green(),
                )
                await move_interaction.response.edit_message(embed=move_embed, view=None)
                move_view.stop()
                turn_done.set()

            for piece_id in range(4):
                btn = discord.ui.Button(
                    label=f"Quân {piece_id + 1}",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"move_{game_id}_{piece_id}",
                    disabled=piece_id not in valid_piece_ids,
                )
                btn.callback = move_callback
                move_view.add_item(btn)

            choose_embed = self._build_board_embed(
                game,
                title=f"{current_player.name} tung được {dice_value}",
                description="Chọn quân cờ hợp lệ để di chuyển.",
                color=discord.Color.blue(),
            )
            await button_interaction.response.edit_message(embed=choose_embed, view=move_view)
            roll_view.stop()

        roll_button.callback = roll_callback

        await roll_view.wait()
        if not rolled:
            await game.switch_turn()
            timeout_embed = self._build_board_embed(
                game,
                title="Hết thời gian",
                description=f"{current_player.name} không tung xúc xắc kịp và bị bỏ qua.",
                color=discord.Color.orange(),
            )
            await status_message.edit(embed=timeout_embed, view=None)
            return

        if not turn_done.is_set():
            try:
                await asyncio.wait_for(turn_done.wait(), timeout=GAME_TIMEOUT)
            except asyncio.TimeoutError:
                if game.current_turn_player_idx < len(game.players) and game.players[game.current_turn_player_idx].id == current_player.id:
                    await game.switch_turn()
                    timeout_embed = self._build_board_embed(
                        game,
                        title="Hết thời gian",
                        description=f"{current_player.name} không chọn quân kịp và bị bỏ qua.",
                        color=discord.Color.orange(),
                    )
                    await status_message.edit(embed=timeout_embed, view=None)

    @app_commands.command(name="help", description="Hướng dẫn cách chơi Cờ Cá Ngựa")
    async def show_help(self, interaction: discord.Interaction):
        """Hiển thị hướng dẫn chơi."""
        embed = discord.Embed(
            title="Hướng dẫn chơi Cờ Cá Ngựa",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Bắt đầu",
            value="Dùng `/horsechess` để tạo bàn chơi. Chọn chế độ 1/2/3 bot.",
            inline=False,
        )
        embed.add_field(
            name="Cách đi",
            value="1) Bấm **Tung xúc xắc**\n2) Chọn quân hợp lệ\n3) Tung số 6 để ra quân từ chuồng",
            inline=False,
        )
        embed.add_field(
            name="Luật nhanh",
            value="- Ăn quân đối thủ khi đứng cùng ô và ô đó không an toàn\n- Ra 6 được đi tiếp\n- 4 quân về đích là thắng",
            inline=False,
        )
        embed.add_field(
            name="Lệnh hữu ích",
            value="`/horsechess` - chơi Cờ Cá Ngựa\n`/stats` - xem thống kê\n`/leaderboard` - bảng xếp hạng\n`/help` - hướng dẫn",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stats", description="Xem thống kê của bạn")
    @app_commands.describe(member="Người chơi (nếu để trống sẽ xem của bạn)")
    async def show_stats(self, interaction: discord.Interaction, member: Optional[discord.User] = None):
        """Hiển thị thống kê người chơi."""
        await interaction.response.defer()
        player = member or interaction.user
        stats = await self.db.get_player_stats(player.name)

        embed = discord.Embed(
            title=f"Thống kê: {player.name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Tổng trận", value=stats['total_games'], inline=True)
        embed.add_field(name="Thắng", value=stats['wins'], inline=True)
        embed.add_field(name="Tỷ lệ thắng", value=f"{stats['win_rate']:.1f}%", inline=True)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="leaderboard", description="Xem bảng xếp hạng")
    @app_commands.describe(game="Trò chơi (nếu để trống sẽ xem tất cả)")
    async def show_leaderboard(self, interaction: discord.Interaction, game: Optional[str] = None):
        """Hiển thị bảng xếp hạng"""
        await interaction.response.defer()
        leaderboard = await self.db.get_leaderboard(game)

        embed = discord.Embed(
            title="🏆 Bảng xếp hạng" + (f" - {game}" if game else ""),
            color=discord.Color.gold()
        )

        if not leaderboard:
            embed.description = "Chưa có dữ liệu"
        else:
            for entry in leaderboard[:10]:  # Top 10
                embed.add_field(
                    name=f"#{entry['rank']} {entry['player']}",
                    value=f"{entry['wins']} trận thắng",
                    inline=False
                )

        await interaction.followup.send(embed=embed)


async def setup(bot):
    """Hàm thiết lập extension Discord bot."""
    pass


async def create_bot(db: SupabaseManager) -> commands.Bot:
    """Tạo và cấu hình bot Discord"""
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix='/', intents=intents)

    @bot.event
    async def on_ready():
        try:
            synced = await bot.tree.sync()
            print(f"✅ Bot {bot.user} đã sẵn sàng!")
            print(f"📝 Đã đồng bộ {len(synced)} slash commands")
        except Exception as e:
            print(f"❌ Lỗi đồng bộ slash commands: {e}")

    # Thêm cogs (add_cog là coroutine từ discord.py 2.0+, bắt buộc await)
    cog = MinigameBot(bot, db)
    await bot.add_cog(cog)

    return bot
