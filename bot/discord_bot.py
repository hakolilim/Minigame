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
    """Cộng đồng của tất cả minigame"""

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
    @app_commands.describe(mode="Chế độ chơi: single (1 bot), double (2 bots), triple (3 bots)")
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
        embed.add_field(name="Game ID", value=game_id, inline=False)
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
                    await game.play_bot_turn()
                else:
                    # Chờ người chơi thực hiện nước đi
                    await self._wait_for_player_move(interaction, game_id)

                # Lưu trạng thái trò chơi
                await self.db.save_game_state(game_id, await game.get_game_state())

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

    async def _wait_for_player_move(self, interaction: discord.Interaction, game_id: str) -> None:
        """Chờ người chơi thực hiện nước đi"""
        game = self.active_games[game_id]
        current_player = await game.get_current_player()
        channel = interaction.channel

        # Gửi thông báo và buttons
        view = discord.ui.View()
        piece_buttons = []

        for piece_id in range(4):
            btn = discord.ui.Button(
                label=f"Quân {piece_id}",
                style=discord.ButtonStyle.primary,
                custom_id=f"move_{game_id}_{piece_id}"
            )
            piece_buttons.append(btn)
            view.add_item(btn)

        embed = discord.Embed(
            title=f"🎮 Lượt chơi: {current_player.name}",
            description=f"Chọn quân cờ để di chuyển",
            color=discord.Color.blue()
        )

        message = await channel.send(embed=embed, view=view)

        # Xác định callback cho nút
        async def button_callback(button_interaction: discord.Interaction):
            if button_interaction.user.id != int(current_player.id):
                await button_interaction.response.send_message("❌ Không phải lượt của bạn!", ephemeral=True)
                return

            piece_id = int(button_interaction.custom_id.split("_")[-1])

            # Tung xúc xắc
            dice_value = await game.roll_dice()

            # Kiểm tra nước đi hợp lệ
            valid_moves = await game.get_valid_moves(game.current_turn_player_idx, dice_value)

            move_valid = any(m['piece_id'] == piece_id for m in valid_moves)

            if not move_valid:
                await button_interaction.response.send_message(
                    f"❌ Nước đi không hợp lệ! Xúc xắc: {dice_value}",
                    ephemeral=True
                )
                return

            # Thực hiện nước đi
            move = {'piece_id': piece_id, 'dice_value': dice_value}
            await game.make_move(game.current_turn_player_idx, move)

            embed_move = discord.Embed(
                title="✅ Nước đi thành công",
                description=f"{current_player.name} di chuyển quân {piece_id}\n🎲 Xúc xắc: {dice_value}",
                color=discord.Color.green()
            )
            await button_interaction.response.send_message(embed=embed_move)

            # Xóa buttons
            view.stop()
            await message.edit(view=None)

        for btn in piece_buttons:
            btn.callback = button_callback

        try:
            await asyncio.wait_for(view.wait(), timeout=GAME_TIMEOUT)
        except asyncio.TimeoutError:
            await channel.send(f"⏱️ Hết thời gian! {current_player.name} bị bỏ qua.")
            await game.switch_turn()
            view.stop()
            await message.edit(view=None)

    @app_commands.command(name="stats", description="Xem thống kê của bạn")
    @app_commands.describe(member="Người chơi (nếu để trống sẽ xem của bạn)")
    async def show_stats(self, interaction: discord.Interaction, member: Optional[discord.User] = None):
        """Hiển thị thống kê người chơi"""
        await interaction.response.defer()
        player = member or interaction.user
        stats = await self.db.get_player_stats(player.name)

        embed = discord.Embed(
            title=f"📊 Thống kê: {player.name}",
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
            title="🏆 Bảng Xếp Hạng" + (f" - {game}" if game else ""),
            color=discord.Color.gold()
        )

        if not leaderboard:
            embed.description = "Chưa có dữ liệu"
        else:
            for entry in leaderboard[:10]:  # Top 10
                embed.add_field(
                    name=f"#{entry['rank']} {entry['player']}",
                    value=f"{entry['wins']} wins",
                    inline=False
                )

        await interaction.followup.send(embed=embed)


async def setup(bot):
    """Setup hàm cho lệnh"""
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
            print(f"📝 Đã sync {len(synced)} slash commands")
        except Exception as e:
            print(f"❌ Lỗi sync commands: {e}")

    # Thêm cogs (add_cog là coroutine từ discord.py 2.0+, bắt buộc await)
    cog = MinigameBot(bot, db)
    await bot.add_cog(cog)

    return bot
