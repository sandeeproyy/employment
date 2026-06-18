"""Add missing posted_at column to jobs table."""
import asyncio
from sqlalchemy import text
from app.core.database import engine


async def add_col():
    async with engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS posted_at VARCHAR(255) DEFAULT NULL")
        )
        print("✅ posted_at column added to jobs table")


asyncio.run(add_col())
