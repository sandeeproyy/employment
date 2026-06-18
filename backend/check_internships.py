import asyncio
from app.core.database import async_session_factory
from app.models.job import Job
from sqlalchemy import select, func

async def main():
    async with async_session_factory() as s:
        res = await s.execute(select(Job).where(Job.job_type == 'internship').order_by(Job.match_score.desc()).limit(15))
        jobs = res.scalars().all()
        print(f"Total Internships: {len(jobs)}")
        for idx, j in enumerate(jobs):
            print(f"{idx+1}: [{j.source.upper()}] {j.title} @ {j.company} | Score: {j.match_score}% | Status: {j.status} | Location: {j.location}")

if __name__ == "__main__":
    asyncio.run(main())
