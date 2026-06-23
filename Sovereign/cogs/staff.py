import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord import ui
from utils.colors import DEFAULT_COLOR
import datetime

DEFAULT_POSITIONS = [
    "Owner",
    "Co-Owner",
    "Head Administrator",
    "Administrator",
    "Head Moderator",
    "Senior Moderator",
    "Moderator",
    "Junior Moderator",
    "Trial Moderator",
    "Ticket Staff",
    "Engagement Administrator"
]
STRIKE_LIMIT = 3

# ── Modals ────────────────────────────────────────────────────────────────────
class PositionCreateModal(discord.ui.Modal, title="Create Staff Position"):
    pos_name = discord.ui.TextInput(label="Position Name", max_length=50, placeholder="e.g. Server Manager")
    rank = discord.ui.TextInput(label="Rank (Lower = Higher Auth, 999 = Unranked)", max_length=4, default="999")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            r = int(self.rank.value)
        except ValueError:
            r = 999
            
        if self.pos_name.value in DEFAULT_POSITIONS:
            await interaction.response.send_message(f"❌ `{self.pos_name.value}` is a default position.", ephemeral=True)
            return
            
        await interaction.client.database.add_staff_position(interaction.guild.id, self.pos_name.value, None, True, r)
        await interaction.response.send_message(f"✅ Position `{self.pos_name.value}` created with rank #{r}!\nTo bind a role, use the Manage Position dropdown.", ephemeral=True)

class PositionRenameModal(discord.ui.Modal, title="Rename Staff Position"):
    new_name = discord.ui.TextInput(label="New Position Name", max_length=50)

    def __init__(self, old_name: str):
        super().__init__()
        self.old_name = old_name
        self.new_name.default = old_name

    async def on_submit(self, interaction: discord.Interaction):
        if self.new_name.value in DEFAULT_POSITIONS:
            await interaction.response.send_message(f"❌ `{self.new_name.value}` is a default position name.", ephemeral=True)
            return
        await interaction.client.database.rename_staff_position(interaction.guild.id, self.old_name, self.new_name.value)
        await interaction.response.send_message(f"✅ Renamed `{self.old_name}` to `{self.new_name.value}`.", ephemeral=True)

class PositionRankModal(discord.ui.Modal, title="Set Position Rank"):
    rank = discord.ui.TextInput(label="Rank (Lower = Higher Auth, 999 = Unranked)", max_length=4)

    def __init__(self, pos_name: str):
        super().__init__()
        self.pos_name = pos_name

    async def on_submit(self, interaction: discord.Interaction):
        try:
            r = int(self.rank.value)
        except ValueError:
            r = 999
        await interaction.client.database.edit_staff_position_rank(interaction.guild.id, self.pos_name, r)
        await interaction.response.send_message(f"✅ Rank for `{self.pos_name}` set to #{r}.", ephemeral=True)

class SayModal(discord.ui.Modal, title="Bot Message Editor"):
    message_input = discord.ui.TextInput(
        label="Message Content",
        style=discord.TextStyle.paragraph,
        placeholder="Type the message you want the bot to say. You can use full formatting here...",
        required=True,
        max_length=4000
    )

    def __init__(self, use_embed: bool):
        super().__init__()
        self.use_embed = use_embed

    async def on_submit(self, interaction: discord.Interaction):
        import os
        owners = os.getenv("OWNERS", "")
        is_owner = str(interaction.user.id) in owners.split(",")
        
        content = self.message_input.value
        
        if self.use_embed:
            from utils.colors import DEFAULT_COLOR
            embed = discord.Embed(description=content, color=DEFAULT_COLOR)
            if is_owner:
                embed.set_footer(text="by owner 👑")
            await interaction.channel.send(embed=embed)
        else:
            if is_owner:
                content += "\n\n-*by owner 👑*"
            await interaction.channel.send(content)
        await interaction.response.send_message("Message sent successfully!", ephemeral=True)

