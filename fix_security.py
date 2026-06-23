with open('cogs/security.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('import time') and len(new_lines) > 20:
        break
    new_lines.append(line)

new_lines.append('''                        try:
                            await guild.ban(entry.user, reason="Anti-Nuke: Deleted too many channels rapidly.")
                            if guild.owner:
                                await guild.owner.send(f"?? **ANTI-NUKE TRIGGERED!**\\nUser {entry.user} was banned for deleting 3+ channels in 60 seconds.")
                            self.channel_deletions[user_id].clear()
                        except Exception as e:
                            self.bot.logger.error(f"Failed to ban rogue admin: {e}")
                    break
        except Exception as e:
            self.bot.logger.error(f"Failed to fetch audit logs for anti-nuke: {e}")

async def setup(bot) -> None:
    await bot.add_cog(Security(bot))
''')

with open('cogs/security.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
