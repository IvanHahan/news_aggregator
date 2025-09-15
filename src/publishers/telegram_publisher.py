from telethon import TelegramClient

from .base_publisher import BasePublisher


class TelegramPublisher(BasePublisher):
    def __init__(self, api_id: int, api_hash: str, channels: list[str]):
        self.client = TelegramClient("telegram_publisher", api_id, api_hash)
        self.channels = channels

    def publish(self, items: list[str]) -> None:
        for item in items:
            for channel in self.channels:
                self._publish_to_channel(channel, item)

    def _publish_to_channel(self, channel: str, item: str) -> None:
        self.client.send_message(self.client.get_entity(channel), item)
