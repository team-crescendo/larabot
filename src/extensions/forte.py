import logging
import os
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
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
            .add_field(name="보유 포인트", value=f"{user['points']}<:fortepoint:788766295406542868>")
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

    @forte.command(aliases=['청약철회'],brief="포르테 아이템 구매를 청약철회 합니다.")
    async def refund(self, ctx, user: ForteUser):
        embed=ForteUser.to_embed(user)
        refund_disabled_env = os.getenv("DISABLE_WITHDRAW_ITEMS").split(",")

        result, resp = await request(
            "get", f"/users/{user['id']}/items"
        )

        if resp.status // 100 == 4:
            message = result.get("message", "Unknown Error")
            return await ctx.send(f"사용자 아이템 리스트 조회 실패: {message}")

        refundable_items=[]
        refundable_item_ids=[]
        for item in result:
            if str(item['item_id']) not in refund_disabled_env and item['expired'] == 0 and item['consumed'] == 0 and item['sync'] == 0 and item['item']['price'] != 0:
                refundable_items.append(item)
                refundable_item_ids.append(str(item['id']))
        embed.add_field(name="청약철회 가능 아이템", value="-------------------------", inline=False)
        for item in refundable_items:
            embed.add_field(name=f"ID: {item['id']}",value=f"{item['item']['name']}\n{item['item']['price']}<:fortepoint:788766295406542868>\n{item['created_at']}")

        if len(refundable_items) == 0:
            return await ctx.send("청약철회 가능한 아이템이 없습니다.")
        await ctx.send("청약철회할 아이템 아이디를 입력해주세요.",embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content in refundable_item_ids
        try:
            msg = await self.bot.wait_for('message',timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("시간초과로 청약철회를 취소합니다.")
        message = await ctx.send("처리중... 잠시만 기다려 주세요.")
        await request(
            "delete", f"/users/{user['id']}/items/{msg.content}"
        )
        result, resp = await request(
            "get", f"/users/{user['id']}/items/{msg.content}"
        )

        if result['expired'] == 1:
            pointresult, resp = await request(
                "post", f"/users/{user['id']}/points",json={"points": result['price']}
            )
            if resp.status // 100 == 4:
                message = result.get("message", "Unknown Error")
                return await message.edit(content=f"아이템 삭제는 완료되었으나, 포인트 지급에 실패했습니다: {message}\n")

            receipt_id = pointresult.get("receipt_id", -1)
            embed = ForteUser.to_embed(user)
            pointresult, resp = await request("get", f"/users/{user['id']}")
            embed.add_field(name="청약철회 이후 포인트",value=f"{int(pointresult['points'])+int(result['price'])}<:fortepoint:788766295406542868>")
            embed.add_field(name="청약철회 정보",value=f"ID: `{msg.content}`\n아이템명: `{result['name']}`\n환불금액: `{result['price']}`<:fortepoint:788766295406542868>\n영수증 ID: `{receipt_id}`",inline=False)

            await message.edit(content=f"청약철회 완료!",embed=embed)
        if result['expried'] == 0:
            return await message.edit(content="아이템 삭제처리가 완료되지 않았습니다. 청약철회 처리를 취소합니다.")



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

    @forte.command(aliases=["토큰"], brief="토큰 리프레시")
    async def refresh(self, ctx, clientId: str):
        message = await ctx.send(content=f"{clientId}의 토큰을 리프레시 합니다.")

        if not await interface.is_confirmed(ctx, message):
            return await ctx.send(f"{ctx.author.mention} 취소되었습니다.")

        result, resp = await request(
            "post", f"/clients/{clientId}/refresh"
        )

        if resp.status // 100 == 4:
            message = result.get("message", "Unknown Error")
            return await ctx.send(f"토큰 리프레시에 실패했습니다: {message}")

        token = result.get('token')

        self.logger.info(
            f"refresh token of {clientId} to {token} by {ctx.author.id}"
        )
        await ctx.send(f"토큰 리프레시에 성공했습니다!\n`{result.get('token')}`")
def setup(bot):
    bot.add_cog(Forte(bot))
