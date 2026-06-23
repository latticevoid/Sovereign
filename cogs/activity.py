import time
import discord
from utils.colors import DEFAULT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, SPECIAL_COLOR
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
import aiosqlite

class Activity(commands.Cog, name="activity"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.voice_join_times = {} # tracking in-memory start times: user_id -> timestamp

    @commands.hybrid_command(name="activity", description="View a user's server activity stats.")
    @app_commands.describe(user="The user to lookup.")
    async def activity(self, context: Context, user: discord.User = None):
        target = user or context.author
        async with aiosqlite.connect("database/database.db") as db:
            cursor = await db.execute("SELECT message_count, voice_time FROM user_activity WHERE user_id=? AND server_id=?", (str(target.id), str(context.guild.id)))
            res = await cursor.fetchone()
            
        messages = res[0] if res else 0
        voice_seconds = res[1] if res else 0
        
        hours, remainder = divmod(voice_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = discord.Embed(title=f"Activity Stats: {target}", color=DEFAULT_COLOR)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Messages Sent", value=f"**{messages}**", inline=True)
        embed.add_field(name="Voice Time", value=f"**{int(hours)}h {int(minutes)}m**", inline=True)
        await context.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
            
        async with aiosqlite.connect("database/database.db") as db:
            await db.execute("""
                INSERT INTO user_activity(user_id, server_id, message_count) 
                VALUES (?, ?, 1) 
                ON CONFLICT(user_id, server_id) 
                DO UPDATE SET message_count = message_count + 1
            """, (str(message.author.id), str(message.guild.id)))
            await db.commit()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
            
        # Joined a channel
        if before.channel is None and after.channel is not None:
            self.voice_join_times[member.id] = time.time()
            
        # Left a channel
        elif before.channel is not None and after.channel is None:
            start_time = self.voice_join_times.pop(member.id, None)
            if start_time:
                duration = int(time.time() - start_time)
                async with aiosqlite.connect("database/database.db") as db:
                    await db.execute("""
                        INSERT INTO user_activity(user_id, server_id, voice_time) 
                        VALUES (?, ?, ?) 
                        ON CONFLICT(user_id, server_id) 
                        DO UPDATE SET voice_time = voice_time + excluded.voice_time
                    """, (str(member.id), str(member.guild.id), duration))
                    await db.commit()

async def setup(bot) -> None:
    await bot.add_cog(Activity(bot))
