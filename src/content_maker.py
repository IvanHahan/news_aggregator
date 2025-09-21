import os
import random

from langchain_openai.chat_models import ChatOpenAI

from aggregators import (
    ArxivAggregator,
    HFTrendingPapersAggregator,
    VentureBeatAggregator,
)
from db import NewsDatabase
from link_explorer import LinkExplorer
from news_summarizer import NewsSummarizer
from publishers import TelegramPublisher


class ContentMaker:
    def __init__(self, aggregators, publishers, news_processor):
        self.aggregators = aggregators
        self.publishers = publishers
        self.news_processor = news_processor
        self.news_database = NewsDatabase()

    def run(self):
        all_news = []
        for aggregator in self.aggregators:
            news = aggregator.poll()
            all_news.extend(news)

        new_news = self.filter_news(all_news)

        # papers = [n for n in new_news if isinstance(n, Paper)]
        # news = [n for n in new_news if isinstance(n, News)]
        news = random.choice(new_news)  # Select a random item from new_news
        self.news_database.insert_document(news.to_dict())
        self.news_database.delete_extra()
        processed_news = self.news_processor.run(news.to_dict(), news.link)
        for publisher in self.publishers:
            publisher.publish(processed_news)

    def filter_news(self, news):
        return [n for n in news if len(self.news_database.query({"link": n.link})) == 0]

    @classmethod
    def build(cls):
        link_explorer = LinkExplorer()
        telegram_publisher = TelegramPublisher(
            channels=["https://t.me/+mp_F_MoCIyQ3NjA6"],
            api_hash=os.getenv("TELEGRAM_API_HASH"),
            api_id=os.getenv("TELEGRAM_API_ID"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        )
        news_summarizer = NewsSummarizer(ChatOpenAI(model="gpt-4.1-nano"))
        return cls(
            aggregators=[
                VentureBeatAggregator(),
                HFTrendingPapersAggregator(),
                ArxivAggregator(),
            ],
            publishers=[telegram_publisher],
            news_processor=news_summarizer,
        )