# ── Select Views (Role / Channel) ──────────────────────────────────────────────
class RoleSelect(discord.ui.RoleSelect):
    def __init__(self, action: str, pos_name: str = None):
        super().__init__(placeholder="Select a role...", min_values=1, max_values=1)
        self.action = action
        self.pos_name = pos_name

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        if self.action == "default_role":
            await interaction.client.database.set_staff_default_role(interaction.guild.id, str(role.id), True)
            await interaction.response.send_message(f"✅ Default staff role set to {role.mention}.", ephemeral=True)
        elif self.action == "bind_role":
            await interaction.client.database.edit_staff_position_role(interaction.guild.id, self.pos_name, str(role.id))
            await interaction.response.send_message(f"✅ Role {role.mention} bound to `{self.pos_name}`.", ephemeral=True)
        self.view.stop()

class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Select a text channel...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        await interaction.client.database.set_staff_updates_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"✅ Staff updates channel set to {channel.mention}.", ephemeral=True)
        self.view.stop()

class TempSelectView(discord.ui.View):
    def __init__(self, item: discord.ui.Item):
        super().__init__(timeout=60)
        self.add_item(item)

# ── Interactive Action Select ──────────────────────────────────────────────────
class ManagePositionSelect(discord.ui.Select):
    def __init__(self, positions: list):
        options = [discord.SelectOption(label=p[0], description="Custom" if p[2] else "Default", value=p[0]) for p in positions]
        super().__init__(placeholder="Manage a position...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        pos_name = self.values[0]
        view = PositionActionView(pos_name)
        await interaction.response.send_message(f"Managing **{pos_name}**:", view=view, ephemeral=True)

class PositionActionView(discord.ui.View):
    def __init__(self, pos_name: str):
        super().__init__(timeout=120)
        self.pos_name = pos_name
        if pos_name in DEFAULT_POSITIONS:
            self.rename_btn.disabled = True
            self.delete_btn.disabled = True

    @discord.ui.button(label="Rename", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def rename_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PositionRenameModal(self.pos_name))

    @discord.ui.button(label="Set Rank", style=discord.ButtonStyle.secondary, emoji="🔢")
    async def rank_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PositionRankModal(self.pos_name))

    @discord.ui.button(label="Bind Role", style=discord.ButtonStyle.primary, emoji="🔗")
    async def role_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = TempSelectView(RoleSelect(action="bind_role", pos_name=self.pos_name))
        await interaction.response.send_message("Select a role to bind:", view=view, ephemeral=True)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.client.database.remove_staff_position(interaction.guild.id, self.pos_name)
        await interaction.response.send_message(f"✅ Position `{self.pos_name}` deleted.", ephemeral=True)
        self.stop()

