import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pyrogram import Client

from .base_aggregator import BaseAggregator


@dataclass
class TelegramMessage:
    """Represents a message from a Telegram channel."""

    channel: str
    text: str
    timestamp: datetime
    message_id: int
    sender_id: Optional[int] = None
    media_type: Optional[str] = None


class TelegramAggregator(BaseAggregator):
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        channels: list[str],
        link_explorer,
        limit: int = 10,
    ):
        self.client = Client(
            "telegram_aggregator",
            api_id or os.environ.get("TELEGRAM_API_ID"),
            api_hash or os.environ.get("TELEGRAM_API_HASH"),
        )
        self.channels = channels
        self.link_explorer = link_explorer
        self.limit = limit

    def poll(self) -> list[str]:
        items = []
        try:
            for channel in self.channels:
                messages = self.client.get_messages(channel, limit=self.limit)
                for msg in messages:
                    links = self._get_links_from_message(msg)
                    links = [self.link_explorer.extract_content(l) for l in links]
                    items.extend(links)
        except Exception as e:
            print(f"Error retrieving messages: {e}")
        return items

    def _get_links_from_message(self, message: TelegramMessage) -> list[str]:
        hyperlinks = []
        for entity in message.get_entities_text():
            if isinstance(entity[0], MessageEntityUrl):
                hyperlinks.append(entity[1])
        return hyperlinks
