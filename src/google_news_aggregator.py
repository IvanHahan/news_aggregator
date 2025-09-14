"""Google News Aggregator.

Searches for news articles on Google and extracts detailed content from each link.
Builds on the Google Search utility to provide news-specific functionality.

Usage:
    from google_news_aggregator import GoogleNewsAggregator

    aggregator = GoogleNewsAggregator()
    articles = aggregator.search_news("artificial intelligence", limit=5)

    for article in articles:
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")
        print(f"Content: {article.content[:200]}...")

CLI:
    python google_news_aggregator.py "machine learning" --limit 5

Environment Variables:
    SERPAPI_KEY: Your SerpAPI key (required for Google search)

Dependencies:
    - serpapi: For Google search functionality
    - requests: For fetching article content
    - beautifulsoup4: For parsing HTML content
    - newspaper3k: For advanced article extraction (optional, fallback to BeautifulSoup)

Design goals:
 - Leverage existing google_search module
 - Extract full article content from news links
 - Graceful error handling for failed content extraction
 - Support multiple extraction methods
 - Structured article objects with rich metadata
 - CLI interface for easy testing
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Set
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Import our existing Google search functionality
from google_search import GoogleSearchError, search_google

logger = logging.getLogger(__name__)


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


class GoogleNewsAggregator:
    """Aggregates news from Google search and extracts article content."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        request_timeout: int = 30,
        delay_between_requests: float = 1.0,
        user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    ):
        """
        Initialize the news aggregator.

        Args:
            api_key: SerpAPI key (if None, will use SERPAPI_KEY env var)
            request_timeout: Timeout for HTTP requests in seconds
            delay_between_requests: Delay between content extraction requests
            user_agent: User agent string for HTTP requests
        """
        self.api_key = api_key
        self.request_timeout = request_timeout
        self.delay_between_requests = delay_between_requests
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        # Domains to skip (social media, aggregators, etc.)
        self.skip_domains: Set[str] = {
            "twitter.com",
            "x.com",
            "facebook.com",
            "instagram.com",
            "linkedin.com",
            "reddit.com",
            "youtube.com",
        }

    def search_news(
        self,
        query: str,
        limit: int = 10,
        extract_content: bool = True,
        news_specific: bool = True,
    ) -> List[NewsArticle]:
        """
        Search for news articles and optionally extract their content.

        Args:
            query: Search query
            limit: Maximum number of articles to return
            extract_content: Whether to extract full article content
            news_specific: Whether to add news-specific search terms

        Returns:
            List of NewsArticle objects

        Raises:
            GoogleSearchError: If the search fails
        """
        # Modify query for news-specific search
        search_query = query
        if news_specific:
            # Add news-related terms to improve relevance
            search_query = f"{query} news OR article OR report"

        logger.info(f"Searching for news: {search_query}")

        try:
            # Use our existing Google search functionality
            search_results = search_google(
                query=search_query,
                limit=limit * 2,  # Get more results to filter out non-news
                api_key=self.api_key,
            )

            # Convert to NewsArticle objects
            articles = []
            for result in search_results[:limit]:
                if self._should_skip_domain(result.url):
                    logger.debug(f"Skipping domain: {result.url}")
                    continue

                article = NewsArticle(
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    domain=result.domain,
                )

                articles.append(article)

                # Stop if we have enough articles
                if len(articles) >= limit:
                    break

            logger.info(f"Found {len(articles)} relevant articles")

            # Extract content if requested
            if extract_content:
                self._extract_content_batch(articles)

            return articles

        except Exception as e:
            if isinstance(e, GoogleSearchError):
                raise
            raise GoogleSearchError(f"News search failed: {str(e)}")

    def _should_skip_domain(self, url: str) -> bool:
        """Check if a domain should be skipped."""
        try:
            domain = urlparse(url).netloc.lower()
            return any(skip_domain in domain for skip_domain in self.skip_domains)
        except Exception:
            return False

    def _extract_content_batch(self, articles: List[NewsArticle]) -> None:
        """Extract content from a batch of articles."""
        logger.info(f"Extracting content from {len(articles)} articles")

        for i, article in enumerate(articles):
            try:
                logger.debug(f"Extracting content from: {article.url}")
                self._extract_article_content(article)

                # Add delay between requests to be respectful
                if i < len(articles) - 1:
                    time.sleep(self.delay_between_requests)

            except Exception as e:
                logger.warning(f"Failed to extract content from {article.url}: {e}")
                article.extraction_error = str(e)

    def _extract_article_content(self, article: NewsArticle) -> None:
        """Extract content from a single article."""
        try:
            # Fetch the webpage
            response = self.session.get(article.url, timeout=self.request_timeout)
            response.raise_for_status()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove unwanted elements
            for element in soup(
                ["script", "style", "nav", "header", "footer", "aside"]
            ):
                element.decompose()

            # Try to extract the main content
            content = self._extract_main_content(soup)

            if content:
                article.content = content
                article.word_count = len(content.split())
                article.extraction_success = True

                # Try to extract additional metadata
                self._extract_metadata(article, soup)

            else:
                article.extraction_error = "No main content found"

        except requests.exceptions.RequestException as e:
            article.extraction_error = f"Request failed: {str(e)}"
        except Exception as e:
            article.extraction_error = f"Extraction failed: {str(e)}"

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main article content from parsed HTML."""
        # Try common article selectors
        content_selectors = [
            "article",
            "[role='main']",
            ".article-content",
            ".post-content",
            ".entry-content",
            ".story-body",
            ".article-body",
            ".content",
            "main",
        ]

        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # Get the largest element (likely the main content)
                element = max(elements, key=lambda x: len(x.get_text()))
                text = element.get_text(separator=" ", strip=True)
                if len(text) > 200:  # Minimum content length
                    return self._clean_text(text)

        # Fallback: try to find paragraphs
        paragraphs = soup.find_all("p")
        if paragraphs:
            content = " ".join(p.get_text(strip=True) for p in paragraphs)
            content = self._clean_text(content)
            if len(content) > 200:
                return content

        return ""

    def _extract_metadata(self, article: NewsArticle, soup: BeautifulSoup) -> None:
        """Extract additional metadata from the article."""
        # Try to extract author
        author_selectors = [
            "[name='author']",
            ".author",
            ".byline",
            "[rel='author']",
            ".article-author",
        ]

        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get("content") or element.get_text(strip=True)
                if author:
                    article.author = self._clean_text(author)
                    break

        # Try to extract published date
        date_selectors = [
            "[name='article:published_time']",
            "[name='publishdate']",
            "[name='date']",
            ".published",
            ".date",
            "time[datetime]",
        ]

        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date_str = (
                    element.get("content")
                    or element.get("datetime")
                    or element.get_text(strip=True)
                )
                if date_str:
                    try:
                        # Try to parse the date (this is a simplified approach)
                        from datetime import datetime

                        # Common date patterns
                        for fmt in [
                            "%Y-%m-%dT%H:%M:%S",
                            "%Y-%m-%d %H:%M:%S",
                            "%Y-%m-%d",
                            "%B %d, %Y",
                            "%b %d, %Y",
                        ]:
                            try:
                                article.published_date = datetime.strptime(
                                    date_str[:19], fmt
                                )
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass
                    break

        # Extract keywords/tags
        keywords_element = soup.select_one("[name='keywords']")
        if keywords_element:
            keywords = keywords_element.get("content", "")
            if keywords:
                article.tags = [
                    tag.strip() for tag in keywords.split(",") if tag.strip()
                ]

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common unwanted patterns
        text = re.sub(
            r"(Subscribe to|Sign up for|Follow us on).*", "", text, flags=re.IGNORECASE
        )
        text = re.sub(
            r"(Advertisement|Sponsored content).*", "", text, flags=re.IGNORECASE
        )

        return text.strip()

    def get_trending_topics(self, limit: int = 10) -> List[NewsArticle]:
        """Get trending news topics."""
        trending_queries = [
            "breaking news today",
            "latest news",
            "trending news",
        ]

        all_articles = []
        for query in trending_queries:
            try:
                articles = self.search_news(query, limit=limit // len(trending_queries))
                all_articles.extend(articles)
            except Exception as e:
                logger.warning(f"Failed to get trending news for '{query}': {e}")

        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)

        return unique_articles[:limit]


def main():
    """CLI interface for the news aggregator."""
    parser = argparse.ArgumentParser(
        description="Aggregate news from Google search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python google_news_aggregator.py "artificial intelligence"
  python google_news_aggregator.py "climate change" --limit 5 --no-content
  python google_news_aggregator.py --trending

Environment Variables:
  SERPAPI_KEY: Your SerpAPI key (required)
        """,
    )

    parser.add_argument("query", nargs="?", help="Search query (omit for trending)")

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of articles to return (default: 5)",
    )

    parser.add_argument(
        "--no-content",
        action="store_true",
        help="Skip content extraction (faster)",
    )

    parser.add_argument(
        "--trending",
        action="store_true",
        help="Get trending news instead of searching",
    )

    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--api-key", help="SerpAPI key (overrides SERPAPI_KEY environment variable)"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if not args.query and not args.trending:
        parser.error("Either provide a search query or use --trending")

    try:
        # Initialize the aggregator
        aggregator = GoogleNewsAggregator(api_key=args.api_key)

        # Get articles
        if args.trending:
            articles = aggregator.get_trending_topics(limit=args.limit)
        else:
            articles = aggregator.search_news(
                query=args.query,
                limit=args.limit,
                extract_content=not args.no_content,
            )

        if not articles:
            print("No articles found.", file=sys.stderr)
            return 1

        # Output results
        if args.format == "json":
            output = {
                "query": args.query or "trending",
                "total_articles": len(articles),
                "articles": [article.to_dict() for article in articles],
            }
            print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
        else:
            query_text = args.query or "trending news"
            print(f"News articles for: {query_text}")
            print(f"Found {len(articles)} articles")
            print("=" * 80)

            for i, article in enumerate(articles, 1):
                print(f"\n{i}. {article.title}")
                print(f"   URL: {article.url}")
                print(f"   Domain: {article.domain}")

                if article.author:
                    print(f"   Author: {article.author}")

                if article.published_date:
                    print(f"   Published: {article.published_date}")

                print(f"   Snippet: {article.snippet}")

                if article.content and len(article.content) > 0:
                    content_preview = (
                        article.content[:300] + "..."
                        if len(article.content) > 300
                        else article.content
                    )
                    print(f"   Content: {content_preview}")
                    print(f"   Word count: {article.word_count}")

                if article.tags:
                    print(f"   Tags: {', '.join(article.tags)}")

                if not article.extraction_success and article.extraction_error:
                    print(f"   Extraction error: {article.extraction_error}")

                print("-" * 80)

        return 0

    except GoogleSearchError as e:
        print(f"Search error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