# ── Components V2 Dashboard ────────────────────────────────────────────────────
class StaffDashboardV2(ui.LayoutView):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
        self.active_tab = "roster"

    async def _handle_tab_roster(self, interaction: discord.Interaction):
        self.active_tab = "roster"
        await self.update_ui(interaction)

    async def _handle_tab_positions(self, interaction: discord.Interaction):
        self.active_tab = "positions"
        await self.update_ui(interaction)

    async def _handle_tab_settings(self, interaction: discord.Interaction):
        self.active_tab = "settings"
        await self.update_ui(interaction)

    async def _handle_create_pos(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PositionCreateModal())

    async def _handle_set_role(self, interaction: discord.Interaction):
        view = TempSelectView(RoleSelect(action="default_role"))
        await interaction.response.send_message("Select a fallback staff role:", view=view, ephemeral=True)

    async def _handle_set_channel(self, interaction: discord.Interaction):
        view = TempSelectView(ChannelSelect())
        await interaction.response.send_message("Select the staff updates channel:", view=view, ephemeral=True)

    async def _handle_refresh(self, interaction: discord.Interaction):
        await self.update_ui(interaction)

    async def build(self):
        self.clear_items()
        
        # --- TAB NAVIGATION ---
        tabs_row = ui.ActionRow()
        btn_roster = ui.Button(label="Roster", emoji="📋", style=discord.ButtonStyle.primary if self.active_tab == "roster" else discord.ButtonStyle.secondary)
        btn_roster.callback = self._handle_tab_roster
        btn_pos = ui.Button(label="Positions", emoji="🛡️", style=discord.ButtonStyle.primary if self.active_tab == "positions" else discord.ButtonStyle.secondary)
        btn_pos.callback = self._handle_tab_positions
        btn_set = ui.Button(label="Settings", emoji="⚙️", style=discord.ButtonStyle.primary if self.active_tab == "settings" else discord.ButtonStyle.secondary)
        btn_set.callback = self._handle_tab_settings
        
        btn_refresh = ui.Button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.secondary)
        btn_refresh.callback = self._handle_refresh
        
        tabs_row.add_item(btn_roster)
        tabs_row.add_item(btn_pos)
        tabs_row.add_item(btn_set)
        tabs_row.add_item(btn_refresh)
        
        self.add_item(tabs_row)
        self.add_item(ui.Separator())

        # --- DYNAMIC CONTENT ---
        container = ui.Container(accent_color=DEFAULT_COLOR)
        
        if self.active_tab == "roster":
            container.add_item(ui.TextDisplay("# 📋 Staff Roster"))
            async with self.bot.database.connection.execute("SELECT user_id, position_name FROM staff_members WHERE server_id=?", (str(self.guild_id),)) as cursor:
                staff_data = await cursor.fetchall()
            
            if not staff_data:
                container.add_item(ui.TextDisplay("There are currently no staff members registered."))
            else:
                position_map = {}
                for uid, pos in staff_data:
                    pos_name = pos if pos else "Default Staff"
                    position_map.setdefault(pos_name, []).append(f"<@{uid}>")
                
                for pos, members in position_map.items():
                    container.add_item(ui.TextDisplay(f"**{pos}**\n" + "\n".join(members)))
                    
        elif self.active_tab == "positions":
            container.add_item(ui.TextDisplay("# 🛡️ Staff Positions & Hierarchy\nPositions ordered by rank (lower number = higher authority)."))
            
            all_positions = await self.bot.database.get_all_staff_positions(self.guild_id) or []
            db_map = {p[0]: (p[1], p[2], p[3]) for p in all_positions}

            default_entries, custom_entries = [], []
            for dp in DEFAULT_POSITIONS:
                info = db_map.get(dp)
                rank    = info[2] if info and info[2] is not None else 999
                role_id = info[0] if info else None
                default_entries.append((rank, dp, role_id))
            
            custom_entries = [(p[3], p[0], p[1]) for p in all_positions if p[2]]
            default_entries.sort(key=lambda x: x[0])
            custom_entries.sort(key=lambda x: x[0])

            def build_str(entries):
                res = ""
                for rank, name, role_id in entries:
                    role_mention = f"<@&{role_id}>" if role_id else "*Unbound*"
                    rank_label   = f"`#{rank}`" if rank != 999 else "`—`"
                    res += f"{rank_label} **{name}** — {role_mention}\n"
                return res or "*None*"

            container.add_item(ui.TextDisplay("### 🛡️ Default Positions\n" + build_str(default_entries)))
            container.add_item(ui.TextDisplay("### 🔧 Custom Positions\n" + build_str(custom_entries)))
            
        elif self.active_tab == "settings":
            container.add_item(ui.TextDisplay("# ⚙️ Staff Settings"))
            channel_id = await self.bot.database.get_staff_updates_channel(self.guild_id)
            ch_desc = f"<#{channel_id}>" if channel_id else "*Not configured*"
            
            default_config = await self.bot.database.get_staff_default_role(self.guild_id)
            role_desc = f"<@&{default_config[0]}>" if default_config and default_config[0] else "*Not configured*"
            
            container.add_item(ui.TextDisplay(f"**📢 Updates Channel**\n{ch_desc}"))
            container.add_item(ui.TextDisplay(f"**🦺 Fallback Staff Role**\n{role_desc}"))

        self.add_item(container)
        self.add_item(ui.Separator())

        # --- ACTIONS ---
        if self.active_tab == "positions":
            act_row1 = ui.ActionRow()
            btn_create = ui.Button(label="Create Position", emoji="➕", style=discord.ButtonStyle.success)
            btn_create.callback = self._handle_create_pos
            act_row1.add_item(btn_create)
            self.add_item(act_row1)

            act_row2 = ui.ActionRow()
            all_pos = await self.bot.database.get_all_staff_positions(self.guild_id) or []
            all_names = DEFAULT_POSITIONS.copy()
            for p in all_pos:
                if p[0] not in all_names:
                    all_names.append(p[0])
            
            options_data = []
            for name in all_names:
                is_cust = False
                for p in all_pos:
                    if p[0] == name:
                        is_cust = bool(p[2])
                        break
                options_data.append((name, None, is_cust, 999))
            
            if len(options_data) > 25:
                options_data = options_data[:25]
            act_row2.add_item(ManagePositionSelect(options_data))
            self.add_item(act_row2)

        elif self.active_tab == "settings":
            act_row = ui.ActionRow()
            btn_role = ui.Button(label="Set Default Role", emoji="🏷️", style=discord.ButtonStyle.secondary)
            btn_role.callback = self._handle_set_role
            btn_channel = ui.Button(label="Set Updates Channel", emoji="📢", style=discord.ButtonStyle.secondary)
            btn_channel.callback = self._handle_set_channel
            act_row.add_item(btn_role)
            act_row.add_item(btn_channel)
            self.add_item(act_row)

    async def update_ui(self, interaction: discord.Interaction):
        await self.build()
        if interaction:
            await interaction.response.edit_message(view=self)

