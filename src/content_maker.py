import os

from langchain_openai.chat_models import ChatOpenAI

from aggregators import ArxivAggregator, GoogleNewsAggregator
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
        for aggregator in self.aggregators:
            news = aggregator.poll()
            if news:
                for n in news:
                    self.news_database.delete_extra()
                    processed_news = self.news_processor.run(n.text, n.url)
                    for publisher in self.publishers:
                        publisher.publish(processed_news)
                    return

    @classmethod
    def build(cls):
        link_explorer = LinkExplorer()
        google_news_aggregator = GoogleNewsAggregator()
        telegram_publisher = TelegramPublisher(
            channels=["https://t.me/+mp_F_MoCIyQ3NjA6"],
            api_hash=os.getenv("TELEGRAM_API_HASH"),
            api_id=os.getenv("TELEGRAM_API_ID"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        )
        news_summarizer = NewsSummarizer(ChatOpenAI(model="gpt-4.1-nano"))
        return cls(
            aggregators=[ArxivAggregator(), google_news_aggregator],
            publishers=[telegram_publisher],
            news_processor=news_summarizer,
        )
