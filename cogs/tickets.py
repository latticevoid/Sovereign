import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands
import typing
import string
import random
import time
import io
import html
import re
from utils.colors import DEFAULT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, SPECIAL_COLOR

def format_color(color):
    if color and color.value != 0:
        return f"#{color.value:06x}"
    return "#dbdee1"

async def generate_transcript(interaction: discord.Interaction, messages: list, ticket_id: str):
    # Get unique participants for the right sidebar
    participants = {}
    for msg in messages:
        if msg.author.id not in participants:
            participants[msg.author.id] = msg.author

    # Include interaction user and bot if not present
    if interaction.user.id not in participants:
        participants[interaction.user.id] = interaction.user
    if interaction.guild.me.id not in participants:
        participants[interaction.guild.me.id] = interaction.guild.me
        
    online_members = []
    bot_members = []
    
    for member in participants.values():
        is_bot = member.bot
        color = format_color(getattr(member, 'color', None))
        av = member.display_avatar.url if member.display_avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
        
        name = html.escape(member.display_name)
        badges_html = ""
        if is_bot:
            badges_html = "<span class='bot-badge'>APP</span>"
            bot_members.append((name, av, color, badges_html))
        else:
            if member.id == interaction.guild.owner_id:
                badges_html += "<span class='owner-badge' title='Server Owner'>👑</span>"
            online_members.append((name, av, color, badges_html))

    def render_member(m):
        name, av, color, badges = m
        return f"""
        <div class="member-item">
            <div class="member-avatar-wrapper">
                <img src="{av}" class="member-avatar" />
                <div class="status-indicator online"></div>
            </div>
            <div class="member-info">
                <span class="member-name" style="color: {color};">{name}</span>
                {badges}
            </div>
        </div>
        """

    members_html = ""
    if online_members:
        members_html += f"<div class='member-category'>Online — {len(online_members)}</div>"
        for m in online_members:
            members_html += render_member(m)
            
    if bot_members:
        members_html += f"<div class='member-category'>Bots — {len(bot_members)}</div>"
        for m in bot_members:
            members_html += render_member(m)

    messages_html = ""
    last_date = None
    
    def process_markdown(text):
        text = html.escape(text)
        text = text.replace("\n", "<br>")
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        text = re.sub(r'```(?:([a-zA-Z0-9]+)\n)?(.*?)```', r'<div class="code-block"><div class="code-header">\1</div><pre><code>\2</code></pre></div>', text, flags=re.DOTALL)
        text = re.sub(r'`(.*?)`', r'<code class="inline-code">\1</code>', text)
        text = re.sub(r'\|\|(.*?)\|\|', r'<span class="spoiler" onclick="this.classList.add(\'revealed\')">\1</span>', text)
        return text

    for msg in messages:
        msg_date = msg.created_at.strftime("%B %d, %Y")
        if msg_date != last_date:
            messages_html += f"""
            <div class="date-divider">
                <span class="date-text">{msg_date}</span>
            </div>
            """
            last_date = msg_date

        author_name = html.escape(msg.author.display_name)
        author_color = format_color(getattr(msg.author, 'color', None))
        av_url = msg.author.display_avatar.url if msg.author.display_avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
        timestamp = msg.created_at.strftime("%I:%M %p")
        
        bot_badge = "<span class='bot-tag'>APP</span>" if msg.author.bot else ""
        content = process_markdown(msg.content)
        edited_html = "<span class='edited'>(edited)</span>" if msg.edited_at else ""

        embeds_html = ""
        for em in msg.embeds:
            em_color = format_color(em.color) if em.color else "#202225"
            embed_title = f"<div class='embed-title'>{html.escape(em.title)}</div>" if em.title else ""
            embed_desc = f"<div class='embed-description'>{process_markdown(em.description)}</div>" if em.description else ""
            
            fields_html = ""
            for f in em.fields:
                inline_class = "embed-field-inline" if f.inline else ""
                fields_html += f"<div class='embed-field {inline_class}'><div class='embed-field-name'>{html.escape(f.name)}</div><div class='embed-field-value'>{process_markdown(f.value)}</div></div>"
            if fields_html:
                fields_html = f"<div class='embed-fields'>{fields_html}</div>"
                
            embeds_html += f"""
            <div class="embed-wrapper">
                <div class="embed-pill" style="background-color: {em_color};"></div>
                <div class="embed-inner">
                    {embed_title}
                    {embed_desc}
                    {fields_html}
                </div>
            </div>
            """

        messages_html += f"""
        <div class="message">
            <div class="message-avatar-wrapper">
                <img src="{av_url}" class="message-avatar" />
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-author" style="color: {author_color};">{author_name}</span>
                    {bot_badge}
                    <span class="message-timestamp">{timestamp}</span>
                </div>
                <div class="message-text">{content} {edited_html}</div>
                {embeds_html}
            </div>
        </div>
        """

    channel_name = html.escape(interaction.channel.name)
    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcript - {channel_name}</title>
    <style>
        @font-face {{font-family: 'gg sans'; src: local('Segoe UI'), local('Helvetica Neue'), local('Arial');}}
        :root {{
            --bg-primary: #313338;
            --bg-secondary: #2b2d31;
            --bg-tertiary: #1e1f22;
            --member-panel: #2b2d31;
            --hover: #3f4248;
            --text-normal: #dbdee1;
            --text-muted: #949ba4;
            --header-secondary: #b5bac1;
            --interactive-normal: #b5bac1;
            --interactive-hover: #dbdee1;
            --interactive-active: #fff;
            --channel-icon: #80848e;
            --divider: rgba(255, 255, 255, 0.06);
            --brand: #5865F2;
        }}
        * {{box-sizing: border-box; margin: 0; padding: 0;}}
        body {{font-family: 'gg sans', 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: var(--bg-primary); color: var(--text-normal); height: 100vh; display: flex; overflow: hidden; font-size: 16px;}}
        .discord-app {{display: flex; width: 100%; height: 100%;}}
        
        .chat-container {{flex: 1; display: flex; flex-direction: column; min-width: 0; background-color: var(--bg-primary);}}
        .channel-header {{height: 48px; min-height: 48px; display: flex; align-items: center; padding: 0 16px; border-bottom: 1px solid var(--bg-tertiary); box-shadow: 0 1px 2px rgba(0,0,0,0.2); z-index: 2;}}
        .header-icon {{color: var(--channel-icon); margin-right: 8px; font-size: 24px; font-weight: 300;}}
        .header-name {{font-weight: 600; color: var(--interactive-active); margin-right: 8px;}}
        .header-divider {{width: 1px; height: 24px; background-color: var(--divider); margin: 0 8px;}}
        .header-topic {{color: var(--header-secondary); font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}}
        
        .scroller {{flex: 1; overflow-y: scroll; overflow-x: hidden;}}
        .scroller::-webkit-scrollbar {{width: 8px;}}
        .scroller::-webkit-scrollbar-track {{background: var(--bg-secondary); border-radius: 4px;}}
        .scroller::-webkit-scrollbar-thumb {{background: var(--bg-tertiary); border-radius: 4px;}}
        
        .welcome-banner {{padding: 48px 16px 16px; margin-bottom: 16px;}}
        .welcome-icon-wrapper {{width: 68px; height: 68px; border-radius: 50%; background-color: var(--bg-secondary); display: flex; align-items: center; justify-content: center; margin-bottom: 16px;}}
        .welcome-icon {{font-size: 40px; color: #fff;}}
        .welcome-title {{font-size: 32px; font-weight: 700; color: #fff; margin-bottom: 8px;}}
        .welcome-desc {{color: var(--header-secondary); font-size: 16px;}}
        
        .date-divider {{margin: 24px 16px 8px; display: flex; align-items: center; justify-content: center; position: relative;}}
        .date-divider::before {{content: ''; position: absolute; left: 0; right: 0; height: 1px; background-color: var(--divider);}}
        .date-text {{background-color: var(--bg-primary); padding: 0 8px; color: var(--text-muted); font-size: 12px; font-weight: 600; z-index: 1;}}
        
        .message {{display: flex; padding: 2px 48px 2px 16px; margin-top: 17px; position: relative;}}
        .message:hover {{background-color: var(--hover);}}
        .message-avatar-wrapper {{margin-right: 16px; flex-shrink: 0;}}
        .message-avatar {{width: 40px; height: 40px; border-radius: 50%; cursor: pointer;}}
        .message-content {{flex: 1; min-width: 0;}}
        .message-header {{display: flex; align-items: baseline; margin-bottom: 2px;}}
        .message-author {{font-weight: 500; margin-right: 4px; cursor: pointer;}}
        .message-author:hover {{text-decoration: underline;}}
        .bot-tag {{background-color: var(--brand); color: #fff; font-size: 10px; padding: 1px 4px; border-radius: 3px; margin-right: 4px; vertical-align: middle; font-weight: 600; position: relative; top: -1px;}}
        .message-timestamp {{color: var(--text-muted); font-size: 12px; margin-left: 4px;}}
        .message-text {{line-height: 1.375rem; white-space: pre-wrap; word-wrap: break-word;}}
        .edited {{color: var(--text-muted); font-size: 10px; margin-left: 4px;}}
        
        .inline-code {{background-color: var(--bg-secondary); padding: 0.2em; border-radius: 3px; font-family: Consolas, monospace; font-size: 85%;}}
        .code-block {{background-color: var(--bg-secondary); border: 1px solid var(--bg-tertiary); border-radius: 4px; margin-top: 6px; padding: 8px; font-family: Consolas, monospace; font-size: 14px; overflow-x: auto;}}
        .code-header {{font-size: 12px; color: var(--text-muted); margin-bottom: 4px;}}
        .spoiler {{background-color: #202225; color: transparent; border-radius: 3px; padding: 0 2px; cursor: pointer;}}
        .spoiler.revealed {{background-color: rgba(255, 255, 255, 0.1); color: inherit;}}
        
        .embed-wrapper {{display: flex; margin-top: 8px; max-width: 520px; background-color: var(--bg-secondary); border-radius: 4px; overflow: hidden; border: 1px solid var(--bg-tertiary);}}
        .embed-pill {{width: 4px; flex-shrink: 0;}}
        .embed-inner {{padding: 12px; display: flex; flex-direction: column; gap: 8px;}}
        .embed-title {{font-weight: 600; color: #fff;}}
        .embed-description {{font-size: 14px; color: var(--text-normal);}}
        .embed-fields {{display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px;}}
        .embed-field {{flex: 1 1 100%;}}
        .embed-field.embed-field-inline {{flex: 1 1 calc(33% - 12px); min-width: 150px;}}
        .embed-field-name {{font-weight: 600; font-size: 14px; color: #fff; margin-bottom: 2px;}}
        .embed-field-value {{font-size: 14px; color: var(--text-normal);}}
        
        .member-panel {{width: 240px; background-color: var(--member-panel); flex-shrink: 0; display: flex; flex-direction: column;}}
        .member-category {{padding: 24px 8px 0 16px; color: var(--header-secondary); font-size: 12px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px;}}
        .member-item {{display: flex; align-items: center; padding: 4px 8px; margin: 1px 8px; border-radius: 4px; cursor: pointer;}}
        .member-item:hover {{background-color: var(--hover);}}
        .member-avatar-wrapper {{position: relative; margin-right: 12px;}}
        .member-avatar {{width: 32px; height: 32px; border-radius: 50%;}}
        .status-indicator {{position: absolute; bottom: -2px; right: -2px; width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--member-panel);}}
        .status-indicator.online {{background-color: #23a559;}}
        .member-info {{display: flex; align-items: center; gap: 4px; overflow: hidden; white-space: nowrap;}}
        .member-name {{font-size: 16px; font-weight: 500; text-overflow: ellipsis; overflow: hidden;}}
        @media (max-width: 800px) {{.member-panel {{display: none;}}}}
    </style>
</head>
<body>
    <div class="discord-app">
        <div class="chat-container">
            <div class="channel-header"><span class="header-icon">#</span><span class="header-name">{channel_name}</span><div class="header-divider"></div><span class="header-topic">Ticket Transcript</span></div>
            <div class="scroller">
                <div class="welcome-banner"><div class="welcome-icon-wrapper"><span class="welcome-icon">#</span></div><div class="welcome-title">Welcome to #{channel_name}!</div><div class="welcome-desc">This is the start of the #{channel_name} channel transcript.</div></div>
                {messages_html}
                <div style="height: 30px;"></div>
            </div>
        </div>
        <div class="member-panel">
            <div class="scroller">{members_html}</div>
        </div>
    </div>
</body>
</html>"""
    return html_document

class TicketMessageModal(discord.ui.Modal, title='Edit Ticket Panel'):
    panel_title = discord.ui.TextInput(
        label='Panel Title (No Variables Supported)', style=discord.TextStyle.short, required=False, max_length=256
    )
    panel_description = discord.ui.TextInput(
        label='Panel Description (No Variables Supported)', style=discord.TextStyle.paragraph, required=False, max_length=4000
    )

    def __init__(self, bot, panel_id: str, msg: discord.Message):
        super().__init__()
        self.bot = bot
        self.panel_id = panel_id
        self.msg = msg
        
        embed = msg.embeds[0] if msg.embeds else None
        if embed:
            if embed.title: self.panel_title.default = embed.title
            if embed.description: self.panel_description.default = embed.description

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.msg.embeds[0] if self.msg.embeds else discord.Embed(color=DEFAULT_COLOR)
        embed.title = self.panel_title.value
        embed.description = self.panel_description.value
        await self.msg.edit(embed=embed)
        await self.bot.database.update_ticket_panel_message(self.panel_id, interaction.guild.id, self.panel_title.value, self.panel_description.value)
        await interaction.response.send_message("Panel message updated successfully.", ephemeral=True)

class TicketAddButtonModal(discord.ui.Modal, title='Add Button'):
    btn_label = discord.ui.TextInput(label='Button Text', style=discord.TextStyle.short, max_length=50)
    btn_emoji = discord.ui.TextInput(label='Button Emoji (Optional)', style=discord.TextStyle.short, required=False)

    def __init__(self, bot, panel_id: str, msg: discord.Message):
        super().__init__()
        self.bot = bot
        self.panel_id = panel_id
        self.msg = msg

    async def on_submit(self, interaction: discord.Interaction):
        button_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        await self.bot.database.add_ticket_button(button_id, self.panel_id, interaction.guild.id, self.btn_label.value, self.btn_emoji.value, 0, 0)
        
        options = await self.bot.database.get_ticket_options(self.panel_id)
        buttons = await self.bot.database.get_ticket_buttons(self.panel_id)
        await self.msg.edit(view=TicketPanelView(options, buttons, self.bot, self.panel_id))
        await interaction.response.send_message("Button added!", ephemeral=True)

class TicketAddOptionModal(discord.ui.Modal, title='Add Dropdown Option'):
    opt_label = discord.ui.TextInput(label='Option Name', style=discord.TextStyle.short, max_length=50)
    opt_emoji = discord.ui.TextInput(label='Option Emoji (Optional)', style=discord.TextStyle.short, required=False)
    opt_category = discord.ui.TextInput(label='Category Channel ID', style=discord.TextStyle.short)
    opt_role = discord.ui.TextInput(label='Support Role ID (Optional)', style=discord.TextStyle.short, required=False)

    def __init__(self, bot, panel_id: str, msg: discord.Message):
        super().__init__()
        self.bot = bot
        self.panel_id = panel_id
        self.msg = msg

    async def on_submit(self, interaction: discord.Interaction):
        option_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        cat_id = int(self.opt_category.value) if self.opt_category.value.isdigit() else 0
        role_id = int(self.opt_role.value) if self.opt_role.value and self.opt_role.value.isdigit() else 0
        
        await self.bot.database.add_ticket_option(option_id, self.panel_id, interaction.guild.id, self.opt_label.value, self.opt_emoji.value, cat_id, role_id)
        await interaction.response.send_message("Dropdown option added!", ephemeral=True)

class TicketChannelMessageModal(discord.ui.Modal, title='Edit In-Channel Message'):
    ticket_title = discord.ui.TextInput(
        label='Title (Vars: {user}, {button}, {dropdown})', style=discord.TextStyle.short, required=False, max_length=256,
        placeholder='e.g. {button} Ticket Opened'
    )
    ticket_description = discord.ui.TextInput(
        label='Desc (Vars: {user}, {button}, {dropdown})', style=discord.TextStyle.paragraph, required=False, max_length=4000,
        placeholder='e.g. Welcome {user}! Staff will help with {dropdown}.'
    )

    def __init__(self, bot, panel_id: str):
        super().__init__()
        self.bot = bot
        self.panel_id = panel_id

    async def on_submit(self, interaction: discord.Interaction):
        title = self.ticket_title.value or None
        description = self.ticket_description.value or None
        await self.bot.database.update_ticket_channel_message(self.panel_id, interaction.guild.id, title, description)
        await interaction.response.send_message("In-channel message updated. Applying changes to open tickets...", ephemeral=True)

class TicketChannelNameModal(discord.ui.Modal, title='Edit Channel Name Format'):
    name_format = discord.ui.TextInput(
        label='Format (Vars: {button}, {dropdown})', style=discord.TextStyle.short, required=False, max_length=50,
        placeholder='{button}-{dropdown}', default='{button}-{dropdown}'
    )

    def __init__(self, bot, panel_id: str):
        super().__init__()
        self.bot = bot
        self.panel_id = panel_id

    async def on_submit(self, interaction: discord.Interaction):
        fmt = self.name_format.value or "{button}-{dropdown}"
        await self.bot.database.update_ticket_channel_name_format(self.panel_id, interaction.guild.id, fmt)
        await interaction.response.send_message(f"Channel name format updated. New tickets will use: `{fmt}-user`", ephemeral=True)
        
        active_tickets = await self.bot.database.get_all_active_tickets_for_panel(self.panel_id)
        for t in active_tickets:
            try:
                channel = interaction.guild.get_channel(int(t[0]))
                if channel and t[1]:
                    msg = await channel.fetch_message(int(t[1]))
                    if msg and msg.embeds:
                        embed = msg.embeds[0]
                        new_title = title or embed.title
                        new_desc = description or "Welcome {user}! Support will be with you shortly."
                        embed.title = new_title
                        embed.description = new_desc.replace("{user}", f"<@{t[2]}>")
                        await msg.edit(embed=embed)
            except Exception:
                continue

class AdminRemoveSelect(discord.ui.Select):
    def __init__(self, type_str, items, bot, panel_id, msg):
        self.type_str = type_str
        self.bot = bot
        self.panel_id = panel_id
        self.msg = msg
        options = [discord.SelectOption(label=i[1], value=i[0]) for i in items]
        super().__init__(placeholder=f"Select {type_str} to remove...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.type_str == "button":
            await self.bot.database.delete_ticket_button(self.values[0], interaction.guild.id)
            options = await self.bot.database.get_ticket_options(self.panel_id)
            buttons = await self.bot.database.get_ticket_buttons(self.panel_id)
            await self.msg.edit(view=TicketPanelView(options, buttons, self.bot, self.panel_id))
        else:
            await self.bot.database.delete_ticket_option(self.values[0], interaction.guild.id)
        
        await interaction.response.send_message(f"Removed {self.type_str} successfully.", ephemeral=True)

class AdminDashboardView(discord.ui.View):
    def __init__(self, bot, panel_id, msg):
        super().__init__(timeout=300)
        self.bot = bot
        self.panel_id = panel_id
        self.msg = msg

    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def edit_msg(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketMessageModal(self.bot, self.panel_id, self.msg))

    @discord.ui.button(label="Edit Channel Name", style=discord.ButtonStyle.primary, emoji="🏷️", row=0)
    async def edit_chan_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketChannelNameModal(self.bot, self.panel_id))

    @discord.ui.button(label="Add Button", style=discord.ButtonStyle.success, emoji="➕", row=0)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketAddButtonModal(self.bot, self.panel_id, self.msg))

    @discord.ui.button(label="Remove Button", style=discord.ButtonStyle.danger, emoji="➖", row=0)
    async def rem_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        buttons = await self.bot.database.get_ticket_buttons(self.panel_id)
        if not buttons:
            return await interaction.response.send_message("No buttons to remove.", ephemeral=True)
        view = discord.ui.View()
        view.add_item(AdminRemoveSelect("button", buttons, self.bot, self.panel_id, self.msg))
        await interaction.response.send_message("Select a button to remove:", view=view, ephemeral=True)

    @discord.ui.button(label="Add Dropdown Option", style=discord.ButtonStyle.success, emoji="🔽", row=1)
    async def add_opt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketAddOptionModal(self.bot, self.panel_id, self.msg))

    @discord.ui.button(label="Remove Dropdown Option", style=discord.ButtonStyle.danger, emoji="✖️", row=1)
    async def rem_opt(self, interaction: discord.Interaction, button: discord.ui.Button):
        options = await self.bot.database.get_ticket_options(self.panel_id)
        if not options:
            return await interaction.response.send_message("No options to remove.", ephemeral=True)
        view = discord.ui.View()
        view.add_item(AdminRemoveSelect("option", options, self.bot, self.panel_id, self.msg))
        await interaction.response.send_message("Select an option to remove:", view=view, ephemeral=True)

    @discord.ui.button(label="Edit In-Channel Message", style=discord.ButtonStyle.primary, emoji="📨", row=2)
    async def edit_channel_msg(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketChannelMessageModal(self.bot, self.panel_id))

class EphemeralDropdownView(discord.ui.View):
    def __init__(self, options, bot, button_label, panel_id):
        super().__init__(timeout=300)
        self.add_item(TicketDropdown(options, bot, button_label, panel_id))

class TicketDropdown(discord.ui.Select):
    def __init__(self, options, bot, button_label, panel_id):
        self.bot = bot
        self.button_label = button_label
        self.panel_id = panel_id
        self.custom_options_map = {}
        
        select_options = []
        if not options:
            defaults = [
                ("Report a Member", "👥", "Report a member who violated rules"),
                ("Claim Giveaway", "🎁", "Claim your giveaway price"),
                ("Server Issues", "👾", "Report any bugs or issues"),
                ("Host Giveaway", "🎁", "Host a giveaway"),
                ("Host Event", "📅", "Host an event"),
                ("Donation", "🎁", "Donate an item"),
                ("Staff Report", "🔨", "Report staff misconduct"),
                ("Request Role", "✏️", "Request a role")
            ]
            for d in defaults:
                select_options.append(discord.SelectOption(label=d[0], value=d[0], emoji=d[1], description=d[2]))
        else:
            for opt in options:
                emoji = opt[2] if opt[2] else None
                select_options.append(discord.SelectOption(label=opt[1], value=opt[0], emoji=emoji))
                self.custom_options_map[opt[0]] = opt
                
        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=select_options[:25])

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        category_id = 0
        support_role_id = 0
        dropdown_label = selection
        
        if self.custom_options_map:
            opt = self.custom_options_map.get(selection)
            if opt:
                dropdown_label = opt[1]
                category_id = int(opt[3])
                support_role_id = int(opt[4])

        ticket_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        category = interaction.guild.get_channel(category_id) if category_id else interaction.channel.category
        support_role = interaction.guild.get_role(support_role_id) if support_role_id else None
        ticket_staff_pos = await self.bot.database.get_staff_position(interaction.guild.id, "Ticket Staff")
        ticket_staff_role = interaction.guild.get_role(int(ticket_staff_pos[0])) if ticket_staff_pos and ticket_staff_pos[0] else None

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, manage_messages=True)
        if ticket_staff_role:
            overwrites[ticket_staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

        try:
            name_fmt_row = await self.bot.database.get_ticket_channel_name_format(self.panel_id)
            fmt = name_fmt_row[0] if name_fmt_row and name_fmt_row[0] else "{button}-{dropdown}"
            
            clean_btn = self.button_label.lower().replace(' ', '-')
            clean_drop = dropdown_label.lower().replace(' ', '-')
            
            base_name = fmt.replace("{button}", clean_btn).replace("{dropdown}", clean_drop).lower().replace(' ', '-')
            channel_name = f"{base_name}-{interaction.user.name}"
            
            channel = await interaction.guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites, reason="Ticket creation")
            
            # Fetch custom in-channel message if set
            custom_msg = await self.bot.database.get_ticket_channel_message(self.panel_id)
            if custom_msg and (custom_msg[0] or custom_msg[1]):
                embed_title = custom_msg[0] or f"Ticket: {self.button_label} - {dropdown_label}"
                embed_desc = custom_msg[1] or f"Welcome {interaction.user.mention}! Support will be with you shortly."
            else:
                embed_title = f"Ticket: {self.button_label} - {dropdown_label}"
                embed_desc = f"Welcome {interaction.user.mention}! Support will be with you shortly."
            
            # Replace variables in title and description
            embed_title = embed_title.replace("{user}", interaction.user.name).replace("{button}", self.button_label).replace("{dropdown}", dropdown_label)
            embed_desc = embed_desc.replace("{user}", interaction.user.mention).replace("{button}", self.button_label).replace("{dropdown}", dropdown_label)
            
            embed = discord.Embed(title=embed_title, description=embed_desc, color=DEFAULT_COLOR)
            
            if ticket_staff_pos and ticket_staff_pos[0]:
                ping_text = f"<@&{ticket_staff_pos[0]}>"
            else:
                ping_roles = await self.bot.database.get_ticket_ping_roles(interaction.guild.id)
                ping_text = " ".join([f"<@&{r[0]}>" for r in ping_roles])
            
            msg = await channel.send(content=ping_text if ping_text else None, embed=embed, view=TicketControlView(self.bot))
            await msg.pin()
            
            selection_embed = discord.Embed(description=f"**Button Selected:** {self.button_label}\n**Category Selected:** {dropdown_label}", color=discord.Color.dark_theme())
            await channel.send(embed=selection_embed)
            
            await self.bot.database.create_ticket(ticket_id, interaction.guild.id, channel.id, interaction.user.id, selection, self.panel_id, msg.id)
            await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)
            await interaction.edit_original_response(view=None, content="Ticket opened.")
        except Exception as e:
            await interaction.response.send_message(f"Failed to create ticket: {e}", ephemeral=True)

class TicketPanelButton(discord.ui.Button):
    def __init__(self, button_id, label, emoji, bot, panel_id):
        super().__init__(label=label, emoji=emoji, custom_id=f"ticket_btn_{button_id}", style=discord.ButtonStyle.primary)
        self.button_id = button_id
        self.bot = bot
        self.panel_id = panel_id
        
    async def callback(self, interaction: discord.Interaction):
        options = await self.bot.database.get_ticket_options(self.panel_id)
        view = EphemeralDropdownView(options, self.bot, self.label, self.panel_id)
        await interaction.response.send_message("Please select a category:", view=view, ephemeral=True)

class TicketPanelView(discord.ui.View):
    def __init__(self, options, buttons, bot, panel_id):
        super().__init__(timeout=None)
        if not buttons:
            btn = discord.ui.Button(label="Support Tickets", emoji="🎫", style=discord.ButtonStyle.primary, custom_id=f"ticket_default_{panel_id}")
            async def default_callback(interaction: discord.Interaction):
                opts = await bot.database.get_ticket_options(panel_id)
                view = EphemeralDropdownView(opts, bot, "Support Tickets", panel_id)
                await interaction.response.send_message("Please select a category:", view=view, ephemeral=True)
            btn.callback = default_callback
            self.add_item(btn)
        else:
            for b in buttons:
                self.add_item(TicketPanelButton(b[0], b[1], b[2], bot, panel_id))

class PrioritySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Low Priority", value="low", emoji="🟢"),
            discord.SelectOption(label="Medium Priority", value="medium", emoji="🟡"),
            discord.SelectOption(label="High Priority", value="high", emoji="🔴")
        ]
        super().__init__(placeholder="Set Priority...", min_values=1, max_values=1, options=options, custom_id="ticket_priority_select")

    async def callback(self, interaction: discord.Interaction):
        ticket = await self.view.bot.database.get_ticket(interaction.channel.id)
        if not ticket or not ticket[3]:
            return await interaction.response.send_message("You must claim the ticket before setting priority.", ephemeral=True)
            
        if str(interaction.user.id) != str(ticket[3]):
            return await interaction.response.send_message("Only the staff member who claimed this ticket can change its priority.", ephemeral=True)

        level = self.values[0]
        emoji = "🟢" if level == "low" else "🟡" if level == "medium" else "🔴"
        
        name = interaction.channel.name
        for pre in ["low-", "med-", "high-"]:
            if name.startswith(pre):
                name = name[len(pre):]
        for e in ["🟢-", "🟡-", "🔴-", "🟢", "🟡", "🔴"]:
            if name.startswith(e):
                name = name[len(e):]
        
        short_level = "med" if level == "medium" else level
        await interaction.channel.edit(name=f"{emoji}-{name}")
        await interaction.response.send_message(f"Priority updated to {emoji} {level.capitalize()}.", ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(PrioritySelect())

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="ticket_close", emoji="🔒", row=1)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        ticket = await self.bot.database.get_ticket(interaction.channel.id)
        if not ticket:
            return await interaction.followup.send("This channel is not an active ticket in the database.", ephemeral=True)
            
        ticket_id, creator_id, status, claimed_by = ticket
        if interaction.user.id != int(creator_id) and not interaction.user.guild_permissions.manage_messages:
            return await interaction.followup.send("You don't have permission to close this ticket.", ephemeral=True)

        await self.bot.database.update_ticket_status(interaction.channel.id, "closed")
        
        messages = [message async for message in interaction.channel.history(limit=500, oldest_first=True)]
        
        html_content = await generate_transcript(interaction, messages, ticket_id)
        
        transcript_file = discord.File(io.BytesIO(html_content.encode('utf-8')), filename=f"transcript-{ticket_id}.html")
        try: await interaction.user.send(f"Transcript for closed ticket `{ticket_id}`", file=transcript_file)
        except: pass
        try:
            creator = interaction.guild.get_member(int(creator_id)) or await interaction.guild.fetch_member(int(creator_id))
            if creator and creator.id != interaction.user.id:
                transcript_file.seek(0)
                await creator.send(f"Your ticket `{ticket_id}` in {interaction.guild.name} has been closed. Transcript attached.", file=transcript_file)
        except: pass

        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="ticket_claim", emoji="🙋‍♂️", row=1)
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
            
        ticket = await self.bot.database.get_ticket(interaction.channel.id)
        if ticket and str(ticket[1]) == str(interaction.user.id):
            return await interaction.response.send_message("You cannot claim a ticket that you created yourself.", ephemeral=True)
            
        claimed_by = ticket[3] if ticket else None
        
        if claimed_by and str(claimed_by) == str(interaction.user.id):
            # Unclaim logic
            await self.bot.database.update_ticket_claim(interaction.channel.id, None)
            await interaction.channel.set_permissions(interaction.user, overwrite=None)
            
            button.label = "Claim"
            button.style = discord.ButtonStyle.green
            await interaction.message.edit(view=self)
            
            await interaction.response.send_message(f"Ticket unclaimed by {interaction.user.mention}.")
        elif claimed_by and str(claimed_by) != "None":
            return await interaction.response.send_message(f"This ticket is already claimed by <@{claimed_by}>.", ephemeral=True)
        else:
            # Claim logic
            await self.bot.database.update_ticket_claim(interaction.channel.id, interaction.user.id)
            await interaction.channel.set_permissions(interaction.user, read_messages=True, send_messages=True, manage_messages=True)
            
            button.label = "Unclaim"
            button.style = discord.ButtonStyle.danger
            await interaction.message.edit(view=self)
            
            await interaction.response.send_message(f"Ticket claimed by {interaction.user.mention}.")

    @discord.ui.button(label="Archive", style=discord.ButtonStyle.secondary, custom_id="ticket_archive", emoji="📁", row=1)
    async def archive_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Only admins can archive tickets.", ephemeral=True)
        await self.bot.database.update_ticket_status(interaction.channel.id, "archived")
        for target, overwrite in interaction.channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.guild_permissions.manage_messages:
                overwrite.read_messages = False
                await interaction.channel.set_permissions(target, overwrite=overwrite)
        await interaction.response.send_message("Ticket archived.")

class TicketPanelDeleteModal(discord.ui.Modal, title='Delete Ticket Panel'):
    panel_id_input = discord.ui.TextInput(
        label='Panel ID to delete', style=discord.TextStyle.short, required=True, max_length=10,
        placeholder='Enter the ID shown above...'
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        target_id = self.panel_id_input.value.strip()
        panels = await self.bot.database.get_ticket_panels(interaction.guild.id)
            
        # Try to delete the original message if possible
        for p in panels:
            if p[0] == target_id:
                try:
                    channel = interaction.guild.get_channel(int(p[1]))
                    if channel:
                        msg = await channel.fetch_message(int(p[2]))
                        await msg.delete()
                except Exception:
                    pass
                    
        await self.bot.database.delete_ticket_panel(target_id, interaction.guild.id)
        await interaction.response.send_message(f"Panel `{target_id}` deleted successfully from database and channel (if it existed).", ephemeral=True)

class TicketPanelListView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot

    @discord.ui.button(label="Delete Panel", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketPanelDeleteModal(self.bot))

class Tickets(commands.Cog, name="tickets"):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(TicketControlView(self.bot))
        # No need to pre-load TicketPanelViews here anymore because on_interaction handles them dynamically!
        # This guarantees they always fetch no matter what.

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component and not interaction.command:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("ticket_btn_") or custom_id.startswith("ticket_default_"):
                # Always fetch panel no matter what using message_id
                try:
                    panels = await self.bot.database.connection.execute("SELECT panel_id FROM ticket_panels WHERE message_id=?", (str(interaction.message.id),))
                    async with panels as cursor:
                        res = await cursor.fetchone()
                    if not res:
                        # Fallback just in case they clicked a really old unregistered panel
                        return await interaction.response.send_message("This ticket panel is no longer active in the database.", ephemeral=True)
                    
                    panel_id = res[0]
                    options = await self.bot.database.get_ticket_options(panel_id)
                    
                    button_label = "Support Tickets"
                    if custom_id.startswith("ticket_btn_"):
                        btn_id = custom_id.replace("ticket_btn_", "")
                        buttons = await self.bot.database.get_ticket_buttons(panel_id)
                        btn_data = next((b for b in buttons if b[0] == btn_id), None)
                        if btn_data:
                            button_label = btn_data[1]
                    
                    view = EphemeralDropdownView(options, self.bot, button_label, panel_id)
                    await interaction.response.send_message("Please select a category:", view=view, ephemeral=True)
                except Exception as e:
                    self.bot.logger.error(f"Error handling dynamic ticket button: {e}")

    @commands.hybrid_group(name="ticket", description="Manage the ticket system.")
    async def ticket(self, context: Context) -> None:
        if context.invoked_subcommand is None:
            await context.send("Invalid subcommand.", ephemeral=True)

    @ticket.command(name="spawn", description="Spawn a new ticket panel.")
    @app_commands.describe(panel_id="Optional: Re-spawn an existing panel by ID if it was accidentally deleted.")
    @commands.has_permissions(administrator=True)
    async def spawn_panel(self, context: Context, panel_id: str = None) -> None:
        await context.interaction.response.send_message("Spawning panel...", ephemeral=True)
        
        options = []
        buttons = []
        
        embed_title = "Support Tickets"
        embed_desc = "Click the button below to open a ticket."
        
        if panel_id:
            panels = await self.bot.database.get_ticket_panels(context.guild.id)
            if not any(p[0] == panel_id for p in panels):
                return await context.interaction.edit_original_response(content=f"Error: Panel ID `{panel_id}` does not exist in this server.")
            
            options = await self.bot.database.get_ticket_options(panel_id)
            buttons = await self.bot.database.get_ticket_buttons(panel_id)
            
            panel_msg = await self.bot.database.get_ticket_panel_message(panel_id)
            if panel_msg and (panel_msg[0] or panel_msg[1]):
                embed_title = panel_msg[0] or embed_title
                embed_desc = panel_msg[1] or embed_desc
        else:
            panel_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
        embed = discord.Embed(title=embed_title, description=embed_desc, color=DEFAULT_COLOR)
        
        view = TicketPanelView(options, buttons, self.bot, panel_id)
        msg = await context.channel.send(embed=embed, view=view)
        await self.bot.database.add_ticket_panel(panel_id, context.guild.id, context.channel.id, msg.id)
        
        await context.interaction.edit_original_response(content=f"Panel spawned! ID: `{panel_id}`. Use `/ticket edit {panel_id}` to customize it.")

    @ticket.command(name="edit", description="Open the Admin Dashboard to customize a panel.")
    @app_commands.describe(panel_id="The ID of the panel to edit.")
    @commands.has_permissions(administrator=True)
    async def ticket_edit(self, context: Context, panel_id: str) -> None:
        panels = await self.bot.database.get_ticket_panels(context.guild.id)
        
        # Check if panel exists in DB
        panel_data = next((p for p in panels if p[0] == panel_id), None)
        if not panel_data:
            # If not in ticket_panels, they can still open the dashboard (msg=None)
            embed = discord.Embed(title="Ticket Admin Dashboard", description=f"Editing Panel `{panel_id}` (No message linked). Use the buttons below to customize it.", color=0x00FF00)
            view = AdminDashboardView(self.bot, panel_id, None)
            return await context.send(embed=embed, view=view, ephemeral=True)
            
        msg = None
        try:
            channel = context.guild.get_channel(int(panel_data[1]))
            if channel:
                msg = await channel.fetch_message(int(panel_data[2]))
        except Exception:
            pass # Message or channel was deleted, but we still open the dashboard!
            
        embed = discord.Embed(title="Ticket Admin Dashboard", description=f"Editing Panel `{panel_id}`. Use the buttons below to customize it.", color=0x00FF00)
        view = AdminDashboardView(self.bot, panel_id, msg)
        await context.send(embed=embed, view=view, ephemeral=True)

    @ticket.command(name="user", description="Add or remove a user from this ticket.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.choices(action=[app_commands.Choice(name="Add", value="add"), app_commands.Choice(name="Remove", value="remove")])
    async def manage_user(self, context: Context, action: app_commands.Choice[str], user: discord.Member) -> None:
        ticket = await self.bot.database.get_ticket(context.channel.id)
        if not ticket:
            return await context.send("This is not a ticket channel.", ephemeral=True)
            
        if action.value == "remove" and user.id == int(ticket[1]):
            return await context.send("You cannot remove the original ticket creator.", ephemeral=True)
            
        if action.value == "add":
            await context.channel.set_permissions(user, read_messages=True, send_messages=True)
            await context.send(f"Added {user.mention} to the ticket.")
        else:
            await context.channel.set_permissions(user, read_messages=False, send_messages=False)
            await context.send(f"Removed {user.mention} from the ticket.")

    @ticket.command(name="list", description="List ticket info.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.choices(type=[
        app_commands.Choice(name="Panels", value="panels"),
        app_commands.Choice(name="Active Tickets", value="active"),
        app_commands.Choice(name="Handled Tickets", value="handled")
    ])
    async def list_tickets(self, context: Context, type: app_commands.Choice[str]) -> None:
        if type.value == "panels":
            panels = await self.bot.database.get_ticket_panels(context.guild.id)
            if not panels: return await context.send("No panels found.", ephemeral=True)
            embed = discord.Embed(title="Ticket Panels", description=f"Found {len(panels)} panel(s).", color=DEFAULT_COLOR)
            for p in panels:
                embed.add_field(name=f"ID: {p[0]}", value=f"Channel: <#{p[1]}>", inline=False)
            view = TicketPanelListView(self.bot)
            await context.send(embed=embed, view=view, ephemeral=True)
            
        elif type.value == "active":
            tickets = await self.bot.database.get_all_active_tickets(context.guild.id)
            if not tickets: return await context.send("No active tickets.", ephemeral=True)
            embed = discord.Embed(title="Active Tickets", description=f"Found {len(tickets)} active ticket(s).", color=DEFAULT_COLOR)
            for t in tickets[:25]:
                embed.add_field(name=f"Ticket {t[0]}", value=f"Channel: <#{t[1]}>\nCreator: <@{t[2]}>", inline=False)
            await context.send(embed=embed, ephemeral=True)
            
        elif type.value == "handled":
            count = await self.bot.database.get_handled_tickets_count(context.guild.id)
            embed = discord.Embed(title="Handled Tickets", description=f"Total tickets handled: **{count}**", color=DEFAULT_COLOR)
            await context.send(embed=embed, ephemeral=True)

    @ticket.group(name="role", description="Manage roles that are pinged when a ticket is created.")
    @commands.has_permissions(administrator=True)
    async def ticket_role(self, context: Context) -> None:
        if context.invoked_subcommand is None:
            await context.send("Invalid subcommand. Use `/ticket role add`, `/ticket role remove`, or `/ticket role list`.", ephemeral=True)

    @ticket_role.command(name="add", description="Add a role to the ticket ping list.")
    @commands.has_permissions(administrator=True)
    async def role_add(self, context: Context, role: discord.Role) -> None:
        await self.bot.database.add_ticket_ping_role(context.guild.id, role.id)
        embed = discord.Embed(title="✅ Role Added", description=f"Successfully added {role.mention} to the ticket ping list.", color=DEFAULT_COLOR)
        await context.send(embed=embed)

    @ticket_role.command(name="remove", description="Remove a role from the ticket ping list.")
    @commands.has_permissions(administrator=True)
    async def role_remove(self, context: Context, role: discord.Role) -> None:
        await self.bot.database.remove_ticket_ping_role(context.guild.id, role.id)
        embed = discord.Embed(title="❌ Role Removed", description=f"Successfully removed {role.mention} from the ticket ping list.", color=DEFAULT_COLOR)
        await context.send(embed=embed)

    @ticket_role.command(name="list", description="List all roles that are pinged when a ticket is created.")
    @commands.has_permissions(administrator=True)
    async def role_list(self, context: Context) -> None:
        roles = await self.bot.database.get_ticket_ping_roles(context.guild.id)
        if not roles:
            embed = discord.Embed(title="📋 Ticket Ping Roles", description="There are currently no ping roles configured.", color=DEFAULT_COLOR)
            return await context.send(embed=embed)
            
        role_mentions = "\n".join([f"<@&{r[0]}>" for r in roles])
        embed = discord.Embed(title="📋 Ticket Ping Roles", description=role_mentions, color=DEFAULT_COLOR)
        await context.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(Tickets(bot))
