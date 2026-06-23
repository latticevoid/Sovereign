import re
import time
import emoji
from datetime import timedelta
from collections import defaultdict

import discord
from utils.colors import DEFAULT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, SPECIAL_COLOR
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from checks import is_staff

PROFANITY_LIST = [
    "fuck", "shit", "bitch", "cunt", "nigger", "nigga", "faggot", "retard", "whore", "slut"
]

INVITE_REGEX = re.compile(r"(?:discord\.gg/|discord\.com/invite/)[a-zA-Z0-9]+")
LINK_REGEX = re.compile(r"https?://[^\s]+")

class Automod(commands.Cog, name="automod"):
    def __init__(self, bot) -> None:
        self.bot = bot
        # Guild settings (in-memory for now)
        self.settings = defaultdict(lambda: {
            'profanity': True, 
            'invites': True, 
            'links': False, 
            'spam': True, 
            'mentions': True,
            'attachments': False,
            'emojis': True,
            'keywords': True
        })
        
        # User message history for duplicate detection: user_id -> [(content, timestamp), ...]
        self.message_history = defaultdict(list)
        
        # Exemption lists: guild_id -> set of IDs
        self.exempt_roles = defaultdict(set)
        self.exempt_channels = defaultdict(set)
        
        # Custom keywords: guild_id -> list of words
        self.custom_keywords = defaultdict(list)

    @commands.hybrid_group(name="automod", description="Configure automoderation settings.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    async def automod(self, context: Context) -> None:
        if context.invoked_subcommand is None:
            embed = discord.Embed(
                title="Automod Settings",
                description="Use subcommands to toggle filters: `profanity`, `invites`, `links`, `spam`, `mentions`, `attachments`, `emojis`, `keywords`.",
                color=DEFAULT_COLOR
            )
            guild_settings = self.settings[context.guild.id]
            status = "\n".join([f"**{k.capitalize()}**: {'✅ ON' if v else '❌ OFF'}" for k, v in guild_settings.items()])
            embed.add_field(name="Current Status", value=status)
            await context.send(embed=embed)

    async def toggle_setting(self, context: Context, setting: str):
        guild_id = context.guild.id
        self.settings[guild_id][setting] = not self.settings[guild_id][setting]
        status = "enabled" if self.settings[guild_id][setting] else "disabled"
        await context.send(embed=discord.Embed(
            description=f"Automod **{setting}** filter has been **{status}**.",
            color=DEFAULT_COLOR if status == "enabled" else ERROR_COLOR
        ))

    @automod.command(name="profanity", description="Toggle profanity filter.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    async def automod_profanity(self, context: Context):
        await self.toggle_setting(context, "profanity")

    @automod.command(name="invites", description="Toggle Discord invite filter.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    async def automod_invites(self, context: Context):
        await self.toggle_setting(context, "invites")

    @automod.command(name="links", description="Toggle external link filter.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    async def automod_links(self, context: Context):
        await self.toggle_setting(context, "links")

    @automod.command(name="spam", description="Toggle duplicate message & flood filter.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    async def automod_spam(self, context: Context):
        await self.toggle_setting(context, "spam")

    @automod.command(name="mentions", description="Toggle mass mention filter.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    async def automod_mentions(self, context: Context):
        await self.toggle_setting(context, "mentions")

    @automod.command(name="attachments", description="Toggle attachment/image filter.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    async def automod_attachments(self, context: Context):
        await self.toggle_setting(context, "attachments")

    @automod.command(name="emojis", description="Toggle emoji spam filter.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    async def automod_emojis(self, context: Context):
        await self.toggle_setting(context, "emojis")

    @automod.command(name="keywords", description="Toggle custom keyword filter.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    async def automod_keywords(self, context: Context):
        await self.toggle_setting(context, "keywords")

    @automod.command(name="addword", description="Add a custom keyword to filter.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    @app_commands.describe(word="The keyword to filter.")
    async def automod_addword(self, context: Context, word: str):
        word = word.lower()
        if word not in self.custom_keywords[context.guild.id]:
            self.custom_keywords[context.guild.id].append(word)
            await context.send(f"Added `{word}` to custom keyword filter.", ephemeral=True)
        else:
            await context.send(f"`{word}` is already filtered.", ephemeral=True)

    @automod.command(name="exempt_role", description="Toggle Automod exemption for a role.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    @app_commands.describe(role="The role to toggle.")
    async def automod_exempt_role(self, context: Context, role: discord.Role):
        if role.id in self.exempt_roles[context.guild.id]:
            self.exempt_roles[context.guild.id].remove(role.id)
            await context.send(f"Role {role.mention} is no longer exempt from Automod.", ephemeral=True)
        else:
            self.exempt_roles[context.guild.id].add(role.id)
            await context.send(f"Role {role.mention} is now exempt from Automod.", ephemeral=True)

    @automod.command(name="exempt_channel", description="Toggle Automod exemption for a channel.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    @app_commands.describe(channel="The channel to toggle.")
    async def automod_exempt_channel(self, context: Context, channel: discord.TextChannel):
        if channel.id in self.exempt_channels[context.guild.id]:
            self.exempt_channels[context.guild.id].remove(channel.id)
            await context.send(f"Channel {channel.mention} is no longer exempt from Automod.", ephemeral=True)
        else:
            self.exempt_channels[context.guild.id].add(channel.id)
            await context.send(f"Channel {channel.mention} is now exempt from Automod.", ephemeral=True)

    @automod.command(name="test", description="Simulate an Automod test on a specific message string.")
    @commands.has_permissions(administrator=True)
    @is_staff()
    @app_commands.describe(message="The message string to test.")
    async def automod_test(self, context: Context, message: str):
        settings = self.settings[context.guild.id]
        content = message.lower()
        triggers = []

        if settings['invites'] and INVITE_REGEX.search(content):
            triggers.append("Discord Invites")
        if settings['links'] and LINK_REGEX.search(content):
            triggers.append("External Links")
        if settings['profanity'] and any(word in content for word in PROFANITY_LIST):
            triggers.append("Profanity")
        if settings['emojis']:
            emoji_count = emoji.emoji_count(message)
            custom_emoji_count = len(re.findall(r'<a?:\w+:\d+>', message))
            if emoji_count + custom_emoji_count > 10:
                triggers.append("Emoji Spam")
        if settings['keywords'] and any(word in content for word in self.custom_keywords[context.guild.id]):
            triggers.append("Custom Keywords")
        if settings['spam'] and re.search(r'(.)\1{10,}', content):
            triggers.append("Character Flooding")

        if triggers:
            await context.send(embed=discord.Embed(description=f"❌ **Message blocked!**\nTriggers: {', '.join(triggers)}", color=ERROR_COLOR), ephemeral=True)
        else:
            await context.send(embed=discord.Embed(description="✅ **Message passed!** Automod found no issues.", color=SUCCESS_COLOR), ephemeral=True)

    async def escalate_punishment(self, message: discord.Message, reason: str):
        """Adds a warn to the DB and punishes based on total warns."""
        member = message.author
        guild = message.guild
        bot_user_id = self.bot.user.id

        await self.bot.database.add_warn(member.id, guild.id, bot_user_id, f"Automod: {reason}")
        warns = await self.bot.database.get_warnings(member.id, guild.id)
        total_warns = len(warns)

        try:
            await member.send(f"⚠️ You were warned in **{guild.name}** for: **{reason}**.\n*You now have {total_warns} warnings.*")
        except Exception:
            pass

        if total_warns >= 7:
            try:
                await member.ban(reason="Automod Escalation: 7+ Warnings")
                await message.channel.send(f"🔨 **{member}** has been permanently banned by Automod (7+ warnings).")
            except Exception:
                pass
        elif total_warns >= 5:
            try:
                expires_at = int(time.time()) + 86400
                await member.ban(reason="Automod Escalation: 5+ Warnings (1 Day Tempban)")
                await self.bot.database.add_tempban(member.id, guild.id, expires_at)
                await message.channel.send(f"🔨 **{member}** has been temporarily banned for 1 day by Automod (5+ warnings).")
            except Exception:
                pass
        elif total_warns >= 3:
            try:
                await member.timeout(timedelta(hours=1), reason="Automod Escalation: 3+ Warnings")
                await message.channel.send(f"⏱️ **{member}** has been timed out for 1 hour by Automod (3+ warnings).")
            except Exception:
                pass

    async def check_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
            
        # 0. Shadowmute Check
        moderation_cog = self.bot.get_cog("moderation")
        if moderation_cog and message.author.id in moderation_cog.shadow_mutes[message.guild.id]:
            try:
                await message.delete()
            except discord.NotFound:
                pass
            return
        
        # Check Exemptions
        if message.author.guild_permissions.administrator:
            return
        if message.channel.id in self.exempt_channels[message.guild.id]:
            return
        if any(r.id in self.exempt_roles[message.guild.id] for r in message.author.roles):
            return
            
        settings = self.settings[message.guild.id]
        content = message.content.lower()

        # 1. Mass Mention
        if settings['mentions']:
            mentions_count = len(message.mentions) + len(message.role_mentions)
            if mentions_count > 5:
                await message.delete()
                await self.escalate_punishment(message, "Mass Ping/Mention Spam")
                return

        # 2. Discord Invites
        if settings['invites']:
            if INVITE_REGEX.search(content):
                await message.delete()
                await self.escalate_punishment(message, "Posting Discord Invites")
                return

        # 3. Links
        if settings['links']:
            if LINK_REGEX.search(content):
                await message.delete()
                await self.escalate_punishment(message, "Posting External Links")
                return

        # 4. Profanity
        if settings['profanity']:
            if any(word in content for word in PROFANITY_LIST):
                await message.delete()
                await self.escalate_punishment(message, "Profanity/Slur Usage")
                return

        # 5. Emoji Spam
        if settings['emojis']:
            emoji_count = emoji.emoji_count(message.content)
            custom_emoji_count = len(re.findall(r'<a?:\w+:\d+>', message.content))
            if emoji_count + custom_emoji_count > 10:
                await message.delete()
                await self.escalate_punishment(message, "Emoji Spam (>10 Emojis)")
                return

        # 6. Custom Keywords
        if settings['keywords']:
            if any(word in content for word in self.custom_keywords[message.guild.id]):
                await message.delete()
                await self.escalate_punishment(message, "Used a Blacklisted Keyword")
                return
                
        # 7. Attachments
        if settings['attachments']:
            if message.attachments:
                await message.delete()
                await self.escalate_punishment(message, "Posting Attachments (Disabled)")
                return

        # 8. Spam (Flooding & Duplicates)
        if settings['spam']:
            if re.search(r'(.)\1{10,}', content):
                await message.delete()
                await self.escalate_punishment(message, "Character Flooding Spam")
                return
            
            now = time.time()
            history = self.message_history[message.author.id]
            history = [msg for msg in history if now - msg[1] < 60]
            
            duplicate_count = sum(1 for msg in history if msg[0] == content)
            if duplicate_count >= 2:
                await message.delete()
                history.clear()
                self.message_history[message.author.id] = history
                await self.escalate_punishment(message, "Duplicate Message Spam")
                return
                
            history.append((content, now))
            self.message_history[message.author.id] = history

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.check_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content:
            await self.check_message(after)

async def setup(bot) -> None:
    await bot.add_cog(Automod(bot))
