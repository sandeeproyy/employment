import asyncio
from app.core.database import async_session_factory
from app.models.job import Job
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        result = await session.execute(
            select(Job)
            .where(Job.status == "scored")
        )
        jobs = result.scalars().all()
        print(f"Total scored jobs: {len(jobs)}")
        
        senior_scored = [j for j in jobs if any(kw in j.title.lower() for kw in ["senior", "sr.", "sr ", "staff", "lead", "manager", "director", "architect"])]
        print(f"Scored senior/lead jobs: {len(senior_scored)}")
        for idx, j in enumerate(senior_scored[:10]):
            print(f"{idx+1}. {j.title} @ {j.company}")
            print(f"   Score: {j.match_score}")
            print(f"   Breakdown: {j.match_breakdown}")
            print(f"   Reason: {j.match_breakdown.get('reason') if j.match_breakdown else 'None'}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
