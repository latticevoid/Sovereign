"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.5.0
"""

import platform
import random

import aiohttp
import discord
from utils.colors import DEFAULT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, SPECIAL_COLOR
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context



class General(commands.Cog, name="general"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.context_menu_user = app_commands.ContextMenu(
            name="Grab ID", callback=self.grab_id
        )
        self.bot.tree.add_command(self.context_menu_user)
        self.context_menu_message = app_commands.ContextMenu(
            name="Remove spoilers", callback=self.remove_spoilers
        )
        self.bot.tree.add_command(self.context_menu_message)

    @commands.hybrid_group(name="general", description="General utility commands.")
    async def general_group(self, context: Context) -> None:
        """General utility commands."""
        if context.invoked_subcommand is None:
            await context.send("Please specify a valid subcommand.")

    # Message context menu command
    async def remove_spoilers(
        self, interaction: discord.Interaction, message: discord.Message
    ) -> None:
        """
        Removes the spoilers from the message. This command requires the MESSAGE_CONTENT intent to work properly.

        :param interaction: The application command interaction.
        :param message: The message that is being interacted with.
        """
        spoiler_attachment = None
        for attachment in message.attachments:
            if attachment.is_spoiler():
                spoiler_attachment = attachment
                break
        embed = discord.Embed(
            title="Message without spoilers",
            description=message.content.replace("||", ""),
            color=DEFAULT_COLOR,
        )
        if spoiler_attachment is not None:
            embed.set_image(url=attachment.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # User context menu command
    async def grab_id(
        self, interaction: discord.Interaction, user: discord.User
    ) -> None:
        """
        Grabs the ID of the user.

        :param interaction: The application command interaction.
        :param user: The user that is being interacted with.
        """
        embed = discord.Embed(
            description=f"The ID of {user.mention} is `{user.id}`.",
            color=DEFAULT_COLOR,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @general_group.command(
        name="help", description="List all commands the bot has loaded."
    )
    async def help(self, context: Context) -> None:
        embed = discord.Embed(
            title="📖 Sovereign Bot — Command Reference",
            description=f"All available commands, organized by category. Use `{self.bot.bot_prefix}` or `/` to access commands.",
            color=DEFAULT_COLOR,
        )

        # ── General ────────────────────────────────────────────────────────────
        embed.add_field(name="ℹ️ General", inline=False, value=
            "```\n"
            f"{self.bot.bot_prefix}general help         — Show this menu\n"
            f"{self.bot.bot_prefix}general botinfo      — Bot info\n"
            f"{self.bot.bot_prefix}general serverinfo   — Server info\n"
            f"{self.bot.bot_prefix}general ping         — Check bot latency\n"
            f"{self.bot.bot_prefix}general invite       — Get the bot invite link\n"
            "```"
        )

        # ── Fun ────────────────────────────────────────────────────────────────
        embed.add_field(name="🎲 Fun", inline=False, value=
            "```\n"
            f"{self.bot.bot_prefix}fun 8ball <q>      — Ask the 8-ball\n"
            f"{self.bot.bot_prefix}fun coinflip       — Flip a coin with a bet\n"
            f"{self.bot.bot_prefix}fun rps            — Play rock-paper-scissors\n"
            f"{self.bot.bot_prefix}fun randomfact     — Get a random useless fact\n"
            "```"
        )

        # ── AI ─────────────────────────────────────────────────────────────────
        embed.add_field(name="🤖 AI", inline=False, value=
            "```\n"
            f"{self.bot.bot_prefix}ai chat <message>  — Chat with the AI\n"
            "```"
        )

        # ── Moderation ────────────────────────────────────────────────────────
        embed.add_field(name="⚖️ Moderation (Staff Only)", inline=False, value=
            "```\n"
            f"{self.bot.bot_prefix}mod action       — Issue a moderation action (Timeout, Ban, Kick, etc.)\n"
            f"{self.bot.bot_prefix}mod reverse      — Reverse a moderation action\n"
            f"{self.bot.bot_prefix}mod purge        — Bulk delete messages\n"
            f"{self.bot.bot_prefix}mod archive      — Export messages to a file\n"
            f"{self.bot.bot_prefix}mod warning add  — Warn a member\n"
            f"{self.bot.bot_prefix}mod warning rem  — Remove a warning\n"
            f"{self.bot.bot_prefix}mod warning list — View warnings\n"
            f"{self.bot.bot_prefix}mod nick         — Change a user's nickname\n"
            "```"
        )

        # ── Staff & Tickets ───────────────────────────────────────────────────
        embed.add_field(name="🧑‍💼 Staff & Tickets", inline=False, value=
            "```\n"
            f"{self.bot.bot_prefix}staff edit        — Open Interactive Staff Dashboard\n"
            f"{self.bot.bot_prefix}staff add/remove  — Manage staff roster\n"
            f"{self.bot.bot_prefix}staff strike      — Issue staff strikes\n"
            f"{self.bot.bot_prefix}ticket spawn      — Spawn a ticket panel\n"
            f"{self.bot.bot_prefix}ticket edit       — Edit ticket panel\n"
            f"{self.bot.bot_prefix}ticket manage     — Add/remove users from tickets\n"
            f"{self.bot.bot_prefix}modmail setup     — Setup modmail system\n"
            f"{self.bot.bot_prefix}staff say/embed   — Send custom bot messages\n"
            "```"
        )

        # ── Security ───────────────────────────────────────────────────────────
        embed.add_field(name="🛡️ Security (Admin Only)", inline=False, value=
            "```\n"
            f"{self.bot.bot_prefix}security verification     — Set up captcha verification\n"
            f"{self.bot.bot_prefix}security quarantine_setup — Set the quarantine role\n"
            "```"
        )

        # ── Owner ──────────────────────────────────────────────────────────────
        embed.add_field(name="👑 Owner", inline=False, value=
            "```\n"
            f"{self.bot.bot_prefix}owner sync/unsync       — Sync slash commands\n"
            f"{self.bot.bot_prefix}owner load/unload/reload— Manage bot cogs\n"
            f"{self.bot.bot_prefix}owner shutdown          — Shutdown the bot\n"
            "```"
        )

        embed.set_footer(text=f"Tip: You can use slash commands like /mod action instead of {self.bot.bot_prefix}mod action!")
        await context.send(embed=embed)


    @general_group.command(
        name="botinfo",
        description="Get some useful (or not) information about the bot.",
    )
    async def botinfo(self, context: Context) -> None:
        """
        Get some useful (or not) information about the bot.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            title="🤖 Sovereign Bot",
            description="*Voice of Order*\n*Guardian of the Realm*\n*Serving the Sovereign Order*\n\nA simple all-in-one Discord server assistant built to keep your community organized and active.\n\n✨ **Features:**\n• Moderation tools (ban, kick, mute)\n• Utility commands (server info, user info)\n• Basic automation for server management\n\nFast, lightweight, and easy to use.\nMade to keep your server running without chaos taking over.",
            color=DEFAULT_COLOR,
        )
        embed.set_author(name="Bot Information")
        embed.add_field(
            name="Python Version:", value=f"{platform.python_version()}", inline=True
        )
        embed.add_field(
            name="Prefix:",
            value=f"/ (Slash Commands) or {self.bot.bot_prefix} for normal commands",
            inline=False,
        )
        embed.set_footer(text=f"Requested by {context.author}")
        await context.send(embed=embed)

    @general_group.command(
        name="serverinfo",
        description="Get some useful (or not) information about the server.",
    )
    async def serverinfo(self, context: Context) -> None:
        """
        Get some useful (or not) information about the server.

        :param context: The hybrid command context.
        """
        roles = [role.name for role in context.guild.roles]
        num_roles = len(roles)
        if num_roles > 50:
            roles = roles[:50]
            roles.append(f">>>> Displaying [50/{num_roles}] Roles")
        roles = ", ".join(roles)

        embed = discord.Embed(
            title="**Server Name:**", description=f"{context.guild}", color=DEFAULT_COLOR
        )
        if context.guild.icon is not None:
            embed.set_thumbnail(url=context.guild.icon.url)
        embed.add_field(name="Server ID", value=context.guild.id)
        embed.add_field(name="Member Count", value=context.guild.member_count)
        embed.add_field(
            name="Text/Voice Channels", value=f"{len(context.guild.channels)}"
        )
        embed.add_field(name=f"Roles ({len(context.guild.roles)})", value=roles)
        embed.set_footer(text=f"Created at: {context.guild.created_at}")
        await context.send(embed=embed)

    @general_group.command(
        name="ping",
        description="Check if the bot is alive.",
    )
    async def ping(self, context: Context) -> None:
        """
        Check if the bot is alive.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"The bot latency is {round(self.bot.latency * 1000)}ms.",
            color=DEFAULT_COLOR,
        )
        await context.send(embed=embed)

    @general_group.command(
        name="invite",
        description="Get the invite link of the bot to be able to invite it.",
    )
    async def invite(self, context: Context) -> None:
        """
        Get the invite link of the bot to be able to invite it.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            description=f"Invite me by clicking [here]({self.bot.invite_link}).",
            color=SPECIAL_COLOR,
        )
        try:
            await context.author.send(embed=embed)
            await context.send("I sent you a private message!")
        except discord.Forbidden:
            await context.send(embed=embed)




async def setup(bot) -> None:
    await bot.add_cog(General(bot))
