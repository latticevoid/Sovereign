import asyncio
import aiosqlite

async def test():
    db = await aiosqlite.connect('database/database.db')
    cursor = await db.execute('SELECT ticket_title, ticket_description FROM ticket_panels WHERE panel_id=?', ('T6YYT2',))
    print(await cursor.fetchone())
    await db.close()

asyncio.run(test())
