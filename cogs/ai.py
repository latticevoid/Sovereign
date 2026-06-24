import os
import re
import time
from collections import defaultdict
import discord
from utils.colors import DEFAULT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, SPECIAL_COLOR
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from groq import AsyncGroq

class AI(commands.Cog, name="ai"):
    def __init__(self, bot) -> None:
        self.bot = bot
        # Initialize Groq client with API key from environment
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if self.groq_api_key:
            self.groq_client = AsyncGroq(api_key=self.groq_api_key)
        else:
            self.groq_client = None

        # Parse owners from .env
        owners_str = os.getenv("OWNERS", "")
        self.owners = [int(x.strip()) for x in owners_str.split(",") if x.strip().isdigit()]

        # Rate Limiting & State Tracking
        self.user_cooldowns = {}
        self.user_minute_rates = defaultdict(list)
        self.user_hour_rates = defaultdict(list)
        self.user_daily_rates = defaultdict(int)
        self.guild_hour_rates = defaultdict(list)
        self.last_prompts = {}
        
        # Register the Context Menu for AI Moderation
        self.analyze_ctx_menu = app_commands.ContextMenu(
            name="Analyze Message",
            callback=self.analyze_message_context,
        )
        self.bot.tree.add_command(self.analyze_ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.analyze_ctx_menu.name, type=self.analyze_ctx_menu.type)

    @app_commands.default_permissions(moderate_members=True)
    async def analyze_message_context(self, interaction: discord.Interaction, message: discord.Message) -> None:
        """Context menu action to analyze a message using Groq AI."""
        if not self.groq_client:
            await interaction.response.send_message("The Groq API key is not configured.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        system_prompt = (
            "You are Sovereign, an elite Discord moderation AI. "
            "Analyze the user's message for toxicity, phishing, passive-aggression, spam, or severe rule-breaking intent. "
            "Provide a brief analysis (max 3 sentences) and suggest an action (None, Warn, Timeout, Tempban, Ban). "
            "Be direct, objective, and professional."
        )

        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Author: {message.author}\nContent: {message.content}"}
                ],
                model="llama-3.1-70b-versatile",
                max_tokens=250,
                temperature=0.3,
                top_p=0.9,
            )
            reply = chat_completion.choices[0].message.content
            reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()
            
            embed = discord.Embed(
                title="🧠 AI Moderation Analysis",
                description=f"**Message:** {message.content}\n\n**Analysis:**\n{reply}",
                color=WARNING_COLOR
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred during AI analysis: {e}", ephemeral=True)

    def is_spam(self, text: str) -> bool:
        """Detects character flooding and excessive mentions."""
        # Block more than 10 repeated identical characters
        if re.search(r'(.)\1{10,}', text):
            return True
        # Block excessive mentions (e.g. <@123456789>)
        if len(re.findall(r'<@!?\d+>', text)) > 5:
            return True
        return False

    def clean_old_timestamps(self, timestamp_list, duration):
        """Removes timestamps older than the specified duration (in seconds)."""
        now = time.time()
        while timestamp_list and now - timestamp_list[0] > duration:
            timestamp_list.pop(0)

    async def check_rate_limits(self, context: Context, prompt: str) -> bool:
        """
        Checks rate limits and spam filters for a given prompt.
        Returns True if the prompt should be blocked, False if it is allowed.
        """
        user_id = context.author.id
        guild_id = context.guild.id if context.guild else 0
        now = time.time()
        is_owner = user_id in self.owners

        # Only apply limits if user is not an owner
        if not is_owner:
            prompt_stripped = prompt.strip()

            # 1. Input Validation
            if len(prompt_stripped) < 3:
                await context.send("Your prompt is too short. Please provide at least 3 characters.", ephemeral=True)
                return True
            if len(prompt_stripped) > 1500:
                await context.send("Your prompt is too long. Please keep it under 1500 characters.", ephemeral=True)
                return True
            if self.is_spam(prompt_stripped):
                await context.send("Your prompt was flagged for spam (character flooding or excessive mentions). Please try again with regular text.", ephemeral=True)
                return True
            if self.last_prompts.get(user_id) == prompt_stripped:
                await context.send("You just submitted the exact same request! Please don't repeat the same prompt.", ephemeral=True)
                return True

            # 2. Cooldown check
            last_request_time = self.user_cooldowns.get(user_id, 0)
            if now - last_request_time < 15:
                await context.send(f"Please wait 15 seconds between requests! You can try again in {15 - int(now - last_request_time)} seconds.", ephemeral=True)
                return True

            # 3. Clean up old rate limit timestamps
            self.clean_old_timestamps(self.user_minute_rates[user_id], 60)
            self.clean_old_timestamps(self.user_hour_rates[user_id], 3600)
            self.clean_old_timestamps(self.guild_hour_rates[guild_id], 3600)

            # 4. User Minute/Hour limits
            if len(self.user_minute_rates[user_id]) >= 5:
                await context.send("You are sending requests too fast! Please wait a minute. (Max 5 requests/minute)", ephemeral=True)
                return True
            if len(self.user_hour_rates[user_id]) >= 25:
                await context.send("You've reached your hourly limit of 25 requests. Please try again later.", ephemeral=True)
                return True

            # 5. Guild Hour limits
            if guild_id != 0 and len(self.guild_hour_rates[guild_id]) >= 150:
                await context.send("This server has reached its hourly limit of 150 AI requests to prevent resource exhaustion. Please try again later.", ephemeral=True)
                return True

            # 6. Daily Limits
            date_str = time.strftime("%Y-%m-%d")
            daily_key = f"{user_id}_{date_str}"
            is_admin = context.author.guild_permissions.administrator if context.guild else False
            daily_limit = 250 if is_admin else 50
            
            if self.user_daily_rates[daily_key] >= daily_limit:
                role_msg = "premium user / administrator" if is_admin else "regular user"
                await context.send(f"You have reached your daily limit of {daily_limit} requests as a {role_msg}. Please come back tomorrow!", ephemeral=True)
                return True

            # Record the usage
            self.user_cooldowns[user_id] = now
            self.user_minute_rates[user_id].append(now)
            self.user_hour_rates[user_id].append(now)
            self.guild_hour_rates[guild_id].append(now)
            self.user_daily_rates[daily_key] += 1
            self.last_prompts[user_id] = prompt_stripped
        
        return False

    async def split_and_send_embed(self, context: Context, title: str, content: str):
        """Splits long text into multiple embeds if necessary."""
        # Discord limit is 4096 for description. We will split at 4000.
        chunks = [content[i:i+4000] for i in range(0, len(content), 4000)]
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=title if i == 0 else f"{title} (Part {i+1})",
                description=chunk,
                color=DEFAULT_COLOR,
            )
            if i == len(chunks) - 1:
                embed.set_footer(text=f"Requested by {context.author.display_name}")
            
            # Send the first chunk as the interaction response, the rest as follow-ups
            if i == 0:
                await context.send(embed=embed)
            else:
                await context.channel.send(embed=embed)

    @commands.hybrid_group(name="ai", description="AI related commands.")
    async def ai_group(self, context: Context) -> None:
        """AI related commands."""
        if context.invoked_subcommand is None:
            await context.send("Please specify a valid subcommand.")

    @ai_group.command(
        name="chat",
        description="Chat with the AI.",
    )
    @app_commands.describe(question="The message you want to send to the AI.")
    async def chat(self, context: Context, *, question: str) -> None:
        """
        Ask the AI a question using the Groq API.
        """
        if not self.groq_client:
            await context.send(embed=discord.Embed(
                title="Error",
                description="The Groq API key is not configured. Please add `GROQ_API_KEY` to the `.env` file.",
                color=ERROR_COLOR,
            ))
            return

        if await self.check_rate_limits(context, question):
            return

        # Defer the response because API calls can take longer than 3 seconds
        await context.defer()

        try:
            # Call Groq API
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Sovereign, a Discord assistant.\n\n"
                            "Talk like an intelligent, relaxed person, not customer support.\n\n"
                            "Rules:\n\n"
                            "* Never start replies with \"As an AI\", \"I'm an AI\", or similar unless directly relevant.\n"
                            "* Match the user's tone and energy.\n"
                            "* Be conversational, concise, and natural.\n"
                            "* Use contractions naturally.\n"
                            "* Show personality, humor, and opinions when appropriate, but don't invent personal experiences.\n"
                            "* Avoid generic assistant phrases, excessive enthusiasm, and emoji spam.\n"
                            "* For casual messages, reply casually instead of giving formal assistant introductions.\n"
                            "* Lead with the answer, not a disclaimer.\n"
                            "* If the user is wrong, correct them politely and directly.\n"
                            "* Vary sentence structure and wording to avoid repetitive AI patterns.\n\n"
                            "Examples:\n"
                            "User: how are you?\n"
                            "Assistant: Doing pretty well. What's up?\n\n"
                            "User: sup\n"
                            "Assistant: Not much. What are you working on?\n\n"
                            "User: 2+2\n"
                            "Assistant: 4."
                        ),
                    },
                    {
                        "role": "user",
                        "content": question,
                    }
                ],
                model="llama-3.1-70b-versatile",
                max_tokens=1000,
                temperature=0.8,
                top_p=0.9,
            )
            
            answer = chat_completion.choices[0].message.content
            answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL).strip()
            await self.split_and_send_embed(context, "🤖 AI Response", answer)

        except Exception as e:
            self.bot.logger.error(f"Groq API Error: {e}")
            await context.send(embed=discord.Embed(
                title="Error",
                description="There was an error communicating with the AI. Please try again later.",
                color=ERROR_COLOR,
            ))

    @commands.hybrid_group(name="story", description="Generate or continue an AI story.")
    async def story(self, context: Context) -> None:
        """Story generation commands."""
        if context.invoked_subcommand is None:
            await context.send("Invalid subcommand. Use `/story create` or `/story continue`.", ephemeral=True)

    @story.command(name="create", description="Generate the first part of an original story.")
    @app_commands.describe(prompt="The genre, theme, characters, or plot for your story.")
    async def story_create(self, context: Context, *, prompt: str) -> None:
        """Generate a creative story using the Groq API."""
        if not self.groq_client:
            await context.send(embed=discord.Embed(title="Error", description="Groq API key not configured.", color=ERROR_COLOR))
            return

        if await self.check_rate_limits(context, prompt):
            return

        await context.defer()

        import string
        import random
        story_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a master storyteller. Your task is to craft engaging narratives.\n"
                            "Rules:\n"
                            "1. Write beautifully formatted paragraphs.\n"
                            "2. Maintain consistent characters and settings.\n"
                            "3. Stop the story at a midway point, creating a cliffhanger or natural pause.\n"
                            "4. Do NOT include <think> reasoning blocks.\n"
                            "5. Dive straight into the story without conversational filler."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Write the first part of a story based on: {prompt}",
                    }
                ],
                model="llama-3.1-70b-versatile",
                max_tokens=2048,
                temperature=0.85,
                top_p=0.9,
            )
            
            story_text = chat_completion.choices[0].message.content
            story_text = re.sub(r'<think>.*?</think>', '', story_text, flags=re.DOTALL).strip()
            
            embed = discord.Embed(title="📖 AI Story", description=story_text, color=DEFAULT_COLOR)
            embed.set_footer(text=f"Requested by {context.author.display_name} | ID: {story_id}")
            
            msg = await context.send(embed=embed)
            if context.interaction:
                msg = await context.interaction.original_response()
                
            await self.bot.database.save_story(story_id, context.guild.id, context.channel.id, msg.id)

        except Exception as e:
            self.bot.logger.error(f"Groq API Error: {e}")
            await context.send(embed=discord.Embed(title="Error", description="Error generating story.", color=ERROR_COLOR))

    @story.command(name="continue", description="Continue an existing story.")
    @app_commands.describe(story_id="The unique ID of the story you want to continue.")
    async def story_continue(self, context: Context, story_id: str) -> None:
        """Continue a story using its ID."""
        if not self.groq_client:
            await context.send(embed=discord.Embed(title="Error", description="Groq API key not configured.", color=ERROR_COLOR))
            return

        if await self.check_rate_limits(context, f"continue story {story_id}"):
            return

        await context.defer()

        story_data = await self.bot.database.get_story(story_id, context.guild.id)
        if not story_data:
            await context.send(embed=discord.Embed(description="Story not found or invalid ID. If this story is older than 7 months, it has been automatically purged from the archives to save space!", color=ERROR_COLOR), ephemeral=True)
            return

        channel_id, message_id = story_data
        channel = context.guild.get_channel(channel_id)
        if not channel:
            await context.send(embed=discord.Embed(description="Story channel no longer exists.", color=ERROR_COLOR), ephemeral=True)
            return
            
        try:
            msg = await channel.fetch_message(message_id)
            if not msg.embeds or not msg.embeds[0].description:
                raise ValueError("No story text found in message.")
            previous_story = msg.embeds[0].description
        except Exception:
            await context.send(embed=discord.Embed(description="Could not find the original story message.", color=ERROR_COLOR), ephemeral=True)
            return

        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a master storyteller. Your task is to continue the story seamlessly.\n"
                            "Rules:\n"
                            "1. Read the provided story text and seamlessly generate the next part.\n"
                            "2. Do NOT add any introductory text like 'Here is the continuation'. Start immediately with the next sentence or paragraph.\n"
                            "3. Do NOT include <think> reasoning blocks.\n"
                            "4. Provide a satisfying conclusion to the story."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Here is the story so far:\n\n{previous_story}\n\nPlease seamlessly continue from where it left off.",
                    }
                ],
                model="llama-3.1-70b-versatile",
                max_tokens=2048,
                temperature=0.85,
                top_p=0.9,
            )
            
            story_text = chat_completion.choices[0].message.content
            story_text = re.sub(r'<think>.*?</think>', '', story_text, flags=re.DOTALL).strip()
            
            embed = discord.Embed(title=f"📖 AI Story Continued (ID: {story_id})", description=story_text, color=DEFAULT_COLOR)
            embed.set_footer(text=f"Requested by {context.author.display_name}")
            
            await context.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Groq API Error: {e}")
            await context.send(embed=discord.Embed(title="Error", description="Error continuing story.", color=ERROR_COLOR))

async def setup(bot) -> None:
    await bot.add_cog(AI(bot))
