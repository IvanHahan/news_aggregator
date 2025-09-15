import asyncio

from telethon import TelegramClient

from .base_publisher import BasePublisher


class TelegramPublisher(BasePublisher):
    def __init__(
        self, api_id: int, api_hash: str, telegram_bot_token: str, channels: list[str]
    ):
        self.client = TelegramClient("telegram_publisher", api_id, api_hash)
        self.channels = channels
        self.telegram_bot_token = telegram_bot_token

    def publish(self, content: str) -> None:
        for channel in self.channels:
            asyncio.run(self._publish_to_channel(channel, content))

    async def _publish_to_channel(self, channel: str, content: str) -> None:
        async with self.client:
            await self.client.send_message(
                await self.client.get_input_entity(channel), content
            )
