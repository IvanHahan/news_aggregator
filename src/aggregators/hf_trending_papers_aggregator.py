import requests
from bs4 import BeautifulSoup

from data_model import Paper

from .base_aggregator import BaseAggregator

URL = "https://huggingface.co/papers/trending"


class HFTrendingPapersAggregator(BaseAggregator):
    def __init__(self, max_papers=10):
        self.max_papers = max_papers

    def poll(self) -> list[dict]:
        response = requests.get(URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        papers = []

        # Each trending paper is inside a div with class "PaperCard"
        for card in soup.select("article"):
            title_tag = card.select_one("h3")  # usually the title is in <h3>
            title = title_tag.get_text(strip=True) if title_tag else "No title"

            link_tag = card.select_one("a[href]")
            link = "https://huggingface.co" + link_tag["href"] if link_tag else None
            summary_tag = card.select_one("p")
            summary = summary_tag.get_text(strip=True) if summary_tag else "No summary"
            authors_tag = card.select_one("p")
            authors = authors_tag.get_text(strip=True) if authors_tag else "Unknown"
            # Find the published date by looking for text after "Published on"
            published_element = card.find(
                string=lambda text: text and "Published on" in text
            )
            if published_element:
                published_text = published_element.strip()
                # Extract the date part after "Published on"
                published = published_text.split("Published on")[-1].strip()
            else:
                published = "Unknown"

            papers.append(
                Paper(
                    title=title,
                    authors=[authors],
                    link=link,
                    summary=summary,
                    published=published,
                )
            )

        return papers


if __name__ == "__main__":
    aggregator = HFTrendingPapersAggregator(max_papers=5)
    trending_papers = aggregator.poll()
    for paper in trending_papers:
        print(f"Title: {paper['title']}")
        print(f"Authors: {', '.join(paper['authors'])}")
        print(f"Link: {paper['link']}")
        print(f"Summary: {paper['summary']}\n")
