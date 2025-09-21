from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(slots=True)
class LinkContent:
    url: str
    title: Optional[str] = None
    text: Optional[str] = None
    domain: Optional[str] = None
    extraction_error: Optional[str] = None


@dataclass(slots=True)
class WebContent:
    link: str


@dataclass(slots=True)
class News(WebContent):
    title: str
    summary: str

    def to_dict(self) -> dict:
        return {
            "text": self.summary,
            "title": self.title,
            "summary": self.summary,
            "link": self.link,
        }


@dataclass(slots=True)
class Paper(WebContent):
    title: str
    authors: List[str]
    summary: str
    published: Optional[str] = None
    updated: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "text": self.summary,
            "title": self.title,
            "authors": self.authors,
            "summary": self.summary,
            "link": self.link,
            "published": self.published,
            "updated": self.updated,
        }


@dataclass(slots=True)
class NewsArticle:
    """Represents a news article with extracted content."""

    title: str
    url: str
    snippet: str
    content: str = ""
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    domain: Optional[str] = None
    word_count: int = 0
    tags: List[str] = field(default_factory=list)
    extraction_success: bool = False
    extraction_error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert the article to a dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "content": self.content,
            "author": self.author,
            "published_date": (
                self.published_date.isoformat() if self.published_date else None
            ),
            "domain": self.domain,
            "word_count": self.word_count,
            "tags": self.tags,
            "extraction_success": self.extraction_success,
            "extraction_error": self.extraction_error,
        }
