import os
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv

from api import request

load_dotenv(verbose=True, override=True)


class ForteUser(commands.Converter):
    discord_id_pattern = re.compile(r"^(?:<@!?)?(\d{18})>?$")

    async def convert(self, ctx, argument):
        user = None
        match = self.discord_id_pattern.match(argument)
        if match:
            discord_id = match.group(1)
            user, _ = await request("get", f"/discords/{discord_id}")
            if "id" not in user.keys():
                await ctx.send("FORTE에 가입하지 않은 디스코드 계정입니다.")
                raise commands.CommandError(
                    f"Unregistered user (Discord ID: {discord_id})"
                )
        else:
            user, _ = await request("get", f"/users/{argument}")
            if type(user) is not dict:
                await ctx.send("존재하지 않는 사용자 정보입니다.")
                raise commands.CommandError(f"User not found (User ID: {argument})")

        if user.get("deleted_at") is not None:
            await ctx.send("탈퇴한 사용자입니다.")
            raise commands.CommandError(f"Deleted user (User ID: {user['id']})")

        return user

    @staticmethod
    def to_embed(user: dict) -> discord.Embed:
        return (
            discord.Embed(
                title=f"{user['name']} (ID: {user['id']})",
                description=user.get("email", ""),
            )
            .add_field(name="가입 시각", value=user.get("created_at", ""))
            .add_field(name="보유 포인트", value=f"{user['points']}")
        )


class Forte(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if ctx.guild is None:
            return False

        role = ctx.guild.get_role(int(os.getenv("ADMIN_ROLE")))
        if role is None:
            return False

        return role in ctx.author.roles

    async def cog_command_error(self, ctx, error):
        if isinstance(ctx, commands.CheckFailure):
            return

        print(error)

    @commands.command("xsolla:sync")
    async def sync(self, ctx):
        pass

    @commands.group(aliases=["포르테", "ㅍ"])
    async def forte(self, ctx):
        pass

    @forte.command(aliases=["사용자"])
    async def user(self, ctx, user: ForteUser):
        await ctx.send(embed=ForteUser.to_embed(user))

    @forte.group()
    async def items(self, ctx):
        pass

    @forte.command(aliases=["지급"])
    async def deposit(self, ctx, user: ForteUser, point: int):
        embed = ForteUser.to_embed(user).add_field(
            name="예상 포인트", value=str(user["points"] + point)
        )
        await ctx.send(content="다음과 같이 포인트를 지급합니다.", embed=embed)

        # TODO POST /points


def setup(bot):
    bot.add_cog(Forte(bot))
