import os

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class LaraBot(commands.Bot):
    extension_list = ["extensions.user", "extensions.admin", "extensions.forte"]

    def __init__(self):
        super().__init__(commands.when_mentioned_or("라라야 ", "라라 ", "ㄹ ", "lara "))
        for ext in self.extension_list:
            self.load_extension(ext)


bot = LaraBot()


bot.run(os.getenv("BOT_TOKEN"))
