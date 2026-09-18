"""Веб-приложение Personal Finance Tracker."""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    """Возвращает приветствие на главной странице."""
    return "Finance Tracker API работает!"


if __name__ == "__main__":
    app.run(debug=True)
