import discord
from utils.colors import DEFAULT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, SPECIAL_COLOR
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from checks import is_staff
import time

class Dashboard(commands.Cog, name="dashboard"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="mod_dashboard",
        description="View a live overview of server health and moderation statistics.",
    )
    @commands.has_permissions(administrator=True)
    @is_staff()
    async def mod_dashboard(self, context: Context) -> None:
        """Displays a moderation dashboard."""
        guild = context.guild
        embed = discord.Embed(title=f"🛡️ Security Dashboard: {guild.name}", color=DEFAULT_COLOR)
        
        # Calculate stats
        total_members = guild.member_count
        
        # Tempbans
        tempbans = 0
        if hasattr(self.bot, 'database'):
            now = int(time.time())
            rows = await self.bot.database.connection.execute("SELECT COUNT(*) FROM tempbans WHERE server_id=?", (guild.id,))
            async with rows as cursor:
                result = await cursor.fetchone()
                tempbans = result[0] if result else 0
                
            # Warns
            rows = await self.bot.database.connection.execute("SELECT COUNT(*) FROM warns WHERE server_id=?", (guild.id,))
            async with rows as cursor:
                result = await cursor.fetchone()
                warns = result[0] if result else 0
        else:
            tempbans = "Unknown"
            warns = "Unknown"

        # Security Status
        security_cog = self.bot.get_cog("security")
        automod_cog = self.bot.get_cog("automod")
        
        lockdown_status = "✅ Secure"
        if security_cog and len(security_cog.recent_joins[guild.id]) >= 3:
            lockdown_status = "⚠️ Elevated Join Rate"
            
        automod_status = "❌ Disabled"
        if automod_cog:
            settings = automod_cog.settings[guild.id]
            active_filters = sum(1 for v in settings.values() if v)
            automod_status = f"✅ Active ({active_filters}/5 Filters)"

        embed.add_field(name="👥 Total Members", value=str(total_members), inline=True)
        embed.add_field(name="⚠️ Total Warnings", value=str(warns), inline=True)
        embed.add_field(name="🔨 Active Tempbans", value=str(tempbans), inline=True)
        
        embed.add_field(name="🤖 Automoderator", value=automod_status, inline=True)
        embed.add_field(name="🚨 Anti-Raid Status", value=lockdown_status, inline=True)
        
        embed.set_footer(text="Sovereign Moderation Suite • Live Stats")
        await context.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(Dashboard(bot))
