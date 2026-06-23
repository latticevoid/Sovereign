import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from utils.colors import DEFAULT_COLOR
import datetime
import io

class Modmail(commands.Cog, name="modmail"):
    def __init__(self, bot) -> None:
        self.bot = bot

    modmail = app_commands.Group(name="modmail", description="Modmail management commands", default_permissions=discord.Permissions(administrator=True))

    @modmail.command(name="setup", description="Setup modmail by specifying the category and optional log channel.")
    async def modmail_setup(self, interaction: discord.Interaction, category: discord.CategoryChannel, log_channel: discord.TextChannel = None) -> None:
        await self.bot.database.set_modmail_config(interaction.guild.id, category.id, log_channel.id if log_channel else None)
        embed = discord.Embed(title="📨 Modmail Setup", description=f"Modmail threads will be created in {category.mention}.", color=DEFAULT_COLOR)
        if log_channel:
            embed.add_field(name="Log Channel", value=log_channel.mention)
        await interaction.response.send_message(embed=embed)

    @modmail.command(name="close", description="Close the current modmail thread.")
    @app_commands.describe(reason="The reason for closing the thread")
    async def modmail_close(self, interaction: discord.Interaction, reason: str = "No reason provided") -> None:
        rows = await self.bot.database.connection.execute("SELECT user_id, server_id FROM modmail_threads WHERE channel_id=?", (str(interaction.channel.id),))
        async with rows as cursor:
            thread = await cursor.fetchone()
            
        if not thread:
            return await interaction.response.send_message("This channel is not an active modmail thread.", ephemeral=True)
            
        user_id_str, server_id_str = thread
        await self.bot.database.delete_modmail_thread(int(user_id_str), int(server_id_str))
        
        user = self.bot.get_user(int(user_id_str)) or await self.bot.fetch_user(int(user_id_str))
        if user:
            try:
                embed = discord.Embed(title="Thread Closed", description=f"Your modmail thread in **{interaction.guild.name}** has been closed.\n**Reason:** {reason}", color=discord.Color.red())
                await user.send(embed=embed)
            except discord.Forbidden:
                pass
                
        config = await self.bot.database.get_modmail_config(interaction.guild.id)
        if config and config[1]:
            log_channel = interaction.guild.get_channel(int(config[1]))
            if log_channel:
                log_embed = discord.Embed(title="Thread Closed", description=f"Thread for {user.mention if user else user_id_str} closed by {interaction.user.mention}.", color=DEFAULT_COLOR)
                log_embed.add_field(name="Reason", value=reason)
                await log_channel.send(embed=log_embed)

        await interaction.channel.delete(reason=f"Modmail closed by {interaction.user}")

    @modmail.command(name="block", description="Block a user from using modmail.")
    async def modmail_block(self, interaction: discord.Interaction, user: discord.User) -> None:
        await self.bot.database.set_modmail_blocked(user.id, interaction.guild.id, True)
        await interaction.response.send_message(f"Blocked {user.mention} from using modmail.", ephemeral=True)

    @modmail.command(name="unblock", description="Unblock a user from using modmail.")
    async def modmail_unblock(self, interaction: discord.Interaction, user: discord.User) -> None:
        await self.bot.database.set_modmail_blocked(user.id, interaction.guild.id, False)
        await interaction.response.send_message(f"Unblocked {user.mention} from using modmail.", ephemeral=True)

    @commands.hybrid_command(name="reply", description="Reply to a user in a modmail thread.")
    @app_commands.describe(message="The message to send to the user")
    async def reply(self, context: Context, *, message: str) -> None:
        rows = await self.bot.database.connection.execute("SELECT user_id, server_id FROM modmail_threads WHERE channel_id=?", (str(context.channel.id),))
        async with rows as cursor:
            thread = await cursor.fetchone()
            
        if not thread:
            return await context.send("This is not an active modmail thread.", ephemeral=True)
            
        user_id_str, server_id_str = thread
        user = self.bot.get_user(int(user_id_str)) or await self.bot.fetch_user(int(user_id_str))
        
        if not user:
            return await context.send("Could not find the user. They may have deleted their account.", ephemeral=True)
            
        embed = discord.Embed(title="Message from Staff", description=message, color=DEFAULT_COLOR)
        embed.set_author(name=context.guild.name, icon_url=context.guild.icon.url if context.guild.icon else None)
        
        files = []
        if context.message.attachments:
            for attachment in context.message.attachments:
                files.append(await attachment.to_file())
                
        try:
            await user.send(embed=embed, files=files)
            await self.bot.database.update_modmail_thread_activity(int(user_id_str), context.guild.id)
            
            staff_embed = discord.Embed(description=message, color=discord.Color.green())
            staff_embed.set_author(name=context.author.display_name, icon_url=context.author.display_avatar.url)
            await context.send(embed=staff_embed)
            if context.interaction is None:
                await context.message.delete()
        except discord.Forbidden:
            await context.send("Could not send a message to this user. They might have DMs disabled or blocked the bot.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if isinstance(message.channel, discord.DMChannel):
            target_guild = None
            for guild in self.bot.guilds:
                config = await self.bot.database.get_modmail_config(guild.id)
                if config:
                    target_guild = guild
                    break
                    
            if not target_guild:
                return await message.channel.send("Modmail is not configured on my server yet.")
                
            config = await self.bot.database.get_modmail_config(target_guild.id)
            if not config: return
            
            is_blocked = await self.bot.database.is_modmail_blocked(message.author.id, target_guild.id)
            if is_blocked:
                return await message.channel.send("You are blocked from using Modmail in this server.")
                
            thread = await self.bot.database.get_modmail_thread(message.author.id, target_guild.id)
            
            needs_new_thread = True
            if thread:
                last_active_str = thread[1]
                try:
                    last_active = datetime.datetime.strptime(last_active_str, "%Y-%m-%d %H:%M:%S")
                    if (datetime.datetime.utcnow() - last_active).total_seconds() < 86400: # 24 hours
                        needs_new_thread = False
                except Exception:
                    needs_new_thread = False
                    
            channel = None
            if not needs_new_thread:
                channel = target_guild.get_channel(int(thread[0]))
                if not channel:
                    needs_new_thread = True
            
            if needs_new_thread:
                if thread:
                    await self.bot.database.delete_modmail_thread(message.author.id, target_guild.id)
                    old_channel = target_guild.get_channel(int(thread[0]))
                    if old_channel:
                        try:
                            await old_channel.send("Thread automatically closed due to 24 hours of inactivity or new user request.")
                            await old_channel.edit(name=f"closed-{message.author.name}")
                        except: pass
                
                category = target_guild.get_channel(int(config[0]))
                if not category:
                    return await message.channel.send("The modmail category is missing on the server.")
                    
                channel = await target_guild.create_text_channel(
                    name=f"modmail-{message.author.name}",
                    category=category,
                    topic=f"User ID: {message.author.id}"
                )
                await self.bot.database.create_modmail_thread(message.author.id, target_guild.id, channel.id)
                await message.channel.send("A new modmail thread has been opened with the staff.")
                
                info_embed = discord.Embed(title="New Modmail Thread", description=f"User: {message.author.mention}", color=DEFAULT_COLOR)
                info_embed.add_field(name="Account Created", value=f"<t:{int(message.author.created_at.timestamp())}:R>")
                await channel.send(embed=info_embed)
                
                # Send log to log channel
                if config[1]:
                    log_channel = target_guild.get_channel(int(config[1]))
                    if log_channel:
                        log_embed = discord.Embed(title="New Modmail Thread Opened", description=f"A new thread was opened by {message.author.mention}.", color=discord.Color.green())
                        log_embed.add_field(name="Channel", value=channel.mention)
                        try:
                            await log_channel.send(embed=log_embed)
                        except Exception:
                            pass

            user_embed = discord.Embed(description=message.content, color=discord.Color.blue())
            user_embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            
            files = []
            for attachment in message.attachments:
                files.append(await attachment.to_file())
                
            await channel.send(embed=user_embed, files=files)
            await self.bot.database.update_modmail_thread_activity(message.author.id, target_guild.id)
            await message.add_reaction("✅")

async def setup(bot) -> None:
    await bot.add_cog(Modmail(bot))
