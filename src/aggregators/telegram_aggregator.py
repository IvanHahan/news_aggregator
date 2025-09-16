import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityUrl

from data_model import NewsArticle

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
        self.client = TelegramClient("telegram_aggregator", api_id, api_hash)
        self.channels = channels
        self.queue: asyncio.Queue[TelegramMessage] = asyncio.Queue()
        self._task = None
        self.link_explorer = link_explorer
        self.limit = limit

        # Register handler once
        self.client.add_event_handler(
            self._message_handler, events.NewMessage(chats=self.channels)
        )

    async def _message_handler(self, event):
        channel_name = (
            getattr(event.chat, "username", None)
            or getattr(event.chat, "title", None)
            or str(event.chat_id)
        )

        media_type = type(event.message.media).__name__ if event.message.media else None

        msg = NewsArticle(
            title=event.message.message or "",
            url=f"tg://{channel_name}/{event.message.id}",
            snippet=event.message.message or "",
            content=event.message.message or "",
            author=event.sender_id,
            published_date=event.message.date,
            domain=channel_name,
            word_count=len(event.message.message.split()),
            tags=[channel_name],
        )
        await self.queue.put(msg)

    async def start_background(self):
        await self.client.start()
        self._task = asyncio.create_task(self.client.run_until_disconnected())
        print(f"✅ Listening to {len(self.channels)} channels...")

    def poll(self) -> list[str]:
        items = []
        try:
            for channel in self.channels:
                messages = asyncio.run(self._get_messages(channel))
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

    async def _get_messages(self, channel) -> list[TelegramMessage]:
        async with self.client:
            return await self.client.get_messages(channel, limit=self.limit)

    def peek(self) -> list[NewsArticle]:
        return list(self.queue._queue)  # not ideal but works

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.client.disconnect()

    def is_running(self) -> bool:
        return self.client.is_connected()
