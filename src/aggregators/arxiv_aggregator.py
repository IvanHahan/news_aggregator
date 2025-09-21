import xml.etree.ElementTree as ET

import feedparser
import requests

from data_model import Paper

from .base_aggregator import BaseAggregator


class ArxivAggregator(BaseAggregator):
    def __init__(self, max_entries=10):
        self.max_entries = max_entries

    def poll(self) -> list[dict]:
        return fetch_arxiv_atom(self.max_entries)
        # return parse_arxiv_feed(self.feed_url, self.max_entries)


def fetch_arxiv_atom(query="cat:cs.AI", start=0, max_results=5):
    url = f"http://export.arxiv.org/api/query?search_query={query}&start={start}&max_results={max_results}&sortBy=lastUpdatedDate&sortOrder=descending"
    response = requests.get(url)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    papers = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns).text.strip()
        summary = entry.find("atom:summary", ns).text.strip()
        link = entry.find("atom:id", ns).text.strip()
        authors = [
            a.find("atom:name", ns).text.strip()
            for a in entry.findall("atom:author", ns)
        ]
        published = entry.find("atom:published", ns).text.strip()
        updated = entry.find("atom:updated", ns).text.strip()

        papers.append(
            Paper(
                title=title,
                authors=authors,
                link=link,
                summary=summary,
                published=published,
                updated=updated,
            )
        )

    return papers


def parse_arxiv_feed(feed_url="https://rss.arxiv.org/rss/cs.AI", max_entries=10):
    """
    Fetch and parse Arxiv RSS feed.
    Returns a list of papers with title, authors, link, and summary.
    """
    feed = feedparser.parse(feed_url)
    papers = []

    for entry in feed.entries[:max_entries]:
        # Extract authors
        authors = (
            [author.name for author in entry.authors]
            if hasattr(entry, "authors")
            else []
        )

        # Extract summary/abstract
        summary = entry.summary if hasattr(entry, "summary") else ""

        paper = {
            "title": entry.title,
            "authors": authors,
            "link": entry.link,
            "summary": summary,
        }
        papers.append(paper)

    return papers


if __name__ == "__main__":
    aggregator = ArxivAggregator()
    papers = aggregator.poll()
    for paper in papers:
        print(f"Title: {paper['title']}")
        print(f"Authors: {', '.join(paper['authors'])}")
        print(f"Link: {paper['link']}")
        print(f"Summary: {paper['summary']}\n")
