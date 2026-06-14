import os
from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Game settings
GAME_TIMEOUT = 300  # 5 minutes
BOT_DELAY = 1  # 1 second delay trước khi bot chơi
MAX_PLAYERS_PER_GAME = 4

# Validate required configs
required_configs = ['DISCORD_TOKEN', 'SUPABASE_URL', 'SUPABASE_KEY']
for config in required_configs:
    if not globals().get(config):
        raise ValueError(f"Missing required config: {config}")
