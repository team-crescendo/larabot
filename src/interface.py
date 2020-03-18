import asyncio

import discord
from discord.ext import commands


async def is_confirmed(ctx: commands.Context, message: discord.Message) -> bool:
    emojis = ["⭕", "❌"]
    for emoji in emojis:
        await message.add_reaction(emoji)

    def _check(reaction, user):
        return reaction.message.id == message.id and user == ctx.author

    try:
        reaction, _ = await ctx.bot.wait_for("reaction_add", check=_check, timeout=60.0)
        return reaction.emoji == "⭕"
    except asyncio.TimeoutError:
        return False
