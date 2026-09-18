from flask import Flask
from models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_tracker.db'
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route("/")
def home():
    return "Finance Tracker API работает!"

if __name__ == "__main__":
    app.run(debug=True)
    