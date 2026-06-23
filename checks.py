import discord
from discord.ext import commands
from discord.ext.commands import Context

def is_staff():
    """
    A custom check that verifies if the user is in the staff list, or is the server owner/administrator.
    """
    async def predicate(context: Context) -> bool:
        if context.guild is None:
            return False
            
        # Server owner always passes
        if context.author.id == context.guild.owner_id:
            return True
            
        # Bot owners always pass
        if await context.bot.is_owner(context.author):
            return True
            
        # Administrators always pass (so server owners don't get locked out)
        if context.author.guild_permissions.administrator:
            return True
            
        # Check database
        is_staff_member = await context.bot.database.is_staff(context.author.id, context.guild.id, member=context.author)
        if not is_staff_member:
            raise commands.MissingPermissions(["Staff"])
        return True

    return commands.check(predicate)
