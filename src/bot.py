import json
import logging
import logging.config
import os

from discord.ext import commands
from dotenv import load_dotenv

with open("logging.json") as f:
    logging.config.dictConfig(json.load(f))


logger = logging.getLogger("lara")
load_dotenv()


class LaraBot(commands.Bot):
    extension_list = ["extensions.user", "extensions.admin", "extensions.forte"]

    async def on_ready(self):
        logger.info(f"Logged in as {self.user}")

    async def on_error(self, event, *args, **kwargs):
        logger.exception("")

    def __init__(self):
        super().__init__(commands.when_mentioned_or("라라야 ", "라라 ", "ㄹ ", "lara "))
        for ext in self.extension_list:
            self.load_extension(ext)


bot = LaraBot()


bot.run(os.getenv("BOT_TOKEN"))
