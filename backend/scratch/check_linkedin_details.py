import httpx
from bs4 import BeautifulSoup

async def main():
    # Use one of the real links extracted in the previous step
    url = "https://in.linkedin.com/jobs/view/robotics-engineer-universal-robots-bangalore-india-at-universal-robots-4413607111"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
        print(f"Status Code: {r.status_code}")
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Look for description
        desc_el = soup.find("div", class_="show-more-less-html__markup")
        if not desc_el:
            desc_el = soup.find("section", class_="description")
        if not desc_el:
            desc_el = soup.find("div", class_="description__text")
            
        if desc_el:
            print("\n--- DESCRIPTION FOUND ---")
            text = desc_el.text.strip()
            print(f"Length: {len(text)}")
            print(text[:500])
        else:
            print("Description element not found!")
            # Print body tags or headers to see what happened
            print(r.text[:1000])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
