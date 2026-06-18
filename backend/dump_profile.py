import asyncio
import json
from app.core.database import async_session_factory
from app.models.user import UserProfile
from app.models.preference import UserPreference
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        profile = (await session.execute(select(UserProfile).limit(1))).scalar_one_or_none()
        prefs = (await session.execute(select(UserPreference).limit(1))).scalar_one_or_none()
        
        if profile:
            print("--- PROFILE INFO ---")
            print(f"Name: {profile.name}")
            print(f"Email: {profile.email}")
            print("Resume Structured:")
            print(json.dumps(profile.resume_structured, indent=2))
        else:
            print("No profile found")
            
        if prefs:
            print("\n--- PREFERENCES INFO ---")
            print(f"Job Types: {prefs.job_types}")
            print(f"Domains: {prefs.domains}")
            print(f"Min Match Score: {prefs.min_match_score}")
            print(f"Locations: {prefs.locations}")
            print(f"Target Companies: {prefs.target_companies}")
        else:
            print("No preferences found")

if __name__ == "__main__":
    asyncio.run(main())
