from jwt_auth.db.db import safe_query,init_pool
import asyncio

async def main():
    await init_pool()

    users = await safe_query("SELECT * FROM containers", fetch="all")
    for user in users:
        print(f"{user}\n")

asyncio.run(main())

