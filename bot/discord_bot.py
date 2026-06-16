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

    async def create_game(self, interaction: discord.Interaction, mode: GameMode) -> str:
        """Tạo một trò chơi cờ cá ngựa mới"""
        game_id = str(uuid.uuid4())[:8]

        # Tạo danh sách người chơi
        players = [Player(id=str(interaction.user.id), name=interaction.user.name, is_bot=False)]

        # Thêm bot nếu cần
        num_bots = {
            GameMode.SINGLE_PLAYER: 1,
            GameMode.TWO_BOTS: 2,
            GameMode.THREE_BOTS: 3
        }.get(mode, 1)

        for i in range(num_bots):
            players.append(Player(id=f"bot_{i}", name=f"Bot {i + 1}", is_bot=True))

        # Tạo trò chơi
        game = HorseChessGame(game_id, mode, players)
        await game.initialize_game()

        self.active_games[game_id] = game
        self.user_current_game[interaction.user.id] = game_id

        # Lưu vào database
        await self.db.create_game_session(
            game_id,
            "Horse Chess",
            [p.name for p in players],
            mode.value
        )

        return game_id

    @app_commands.command(name="horsechess", description="Bắt đầu trò chơi Cờ Cá Ngựa")
    @app_commands.describe(mode="Chế độ chơi: đơn (1 bot), đôi (2 bot), ba (3 bot)")
    @app_commands.choices(mode=[
        app_commands.Choice(name="1 Bot", value="single"),
        app_commands.Choice(name="2 Bots", value="double"),
        app_commands.Choice(name="3 Bots", value="triple"),
    ])
    async def start_horse_chess(self, interaction: discord.Interaction, mode: str = "single"):
        """Bắt đầu trò chơi cờ cá ngựa"""
        mode_map = {
            'single': GameMode.SINGLE_PLAYER,
            'double': GameMode.TWO_BOTS,
            'triple': GameMode.THREE_BOTS
        }

        await interaction.response.defer()

        game_mode = mode_map.get(mode.lower(), GameMode.SINGLE_PLAYER)
        game_id = await self.create_game(interaction, game_mode)

        game = self.active_games[game_id]

        # Hiển thị thông tin trò chơi
        embed = discord.Embed(
            title="🐴 Cờ Cá Ngựa",
            color=discord.Color.blue()
        )
        embed.add_field(name="Mã game", value=game_id, inline=False)
        embed.add_field(name="Chế độ", value=game_mode.value, inline=False)
        embed.add_field(name="Người chơi", value='\n'.join([f"{'🤖' if p.is_bot else '👤'} {p.name}" for p in game.players]), inline=False)

        await interaction.followup.send(embed=embed)

        # Bắt đầu trò chơi
        await self._game_loop(interaction, game_id)

    async def _game_loop(self, interaction: discord.Interaction, game_id: str) -> None:
        """Vòng lặp chính của trò chơi"""
        game = self.active_games[game_id]
        channel = interaction.channel

        try:
            while not await game.is_game_over():
                current_player = await game.get_current_player()

                # Hiển thị lượt chơi
                embed = discord.Embed(
                    title=f"Lượt chơi: {current_player.name}",
                    color=discord.Color.green()
                )

                embed.add_field(name="Trạng thái bàn cờ", value=game.render_board(), inline=False)

                await channel.send(embed=embed)

                if current_player.is_bot:
                    # Bot chơi tự động
                    await asyncio.sleep(BOT_DELAY)
                    await self._play_bot_turn_and_report(channel, game)
                else:
                    # Cho người chơi thực hiện nước đi
                    await self._wait_for_player_move(interaction, game_id)

                # Lưu trạng thái trò chơi; lỗi DB không được làm dừng ván đang chơi
                try:
                    await self.db.save_game_state(game_id, await game.get_game_state())
                except Exception as db_error:
                    print(f"Không thể lưu trạng thái game {game_id}: {db_error}")
                await asyncio.sleep(1)

            # Trò chơi kết thúc
            winner = await game.get_winner()
            if winner:
                game.state = GameState.FINISHED

                embed = discord.Embed(
                    title="🎉 Trò chơi kết thúc!",
                    description=f"Người thắng: {winner.name}",
                    color=discord.Color.gold()
                )

                await channel.send(embed=embed)

                # Lưu kết quả
                await self.db.finish_game(game_id, winner.name, await game.get_game_state())

                # Xóa trò chơi
                del self.active_games[game_id]
                if interaction.user.id in self.user_current_game:
                    del self.user_current_game[interaction.user.id]

        except asyncio.TimeoutError:
            await channel.send("❌ Trò chơi hết thời gian!")

    async def _play_bot_turn_and_report(self, channel, game: HorseChessGame) -> None:
        """Cho bot chơi và báo cáo kết quả trong kênh Discord."""
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

        embed = discord.Embed(
            title="Lượt bot",
            description=description,
            color=color,
        )
        embed.add_field(name="Bàn cờ", value=game.render_board(), inline=False)
        await channel.send(embed=embed)

    async def _wait_for_player_move(self, interaction: discord.Interaction, game_id: str) -> None:
        """Chờ người chơi tung xúc xắc và chọn quân hợp lệ."""
        game = self.active_games[game_id]
        current_player = await game.get_current_player()
        channel = interaction.channel
        player_id = int(current_player.id)
        turn_done = asyncio.Event()
        rolled = False
        move_message: Optional[discord.Message] = None

        roll_view = discord.ui.View(timeout=GAME_TIMEOUT)
        roll_button = discord.ui.Button(
            label="Tung xúc xắc",
            style=discord.ButtonStyle.success,
            custom_id=f"roll_{game_id}",
        )
        roll_view.add_item(roll_button)

        roll_embed = discord.Embed(
            title=f"Lượt chơi: {current_player.name}",
            description="Bấm **Tung xúc xắc** để bắt đầu lượt của bạn.",
            color=discord.Color.blue(),
        )
        roll_message = await channel.send(embed=roll_embed, view=roll_view)

        async def reject_wrong_user(button_interaction: discord.Interaction) -> bool:
            if button_interaction.user.id != player_id:
                await button_interaction.response.send_message("Không phải lượt của bạn!", ephemeral=True)
                return False
            return True

        async def roll_callback(button_interaction: discord.Interaction):
            nonlocal rolled, move_message
            if not await reject_wrong_user(button_interaction):
                return

            rolled = True
            dice_value = await game.roll_dice()
            valid_moves = await game.get_valid_moves(game.current_turn_player_idx, dice_value)
            roll_button.disabled = True

            if not valid_moves:
                await game.pass_turn(dice_value)
                no_move_embed = discord.Embed(
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

                for item in move_view.children:
                    item.disabled = True

                move_embed = discord.Embed(
                    title="Nước đi thành công",
                    description=f"{current_player.name} di chuyển quân **{piece_id + 1}**\nXúc xắc: **{dice_value}**",
                    color=discord.Color.green(),
                )
                move_embed.add_field(name="Bàn cờ", value=game.render_board(), inline=False)
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

            choose_embed = discord.Embed(
                title=f"{current_player.name} tung được {dice_value}",
                description="Chọn quân cờ hợp lệ để di chuyển.",
                color=discord.Color.blue(),
            )
            await button_interaction.response.edit_message(embed=choose_embed, view=move_view)
            move_message = roll_message
            roll_view.stop()

        roll_button.callback = roll_callback

        await roll_view.wait()
        if not rolled:
            await channel.send(f"Hết thời gian tung xúc xắc! {current_player.name} bị bỏ qua.")
            await game.switch_turn()
            await roll_message.edit(view=None)
            return

        if not turn_done.is_set():
            try:
                await asyncio.wait_for(turn_done.wait(), timeout=GAME_TIMEOUT)
            except asyncio.TimeoutError:
                if game.current_turn_player_idx < len(game.players) and game.players[game.current_turn_player_idx].id == current_player.id:
                    await channel.send(f"Hết thời gian chọn quân! {current_player.name} bị bỏ qua.")
                    await game.switch_turn()
                    if move_message:
                        await move_message.edit(view=None)

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
