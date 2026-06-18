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
            print("Created new preferences record.")
        
        sample_sources = [
            {"type": "linkedin", "keywords": "Mechanical Engineer", "location": "India", "job_type": "full-time", "interval_minutes": 30, "enabled": True, "label": "LinkedIn Mechanical Engineer India"},
            {"type": "linkedin", "keywords": "SolidWorks", "location": "India", "job_type": "full-time", "interval_minutes": 30, "enabled": True, "label": "LinkedIn SolidWorks India"},
            {"type": "linkedin", "keywords": "CAD Engineer", "location": "India", "job_type": "full-time", "interval_minutes": 30, "enabled": True, "label": "LinkedIn CAD Engineer India"},
            {"type": "linkedin", "keywords": "robotics intern", "location": "India", "job_type": "internship", "interval_minutes": 30, "enabled": True, "label": "LinkedIn Robotics Intern India"},
            {"type": "linkedin", "keywords": "robotics", "location": "India", "job_type": "full-time", "interval_minutes": 30, "enabled": True, "label": "LinkedIn Robotics Full-Time India"},
            {"type": "linkedin", "keywords": "computer vision", "location": "India", "job_type": "full-time", "interval_minutes": 30, "enabled": True, "label": "LinkedIn Computer Vision Full-Time India"},
        ]
        
        prefs.job_sources = sample_sources
        await session.commit()
        print("Configured Greenhouse, Lever, and LinkedIn job sources successfully!")

if __name__ == "__main__":
    asyncio.run(main())
