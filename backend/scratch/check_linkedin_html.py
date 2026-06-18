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
        print(f"Status Code: {r.status_code}")
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.find_all("li")
        print(f"Number of li items found: {len(items)}")
        
        if items:
            print("\n--- SAMPLE ITEM HTML ---")
            print(items[0].prettify()[:1000])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
