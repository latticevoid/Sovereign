import discord
from utils.colors import DEFAULT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, SPECIAL_COLOR
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from checks import is_staff
from datetime import timedelta
import re

class MassMod(commands.Cog, name="massmod"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_group(name="mass", description="Mass moderation commands.")
    async def mass(self, context: Context):
        if context.invoked_subcommand is None:
            await context.send("Invalid mass moderation command.", ephemeral=True)

    def extract_users(self, context: Context, targets: str):
        # Extracts user IDs from mentions or plain IDs
        user_ids = set()
        for match in re.findall(r'<@!?(\d+)>', targets):
            user_ids.add(int(match))
        for token in targets.split():
            if token.isdigit():
                user_ids.add(int(token))
        return list(user_ids)

    @mass.command(name="ban", description="Ban multiple users at once.")
    @commands.has_permissions(ban_members=True)
    @is_staff()
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(targets="Space-separated mentions or user IDs to ban.", reason="Reason for mass ban.")
    async def mass_ban(self, context: Context, targets: str, *, reason: str = "Mass ban") -> None:
        user_ids = self.extract_users(context, targets)
        if not user_ids:
            await context.send("No valid users found.", ephemeral=True)
            return

        banned = 0
        failed = 0
        await context.defer()
        for uid in user_ids:
            try:
                user = self.bot.get_user(uid) or await self.bot.fetch_user(uid)
                await context.guild.ban(user, reason=reason)
                banned += 1
            except Exception:
                failed += 1

        await context.send(embed=discord.Embed(description=f"Mass ban complete.\n✅ Banned: {banned}\n❌ Failed: {failed}", color=SUCCESS_COLOR))

    @mass.command(name="kick", description="Kick multiple users at once.")
    @commands.has_permissions(kick_members=True)
    @is_staff()
    @commands.bot_has_permissions(kick_members=True)
    @app_commands.describe(targets="Space-separated mentions or user IDs to kick.", reason="Reason for mass kick.")
    async def mass_kick(self, context: Context, targets: str, *, reason: str = "Mass kick") -> None:
        user_ids = self.extract_users(context, targets)
        if not user_ids:
            await context.send("No valid users found.", ephemeral=True)
            return

        kicked = 0
        failed = 0
        await context.defer()
        for uid in user_ids:
            member = context.guild.get_member(uid)
            if member:
                try:
                    await member.kick(reason=reason)
                    kicked += 1
                except Exception:
                    failed += 1
            else:
                failed += 1

        await context.send(embed=discord.Embed(description=f"Mass kick complete.\n✅ Kicked: {kicked}\n❌ Failed: {failed}", color=SUCCESS_COLOR))

    @mass.command(name="timeout", description="Timeout multiple users at once.")
    @commands.has_permissions(moderate_members=True)
    @is_staff()
    @commands.bot_has_permissions(moderate_members=True)
    @app_commands.describe(targets="Space-separated mentions or user IDs.", duration_hours="Hours to timeout.", reason="Reason.")
    async def mass_timeout(self, context: Context, targets: str, duration_hours: float, *, reason: str = "Mass timeout") -> None:
        user_ids = self.extract_users(context, targets)
        if not user_ids:
            await context.send("No valid users found.", ephemeral=True)
            return

        timed_out = 0
        failed = 0
        duration = timedelta(hours=duration_hours)
        await context.defer()
        for uid in user_ids:
            member = context.guild.get_member(uid)
            if member:
                try:
                    await member.timeout(duration, reason=reason)
                    timed_out += 1
                except Exception:
                    failed += 1
            else:
                failed += 1

        await context.send(embed=discord.Embed(description=f"Mass timeout complete.\n✅ Timed out: {timed_out}\n❌ Failed: {failed}", color=SUCCESS_COLOR))

async def setup(bot) -> None:
    await bot.add_cog(MassMod(bot))
