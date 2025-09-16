import asyncio

from telethon import TelegramClient

from .base_publisher import BasePublisher


class TelegramPublisher(BasePublisher):
    def __init__(
        self, api_id: int, api_hash: str, telegram_bot_token: str, channels: list[str]
    ):
        self.channels = channels
        self.telegram_bot_token = telegram_bot_token
        self.api_id = api_id
        self.api_hash = api_hash

    def publish(self, content: str) -> None:
        asyncio.run(self._publish_to_all_channels(content))

    async def _publish_to_all_channels(self, content: str) -> None:
        async with TelegramClient(
            "telegram_publisher", self.api_id, self.api_hash
        ) as client:
            for channel in self.channels:
                await client.send_message(
                    await client.get_input_entity(channel), content
                )
