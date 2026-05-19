import asyncio
from bot.database import get_supabase

async def main():
    sb = await get_supabase()
    res = await sb.table('templates').select('*').limit(1).execute()
    if res.data:
        print(list(res.data[0].keys()))
    else:
        print("No templates found")

asyncio.run(main())
