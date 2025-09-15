import os

from langchain_community.chat_models import ChatOpenAI

from aggregators import GoogleNewsAggregator, TelegramAggregator
from data_model import LinkContent, News
from link_explorer import LinkExplorer
from news_summarizer import NewsSummarizer
from publishers import TelegramPublisher


class ContentMaker:
    def __init__(self, aggregators, publishers, news_processor):
        self.aggregators = aggregators
        self.publishers = publishers
        self.news_processor = news_processor

    def run(self):
        for aggregator in self.aggregators:
            news = aggregator.poll()
            if news:
                for n in news:
                    if isinstance(n, News):
                        if news.links:
                            processed_news = self.news_processor.run(news.links[0].text)
                        else:
                            processed_news = self.news_processor.run(news.content)
                    elif isinstance(n, LinkContent):
                        processed_news = self.news_processor.run(n.text)
                    for publisher in self.publishers:
                        publisher.publish(processed_news)
                    break
                break

    @classmethod
    def build(cls):
        link_explorer = LinkExplorer()
        telegram_aggregator = TelegramAggregator(
            channels=["@ai_machinelearning_big_data"],
            api_hash=os.getenv("TELEGRAM_API_HASH"),
            api_id=os.getenv("TELEGRAM_API_ID"),
            link_explorer=link_explorer,
        )
        google_news_aggregator = GoogleNewsAggregator()
        telegram_publisher = TelegramPublisher(
            channels=["https://t.me/+mp_F_MoCIyQ3NjA6"],
            api_hash=os.getenv("TELEGRAM_API_HASH"),
            api_id=os.getenv("TELEGRAM_API_ID"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        )
        news_summarizer = NewsSummarizer(ChatOpenAI(model="gpt-4.1-nano"))
        return cls(
            aggregators=[telegram_aggregator, google_news_aggregator],
            publishers=[telegram_publisher],
            news_processor=news_summarizer,
        )
