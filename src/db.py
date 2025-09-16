from peewee import CharField, DateTimeField, Model, SqliteDatabase, TextField

db = SqliteDatabase("news.db")


class BaseModel(Model):
    class Meta:
        database = db

    date = DateTimeField()

    @classmethod
    def evict_old(cls, days: int):
        """Evict records older than the specified number of days."""
        from datetime import datetime, timedelta

        threshold_date = datetime.now() - timedelta(days=days)
        query = cls.delete().where(cls.date < threshold_date)
        deleted_count = query.execute()
        return deleted_count

    @classmethod
    def evict_excess(cls, max_records: int):
        """Evict oldest records to maintain a maximum number of records."""
        total_count = cls.select().count()
        if total_count <= max_records:
            return 0

        excess_count = total_count - max_records
        subquery = cls.select().order_by(cls.date.asc()).limit(excess_count)

        query = cls.delete().where(cls.id.in_(subquery))
        deleted_count = query.execute()
        return deleted_count


class NewsArticle(BaseModel):
    title = CharField(null=True)
    url = CharField(unique=True)
    content = TextField()

    @classmethod
    def has_url(cls, url: str) -> bool:
        """Check if an article with the given URL already exists."""
        return cls.select().where(cls.url == url).exists()


db.connect()
db.create_tables([NewsArticle])
