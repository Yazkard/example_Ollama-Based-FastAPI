from llm import safe_get_response_llm
from models.books import BookInfo, PriceInfo, BookPriceResponse
from typing import List
import httpx
from fastapi import HTTPException
from bs4 import BeautifulSoup
from prompts import book_info_prompt, price_analysis_prompt, book_prompt
import re
import json
from openai import AsyncOpenAI

async def fetch_webpage(url: str) -> str:
    """Fetch webpage content"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

async def extract_book_info(client: AsyncOpenAI, url: str, html_content: str) -> BookInfo:
    """Extract book information using BeautifulSoup and Ollama"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    texts = soup.get_text(separator='\n', strip=True).split("\n")
    texts = [text for text in texts if text.strip()]

    text_content = ", ".join(texts)

    ollama_response = await safe_get_response_llm(client, book_info_prompt, text_content)

    # Parse Ollama response
    try:
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', ollama_response, re.DOTALL)
        if json_match:
            book_data = json.loads(json_match.group())
        else:
            book_data = json.loads(ollama_response)
        
        # Try to find cover image
        cover_url = None
        cover_img = soup.find('picture', {'data-ta': 'cover'})
        
        if cover_img:
            cover_url = cover_img.contents[0].attrs.get("srcset")
        else:
            # Fallback: look for other cover images
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src', '')
                alt = img.get('alt', '').lower()
                if 'cover' in alt or 'book' in src.lower():
                    cover_url = src
                    break
        
        return BookInfo(
            title=book_data.get('title', 'Unknown'),
            author=book_data.get('author', 'Unknown'),
            description=book_data.get('description', 'No description available'),
            cover_url=cover_url,
            original_url=url
        )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse book info: {str(e)}")

async def search_book_prices(client: AsyncOpenAI, title: str, author: str) -> List[PriceInfo]:
    """Search for book prices by directly querying Polish bookstore websites"""
    
    print(f"Searching for prices: {title} by {author}")
    
    # Polish bookstores to search
    bookstores = [
        {
            "name": "Empik",
            "search_url": f"https://www.empik.com/szukaj/produkt?q="
        },
        {
            "name": "Matras",
            "search_url": f"https://www.matras.pl/listing?szukasz="
        },
        {
            "name": "TaniaKsiazka",
            "search_url": f"https://www.taniaksiazka.pl/SzukajPfbx?query="
        },
        {
            "name": "Bonito",
            "search_url": f"https://bonito.pl/szukaj?q="
        },
        {
            "name": "Allegro",
            "search_url": f"https://allegro.pl/listing?string="
        }
    ]
    
    results_text_parts = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client_http:
            for store in bookstores:
                try:
                    # Build search URL
                    search_term = f"{title} {author}".replace(' ', '+')
                    search_url = store["search_url"] + search_term
                    
                    print(f"Searching {store['name']}: {search_url}")
                    
                    response = await client_http.get(search_url)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Try to extract price information (this is generic, might need adjustment per site)
                        page_text = soup.get_text()[:1000]  # Get first 1000 chars
                        
                        # Look for common price patterns
                        price_match = re.search(r'(\d+[,\.]\d{2})\s*zł', page_text)
                        price = price_match.group(0) if price_match else "Sprawdź cenę"
                        
                        results_text_parts.append(
                            f"- {store['name']}: Znaleziono wyniki, możliwa cena: {price} - {search_url}"
                        )
                        print(f"✓ {store['name']}: Found results")
                    else:
                        print(f"✗ {store['name']}: Status {response.status_code}")
                        results_text_parts.append(f"- {store['name']}: {search_url}")
                        
                except Exception as e:
                    print(f"✗ {store['name']}: Error - {e}")
                    search_term = f"{title} {author}".replace(' ', '+')
                    search_url = store["search_url"] + search_term
                    results_text_parts.append(f"- {store['name']}: {search_url}")
        
        if not results_text_parts:
            print("No bookstore results found")
            return []
        
        # Send to Ollama for analysis
        results_text = "\n".join(results_text_parts)
        formatted_prompt = price_analysis_prompt.format(search_results=results_text)
        
        print("Sending results to Ollama for analysis...")
        ollama_response = await safe_get_response_llm(client, book_prompt, formatted_prompt)
        
        # Extract JSON from response
        try:
            json_match = re.search(r'\[.*\]', ollama_response, re.DOTALL)
            if json_match:
                prices_data = json.loads(json_match.group())
            else:
                prices_data = json.loads(ollama_response)
            
            prices = [PriceInfo(**item) for item in prices_data]
            print(f"✓ Extracted {len(prices)} prices from Ollama")
            return prices
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error parsing Ollama response: {e}")
            print(f"Response preview: {ollama_response[:300]}")
            
            # Fallback: return direct links
            fallback_prices = []
            for store in bookstores:
                search_term = f"{title} {author}".replace(' ', '+')
                fallback_prices.append(PriceInfo(
                    store=store["name"],
                    price="Sprawdź cenę",
                    url=store["search_url"] + search_term
                ))
            return fallback_prices[:3]  # Return top 3
            
    except Exception as e:
        print(f"Search failed: {e}")
        import traceback
        traceback.print_exc()
        return []