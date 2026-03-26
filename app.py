import random
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, ReadChapter


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    os.makedirs(app.instance_path, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(app.instance_path, 'app.sqlite3')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

    # Helper functions
    def get_chapter(book):
        return random.randint(1, 150 if book == "psalms" else 31)

    def normalize_user_key(full_name):
        full_name = full_name.strip().lower()
        first_name = full_name.split()[0] if full_name else "Friend"
        key = "_".join(full_name.split())
        return key, first_name.title()

    # Routes
    @app.get("/")
    def home():
        return render_template("home.html")

    @app.post("/start")
    def start():
        full_name = request.form.get("full_name", "").strip()
        if not full_name or len(full_name.split()) < 2:
            flash("Please enter your FIRST and LAST name (e.g., 'Kelechi Okoroafor').", "error")
            return redirect(url_for("home"))
        user_key, first_name = normalize_user_key(full_name)
        session["user_key"] = user_key
        session["first_name"] = first_name
        return redirect(url_for("dashboard"))

    @app.get("/app")
    def dashboard():
        if "user_key" not in session:
            return redirect(url_for("home"))
        return render_template("dashboard.html", first_name=session["first_name"])

    @app.post("/suggest")
    def suggest():
        if "user_key" not in session:
            return redirect(url_for("home"))
        choice = request.form.get("book", "").lower().strip()
        if choice not in ["psalm", "psalms", "proverb", "proverbs"]:
            flash("Please choose Psalms or Proverbs.", "error")
            return redirect(url_for("dashboard"))

        book = "psalms" if "psalm" in choice else "proverbs"
        user_key = session["user_key"]

        read_set = {r.chapter for r in ReadChapter.query.filter_by(user_key=user_key, book=book).all()}
        max_chapter = 150 if book == "psalms" else 31
        if len(read_set) >= max_chapter:
            flash(f"You've read all {max_chapter} chapters of {book.title()}! 🎉", "success")
            return redirect(url_for("report"))

        chapter = get_chapter(book)
        while chapter in read_set:
            chapter = get_chapter(book)

        session["pending_book"] = book
        session["pending_chapter"] = chapter

        return render_template(
            "suggest.html",
            first_name=session.get("first_name", "Friend"),
            book=book,
            chapter=chapter,
        )

    @app.post("/confirm")
    def confirm():
        if "user_key" not in session:
            return redirect(url_for("home"))
        book = session.get("pending_book")
        chapter = session.get("pending_chapter")
        if not book or not chapter:
            flash("No suggestion to confirm.", "error")
            return redirect(url_for("dashboard"))

        user_key = session["user_key"]
        existing = ReadChapter.query.filter_by(user_key=user_key, book=book, chapter=chapter).first()
        if not existing:
            db.session.add(ReadChapter(user_key=user_key, book=book, chapter=chapter))
            db.session.commit()

        session.pop("pending_book", None)
        session.pop("pending_chapter", None)
        flash(f"Marked {book.title()} Chapter {chapter} as read ✅", "success")
        return redirect(url_for("dashboard"))

    @app.get("/report")
    def report():
        if "user_key" not in session:
            return redirect(url_for("home"))
        user_key = session["user_key"]
        psalms = [r.chapter for r in ReadChapter.query.filter_by(user_key=user_key, book="psalms").order_by(ReadChapter.chapter).all()]
        proverbs = [r.chapter for r in ReadChapter.query.filter_by(user_key=user_key, book="proverbs").order_by(ReadChapter.chapter).all()]
        return render_template(
            "report.html",
            first_name=session.get("first_name", "Friend"),
            psalms=psalms,
            proverbs=proverbs,
            psalms_done=len(psalms),
            proverbs_done=len(proverbs),
            psalms_total=150,
            proverbs_total=31,
        )

    @app.get("/reset")
    def reset():
        if "user_key" in session:
            ReadChapter.query.filter_by(user_key=session["user_key"]).delete()
            db.session.commit()
            flash("Your progress has been reset.", "info")
        return redirect(url_for("dashboard"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
