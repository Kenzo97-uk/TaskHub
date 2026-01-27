from __future__ import annotations

import os
from datetime import datetime
from dotenv import load_dotenv
from redis.asyncio import Redis
import asyncio

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
LOG_PATH = os.getenv("LOG_PATH", "/data/events.log")
CHANNEL_EVENTS = "par:events"

async def main():
    r = Redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL_EVENTS)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    async for msg in pubsub.listen():
        if msg.get("type") != "message":
            continue
        data = msg.get("data")
        line = f"{datetime.utcnow().isoformat()}Z {data}\n"
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
        print(line.strip())

if __name__ == "__main__":
    asyncio.run(main())
