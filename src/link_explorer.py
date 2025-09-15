"""Link Explorer utility for fetching and parsing web content.

Provides functionality to open URLs, extract content, and parse metadata from web pages.
This module centralizes all link opening and content parsing functionality.

Usage:
    from link_explorer import LinkExplorer, ExtractedContent

    explorer = LinkExplorer()
    result = explorer.extract_content("https://example.com/article")

    if result.extraction_success:
        print(f"Title: {result.title}")
        print(f"Content: {result.content[:200]}...")
        print(f"Author: {result.author}")

Features:
    - Robust content extraction from various article formats
    - Metadata parsing (author, published date, keywords)
    - Domain filtering and validation
    - Error handling and graceful degradation
    - Configurable extraction parameters
    - Text cleaning and normalization

Dependencies:
    - requests: For HTTP requests
    - beautifulsoup4: For HTML parsing and content extraction
"""

from __future__ import annotations

import time
from typing import List, Set
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from data_model import LinkContent


class LinkExplorer:
    """Utility class for opening links and extracting content from web pages."""

    def __init__(
        self,
        request_timeout: int = 30,
        user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        max_content_length: int = 1024 * 1024,  # 1MB
        min_content_length: int = 200,
    ):
        """
        Initialize the link explorer.

        Args:
            request_timeout: Timeout for HTTP requests in seconds
            user_agent: User agent string for HTTP requests
            max_content_length: Maximum content length to process
            min_content_length: Minimum content length to consider valid
        """
        self.request_timeout = request_timeout
        self.user_agent = user_agent
        self.max_content_length = max_content_length
        self.min_content_length = min_content_length

        # Initialize HTTP session
        self.session = requests.Session()

        # Domains to skip (social media, aggregators, etc.)
        self.skip_domains: Set[str] = {
            "facebook.com",
            "instagram.com",
            "linkedin.com",
            "youtube.com",
            "tiktok.com",
            "pinterest.com",
        }

        # Content selectors for main article content (in order of preference)
        self.content_selectors = [
            "article",
            "[role='main']",
            ".article-content",
            ".post-content",
            ".entry-content",
            ".story-body",
            ".article-body",
            ".content",
            ".main-content",
            ".post-body",
            ".article-text",
            "main",
        ]

        # Author selectors
        self.author_selectors = [
            "[name='author']",
            "[property='article:author']",
            ".author",
            ".byline",
            "[rel='author']",
            ".article-author",
            ".post-author",
            ".author-name",
        ]

        # Date selectors
        self.date_selectors = [
            "[property='article:published_time']",
            "[name='article:published_time']",
            "[name='publishdate']",
            "[name='date']",
            ".published",
            ".date",
            ".publication-date",
            ".post-date",
            "time[datetime]",
            "[datetime]",
        ]

    def should_skip_domain(self, url: str) -> bool:
        """Check if a domain should be skipped based on the skip list."""
        try:
            domain = urlparse(url).netloc.lower()
            return any(skip_domain in domain for skip_domain in self.skip_domains)
        except Exception:
            return False

    def extract_content(self, url: str) -> LinkContent:
        """
        Extract content from a single URL.

        Args:
            url: The URL to extract content from

        Returns:
            ExtractedContent object with extracted data and metadata
        """
        result = LinkContent(url=url)

        try:
            # Parse domain
            parsed_url = urlparse(url)
            result.domain = parsed_url.netloc

            if not parsed_url.scheme:
                url = f"https://{url}"
                result.url = url

            # Check if domain should be skipped
            if self.should_skip_domain(url):
                result.extraction_error = f"Domain {result.domain} is in skip list"
                return result

            # Fetch the webpage
            response = self.session.get(url, timeout=self.request_timeout)
            result.extraction_error = (
                f"HTTP {response.status_code}" if response.status_code != 200 else None
            )

            response.raise_for_status()
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove unwanted elements
            self._clean_soup(soup)

            # Extract main content
            result.text = soup.text.strip()

        except requests.exceptions.Timeout:
            result.extraction_error = f"Request timeout after {self.request_timeout}s"
        except requests.exceptions.RequestException as e:
            result.extraction_error = f"Request failed: {str(e)}"
        except Exception as e:
            result.extraction_error = f"Extraction failed: {str(e)}"

        return result

    def _parse_content_with_llm(self, content: str) -> str:
        """Use LLM to parse and summarize content."""
        try:

            chain = (
                PromptTemplate.from_template(PARSE_NEWS_PROMPT)
                | self.llm
                | JsonOutputParser()
            )

            return chain.invoke({"content": content.strip()})
        except Exception as e:
            return {"content": content}  # Fallback to original content if LLM fails

    def extract_content_batch(
        self, urls: List[str], delay_between_requests: float = 1.0
    ) -> List[LinkContent]:
        """
        Extract content from multiple URLs with rate limiting.

        Args:
            urls: List of URLs to process
            delay_between_requests: Delay between requests in seconds

        Returns:
            List of ExtractedContent objects
        """
        results = []

        for i, url in enumerate(urls):
            try:
                result = self.extract_content(url)
                results.append(result)

                # Add delay between requests to be respectful
                if i < len(urls) - 1 and delay_between_requests > 0:
                    time.sleep(delay_between_requests)

            except Exception as e:
                # Create failed result
                result = LinkContent(url=url)
                result.extraction_error = f"Batch extraction failed: {str(e)}"
                results.append(result)

        return results

    def _clean_soup(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements from the soup."""
        unwanted_tags = [
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "aside",
            "noscript",
            "iframe",
            "form",
            "input",
            "button",
            ".advertisement",
            ".ad",
            ".ads",
            ".sidebar",
            ".menu",
            ".navigation",
            ".nav",
            ".social",
        ]

        for tag in unwanted_tags:
            for element in soup.select(tag):
                element.decompose()

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main article content from parsed HTML."""
        # Try content selectors in order of preference
        return soup.text.strip()


PARSE_NEWS_PROMPT = """
Role: You are an expert content extractor. 
Task: Given the raw text of a web page, parse it to a structured format.

Schema:
- title: The title of the article (string)
- summary: The main content of the article (string)
- author: The author of the article (string)
- published_date: [dd-mm-yyyy] The published date of the article (string)
- tags: A list of tags associated with the article (list of strings)

Response Format (strict):
<JSON object of provided schema>

Web page content:
```
{content}
```

## Response
"""
