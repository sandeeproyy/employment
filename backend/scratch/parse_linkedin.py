import httpx
from bs4 import BeautifulSoup

async def main():
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {
        "keywords": "robotics",
        "location": "India",
        "start": 0
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.find_all("li")
        
        print(f"Parsing {len(items)} items...")
        for idx, item in enumerate(items):
            # Try to get link and title
            link_el = item.find("a", class_="base-card__full-link")
            link = link_el["href"] if link_el else None
            
            # Title
            title_el = item.find("h3", class_="base-search-card__title")
            title = title_el.text.strip() if title_el else None
            
            # Company
            company_el = item.find("h4", class_="base-search-card__subtitle")
            company = company_el.text.strip() if company_el else None
            
            # Location
            location_el = item.find("span", class_="job-search-card__location")
            location = location_el.text.strip() if location_el else None
            
            # Print details
            print(f"{idx+1}. Title: {title}")
            print(f"   Company: {company}")
            print(f"   Location: {location}")
            print(f"   Link: {link}")
            print("-" * 50)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
