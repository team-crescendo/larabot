import logging
import os
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv

import interface
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
    logger = logging.getLogger("lara.forte")

    def __init__(self, bot):
        self.bot = bot

        admin_role_env = os.getenv("ADMIN_ROLE")
        if admin_role_env is None:
            raise ValueError("Environment variable ADMIN_ROLE is not defined")
        self.admin_role = int(admin_role_env)

    async def cog_check(self, ctx):
        if ctx.guild is None:
            return False

        role = ctx.guild.get_role(self.admin_role)
        if role is None:
            return False

        return role in ctx.author.roles

    async def cog_command_error(self, ctx, error):
        if isinstance(ctx, commands.CheckFailure):
            return

        self.logger.error(str(error))

    @commands.group(aliases=["포르테", "ㅍ"], brief="포르테 API 관련 명령어가 모아져 있습니다.")
    async def forte(self, ctx):
        pass

    @forte.command(aliases=["사용자"], brief="포르테 이용자 정보를 확인합니다.")
    async def user(self, ctx, user: ForteUser):
        await ctx.send(embed=ForteUser.to_embed(user))

    @forte.command(aliases=["지급"], brief="포르테 이용자에게 포인트를 지급합니다.")
    async def deposit(self, ctx, user: ForteUser, point: int):
        embed = ForteUser.to_embed(user).add_field(
            name="예상 포인트", value=str(user["points"] + point)
        )
        message = await ctx.send(content="다음과 같이 포인트를 지급합니다.", embed=embed)

        if not await interface.is_confirmed(ctx, message):
            return await ctx.send(f"{ctx.author.mention} 취소되었습니다.")

        result, resp = await request(
            "post", f"/users/{user['id']}/points", json={"points": point}
        )
        if resp.status // 100 == 4:
            message = result.get("message", "Unknown Error")
            return await ctx.send(f"포인트 지급에 실패했습니다: {message}")

        receipt_id = result.get("receipt_id", -1)
        self.logger.info(
            f"deposit {point} points to User ID {user['id']} by {ctx.author.id} - Receipt {receipt_id}"
        )
        await ctx.send(f"포인트 지급에 성공했습니다! (영수증 ID: {receipt_id})")


def setup(bot):
    bot.add_cog(Forte(bot))
