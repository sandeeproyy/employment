import asyncio
from app.core.database import async_session_factory
from app.models.user import UserProfile
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(UserProfile))
        profiles = result.scalars().all()
        print(f"Total Profiles in DB: {len(profiles)}")
        for idx, p in enumerate(profiles):
            print(f"\n--- Profile {idx+1} ---")
            print(f"ID: {p.id}")
            print(f"Name: {p.name}")
            print(f"Email: {p.email}")
            print(f"PDF Path: {p.resume_pdf_path}")
            print(f"Raw text length: {len(p.resume_raw_text or '')}")
            print(f"Structured resume exists: {bool(p.resume_structured)}")
            if p.resume_structured:
                skills = p.resume_structured.get("skills", [])
                print(f"Skills extracted ({len(skills)}): {skills[:10]}")

if __name__ == "__main__":
    asyncio.run(main())
