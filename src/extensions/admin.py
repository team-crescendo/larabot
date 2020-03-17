from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command()
    async def reload(self, ctx, path):
        self.bot.reload_extension(f"extensions.{path}")
        await ctx.send(f"Successfully reloaded `{path}`!")

    @commands.command()
    async def uptime(self, ctx):
        pass


def setup(bot):
    bot.add_cog(Admin(bot))
