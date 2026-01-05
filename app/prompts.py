generate_prompt: str = """You are Students helper, you should answer for each question."""
book_prompt: str = """You are an expert in books. help with all user queries about books."""
book_info_prompt: str = """from texts provided by user choose the most relevant information to extract:
- title: book title
- author: book author(s)

Respond with ONLY a JSON object in this exact format, no other text:
{{"title": "...", "author": "..."}}"""
