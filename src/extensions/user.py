import logging
import os

from discord.ext import commands
from dotenv import load_dotenv

from api import request

load_dotenv(verbose=True, override=True)


class User(commands.Cog):
    guild_whitelist = [
        int(guild_id.strip()) for guild_id in os.getenv("GUILD_WHITELIST").split(",")
    ]
    logger = logging.getLogger("lara.user")

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return ctx.guild is not None and ctx.guild.id in self.guild_whitelist

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("⚠️ **팀 크레센도 디스코드**에서만 사용 가능한 명령어입니다.")
            return

        self.logger.error(str(error))

    @commands.command(
        "출석", aliases=["출석체크", "출첵", "ㅊ"], brief="팀 크레센도 디스코드 서버에 출석합니다.",
    )
    async def attend(self, ctx):
        await ctx.send(
            f"""{ctx.author.mention}, 출석해주셔서 감사합니다. 🙌

아쉽지만 `팀 크레센도 디스코드에서 출석하고 무료 POINT를 얻자!` 이벤트는 종료됐습니다.

팀 크레센도에서 🌟 **새로운 출석 이벤트**를 야심차게 준비하고 있으니, 조금만 기다려주세요!"""
        )

    @commands.command("구독", brief="전용 구독자 역할을 지급받거나 반환합니다.")
    async def subscribe(self, ctx):
        role = ctx.guild.get_role(int(os.getenv("SUBSCRIBER_ROLE")))
        if role is None:
            return await ctx.send("⚠️ 구독자 역할을 찾을 수 없습니다.")

        if role not in ctx.author.roles:
            await ctx.author.add_roles(role)
            await ctx.send(f"{ctx.author.mention}, 구독자 역할을 지급했습니다.")
        else:
            await ctx.author.remove_roles(role)
            await ctx.send(f"{ctx.author.mention}, 구독자 역할을 회수했습니다.")


def setup(bot):
    bot.add_cog(User(bot))
