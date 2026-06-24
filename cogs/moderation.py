"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.5.0
"""

import os
from datetime import datetime

import discord
from utils.colors import DEFAULT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, SPECIAL_COLOR
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from collections import defaultdict
import re
from datetime import timedelta

def parse_duration(duration_str: str):
    matches = re.match(r"(\d+)([smhd])", duration_str.lower())
    if not matches: return None
    val, unit = int(matches.group(1)), matches.group(2)
    if unit == 's': return timedelta(seconds=val)
    if unit == 'm': return timedelta(minutes=val)
    if unit == 'h': return timedelta(hours=val)
    if unit == 'd': return timedelta(days=val)
    return None

MOD_ACTIONS = [
    app_commands.Choice(name="Timeout", value="timeout"),
    app_commands.Choice(name="Mute", value="mute"),
    app_commands.Choice(name="Tempmute", value="tempmute"),
    app_commands.Choice(name="Voice Mute", value="voicemute"),
    app_commands.Choice(name="Media Ban", value="mediaban"),
    app_commands.Choice(name="Link Ban", value="linkban"),
    app_commands.Choice(name="Reaction Ban", value="reactionban"),
    app_commands.Choice(name="Command Ban", value="commandban"),
    app_commands.Choice(name="Ticket Ban", value="ticketban"),
    app_commands.Choice(name="Jail", value="jail"),
    app_commands.Choice(name="Quarantine", value="quarantine"),
    app_commands.Choice(name="Kick", value="kick"),
    app_commands.Choice(name="Softban", value="softban"),
    app_commands.Choice(name="Tempban", value="tempban"),
    app_commands.Choice(name="Ban", value="ban"),
    app_commands.Choice(name="Hackban", value="hackban"),
    app_commands.Choice(name="Massban", value="massban"),
    app_commands.Choice(name="Blacklist", value="blacklist"),
    app_commands.Choice(name="Raid Ban", value="raidban"),
    app_commands.Choice(name="Evasion Ban", value="evasionban"),
    app_commands.Choice(name="Auto Ban", value="autoban"),
]

UNMOD_ACTIONS = [
    app_commands.Choice(name="Untimeout", value="untimeout"),
    app_commands.Choice(name="Unmute", value="unmute"),
    app_commands.Choice(name="Un-Voice Mute", value="unvoicemute"),
    app_commands.Choice(name="Un-Media Ban", value="unmediaban"),
    app_commands.Choice(name="Un-Link Ban", value="unlinkban"),
    app_commands.Choice(name="Un-Reaction Ban", value="unreactionban"),
    app_commands.Choice(name="Un-Command Ban", value="uncommandban"),
    app_commands.Choice(name="Un-Ticket Ban", value="unticketban"),
    app_commands.Choice(name="Unjail", value="unjail"),
    app_commands.Choice(name="Unquarantine", value="unquarantine"),
    app_commands.Choice(name="Unban", value="unban"),
    app_commands.Choice(name="Un-Blacklist", value="unblacklist"),
]

class Moderation(commands.Cog, name="moderation"):
    def __init__(self, bot) -> None:
        self.bot = bot
        # guild_id -> set of user_ids
        self.shadow_mutes = defaultdict(set)



    @commands.hybrid_group(name="mod", description="Moderation commands.")
    @app_commands.default_permissions(manage_messages=True)
    async def mod_group(self, context: Context) -> None:
        """Moderation commands."""
        if context.invoked_subcommand is None:
            await context.send("Please specify a valid subcommand.")

    @mod_group.command(
        name="nick",
        description="Change the nickname of a user on a server.",
    )
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    @app_commands.describe(
        user="The user that should have a new nickname.",
        nickname="The new nickname that should be set.",
    )
    async def nick(
        self, context: Context, user: discord.User, *, nickname: str = None
    ) -> None:
        """
        Change the nickname of a user on a server.

        :param context: The hybrid command context.
        :param user: The user that should have its nickname changed.
        :param nickname: The new nickname of the user. Default is None, which will reset the nickname.
        """
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(
            user.id
        )
        try:
            await member.edit(nick=nickname)
            embed = discord.Embed(
                description=f"**{member}'s** new nickname is **{nickname}**!",
                color=DEFAULT_COLOR,
            )
            await context.send(embed=embed)
        except:
            embed = discord.Embed(
                description="An error occurred while trying to change the nickname of the user. Make sure my role is above the role of the user you want to change the nickname.",
                color=ERROR_COLOR,
            )
            await context.send(embed=embed)

    @mod_group.command(name="action", description="Issue a moderation action against a user.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(
        user="The primary user to moderate",
        action_type="The type of moderation action",
        reason="Reason for the action",
        duration="Duration (e.g. 1d, 2h) for temporary actions",
        extra_users="Comma-separated IDs for mass actions"
    )
    @app_commands.choices(action_type=MOD_ACTIONS)
    async def mod(self, context: Context, user: discord.User, action_type: str, reason: str = "Not specified", duration: str = None, extra_users: str = None) -> None:
        await context.defer()
        
        if isinstance(action_type, app_commands.Choice):
            val = action_type.value
            action_name = action_type.name
        else:
            val = action_type
            action_name = next((c.name for c in MOD_ACTIONS if c.value == val), val.capitalize())
        
        if val in ["kick"]:
            if not context.author.guild_permissions.kick_members:
                return await context.send("You need Kick Members permission for this action.")
        elif val in ["ban", "softban", "tempban", "hackban", "massban", "blacklist", "raidban", "evasionban", "autoban"]:
            if not context.author.guild_permissions.ban_members:
                return await context.send("You need Ban Members permission for this action.")

        targets = [user]
        if extra_users and val == "massban":
            for uid_str in extra_users.split(","):
                uid_str = uid_str.strip()
                if uid_str.isdigit():
                    try:
                        u = await self.bot.fetch_user(int(uid_str))
                        if u and u not in targets: targets.append(u)
                    except: pass
        
        parsed_duration = None
        if duration:
            parsed_duration = parse_duration(duration)
            if not parsed_duration:
                return await context.send("Invalid duration format. Use e.g. 1d, 2h, 30m.")

        success_count = 0
        for target in targets:
            member = context.guild.get_member(target.id)
            if member and member.top_role >= context.author.top_role and context.author.id != context.guild.owner_id:
                await context.send(f"Cannot moderate {target.mention} because their role is higher or equal to yours.", ephemeral=True)
                continue
                
            try:
                if val in ["timeout", "mute", "tempmute", "voicemute"]:
                    if not member:
                        await context.send(f"{target.mention} is not in the server.")
                        continue
                    timeout_until = discord.utils.utcnow() + (parsed_duration or timedelta(days=28))
                    await member.timeout(timeout_until, reason=reason)
                    success_count += 1
                
                elif val in ["quarantine", "jail", "mediaban", "linkban", "reactionban", "commandban", "ticketban"]:
                    if not member: continue
                    q_role_id = await self.bot.database.get_quarantine_role(context.guild.id)
                    if not q_role_id:
                        await context.send(f"⚠️ No quarantine/restriction role configured! Please run `/quarantine setup` first.", ephemeral=True)
                        return
                    r = context.guild.get_role(q_role_id)
                    if r:
                        await member.add_roles(r, reason=reason)
                        success_count += 1

                elif val == "kick":
                    if not member: continue
                    try: await member.send(f"You were kicked from **{context.guild.name}**!\nReason: {reason}")
                    except: pass
                    await member.kick(reason=reason)
                    success_count += 1
                
                elif val in ["ban", "softban", "tempban", "hackban", "massban", "blacklist", "raidban", "evasionban", "autoban"]:
                    delete_days = 7 if val in ["softban", "raidban", "massban"] else 0
                    try:
                        if member: await member.send(f"You were {val} from **{context.guild.name}**!\nReason: {reason}")
                    except: pass
                    await context.guild.ban(target, reason=f"[{action_name}] {reason}", delete_message_days=delete_days)
                    if val == "softban":
                        await context.guild.unban(target, reason="Softban release")
                    success_count += 1
            except discord.Forbidden:
                await context.send(f"❌ Missing permissions to apply {action_name} to {target.mention}.", ephemeral=True)
            except Exception as e:
                self.bot.logger.error(f"Mod error: {e}")
        
        embed = discord.Embed(
            title=f"🛡️ Action: {action_name}",
            description=f"Successfully applied to {success_count} user(s).",
            color=ERROR_COLOR
        )
        embed.add_field(name="Target(s)", value=", ".join(u.mention for u in targets[:10]) + ("..." if len(targets)>10 else ""))
        embed.add_field(name="Reason", value=reason, inline=False)
        if parsed_duration:
            embed.add_field(name="Duration", value=duration)
        
        await context.send(embed=embed)
        await self.bot.database.log_mod_action(context.guild.id, context.author.id, val)

    @mod_group.command(name="reverse", description="Reverse a moderation action.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(
        user="The user to unmoderate",
        action_type="The type of moderation action to reverse",
        reason="Reason for the action"
    )
    @app_commands.choices(action_type=UNMOD_ACTIONS)
    async def unmod(self, context: Context, user: discord.User, action_type: str, reason: str = "Not specified") -> None:
        await context.defer()
        val = action_type.value if isinstance(action_type, app_commands.Choice) else action_type
        
        if val in ["unban", "unblacklist"]:
            if not context.author.guild_permissions.ban_members:
                return await context.send("You need Ban Members permission.")
            try:
                await context.guild.unban(user, reason=reason)
                return await context.send(f"✅ Unbanned {user.mention}.")
            except:
                return await context.send("Failed to unban or user was not banned.")
                
        member = context.guild.get_member(user.id)
        if not member:
            return await context.send("User is not in the server.")
            
        try:
            if val in ["untimeout", "unmute", "unvoicemute"]:
                await member.timeout(None, reason=reason)
                await context.send(f"✅ Removed timeout/mute for {member.mention}.")
                
            elif val in ["unjail", "unquarantine", "unmediaban", "unlinkban", "unreactionban", "uncommandban", "unticketban"]:
                q_role_id = await self.bot.database.get_quarantine_role(context.guild.id)
                if q_role_id:
                    r = context.guild.get_role(q_role_id)
                    if r and r in member.roles:
                        await member.remove_roles(r, reason=reason)
                        return await context.send(f"✅ Removed restriction role from {member.mention}.")
                await context.send("No restriction role to remove or not configured.")
        except discord.Forbidden:
            await context.send("Missing permissions.")

    @mod_group.group(
        name="warning",
        description="Manage warnings of a user on a server.",
    )
    @commands.has_permissions(manage_messages=True)
    async def warning(self, context: Context) -> None:
        """
        Manage warnings of a user on a server.

        :param context: The hybrid command context.
        """
        if context.invoked_subcommand is None:
            embed = discord.Embed(
                description="Please specify a subcommand.\n\n**Subcommands:**\n`add` - Add a warning to a user.\n`remove` - Remove a warning from a user.\n`list` - List all warnings of a user.",
                color=ERROR_COLOR,
            )
            await context.send(embed=embed)

    @warning.command(
        name="add",
        description="Adds a warning to a user in the server.",
    )
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(
        user="The user that should be warned.",
        reason="The reason why the user should be warned.",
    )
    async def warning_add(
        self, context: Context, user: discord.User, *, reason: str = "Not specified"
    ) -> None:
        """
        Warns a user in his private messages.

        :param context: The hybrid command context.
        :param user: The user that should be warned.
        :param reason: The reason for the warn. Default is "Not specified".
        """
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(
            user.id
        )
        total = await self.bot.database.add_warn(
            user.id, context.guild.id, context.author.id, reason
        )
        await self.bot.database.log_mod_action(context.guild.id, context.author.id, "warn")
        embed = discord.Embed(
            description=f"**{member}** was warned by **{context.author}**!\nTotal warns for this user: {total}",
            color=DEFAULT_COLOR,
        )
        embed.add_field(name="Reason:", value=reason)
        await context.send(embed=embed)
        try:
            await member.send(
                f"You were warned by **{context.author}** in **{context.guild.name}**!\nReason: {reason}"
            )
        except:
            await context.send(
                f"{member.mention}, you were warned by **{context.author}**!\nReason: {reason}"
            )

    @warning.command(
        name="remove",
        description="Removes a warning from a user in the server.",
    )
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(
        user="The user that should get their warning removed.",
        warn_id="The ID of the warning that should be removed.",
    )
    async def warning_remove(
        self, context: Context, user: discord.User, warn_id: int
    ) -> None:
        """
        Warns a user in his private messages.

        :param context: The hybrid command context.
        :param user: The user that should get their warning removed.
        :param warn_id: The ID of the warning that should be removed.
        """
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(
            user.id
        )
        total = await self.bot.database.remove_warn(warn_id, user.id, context.guild.id)
        embed = discord.Embed(
            description=f"I've removed the warning **#{warn_id}** from **{member}**!\nTotal warns for this user: {total}",
            color=DEFAULT_COLOR,
        )
        await context.send(embed=embed)

    @warning.command(
        name="list",
        description="Shows the warnings of a user in the server.",
    )
    @commands.has_guild_permissions(manage_messages=True)
    @app_commands.describe(user="The user you want to get the warnings of.")
    async def warning_list(self, context: Context, user: discord.User) -> None:
        """
        Shows the warnings of a user in the server.

        :param context: The hybrid command context.
        :param user: The user you want to get the warnings of.
        """
        warnings_list = await self.bot.database.get_warnings(user.id, context.guild.id)
        embed = discord.Embed(title=f"Warnings of {user}", color=DEFAULT_COLOR)
        description = ""
        if len(warnings_list) == 0:
            description = "This user has no warnings."
        else:
            for warning in warnings_list:
                description += f"• Warned by <@{warning[2]}>: **{warning[3]}** (<t:{warning[4]}>) - Warn ID #{warning[5]}\n"
        embed.description = description
        await context.send(embed=embed)

    @mod_group.command(
        name="purge",
        description="Delete a number of messages.",
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @app_commands.describe(amount="The amount of messages that should be deleted.")
    async def purge(self, context: Context, amount: int) -> None:
        """
        Delete a number of messages.

        :param context: The hybrid command context.
        :param amount: The number of messages that should be deleted.
        """
        await context.send(
            "Deleting messages..."
        )  # Bit of a hacky way to make sure the bot responds to the interaction and doens't get a "Unknown Interaction" response
        purged_messages = await context.channel.purge(limit=amount + 1)
        embed = discord.Embed(
            description=f"**{context.author}** cleared **{len(purged_messages)-1}** messages!",
            color=DEFAULT_COLOR,
        )
        await context.channel.send(embed=embed)



    @mod_group.command(
        name="archive",
        description="Archives in a text file the last messages with a chosen limit of messages.",
    )
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(
        limit="The limit of messages that should be archived.",
    )
    async def archive(self, context: Context, limit: int = 10) -> None:
        """
        Archives in a text file the last messages with a chosen limit of messages. This command requires the MESSAGE_CONTENT intent to work properly.

        :param limit: The limit of messages that should be archived. Default is 10.
        """
        log_file = f"{context.channel.id}.log"
        with open(log_file, "w", encoding="UTF-8") as f:
            f.write(
                f'Archived messages from: #{context.channel} ({context.channel.id}) in the guild "{context.guild}" ({context.guild.id}) at {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}\n'
            )
            async for message in context.channel.history(
                limit=limit, before=context.message
            ):
                attachments = []
                for attachment in message.attachments:
                    attachments.append(attachment.url)
                attachments_text = (
                    f"[Attached File{'s' if len(attachments) >= 2 else ''}: {', '.join(attachments)}]"
                    if len(attachments) >= 1
                    else ""
                )
                f.write(
                    f"{message.created_at.strftime('%d.%m.%Y %H:%M:%S')} {message.author} {message.id}: {message.clean_content} {attachments_text}\n"
                )
        f = discord.File(log_file)
        await context.send(file=f)
        os.remove(log_file)


async def setup(bot) -> None:
    await bot.add_cog(Moderation(bot))

