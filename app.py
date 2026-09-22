from flask import Flask, request, jsonify
from datetime import datetime
from models import db, Category, Transaction

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_tracker.db'
db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return "Finance Tracker API работает!"


@app.route("/categories", methods=["GET"])
def get_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories])


@app.route("/transactions", methods=["GET"])
def get_transactions():
    transactions = Transaction.query.all()
    return jsonify([t.to_dict() for t in transactions])


@app.route("/transactions/<int:transaction_id>", methods=["GET"])
def get_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({"error": "Транзакция не найдена"}), 404
    return jsonify(transaction.to_dict())


@app.route("/transactions", methods=["POST"])
def create_transaction():
    data = request.get_json()

    required_fields = ["category_id", "amount", "type", "date"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Поле {field} обязательно"}), 400

    category = Category.query.get(data["category_id"])
    if not category:
        return jsonify({"error": "Категория не найдена"}), 404

    transaction = Transaction(
        category_id=data["category_id"],
        amount=data["amount"],
        type=data["type"],
        date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
        note=data.get("note")
    )
    db.session.add(transaction)
    db.session.commit()

    return jsonify(transaction.to_dict()), 201


@app.route("/transactions/<int:transaction_id>", methods=["PUT"])
def update_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({"error": "Транзакция не найдена"}), 404

    data = request.get_json()
    if "category_id" in data:
        transaction.category_id = data["category_id"]
    if "amount" in data:
        transaction.amount = data["amount"]
    if "type" in data:
        transaction.type = data["type"]
    if "date" in data:
        transaction.date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    if "note" in data:
        transaction.note = data["note"]

    db.session.commit()
    return jsonify(transaction.to_dict())


@app.route("/transactions/<int:transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({"error": "Транзакция не найдена"}), 404

    db.session.delete(transaction)
    db.session.commit()
    return jsonify({"message": "Транзакция удалена"}), 200


if __name__ == "__main__":
    app.run(debug=True)
    