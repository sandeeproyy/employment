import asyncio
from app.core.database import async_session_factory
from app.models.job import Job
from sqlalchemy import select, func

async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(func.count(Job.id)))
        count = result.scalar()
        print(f"Total Jobs in DB: {count}")
        
        result_details = await session.execute(select(Job).limit(5))
        jobs = result_details.scalars().all()
        for idx, j in enumerate(jobs):
            print(f"Job {idx+1}: {j.title} @ {j.company} | Score: {j.match_score} | Status: {j.status}")

if __name__ == "__main__":
    asyncio.run(main())
