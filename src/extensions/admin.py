import os
from datetime import datetime

import psutil
from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(brief="특정 모듈을 핫 리로딩 합니다.")
    async def reload(self, ctx, path):
        self.bot.reload_extension(f"extensions.{path}")
        await ctx.send(f"Successfully reloaded `{path}`!")

    @commands.command(brief="서버 업타임과 봇 가동 시간을 확인합니다.")
    async def uptime(self, ctx):
        now = datetime.now()
        server_uptime = now - datetime.fromtimestamp(psutil.boot_time())
        python_uptime = now - datetime.fromtimestamp(
            psutil.Process(os.getpid()).create_time()
        )

        await ctx.send(
            f"**Server Uptime** {server_uptime}\n" + f"**Bot Uptime** {python_uptime}"
        )


def setup(bot):
    bot.add_cog(Admin(bot))
