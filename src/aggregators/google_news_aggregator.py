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
import sys
from typing import List, Optional
from urllib.parse import urlparse

from loguru import logger

from data_model import LinkContent

# Import our existing Google search functionality
from google_search import GoogleSearchError, search_google
from link_explorer import LinkExplorer

from .base_aggregator import BaseAggregator


class GoogleNewsAggregator(BaseAggregator):
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
        self.delay_between_requests = delay_between_requests

        # Initialize link explorer for content extraction
        self.link_explorer = LinkExplorer(
            request_timeout=request_timeout, user_agent=user_agent
        )

    def poll(self, query="AI news"):
        return self.search_news(query=query)

    def search_news(
        self,
        query: str,
        limit: int = 10,
        extract_content: bool = True,
        news_specific: bool = True,
    ) -> List[LinkContent]:
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
                if self.link_explorer.should_skip_domain(result.url):
                    logger.debug(f"Skipping domain: {result.url}")
                    continue

                article = LinkContent(
                    title=result.title,
                    url=result.url,
                    text=result.snippet,
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

    def _extract_content_batch(self, articles: List[LinkContent]) -> None:
        """Extract content from a batch of articles using LinkExplorer."""
        logger.info(f"Extracting content from {len(articles)} articles")

        # Extract URLs for batch processing
        urls = [article.url for article in articles]

        # Use LinkExplorer for batch content extraction
        extracted_contents = self.link_explorer.extract_content_batch(
            urls, delay_between_requests=self.delay_between_requests
        )

        # Map results back to articles
        for article, extracted in zip(articles, extracted_contents):
            if extracted.extraction_error is None:
                article.text = extracted.text
            else:
                article.extraction_error = extracted.extraction_error

    def get_trending_topics(self, limit: int = 10) -> List[LinkContent]:
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
