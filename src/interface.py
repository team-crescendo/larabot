import asyncio
from typing import List

import discord
from discord.ext import commands


async def input_emojis(
    ctx: commands.Context, message: discord.Message, emojis: List[str]
) -> str:
    for emoji in emojis:
        await message.add_reaction(emoji)

    def _check(reaction, user):
        return reaction.message.id == message.id and user == ctx.author

    reaction, _ = await ctx.bot.wait_for("reaction_add", check=_check, timeout=60.0)
    return reaction.emoji


async def is_confirmed(ctx: commands.Context, message: discord.Message) -> bool:
    try:
        return await input_emojis(ctx, message, ["⭕", "❌"]) == "⭕"
    except asyncio.TimeoutError:
        return False
