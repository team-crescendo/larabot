import json
import logging
import os

from discord import Embed
from discord.ext import commands
from dotenv import load_dotenv

import api
import interface
from api import request

load_dotenv(verbose=True, override=True)

with open("src/resources/box.json", encoding="utf-8") as f:
    box_types = json.load(f)


def describe_box(box: dict, is_premium: bool) -> str:
    key = box.get("key_premium", box["key"]) if is_premium else box["key"]
    max_point = max(p["point"] for p in box["probabilities"])
    return "{emoji} **{name}** (열쇠 {key}개 필요, 최대 {max_point}P)".format(
        **dict(box, key=key, max_point=max_point)
    )


def box_open_view(box: dict, is_premium: bool, key_count: int) -> Embed:
    embed = Embed(title=box["name"]).set_thumbnail(url=box["image"])

    # 필요 열쇠량
    description = f"열쇠 {box['key']}개 필요"
    if "key_premium" in box.keys():
        description += f" (프리미엄: {box['key_premium']}개 필요)"

    # 확률 분포
    description += "\n\n이 상자를 열면..\n"
    description += "\n".join(
        [
            f"{100 * prob['prob']:.0f}%의 확률로 {prob['point']}P 획득"
            for prob in box["probabilities"]
        ]
    )

    # 사용자에게 안내
    key = box.get("key_premium", box["key"]) if is_premium else box["key"]
    description += f"\n\n열쇠 {key}개를 사용해서 **{box['name']}**를 열어볼까요?\n"
    description += f"(현재 열쇠 **{key_count}개**를 가지고 있어요!)"

    embed.description = description
    return embed


class User(commands.Cog):
    guild_whitelist = [
        int(guild_id.strip()) for guild_id in os.getenv("GUILD_WHITELIST").split(",")
    ]
    logger = logging.getLogger("lara.user")

    def __init__(self, bot):
        self.bot = bot

        premium_role_env = os.getenv("PREMIUM_ROLE")
        if premium_role_env is None:
            raise ValueError("Environment variable PREMIUM_ROLE is not defined")
        self.premium_role = int(premium_role_env)

        subscriber_role_env = os.getenv("SUBSCRIBER_ROLE")
        if subscriber_role_env is None:
            raise ValueError("Environmant variable SUBSCRIBER_ROLE is not defined")
        self.subscriber_role = int(subscriber_role_env)

    async def cog_check(self, ctx):
        return ctx.guild is not None and ctx.guild.id in self.guild_whitelist

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("⚠️ **팀 크레센도 디스코드**에서만 사용 가능한 명령어입니다.")
            return

        self.logger.error(str(error))

    def is_premium(self, ctx: commands.Context) -> bool:
        return ctx.guild.get_role(self.premium_role) in ctx.author.roles

    @commands.command(
        "출석", aliases=["출석체크", "출첵", "ㅊ"], brief="팀 크레센도 디스코드 서버에 출석하고 열쇠를 얻습니다.",
    )
    async def attend(self, ctx):
        user, _ = await request("get", f"/discords/{ctx.author.id}")
        if len(user) == 0:
            return await ctx.send(
                f"""{ctx.author.mention}, ⚠️ 팀 크레센도 FORTE에 가입하지 않은 계정입니다.
출석체크 보상으로 POINT를 지급받기 위해선 FORTE 가입이 필요합니다.
하단의 링크에서 Discord 계정 연동을 통해 가입해주세요.
> https://forte.team-crescendo.me/login/discord"""
            )

        try:
            key_count = await api.post_attendace(ctx.author.id)
        except api.AttendanceError as e:
            self.logger.log(e.level, f"{ctx.author.id} attend failure, {e.status}")
            return await ctx.send(f"{ctx.author.mention}, {e}")

        self.logger.info(f"{ctx.author.id} attend success, key_count = {key_count}")
        progress = key_count * "🔑" + (10 - key_count) * "❔"
        return await ctx.send(
            f"""{ctx.author.mention}, ⚡ **출석 체크 완료!**

{progress}

모은 열쇠로 상자를 열면 POINT를 받을 수 있습니다. (`라라야 상자` 입력)

※ `💎Premium` 역할을 갖고 있으면 상자를 열 때 필요한 열쇠가 줄어듭니다. (<#585653003122507796> 확인)"""
        )

    async def select_box(self, ctx: commands.Context) -> str:
        """
        사용자의 입력에 따라 TimeoutError 또는 KeyError가 발생할 수 있습니다.
        """
        is_premium = self.is_premium(ctx)
        description = "\n".join(
            describe_box(box, is_premium) for box in box_types.values()
        )
        embed = Embed(title="어떤 상자를 열어볼까요?", description=description)

        prompt = await ctx.send(ctx.author.mention, embed=embed)
        emoji_map = {box["emoji"]: key for key, box in box_types.items()}
        user_input = await interface.input_emojis(ctx, prompt, [*emoji_map.keys(), "❌"])
        return emoji_map[user_input]

    @commands.command("상자", brief="열쇠를 사용하여 상자를 열고 확률적으로 포인트를 받습니다.")
    async def unpack_box(self, ctx):
        key_count = await api.get_key_count(ctx.author.id)
        if key_count == 0:
            await ctx.send(
                f"{ctx.author.mention}, 상자를 열 수 있는 열쇠가 없습니다.\n"
                + "`라라야 출석` 명령어로 매일 열쇠를 하나씩 얻을 수 있습니다."
            )
            return

        box_type = await self.select_box(ctx)

        prompt = await ctx.send(
            ctx.author.mention,
            embed=box_open_view(box_types[box_type], self.is_premium(ctx), key_count),
        )
        if await interface.is_confirmed(ctx, prompt):
            await prompt.edit(
                content=f"{ctx.author.mention}, **{box_types[box_type]['name']}**를 여는 중...",
                embed=None,
            )
            try:
                point, remaining_keys = await api.unpack_box(
                    ctx.author.id, box_type, self.is_premium(ctx)
                )
                self.logger.info(
                    f"{ctx.author.id} unpack success, {box_type}, point = {point}, key_count = {remaining_keys}"
                )
                await ctx.send(
                    f"{ctx.author.mention}, 상자를 열어 **{point}P**를 얻었습니다! (남은 열쇠: **{remaining_keys}개**)"
                )
            except api.AttendanceError as e:
                self.logger.log(e.level, f"{ctx.author.id} unpack failure, {e.status}")
                return await ctx.send(f"{ctx.author.mention}, {e}")

    @commands.command("구독", brief="전용 구독자 역할을 지급받거나 반환합니다.")
    async def subscribe(self, ctx):
        role = ctx.guild.get_role(self.subscriber_role)
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
