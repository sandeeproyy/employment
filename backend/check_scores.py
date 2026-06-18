import asyncio
from app.core.database import async_session_factory
from app.models.job import Job
from sqlalchemy import select, func

async def main():
    async with async_session_factory() as session:
        # Total count
        total = (await session.execute(select(func.count(Job.id)))).scalar()
        
        # Count above 75
        high = (await session.execute(select(func.count(Job.id)).where(Job.match_score >= 75))).scalar()
        
        # Count between 50 and 75
        med = (await session.execute(select(func.count(Job.id)).where(Job.match_score >= 50, Job.match_score < 75))).scalar()
        
        # Count below 50
        low = (await session.execute(select(func.count(Job.id)).where(Job.match_score < 50))).scalar()
        
        # Max score
        max_score = (await session.execute(select(func.max(Job.match_score)))).scalar()
        
        print(f"Total jobs: {total}")
        print(f"Score >= 75: {high}")
        print(f"Score 50-74: {med}")
        print(f"Score < 50: {low}")
        print(f"Max score in DB: {max_score}")

if __name__ == "__main__":
    asyncio.run(main())
