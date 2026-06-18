import asyncio
from app.core.database import async_session_factory
from app.models.job import Job
from sqlalchemy import select, func

async def main():
    async with async_session_factory() as s:
        res = await s.execute(select(func.count(Job.id)).where(Job.source == 'linkedin'))
        print('LinkedIn jobs count:', res.scalar())
        
        res_intern = await s.execute(select(func.count(Job.id)).where(Job.source == 'linkedin', Job.job_type == 'internship'))
        print('LinkedIn internships count:', res_intern.scalar())
        
        res_scored = await s.execute(select(func.count(Job.id)).where(Job.source == 'linkedin', Job.status == 'scored'))
        print('LinkedIn scored count:', res_scored.scalar())
        
        res_all = await s.execute(select(Job).where(Job.source == 'linkedin').limit(10))
        for j in res_all.scalars():
            print(f"- [{j.job_type.upper()}] {j.title} at {j.company} in {j.location} (Score: {j.match_score}, Status: {j.status})")

if __name__ == "__main__":
    asyncio.run(main())
