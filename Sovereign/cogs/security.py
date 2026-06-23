import time
import datetime
from collections import defaultdict

import discord
from utils.colors import DEFAULT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, SPECIAL_COLOR
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

class VerificationModal(discord.ui.Modal, title="Security Verification"):
    answer = discord.ui.TextInput(
        label="What is 5 + 7?",
        placeholder="Enter your answer here...",
        required=True,
        max_length=2,
    )

    def __init__(self, role_id: int):
        super().__init__()
        self.role_id = role_id

    async def on_submit(self, interaction: discord.Interaction):
        if self.answer.value.strip() == "12":
            role = interaction.guild.get_role(self.role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message("Verification successful! You have been granted access.", ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("I do not have permission to give you the role. Please contact an admin.", ephemeral=True)
            else:
                await interaction.response.send_message("The verification role is improperly configured. Please contact an admin.", ephemeral=True)
        else:
            await interaction.response.send_message("Incorrect answer. Please try again.", ephemeral=True)

class Security(commands.Cog, name="security"):
    def __init__(self, bot) -> None:
        self.bot = bot
        # guild_id -> list of timestamps
        self.recent_joins = defaultdict(list)
        # user_id -> list of timestamps
        self.channel_deletions = defaultdict(list)

    @commands.hybrid_group(name="security", description="Security and verification commands.")
    @app_commands.default_permissions(administrator=True)
    async def security_group(self, context: Context) -> None:
        """Security commands."""
        if context.invoked_subcommand is None:
            await context.send("Please specify a valid subcommand.")

    @security_group.command(
        name="verification",
        description="Set up a captcha verification button in a channel.",
    )
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        channel="The channel to post the verification message in.",
        role="The role to grant upon successful verification."
    )
    async def setup_verification(self, context: Context, channel: discord.TextChannel, role: discord.Role) -> None:
        """Sets up the persistent verification button system."""
        embed = discord.Embed(
            title="Server Verification",
            description="To gain access to the rest of the server, please complete the verification process by clicking the button below.",
            color=DEFAULT_COLOR
        )
        
        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(
            label="Verify", 
            style=discord.ButtonStyle.green, 
            custom_id=f"verify_btn_{role.id}"
        )
        view.add_item(button)

        try:
            await channel.send(embed=embed, view=view)
            await context.send(f"Verification system successfully set up in {channel.mention} assigning the {role.mention} role.", ephemeral=True)
        except discord.Forbidden:
            await context.send("I do not have permission to send messages in that channel.", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Stateless interaction listener for persistent verify buttons."""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("verify_btn_"):
                try:
                    role_id = int(custom_id.split("_")[2])
                    await interaction.response.send_modal(VerificationModal(role_id))
                except Exception as e:
                    self.bot.logger.error(f"Error handling verification interaction: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Anti-Raid and Account Age checks."""
        guild = member.guild
        now = time.time()
        
        # 1. Account Age Check (Kick if under 3 days old)
        age = discord.utils.utcnow() - member.created_at
        if age.days < 3:
            try:
                await member.send(f"You have been kicked from **{guild.name}** because your account is too new. This is an anti-raid measure.")
            except Exception:
                pass
            try:
                await member.kick(reason="Anti-Raid: Account too new (under 3 days old).")
            except Exception:
                pass
            return

        # 2. Raid Velocity Check (5 joins in 10 seconds -> Lockdown)
        history = self.recent_joins[guild.id]
        history = [t for t in history if now - t < 10]
        history.append(now)
        self.recent_joins[guild.id] = history
        
        if len(history) >= 5:
            # Trigger lockdown
            try:
                await guild.default_role.edit(send_messages=False, reason="Anti-Raid Lockdown Triggered")
                if guild.system_channel:
                    await guild.system_channel.send(
                        "🚨 **ANTI-RAID LOCKDOWN INITIATED!** 🚨\n"
                        "More than 5 users joined in 10 seconds. The server has been locked down. "
                        "Administrators must manually re-enable `send_messages` for @everyone."
                    )
                # Clear the list to prevent spamming the lockdown action
                self.recent_joins[guild.id].clear() 
            except Exception as e:
                self.bot.logger.error(f"Failed to lockdown server during raid: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Anti-Nuke protection."""
        guild = channel.guild
        
        # We must wait a brief moment for the audit log to populate
        await discord.utils.sleep_until(discord.utils.utcnow() + datetime.timedelta(seconds=1))

        # Fetch audit logs to find who deleted the channel
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=5):
                if entry.target.id == channel.id:
                    user_id = entry.user.id
                    
                    # Ignore the bot itself
                    if user_id == self.bot.user.id:
                        return
                        
                        try:
                            await guild.ban(entry.user, reason="Anti-Nuke: Deleted too many channels rapidly.")
                            if guild.owner:
                                await guild.owner.send(f"?? **ANTI-NUKE TRIGGERED!**\nUser {entry.user} was banned for deleting 3+ channels in 60 seconds.")
                            self.channel_deletions[user_id].clear()
                        except Exception as e:
                            self.bot.logger.error(f"Failed to ban rogue admin: {e}")
                    break
        except Exception as e:
            self.bot.logger.error(f"Failed to fetch audit logs for anti-nuke: {e}")

    @security_group.command(name="quarantine_setup", description="Set the quarantine role for this server.")
    @app_commands.describe(role="The role to use as the quarantine role")
    async def quarantine_setup(self, interaction: discord.Interaction, role: discord.Role) -> None:
        await self.bot.database.set_quarantine_role(interaction.guild.id, role.id)
        embed = discord.Embed(
            title="🔒 Quarantine Role Set",
            description=f"The quarantine role has been set to {role.mention}.\n\nUse `/quarantine add` to quarantine a member and `/quarantine remove` to lift it.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)



async def setup(bot) -> None:
    await bot.add_cog(Security(bot))

