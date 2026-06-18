import asyncio
from app.core.database import async_session_factory
from app.models.job import Job
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        result = await session.execute(
            select(Job)
            .order_by(Job.match_score.desc())
            .limit(10)
        )
        jobs = result.scalars().all()
        print("--- TOP 10 HIGHEST SCORING JOBS ---")
        for idx, j in enumerate(jobs):
            print(f"{idx+1}. {j.title} @ {j.company}")
            print(f"   Score: {j.match_score} | Status: {j.status}")
            print(f"   Location: {j.location} | Source: {j.source}")
            print(f"   Breakdown: {j.match_breakdown}")
            print(f"   Reason: {j.match_breakdown.get('reason') if j.match_breakdown else 'None'}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
