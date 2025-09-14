import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from telethon import TelegramClient, events

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
    def __init__(self, api_id: int, api_hash: str, channels: list[str]):
        self.client = TelegramClient("telegram_aggregator", api_id, api_hash)
        self.channels = channels
        self.queue: asyncio.Queue[TelegramMessage] = asyncio.Queue()
        self._task = None

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

        msg = TelegramMessage(
            channel=channel_name,
            text=event.message.message or "",
            timestamp=event.message.date,
            message_id=event.message.id,
            sender_id=event.sender_id,
            media_type=media_type,
        )
        await self.queue.put(msg)

    async def start_background(self):
        await self.client.start()
        self._task = asyncio.create_task(self.client.run_until_disconnected())
        print(f"✅ Listening to {len(self.channels)} channels...")

    def poll(self) -> list[TelegramMessage]:
        items = []
        while not self.queue.empty():
            items.append(self.queue.get_nowait())
        return items

    def peek(self) -> list[TelegramMessage]:
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
