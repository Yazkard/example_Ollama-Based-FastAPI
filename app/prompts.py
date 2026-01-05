generate_prompt: str = """You are Students helper, you should answer for each question."""
book_prompt: str = """You are an expert in books. help with all user queries about books."""
book_info_prompt: str = """from texts provided by user choose the most relevant information to extract:
- title: book title
- author: book author(s)

Respond with ONLY a JSON object in this exact format, no other text:
{{"title": "...", "author": "..."}}"""

price_analysis_prompt: str = """Given these search results for a book, extract available prices and store names.
Search results:
{search_results}

Respond with ONLY a JSON array of objects in this exact format:
[
  {{"store": "Store Name", "price": "$XX.XX", "url": "https://..."}}
]
Include up to 5 best options. If no prices found, return empty list []."""
