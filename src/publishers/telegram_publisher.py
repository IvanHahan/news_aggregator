import asyncio

from pyrogram import Client

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
        async with Client(
            "telegram_publisher",
            api_id=self.api_id,
            api_hash=self.api_hash,
            bot_token=self.telegram_bot_token,
        ) as client:
            for channel in self.channels:
                await client.send_message("@hahanov_ai", content)
