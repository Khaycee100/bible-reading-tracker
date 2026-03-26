from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ReadChapter(db.Model):
    __tablename__ = "read_chapters"
    id = db.Column(db.Integer, primary_key=True)
    user_key = db.Column(db.String(120), index=True, nullable=False)
    book = db.Column(db.String(20), index=True, nullable=False)
    chapter = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_key", "book", "chapter", name="uq_user_book_chapter"),
    )
