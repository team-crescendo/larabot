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
        "출석", aliases=["출석체크", "출첵", "ㅊ"], brief="팀 크레센도 디스코드 서버에 출석하고 포인트 보상을 받습니다.",
    )
    async def attend(self, ctx):
        user, _ = await request("get", f"/discords/{ctx.author.id}")
        if len(user) == 0:
            return await ctx.send(
                """⚠️ 팀 크레센도 FOTRE에 가입하지 않은 계정입니다.
출석체크 및 개근 보상으로 POINT를 지급받기 위해선 FORTE 가입이 필요합니다.
하단의 링크에서 Discord 계정 연동을 통해 가입해주세요.
> https://forte.team-crescendo.me/login/discord"""
            )

        role = ctx.guild.get_role(int(os.getenv("PREMIUM_ROLE")))
        is_premium = int(role in ctx.author.roles)

        attendance, _ = await request(
            "post", f"/discords/{ctx.author.id}/attendances?isPremium={is_premium}"
        )

        if attendance.get("error"):
            self.logger.warning(f"failed to check attendance of {ctx.author.id}")
            return await ctx.send("🔥 에러가 발생했습니다. 잠시 후 다시 시도해주세요.")

        status = attendance.get("status")
        self.logger.info(
            f"attendance check of {ctx.author.id}"
            + (", premium user" if is_premium else "")
            + f": {status}"
        )
        if status == "exist_attendance":
            return await ctx.send(
                f"최근에 이미 출석체크 하셨습니다.\n`{attendance.get('diff')}` 후 다시 시도해주세요."
            )

        FULL = 7
        if status == "success":
            progress = ("❤️" * attendance["stack"]).ljust(FULL, "🖤")
            return await ctx.send(
                f"""⚡ **출석 체크 완료!**

개근까지 앞으로 {FULL - attendance['stack']}일 남았습니다. 내일 또 만나요!

{progress}

__7일 누적으로__ 출석하면 출석 보상으로 FORTE STORE(포르테 스토어)에서 사용할 수 있는 POINT를 지급해 드립니다.

※ 개근 보상을 받을 때 `💎Premium` 역할을 보유하고 있다면 POINT가 추가로 지급됩니다! (자세한 사항은 <#585653003122507796> 를 확인해주세요.)"""
            )
        elif status == "regular":
            bonus_description = "(`💎Premium` 보유 보너스 포함)" if is_premium else ""
            return await ctx.send(
                f"""💝 **출석 성공!**

축하드립니다! {FULL}일 누적으로 출석체크에 성공하여 개근 보상을 획득했습니다.

> `{attendance['point']}` POINT {bonus_description}
"""
            )

    @commands.command("구독", brief="전용 구독자 역할을 지급받거나 반환합니다.")
    async def subscribe(self, ctx):
        role = ctx.guild.get_role(int(os.getenv("SUBSCRIBER_ROLE")))
        if role is None:
            return await ctx.send("⚠️ 구독자 역할을 찾을 수 없습니다.")

        if role not in ctx.author.roles:
            await ctx.author.add_roles(role)
            await ctx.send(f"{ctx.author.mention} 구독자 역할을 지급했습니다.")
        else:
            await ctx.author.remove_roles(role)
            await ctx.send(f"{ctx.author.mention} 구독자 역할을 회수했습니다.")


def setup(bot):
    bot.add_cog(User(bot))
