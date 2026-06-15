import asyncio
import os
from bot.discord_bot import create_bot
from database.supabase_manager import SupabaseManager
from config.settings import DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY

async def main():
    # Khởi tạo database
    db = SupabaseManager(SUPABASE_URL, SUPABASE_KEY)

    # Tạo bot
    bot = await create_bot(db)

    # Chạy bot
    await bot.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
