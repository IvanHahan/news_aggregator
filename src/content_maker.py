from .aggregators import TelegramAggregator
from .news_summarizer import NewsSummarizer
from .publishers import TelegramPublisher


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
        telegram_aggregator = TelegramAggregator(
            channels=["@ai_machinelearning_big_data"]
        )
        telegram_publisher = TelegramPublisher(
            channels=["https://t.me/+mp_F_MoCIyQ3NjA6"]
        )
        news_summarizer = NewsSummarizer()
        return cls(
            aggregators=[telegram_aggregator],
            publishers=[telegram_publisher],
            news_processor=news_summarizer,
        )