# ── Cog ───────────────────────────────────────────────────────────────────────
class Staff(commands.Cog, name="staff"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.weekly_stats_task.start()

    def cog_unload(self):
        self.weekly_stats_task.cancel()

    staff_group = app_commands.Group(name="staff", description="Staff management commands", default_permissions=discord.Permissions(administrator=True))

    async def send_staff_update(self, guild: discord.Guild, embed: discord.Embed):
        channel_id = await self.bot.database.get_staff_updates_channel(guild.id)
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except Exception:
                    pass

    async def position_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        custom_positions = await self.bot.database.get_all_staff_positions(interaction.guild.id)
        positions = DEFAULT_POSITIONS.copy()
        if custom_positions:
            for p in custom_positions:
                if p[0] not in positions:
                    positions.append(p[0])
        return [app_commands.Choice(name=p, value=p) for p in positions if current.lower() in p.lower()][:25]

    # ── /staff edit (Dashboard) ────────────────────────────────────────────────
    @staff_group.command(name="edit", description="Open the interactive staff management dashboard.")
    async def staff_edit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=False)
        view = StaffDashboardV2(self.bot, interaction.guild.id)
        await view.build()
        # V2 layout views are sent directly, with no embeds or content needed!
        # Discord's Interaction API rejects Components V2 in direct responses, so we send it to the channel.
        message = await interaction.channel.send(view=view)
        await interaction.delete_original_response()

    # ── /staff add ─────────────────────────────────────────────────────────────
    @staff_group.command(name="add", description="Add a staff member. Auto-creates position and binds role if provided!")
    @app_commands.autocomplete(position=position_autocomplete)
    @app_commands.describe(
        user="The user to add to the staff team",
        position="The position to assign (e.g., Administrator, Moderator)",
        reason="The reason for adding this staff member"
    )
    async def staff_add(self, interaction: discord.Interaction, user: discord.Member, position: str = None, reason: str = "Not specified") -> None:
        await interaction.response.defer(ephemeral=False)
        roles_to_give = []

        default_config = await self.bot.database.get_staff_default_role(interaction.guild.id)
        default_role = None
        always_apply = True
        if default_config:
            default_role = interaction.guild.get_role(int(default_config[0]))
            always_apply = bool(default_config[1])

        pos_role = None
        if position:
            is_custom = position not in DEFAULT_POSITIONS
            existing_pos = await self.bot.database.get_staff_position(interaction.guild.id, position)
            if existing_pos and existing_pos[0]:
                pos_role = interaction.guild.get_role(int(existing_pos[0]))
            elif not existing_pos:
                await self.bot.database.add_staff_position(interaction.guild.id, position, None, is_custom, 999)

        if pos_role:
            roles_to_give.append(pos_role)
            if default_role and always_apply:
                roles_to_give.append(default_role)
        elif default_role:
            roles_to_give.append(default_role)

        await self.bot.database.add_staff_member(user.id, interaction.guild.id, position)

        embed = discord.Embed(title="🧑‍💼 Staff Member Added", color=DEFAULT_COLOR, timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="User",     value=user.mention,                          inline=True)
        embed.add_field(name="Position", value=position if position else "Default Staff", inline=True)
        embed.add_field(name="Added by", value=interaction.user.mention,              inline=True)
        embed.add_field(name="Reason",   value=reason,                                inline=False)

        if roles_to_give:
            assigned, failed = [], []
            for r in set(roles_to_give):
                try:
                    await user.add_roles(r)
                    assigned.append(r.mention)
                except discord.Forbidden:
                    failed.append(r.mention)
            if assigned: embed.add_field(name="Roles Assigned", value="\n".join(assigned), inline=False)
            if failed:   embed.add_field(name="⚠️ Failed (Check Hierarchy)", value="\n".join(failed), inline=False)
        elif not position and not default_role:
            embed.set_footer(text="No roles given. Set a default role via /staff edit settings")

        await interaction.followup.send(embed=embed)
        await self.send_staff_update(interaction.guild, embed)

    # ── /staff remove ──────────────────────────────────────────────────────────
    @staff_group.command(name="remove", description="Remove a user from the staff team.")
    @app_commands.describe(
        user="The staff member to remove",
        reason="The reason for removing this staff member"
    )
    async def staff_remove(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Not specified") -> None:
        await interaction.response.defer(ephemeral=False)
        is_staff = await self.bot.database.is_staff(user.id, interaction.guild.id)
        if not is_staff:
            embed = discord.Embed(title="❌ Error", description=f"{user.mention} is not currently a staff member.", color=discord.Color.red())
            return await interaction.followup.send(embed=embed)

        await self.bot.database.remove_staff_member(user.id, interaction.guild.id)
        embed = discord.Embed(title="👋 Staff Member Removed", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="User",       value=user.mention,              inline=True)
        embed.add_field(name="Removed by", value=interaction.user.mention,  inline=True)
        embed.add_field(name="Reason",     value=reason,                    inline=False)
        await interaction.followup.send(embed=embed)
        await self.send_staff_update(interaction.guild, embed)

    # ── /staff strike ──────────────────────────────────────────────────────────
    @staff_group.command(name="strike", description="Issue a strike to a staff member. 3 strikes = automatic demotion.")
    @app_commands.describe(
        user="The staff member to strike",
        reason="The reason for the strike"
    )
    async def staff_strike(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Not specified") -> None:
        await interaction.response.defer(ephemeral=False)

        is_staff = await self.bot.database.is_staff(user.id, interaction.guild.id, member=user)
        if not is_staff:
            embed = discord.Embed(title="❌ Error", description=f"{user.mention} is not a staff member.", color=discord.Color.red())
            return await interaction.followup.send(embed=embed, ephemeral=True)

        async with self.bot.database.connection.execute(
            "SELECT position_name FROM staff_members WHERE server_id=? AND user_id=?",
            (str(interaction.guild.id), str(user.id))
        ) as cur:
            target_row = await cur.fetchone()
        async with self.bot.database.connection.execute(
            "SELECT position_name FROM staff_members WHERE server_id=? AND user_id=?",
            (str(interaction.guild.id), str(interaction.user.id))
        ) as cur:
            striker_row = await cur.fetchone()

        target_pos  = target_row[0]  if target_row  else None
        striker_pos = striker_row[0] if striker_row else None

        target_rank  = await self.bot.database.get_staff_position_rank(interaction.guild.id, target_pos)  if target_pos  else 999
        striker_rank = await self.bot.database.get_staff_position_rank(interaction.guild.id, striker_pos) if striker_pos else 999

        if striker_rank >= target_rank:
            embed = discord.Embed(
                title="❌ Hierarchy Error",
                description=f"You cannot strike {user.mention} — they hold an equal or higher rank than you.",
                color=discord.Color.red()
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        total_strikes = await self.bot.database.add_staff_strike(interaction.guild.id, user.id, interaction.user.id, reason)

        strike_icons = "🟥" * total_strikes + "⬜" * (STRIKE_LIMIT - total_strikes)
        embed = discord.Embed(
            title="⚠️ Staff Strike Issued",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Staff Member",  value=user.mention,              inline=True)
        embed.add_field(name="Issued by",     value=interaction.user.mention,  inline=True)
        embed.add_field(name="Reason",        value=reason,                    inline=False)
        embed.add_field(name="Strike Count",  value=f"{strike_icons}  ({total_strikes}/{STRIKE_LIMIT})", inline=False)

        if total_strikes >= STRIKE_LIMIT:
            embed.title = "🚨 Staff Demoted — 3 Strikes Reached"
            embed.color = discord.Color.red()
            embed.description = f"{user.mention} has been **automatically demoted** from the staff team after reaching {STRIKE_LIMIT} strikes."

            staff_positions = await self.bot.database.get_all_staff_positions(interaction.guild.id)
            staff_role_ids = set()
            for pos in staff_positions:
                if pos[1] and str(pos[1]).lower() != 'none':
                    staff_role_ids.add(int(pos[1]))
            default_cfg = await self.bot.database.get_staff_default_role(interaction.guild.id)
            if default_cfg and default_cfg[0]:
                staff_role_ids.add(int(default_cfg[0]))

            roles_removed = []
            for rid in staff_role_ids:
                role = interaction.guild.get_role(rid)
                if role and role in user.roles:
                    try:
                        await user.remove_roles(role, reason="3-strike auto-demotion")
                        roles_removed.append(role.mention)
                    except discord.Forbidden:
                        pass

            await self.bot.database.remove_staff_member(user.id, interaction.guild.id)
            await self.bot.database.clear_staff_strikes(interaction.guild.id, user.id)

            if roles_removed:
                embed.add_field(name="Roles Removed", value="\n".join(roles_removed), inline=False)
            embed.set_footer(text="This user can be re-added to staff with /staff add")

        await interaction.followup.send(embed=embed)
        await self.send_staff_update(interaction.guild, embed)

    @staff_group.command(
        name="say",
        description="Opens a modal to make the bot say anything you want.",
    )
    async def say(self, context: Context) -> None:
        """
        Opens a modal to make the bot say anything you want.

        :param context: The hybrid command context.
        """
        if context.interaction:
            await context.interaction.response.send_modal(SayModal(use_embed=False))
        else:
            await context.send("Please use this as a slash command (`/staff say`) to open the formatting modal.")

    @staff_group.command(
        name="embed",
        description="Opens a modal to make the bot say anything you want within an embed.",
    )
    async def embed(self, context: Context) -> None:
        """
        Opens a modal to make the bot say anything you want, but using embeds.

        :param context: The hybrid command context.
        """
        if context.interaction:
            await context.interaction.response.send_modal(SayModal(use_embed=True))
        else:
            await context.send("Please use this as a slash command (`/staff embed`) to open the formatting modal.")

    # ── Weekly mod stats task ──────────────────────────────────────────────────
    @tasks.loop(time=datetime.time(hour=0, minute=0))
    async def weekly_stats_task(self):
        if datetime.datetime.utcnow().weekday() != 0:
            return

        for guild in self.bot.guilds:
            channel_id = await self.bot.database.get_staff_updates_channel(guild.id)
            if not channel_id:
                continue
            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            stats = await self.bot.database.get_weekly_mod_stats(guild.id)
            if not stats:
                continue

            mod_stats = {}
            for moderator_id, action_type, count in stats:
                if moderator_id not in mod_stats:
                    mod_stats[moderator_id] = {}
                mod_stats[moderator_id][action_type] = count

            embed = discord.Embed(
                title="📊 Weekly Moderation Stats",
                description="Here's a summary of moderation actions taken in the past 7 days.",
                color=DEFAULT_COLOR,
                timestamp=discord.utils.utcnow()
            )

            for mod_id, actions in mod_stats.items():
                total = sum(actions.values())
                lines = "\n".join(f"• **{atype.capitalize()}**: {cnt}" for atype, cnt in sorted(actions.items()))
                lines += f"\n**Total: {total}**"
                embed.add_field(name=f"<@{mod_id}>", value=lines, inline=True)

            embed.set_footer(text="Stats reset every Monday")
            try:
                await channel.send(embed=embed)
            except Exception:
                pass

    @weekly_stats_task.before_loop
    async def before_weekly_stats(self):
        await self.bot.wait_until_ready()

async def setup(bot) -> None:
    try:
        await bot.database.connection.execute("ALTER TABLE staff_positions ADD COLUMN rank INTEGER DEFAULT 999")
        await bot.database.connection.commit()
    except Exception:
        pass  # Column already exists
    await bot.add_cog(Staff(bot))
