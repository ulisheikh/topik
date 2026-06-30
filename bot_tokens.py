from pathlib import Path
from environs import Env

BASE_DIR = Path(__file__).resolve().parent

env = Env()
env.read_env(BASE_DIR / ".env")

DICT_BOT_TOKEN = env.str("DICT_BOT_TOKEN")
MEMO_BOT_TOKEN = env.str("MEMO_BOT_TOKEN")