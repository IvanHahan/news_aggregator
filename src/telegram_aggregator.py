import os

from telethon import TelegramClient, events

from .news_summarizer import NewsSummarizer

bot = TelegramClient(
    "telegram_aggregator",
    api_id=os.getenv("TELEGRAM_API_ID"),
    api_hash=os.getenv("TELEGRAM_API_HASH"),
)


@bot.on(events.NewMessage(chats=["@ai_machinelearning_big_data"]))
async def handler(event):
    news_summarizer = NewsSummarizer()
    summary = news_summarizer.run(event.message.text, language="Ukrainian")
    entity = await bot.get_entity("https://t.me/+mp_F_MoCIyQ3NjA6")
    await bot.send_message(entity, summary)


if __name__ == "__main__":
    bot.start()
    bot.run_until_disconnected()
