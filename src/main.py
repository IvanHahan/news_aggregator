import time

from content_maker import ContentMaker

if __name__ == "__main__":
    content_maker = ContentMaker.build()
    while True:
        content_maker.run()
        time.sleep(30 * 60)  # Sleep for 30 minutes (1800 seconds)
