import discord
from utils.colors import DEFAULT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, SPECIAL_COLOR
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from checks import is_staff
from datetime import datetime

class Logging(commands.Cog, name="logging"):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def get_log_channel(self, guild: discord.Guild):
        channel_id = await self.bot.database.get_log_channel(guild.id)
        if channel_id:
            return guild.get_channel(channel_id)
        return None

    @commands.hybrid_command(
        name="setup_logging",
        description="Set the channel where server logs should be sent.",
    )
    @commands.has_permissions(administrator=True)
    @is_staff()
    @app_commands.describe(channel="The channel for server logs.")
    async def setup_logging(self, context: Context, channel: discord.TextChannel) -> None:
        """Sets up the server logging channel."""
        await self.bot.database.set_log_channel(context.guild.id, channel.id)
        await context.send(f"Server logs will now be sent to {channel.mention}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
            
        log_channel = await self.get_log_channel(message.guild)
        if not log_channel: return

        embed = discord.Embed(
            description=f"🗑️ **Message sent by {message.author.mention} deleted in {message.channel.mention}**\n\n{message.content}",
            color=ERROR_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"{message.author}", icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"Author: {message.author.id} | Message ID: {message.id}")
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
            
        log_channel = await self.get_log_channel(before.guild)
        if not log_channel: return

        embed = discord.Embed(
            description=f"✏️ **Message edited in {before.channel.mention}** [Jump to Message]({after.jump_url})",
            color=DEFAULT_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Before", value=before.content or "None", inline=False)
        embed.add_field(name="After", value=after.content or "None", inline=False)
        embed.set_author(name=f"{before.author}", icon_url=before.author.display_avatar.url)
        embed.set_footer(text=f"User ID: {before.author.id}")
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot: return
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel: return

        embed = discord.Embed(timestamp=discord.utils.utcnow())
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.url)
        
        if before.channel is None and after.channel is not None:
            embed.description = f"🎤 **{member.mention} joined voice channel `{after.channel.name}`**"
            embed.color = SUCCESS_COLOR
        elif before.channel is not None and after.channel is None:
            embed.description = f"🚪 **{member.mention} left voice channel `{before.channel.name}`**"
            embed.color = ERROR_COLOR
        elif before.channel != after.channel:
            embed.description = f"🔀 **{member.mention} moved from `{before.channel.name}` to `{after.channel.name}`**"
            embed.color = WARNING_COLOR
        else:
            return # E.g. mute/deafen changes

        embed.set_footer(text=f"User ID: {member.id}")
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel: return

        age = discord.utils.utcnow() - member.created_at
        embed = discord.Embed(
            description=f"📥 **{member.mention} joined the server.**\nAccount created: <t:{int(member.created_at.timestamp())}:R> ({age.days} days ago)",
            color=SUCCESS_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel: return

        embed = discord.Embed(
            description=f"📤 **{member.mention} left the server.**",
            color=ERROR_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        log_channel = await self.get_log_channel(before.guild)
        if not log_channel: return

        if before.nick != after.nick:
            embed = discord.Embed(
                description=f"🏷️ **{before.mention} changed their nickname.**",
                color=DEFAULT_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Before", value=before.nick or before.name, inline=True)
            embed.add_field(name="After", value=after.nick or after.name, inline=True)
            embed.set_author(name=f"{before}", icon_url=before.display_avatar.url)
            await log_channel.send(embed=embed)

        if before.roles != after.roles:
            added = [r.mention for r in after.roles if r not in before.roles]
            removed = [r.mention for r in before.roles if r not in after.roles]
            if added or removed:
                embed = discord.Embed(
                    description=f"🛡️ **{before.mention} had their roles updated.**",
                    color=DEFAULT_COLOR,
                    timestamp=discord.utils.utcnow()
                )
                if added: embed.add_field(name="Added", value=", ".join(added), inline=False)
                if removed: embed.add_field(name="Removed", value=", ".join(removed), inline=False)
                embed.set_author(name=f"{before}", icon_url=before.display_avatar.url)
                await log_channel.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(Logging(bot))
