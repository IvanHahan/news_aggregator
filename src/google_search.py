"""Google Search utility using SerpAPI.

Provides a simple way to search Google using SerpAPI and get structured results.
Requires a SerpAPI key which can be obtained from https://serpapi.com/

Usage (programmatic):
    from google_search import search_google
    results = search_google("artificial intelligence", limit=10)
    for result in results:
        print(result.title, result.url, result.snippet)

CLI:
    python google_search.py "quantum computing" --limit 5

Environment Variables:
    SERPAPI_KEY: Your SerpAPI key (required)

Design goals:
 - Clean API similar to the news module
 - Graceful error handling
 - Structured result objects
 - CLI interface for easy testing
 - Configurable result limits

Limitations:
 - Requires SerpAPI key (paid service after free tier)
 - Rate limited by SerpAPI plan
 - Only returns organic search results (no ads, knowledge panels, etc.)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

from serpapi import GoogleSearch

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SearchResult:
    """Represents a single Google search result."""

    title: str
    url: str
    snippet: str
    position: int
    domain: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert the result to a dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "position": self.position,
            "domain": self.domain,
        }


class GoogleSearchError(Exception):
    """Custom exception for Google search errors."""

    pass


def search_google(
    query: str,
    limit: int = 10,
    api_key: Optional[str] = None,
    country: str = "us",
    language: str = "en",
) -> List[SearchResult]:
    """
    Search Google using SerpAPI and return structured results.

    Args:
        query: The search query
        limit: Maximum number of results to return (default: 10, max: 100)
        api_key: SerpAPI key (if None, will try to get from SERPAPI_KEY env var)
        country: Country code for search localization (default: "us")
        language: Language code for search (default: "en")

    Returns:
        List of SearchResult objects

    Raises:
        GoogleSearchError: If the search fails or API key is missing
    """
    # Get API key from parameter or environment
    if api_key is None:
        api_key = os.getenv("SERPAPI_KEY")

    if not api_key:
        raise GoogleSearchError(
            "SerpAPI key is required. Set SERPAPI_KEY environment variable or pass api_key parameter. "
            "Get your key at https://serpapi.com/"
        )

    # Limit the number of results to reasonable bounds
    limit = min(max(1, limit), 100)

    try:
        # Initialize the search
        search = GoogleSearch(
            {
                "q": query,
                "api_key": api_key,
                "num": limit,
                "gl": country,
                "hl": language,
            }
        )

        # Get the results
        results = search.get_dict()

        # Check for errors in the response
        if "error" in results:
            raise GoogleSearchError(f"SerpAPI error: {results['error']}")

        # Extract organic results
        organic_results = results.get("organic_results", [])

        if not organic_results:
            logger.warning(f"No organic results found for query: {query}")
            return []

        # Convert to SearchResult objects
        search_results = []
        for i, result in enumerate(organic_results[:limit]):
            try:
                # Extract domain from URL
                domain = None
                if "link" in result:
                    try:
                        from urllib.parse import urlparse

                        domain = urlparse(result["link"]).netloc
                    except Exception:
                        pass

                search_result = SearchResult(
                    title=result.get("title", ""),
                    url=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    position=result.get("position", i + 1),
                    domain=domain,
                )
                search_results.append(search_result)

            except Exception as e:
                logger.warning(f"Error parsing result {i}: {e}")
                continue

        logger.info(
            f"Successfully retrieved {len(search_results)} results for query: {query}"
        )
        return search_results

    except Exception as e:
        if isinstance(e, GoogleSearchError):
            raise
        raise GoogleSearchError(f"Search failed: {str(e)}")


def main():
    """CLI interface for Google search."""
    parser = argparse.ArgumentParser(
        description="Search Google using SerpAPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python google_search.py "artificial intelligence"
  python google_search.py "machine learning" --limit 5
  python google_search.py "quantum computing" --country uk --language en

Environment Variables:
  SERPAPI_KEY: Your SerpAPI key (required)
        """,
    )

    parser.add_argument("query", help="Search query")

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results to return (default: 10, max: 100)",
    )

    parser.add_argument(
        "--country",
        default="us",
        help="Country code for search localization (default: us)",
    )

    parser.add_argument(
        "--language", default="en", help="Language code for search (default: en)"
    )

    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
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

    try:
        # Perform the search
        results = search_google(
            query=args.query,
            limit=args.limit,
            api_key=args.api_key,
            country=args.country,
            language=args.language,
        )

        if not results:
            print("No results found.", file=sys.stderr)
            return 1

        # Output results
        if args.format == "json":
            output = {
                "query": args.query,
                "total_results": len(results),
                "results": [result.to_dict() for result in results],
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            print(f"Search results for: {args.query}")
            print(f"Found {len(results)} results")
            print("-" * 80)

            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title}")
                print(f"   URL: {result.url}")
                if result.domain:
                    print(f"   Domain: {result.domain}")
                print(f"   Snippet: {result.snippet}")
                print()

        return 0

    except GoogleSearchError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nSearch cancelled.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
