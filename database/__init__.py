"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.5.0
"""

import aiosqlite
"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.5.0
"""

import aiosqlite


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def add_warn(
        self, user_id: int, server_id: int, moderator_id: int, reason: str
    ) -> int:
        """
        This function will add a warn to the database.

        :param user_id: The ID of the user that should be warned.
        :param reason: The reason why the user should be warned.
        """
        rows = await self.connection.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result is not None else 1
            await self.connection.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (
                    warn_id,
                    user_id,
                    server_id,
                    moderator_id,
                    reason,
                ),
            )
            await self.connection.commit()
            return warn_id

    async def add_tempban(self, user_id: int, server_id: int, expires_at: int) -> None:
        """
        Adds a tempban to the database.
        """
        await self.connection.execute(
            "INSERT OR REPLACE INTO tempbans(user_id, server_id, expires_at) VALUES (?, ?, ?)",
            (str(user_id), str(server_id), expires_at)
        )
        await self.connection.commit()

    async def remove_warn(self, warn_id: int, user_id: int, server_id: int) -> int:
        """
        This function will remove a warn from the database.

        :param warn_id: The ID of the warn.
        :param user_id: The ID of the user that was warned.
        :param server_id: The ID of the server where the user has been warned
        """
        await self.connection.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (
                warn_id,
                user_id,
                server_id,
            ),
        )
        await self.connection.commit()
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0

    async def get_warnings(self, user_id: int, server_id: int) -> list:
        """
        This function will get all the warnings of a user.

        :param user_id: The ID of the user that should be checked.
        :param server_id: The ID of the server that should be checked.
        :return: A list of all the warnings of the user.
        """
        rows = await self.connection.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            result_list = []
            for row in result:
                result_list.append(row)
            return result_list

    async def get_log_channel(self, server_id: int) -> int | None:
        rows = await self.connection.execute(
            "SELECT channel_id FROM log_channels WHERE server_id=?",
            (str(server_id),)
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return int(result[0]) if result else None

    async def set_log_channel(self, server_id: int, channel_id: int) -> None:
        await self.connection.execute(
            "INSERT OR REPLACE INTO log_channels(server_id, channel_id) VALUES (?, ?)",
            (str(server_id), str(channel_id))
        )
        await self.connection.commit()
    async def add_ticket_panel(self, panel_id: str, server_id: int, channel_id: int, message_id: int) -> None:
        await self.connection.execute("INSERT INTO ticket_panels(panel_id, server_id, channel_id, message_id) VALUES (?, ?, ?, ?)", (panel_id, str(server_id), str(channel_id), str(message_id)))
        await self.connection.commit()

    async def get_ticket_panels(self, server_id: int) -> list:
        rows = await self.connection.execute("SELECT panel_id, channel_id, message_id FROM ticket_panels WHERE server_id=?", (str(server_id),))
        async with rows as cursor: return await cursor.fetchall()

    async def update_ticket_panel(self, panel_id: str, server_id: int, channel_id: int, message_id: int) -> None:
        await self.connection.execute("UPDATE ticket_panels SET channel_id=?, message_id=? WHERE panel_id=? AND server_id=?", (str(channel_id), str(message_id), panel_id, str(server_id)))
        await self.connection.commit()

    async def delete_ticket_panel(self, panel_id: str, server_id: int) -> None:
        await self.connection.execute("DELETE FROM ticket_panels WHERE panel_id=? AND server_id=?", (panel_id, str(server_id)))
        await self.connection.execute("DELETE FROM ticket_options WHERE panel_id=? AND server_id=?", (panel_id, str(server_id)))
        await self.connection.execute("DELETE FROM ticket_buttons WHERE panel_id=? AND server_id=?", (panel_id, str(server_id)))
        await self.connection.commit()

    async def update_ticket_channel_message(self, panel_id: str, server_id: int, ticket_title: str, ticket_description: str) -> None:
        await self.connection.execute("UPDATE ticket_panels SET ticket_title=?, ticket_description=? WHERE panel_id=? AND server_id=?", (ticket_title, ticket_description, panel_id, str(server_id)))
        await self.connection.commit()

    async def get_ticket_channel_message(self, panel_id: str) -> tuple:
        rows = await self.connection.execute("SELECT ticket_title, ticket_description FROM ticket_panels WHERE panel_id=?", (panel_id,))
        async with rows as cursor: return await cursor.fetchone()

    async def update_ticket_panel_message(self, panel_id: str, server_id: int, panel_title: str, panel_description: str) -> None:
        await self.connection.execute("UPDATE ticket_panels SET panel_title=?, panel_description=? WHERE panel_id=? AND server_id=?", (panel_title, panel_description, panel_id, str(server_id)))
        await self.connection.commit()

    async def get_ticket_panel_message(self, panel_id: str) -> tuple:
        rows = await self.connection.execute("SELECT panel_title, panel_description FROM ticket_panels WHERE panel_id=?", (panel_id,))
        async with rows as cursor: return await cursor.fetchone()

    async def update_ticket_channel_name_format(self, panel_id: str, server_id: int, format_str: str) -> None:
        await self.connection.execute("UPDATE ticket_panels SET channel_name_format=? WHERE panel_id=? AND server_id=?", (format_str, panel_id, str(server_id)))
        await self.connection.commit()

    async def get_ticket_channel_name_format(self, panel_id: str) -> tuple:
        rows = await self.connection.execute("SELECT channel_name_format FROM ticket_panels WHERE panel_id=?", (panel_id,))
        async with rows as cursor: return await cursor.fetchone()

    async def add_ticket_option(self, option_id: str, panel_id: str, server_id: int, name: str, emoji: str, category_id: int, support_role_id: int) -> None:
        await self.connection.execute("INSERT INTO ticket_options(option_id, panel_id, server_id, name, emoji, category_id, support_role_id) VALUES (?, ?, ?, ?, ?, ?, ?)", (option_id, panel_id, str(server_id), name, emoji, str(category_id), str(support_role_id)))
        await self.connection.commit()

    async def delete_ticket_option(self, option_id: str, server_id: int) -> None:
        await self.connection.execute("DELETE FROM ticket_options WHERE option_id=? AND server_id=?", (option_id, str(server_id)))
        await self.connection.commit()

    async def get_ticket_options(self, panel_id: str) -> list:
        rows = await self.connection.execute("SELECT option_id, name, emoji, category_id, support_role_id FROM ticket_options WHERE panel_id=?", (panel_id,))
        async with rows as cursor: return await cursor.fetchall()

    async def get_ticket_option(self, option_id: str) -> tuple:
        rows = await self.connection.execute("SELECT name, category_id, support_role_id FROM ticket_options WHERE option_id=?", (option_id,))
        async with rows as cursor: return await cursor.fetchone()

    async def add_ticket_button(self, button_id: str, panel_id: str, server_id: int, label: str, emoji: str, category_id: int, support_role_id: int) -> None:
        await self.connection.execute("INSERT INTO ticket_buttons(button_id, panel_id, server_id, label, emoji, category_id, support_role_id) VALUES (?, ?, ?, ?, ?, ?, ?)", (button_id, panel_id, str(server_id), label, emoji, str(category_id), str(support_role_id)))
        await self.connection.commit()

    async def delete_ticket_button(self, button_id: str, server_id: int) -> None:
        await self.connection.execute("DELETE FROM ticket_buttons WHERE button_id=? AND server_id=?", (button_id, str(server_id)))
        await self.connection.commit()

    async def get_ticket_buttons(self, panel_id: str) -> list:
        rows = await self.connection.execute("SELECT button_id, label, emoji, category_id, support_role_id FROM ticket_buttons WHERE panel_id=?", (panel_id,))
        async with rows as cursor: return await cursor.fetchall()

    async def get_ticket_button(self, button_id: str) -> tuple:
        rows = await self.connection.execute("SELECT label, category_id, support_role_id FROM ticket_buttons WHERE button_id=?", (button_id,))
        async with rows as cursor: return await cursor.fetchone()

    async def create_ticket(self, ticket_id: str, server_id: int, channel_id: int, creator_id: int, option_id: str, panel_id: str, welcome_msg_id: int) -> None:
        await self.connection.execute("INSERT INTO tickets(ticket_id, server_id, channel_id, creator_id, option_id, panel_id, welcome_msg_id) VALUES (?, ?, ?, ?, ?, ?, ?)", (ticket_id, str(server_id), str(channel_id), str(creator_id), option_id, panel_id, str(welcome_msg_id)))
        await self.connection.commit()

    async def get_ticket(self, channel_id: int) -> tuple:
        rows = await self.connection.execute("SELECT ticket_id, creator_id, status, claimed_by FROM tickets WHERE channel_id=?", (str(channel_id),))
        async with rows as cursor: return await cursor.fetchone()

    async def get_all_active_tickets(self, server_id: int) -> list:
        rows = await self.connection.execute("SELECT ticket_id, channel_id, creator_id FROM tickets WHERE server_id=? AND status='open'", (str(server_id),))
        async with rows as cursor: return await cursor.fetchall()

    async def get_all_active_tickets_for_panel(self, panel_id: str) -> list:
        rows = await self.connection.execute("SELECT channel_id, welcome_msg_id, creator_id FROM tickets WHERE panel_id=? AND status='open'", (panel_id,))
        async with rows as cursor: return await cursor.fetchall()

    async def update_ticket_status(self, channel_id: int, status: str) -> None:
        await self.connection.execute("UPDATE tickets SET status=? WHERE channel_id=?", (status, str(channel_id)))
        await self.connection.commit()

    async def update_ticket_claim(self, channel_id: int, claimed_by: int) -> None:
        val = str(claimed_by) if claimed_by else None
        await self.connection.execute("UPDATE tickets SET claimed_by=? WHERE channel_id=?", (val, str(channel_id)))
        await self.connection.commit()

    async def get_handled_tickets_count(self, server_id: int) -> int:
        rows = await self.connection.execute("SELECT COUNT(*) FROM tickets WHERE server_id=? AND status='closed'", (str(server_id),))
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0
    async def add_ticket_ping_role(self, server_id: int, role_id: int) -> None:
        await self.connection.execute("INSERT OR IGNORE INTO ticket_ping_roles(server_id, role_id) VALUES (?, ?)", (str(server_id), str(role_id)))
        await self.connection.commit()

    async def remove_ticket_ping_role(self, server_id: int, role_id: int) -> None:
        await self.connection.execute("DELETE FROM ticket_ping_roles WHERE server_id=? AND role_id=?", (str(server_id), str(role_id)))
        await self.connection.commit()

    async def get_ticket_ping_roles(self, server_id: int) -> list:
        rows = await self.connection.execute("SELECT role_id FROM ticket_ping_roles WHERE server_id=?", (str(server_id),))
        async with rows as cursor:
            return await cursor.fetchall()

    # Staff Management
    async def is_staff(self, user_id: int, server_id: int, member=None) -> bool:
        rows = await self.connection.execute(
            "SELECT 1 FROM staff_members WHERE user_id=? AND server_id=?", 
            (str(user_id), str(server_id))
        )
        async with rows as cursor:
            if await cursor.fetchone():
                return True
                
        if member:
            staff_positions = await self.get_all_staff_positions(server_id)
            staff_role_ids = [int(pos[1]) for pos in staff_positions if pos[1] and str(pos[1]).lower() != 'none']
            
            default_role = await self.get_staff_default_role(server_id)
            if default_role and default_role[0] and str(default_role[0]).lower() != 'none':
                staff_role_ids.append(int(default_role[0]))
                
            author_role_ids = [role.id for role in member.roles]
            if any(role_id in author_role_ids for role_id in staff_role_ids):
                return True
                
        return False

    async def add_staff_member(self, user_id: int, server_id: int, position_name: str = None) -> None:
        await self.connection.execute(
            "INSERT OR REPLACE INTO staff_members(server_id, user_id, position_name) VALUES (?, ?, ?)", 
            (str(server_id), str(user_id), position_name)
        )
        await self.connection.commit()

    async def remove_staff_member(self, user_id: int, server_id: int) -> None:
        await self.connection.execute(
            "DELETE FROM staff_members WHERE user_id=? AND server_id=?", 
            (str(user_id), str(server_id))
        )
        await self.connection.commit()

    async def get_staff_position(self, server_id: int, position_name: str) -> tuple:
        rows = await self.connection.execute(
            "SELECT role_id, is_custom FROM staff_positions WHERE server_id=? AND position_name=?",
            (str(server_id), position_name)
        )
        async with rows as cursor: return await cursor.fetchone()

    async def rename_staff_position(self, server_id: int, old_name: str, new_name: str) -> None:
        await self.connection.execute(
            "UPDATE staff_positions SET position_name=? WHERE server_id=? AND position_name=?",
            (new_name, str(server_id), old_name)
        )
        await self.connection.execute(
            "UPDATE staff_members SET position_name=? WHERE server_id=? AND position_name=?",
            (new_name, str(server_id), old_name)
        )
        await self.connection.commit()

    async def edit_staff_position_role(self, server_id: int, position_name: str, role_id: str) -> None:
        await self.connection.execute(
            "UPDATE staff_positions SET role_id=? WHERE server_id=? AND position_name=?",
            (role_id, str(server_id), position_name)
        )
        await self.connection.commit()

    async def get_all_staff_positions(self, server_id: int) -> list:
        rows = await self.connection.execute(
            "SELECT position_name, role_id, is_custom, rank FROM staff_positions WHERE server_id=? ORDER BY rank ASC",
            (str(server_id),)
        )
        async with rows as cursor: return await cursor.fetchall()

    async def get_staff_position_rank(self, server_id: int, position_name: str) -> int:
        """Returns the rank of a position. Lower number = higher rank. Returns 999 if unset."""
        rows = await self.connection.execute(
            "SELECT rank FROM staff_positions WHERE server_id=? AND position_name=?",
            (str(server_id), position_name)
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result and result[0] is not None else 999

    async def add_staff_position(self, server_id: int, position_name: str, role_id: str = None, is_custom: bool = True, rank: int = 999) -> None:
        await self.connection.execute(
            "INSERT OR REPLACE INTO staff_positions(server_id, position_name, role_id, is_custom, rank) VALUES (?, ?, ?, ?, ?)",
            (str(server_id), position_name, role_id, is_custom, rank)
        )
        await self.connection.commit()

    async def edit_staff_position_rank(self, server_id: int, position_name: str, rank: int) -> None:
        await self.connection.execute(
            "UPDATE staff_positions SET rank=? WHERE server_id=? AND position_name=?",
            (rank, str(server_id), position_name)
        )
        await self.connection.commit()

    async def remove_staff_position(self, server_id: int, position_name: str) -> None:
        await self.connection.execute(
            "DELETE FROM staff_positions WHERE server_id=? AND position_name=?",
            (str(server_id), position_name)
        )
        await self.connection.commit()

    async def set_staff_default_role(self, server_id: int, role_id: str, always_apply: bool = True) -> None:
        await self.connection.execute(
            "INSERT OR REPLACE INTO staff_autorole_config(server_id, role_id, always_apply) VALUES (?, ?, ?)",
            (str(server_id), role_id, 1 if always_apply else 0)
        )
        await self.connection.commit()

    async def get_staff_default_role(self, server_id: int) -> tuple:
        rows = await self.connection.execute(
            "SELECT role_id, always_apply FROM staff_autorole_config WHERE server_id=?",
            (str(server_id),)
        )
        async with rows as cursor:
            return await cursor.fetchone()

    # Modmail
    async def get_modmail_config(self, server_id: int) -> tuple:
        rows = await self.connection.execute("SELECT category_id, log_channel_id FROM modmail_config WHERE server_id=?", (str(server_id),))
        async with rows as cursor: return await cursor.fetchone()

    async def set_modmail_config(self, server_id: int, category_id: int, log_channel_id: int = None) -> None:
        await self.connection.execute("INSERT OR REPLACE INTO modmail_config(server_id, category_id, log_channel_id) VALUES (?, ?, ?)", (str(server_id), str(category_id), str(log_channel_id) if log_channel_id else None))
        await self.connection.commit()

    async def get_modmail_thread(self, user_id: int, server_id: int) -> tuple:
        rows = await self.connection.execute("SELECT channel_id, last_active FROM modmail_threads WHERE user_id=? AND server_id=?", (str(user_id), str(server_id)))
        async with rows as cursor: return await cursor.fetchone()

    async def create_modmail_thread(self, user_id: int, server_id: int, channel_id: int) -> None:
        await self.connection.execute("INSERT OR REPLACE INTO modmail_threads(user_id, server_id, channel_id, last_active) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", (str(user_id), str(server_id), str(channel_id)))
        await self.connection.commit()

    async def update_modmail_thread_activity(self, user_id: int, server_id: int) -> None:
        await self.connection.execute("UPDATE modmail_threads SET last_active=CURRENT_TIMESTAMP WHERE user_id=? AND server_id=?", (str(user_id), str(server_id)))
        await self.connection.commit()

    async def delete_modmail_thread(self, user_id: int, server_id: int) -> None:
        await self.connection.execute("DELETE FROM modmail_threads WHERE user_id=? AND server_id=?", (str(user_id), str(server_id)))
        await self.connection.commit()

    async def is_modmail_blocked(self, user_id: int, server_id: int) -> bool:
        rows = await self.connection.execute("SELECT 1 FROM modmail_blocked WHERE user_id=? AND server_id=?", (str(user_id), str(server_id)))
        async with rows as cursor: return bool(await cursor.fetchone())

    async def set_modmail_blocked(self, user_id: int, server_id: int, blocked: bool) -> None:
        if blocked:
            await self.connection.execute("INSERT OR IGNORE INTO modmail_blocked(user_id, server_id) VALUES (?, ?)", (str(user_id), str(server_id)))
        else:
            await self.connection.execute("DELETE FROM modmail_blocked WHERE user_id=? AND server_id=?", (str(user_id), str(server_id)))
        await self.connection.commit()

    # Staff Updates Channel
    async def get_staff_updates_channel(self, server_id: int) -> int | None:
        rows = await self.connection.execute(
            "SELECT channel_id FROM staff_updates_config WHERE server_id=?",
            (str(server_id),)
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return int(result[0]) if result else None

    async def set_staff_updates_channel(self, server_id: int, channel_id: int) -> None:
        await self.connection.execute(
            "INSERT OR REPLACE INTO staff_updates_config(server_id, channel_id) VALUES (?, ?)",
            (str(server_id), str(channel_id))
        )
        await self.connection.commit()

    # Staff Strikes
    async def add_staff_strike(self, server_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        await self.connection.execute(
            "INSERT INTO staff_strikes(server_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            (str(server_id), str(user_id), str(moderator_id), reason)
        )
        await self.connection.commit()
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM staff_strikes WHERE server_id=? AND user_id=?",
            (str(server_id), str(user_id))
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def get_staff_strikes(self, server_id: int, user_id: int) -> list:
        rows = await self.connection.execute(
            "SELECT id, moderator_id, reason, strftime('%s', created_at) FROM staff_strikes WHERE server_id=? AND user_id=? ORDER BY created_at ASC",
            (str(server_id), str(user_id))
        )
        async with rows as cursor:
            return await cursor.fetchall()

    async def clear_staff_strikes(self, server_id: int, user_id: int) -> None:
        await self.connection.execute(
            "DELETE FROM staff_strikes WHERE server_id=? AND user_id=?",
            (str(server_id), str(user_id))
        )
        await self.connection.commit()

    # Mod Action Logging (for weekly stats)
    async def log_mod_action(self, server_id: int, moderator_id: int, action_type: str) -> None:
        await self.connection.execute(
            "INSERT INTO mod_actions(server_id, moderator_id, action_type) VALUES (?, ?, ?)",
            (str(server_id), str(moderator_id), action_type)
        )
        await self.connection.commit()

    async def get_weekly_mod_stats(self, server_id: int) -> list:
        rows = await self.connection.execute(
            """SELECT moderator_id, action_type, COUNT(*) as count
               FROM mod_actions
               WHERE server_id=? AND created_at >= datetime('now', '-7 days')
               GROUP BY moderator_id, action_type
               ORDER BY moderator_id, action_type""",
            (str(server_id),)
        )
        async with rows as cursor:
            return await cursor.fetchall()

    # Quarantine config
    async def get_roles_by_category(self, guild_id: int, category: str) -> list:
        rows = await self.connection.execute(
            "SELECT role_id FROM roles WHERE guild_id=? AND category=?",
            (str(guild_id), category)
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return [int(row[0]) for row in result] if result else []

    async def save_story(self, story_id: str, server_id: int, channel_id: int, message_id: int) -> None:
        await self.connection.execute(
            "INSERT INTO stories(story_id, server_id, channel_id, message_id) VALUES (?, ?, ?, ?)",
            (story_id, str(server_id), str(channel_id), str(message_id))
        )
        await self.connection.commit()

    async def get_story(self, story_id: str, server_id: int):
        rows = await self.connection.execute(
            "SELECT channel_id, message_id FROM stories WHERE story_id=? AND server_id=?",
            (story_id, str(server_id))
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            if result:
                return (int(result[0]), int(result[1]))
            return None

    async def get_quarantine_role(self, server_id: int) -> int | None:
        rows = await self.connection.execute(
            "SELECT role_id FROM quarantine_config WHERE server_id=?",
            (str(server_id),)
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return int(result[0]) if result else None

    async def set_quarantine_role(self, server_id: int, role_id: int) -> None:
        await self.connection.execute(
            "INSERT OR REPLACE INTO quarantine_config(server_id, role_id) VALUES (?, ?)",
            (str(server_id), str(role_id))
        )
        await self.connection.commit()
