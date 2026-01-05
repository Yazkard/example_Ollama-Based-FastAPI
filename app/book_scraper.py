from llm import safe_get_response_llm
from models.books import BookInfo, PriceInfo, BookPriceResponse
from typing import List
import httpx
from fastapi import HTTPException
from bs4 import BeautifulSoup
from prompts import book_info_prompt
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
            cover_url = cover_img.get('src') or cover_img.get('data-src') cover_img.get(content='source')
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
    """Search for book prices using Ollama to generate search queries and simulate results"""
    
    # Create a prompt for Ollama to suggest where to search and simulate finding prices
    prompt = f"""Given this book information:
Title: {title}
Author: {author}

Generate a list of 3-5 online bookstores where this book might be available with estimated price ranges.
Respond ONLY with valid JSON in this format:
[
  {{"store": "Amazon", "price": "$15.99", "url": "https://amazon.com/search?q=book+title"}},
  {{"store": "Barnes & Noble", "price": "$16.50", "url": "https://barnesandnoble.com/search?q=book+title"}}
]

Include realistic stores like: Amazon, Barnes & Noble, Book Depository, AbeBooks, ThriftBooks."""

    ollama_response = await safe_get_response_llm(client, book_prompt, prompt)
    
    try:
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', ollama_response, re.DOTALL)
        if json_match:
            prices_data = json.loads(json_match.group())
        else:
            prices_data = json.loads(ollama_response)
        
        prices = [PriceInfo(**item) for item in prices_data]
        return prices
    except Exception as e:
        # Return fallback prices if parsing fails
        search_query = f"{title} {author}".replace(' ', '+')
        return [
            PriceInfo(
                store="Amazon",
                price="Search required",
                url=f"https://www.amazon.com/s?k={search_query}"
            ),
            PriceInfo(
                store="Barnes & Noble",
                price="Search required",
                url=f"https://www.barnesandnoble.com/s/{search_query}"
            )
        ]