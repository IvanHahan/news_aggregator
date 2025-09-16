import time

from dotenv import load_dotenv

from content_maker import ContentMaker

if __name__ == "__main__":
    load_dotenv()
    content_maker = ContentMaker.build()
    while True:
        content_maker.run()
        time.sleep(60 * 60)  # Sleep for 30 minutes (1800 seconds)
