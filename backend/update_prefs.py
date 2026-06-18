import asyncio
from app.core.database import async_session_factory
from app.models.preference import UserPreference
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(UserPreference))
        prefs = result.scalars().first()
        if not prefs:
            prefs = UserPreference()
            session.add(prefs)
            
        prefs.min_match_score = 35
        prefs.domains = ['robotics', 'computer_vision', 'mechanical_engineering']
        await session.commit()
        print("Updated user preferences:")
        print(f"Min Match Score: {prefs.min_match_score}")
        print(f"Domains: {prefs.domains}")

if __name__ == "__main__":
    asyncio.run(main())
