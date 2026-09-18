from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' или 'expense'
    date = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(200))

    category = db.relationship('Category', backref='transactions')

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), unique=True, nullable=False)
    monthly_limit = db.Column(db.Float, nullable=False)

    category = db.relationship('Category', backref='budget', uselist=False)
    