import os

from langchain_community.chat_models import ChatOpenAI

from aggregators import TelegramAggregator
from link_explorer import LinkExplorer
from news_summarizer import NewsSummarizer
from publishers import TelegramPublisher


class ContentMaker:
    def __init__(self, aggregators, publishers, news_processor):
        self.aggregators = aggregators
        self.publishers = publishers
        self.news_processor = news_processor
        self.cache = set()

    def run(self):
        for aggregator in self.aggregators:
            news = aggregator.poll()
            if news:
                news = news[0]
                processed_news = self.news_processor.run(news)
                for publisher in self.publishers:
                    publisher.publish(processed_news)

    @classmethod
    def build(cls):
        link_explorer = LinkExplorer(ChatOpenAI(model="gpt-4.1-nano"))
        telegram_aggregator = TelegramAggregator(
            channels=["@ai_machinelearning_big_data"],
            api_hash=os.getenv("TELEGRAM_API_HASH"),
            api_id=os.getenv("TELEGRAM_API_ID"),
            link_explorer=link_explorer,
        )
        telegram_publisher = TelegramPublisher(
            channels=["https://t.me/+mp_F_MoCIyQ3NjA6"],
            api_hash=os.getenv("TELEGRAM_API_HASH"),
            api_id=os.getenv("TELEGRAM_API_ID"),
        )
        news_summarizer = NewsSummarizer(ChatOpenAI(model="gpt-4.1-nano"))
        return cls(
            aggregators=[telegram_aggregator],
            publishers=[telegram_publisher],
            news_processor=news_summarizer,
        )
