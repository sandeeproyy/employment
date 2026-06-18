import asyncio
from app.core.database import async_session_factory
from app.models.job import Job
from sqlalchemy import select, update

async def main():
    async with async_session_factory() as session:
        # Get count of scored jobs
        scored_count = (await session.execute(select(Job).where(Job.status == "scored"))).scalars().all()
        print(f"Found {len(scored_count)} jobs with status 'scored'.")
        
        # Reset them
        result = await session.execute(
            update(Job)
            .where(Job.status == "scored")
            .values(
                status="new",
                match_score=0.0,
                match_breakdown=None,
                scored_at=None
            )
        )
        await session.commit()
        print("Successfully reset all scored jobs to 'new'.")

if __name__ == "__main__":
    asyncio.run(main())
