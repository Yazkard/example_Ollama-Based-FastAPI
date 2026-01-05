from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class BookInfo(BaseModel):
    title: str
    author: str
    cover_url: Optional[str]
    original_url: str

class PriceInfo(BaseModel):
    store: str
    price: str
    url: str

class BookPriceResponse(BaseModel):
    book: BookInfo
    prices: List[PriceInfo]

class BookURLRequest(BaseModel):
    url: HttpUrl