import requests
from bs4 import BeautifulSoup

from data_model import News

from .base_aggregator import BaseAggregator


class VentureBeatAggregator(BaseAggregator):
    def __init__(self, max_articles=10):
        self.max_articles = max_articles

    def poll(self) -> list[News]:
        url = "https://venturebeat.com/ai/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # VentureBeat article blocks are in <a> tags with 'ArticleListItem' in class
        articles = soup.find_all("article")
        news = []
        for article in articles[:5]:  # get first 5 articles
            title_tag = article.find("header")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link_tag = article.find("a", href=True)
            link = link_tag["href"] if link_tag else "No link found"
            if not link.startswith("http"):
                link = "https://venturebeat.com" + link
            summary_tag = article.find("p")
            summary = summary_tag.get_text(strip=True) if summary_tag else "No summary"

            news.append(News(title=title, summary=summary, link=link))
        return news
