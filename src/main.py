from dotenv import load_dotenv

from content_maker import ContentMaker

if __name__ == "__main__":
    load_dotenv()
    content_maker = ContentMaker.build()
    content_maker.run()
