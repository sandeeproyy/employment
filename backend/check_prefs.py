import asyncio
from app.core.database import async_session_factory
from app.models.preference import UserPreference
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(UserPreference))
        prefs = result.scalars().first()
        if prefs:
            print("Job Sources configured:")
            for s in prefs.job_sources:
                print(s)
            print(f"Min Match Score: {prefs.min_match_score}")
            print(f"Experience Level: {prefs.experience_level}")
            print(f"Domains: {prefs.domains}")
            print(f"Job Types: {prefs.job_types}")
            print(f"Locations: {prefs.locations}")
            print(f"Target Companies: {prefs.target_companies}")
        else:
            print("No preferences found!")

if __name__ == "__main__":
    asyncio.run(main())
