from datetime import date, datetime

from flask import Flask, request, jsonify
from sqlalchemy import func

from models import db, Category, Transaction, Budget
from telegram_notify import send_telegram_message

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_tracker.db'
app.json.ensure_ascii = False
db.init_app(app)

with app.app_context():
    db.create_all()


def parse_date(value):
    """Преобразует строку вида 2026-09-23 в дату. Возвращает None при неверном формате."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


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
    transaction = db.session.get(Transaction, transaction_id)
    if not transaction:
        return jsonify({"error": "Транзакция не найдена"}), 404
    return jsonify(transaction.to_dict())


@app.route("/transactions", methods=["POST"])
def create_transaction():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Ожидается тело запроса в формате JSON"}), 400

    required_fields = ["category_id", "amount", "type", "date"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Поле {field} обязательно"}), 400

    if data["type"] not in ("income", "expense"):
        return jsonify({"error": "Поле type должно быть income или expense"}), 400

    transaction_date = parse_date(data["date"])
    if not transaction_date:
        return jsonify({"error": "Поле date должно быть в формате ГГГГ-ММ-ДД"}), 400

    category = db.session.get(Category, data["category_id"])
    if not category:
        return jsonify({"error": "Категория не найдена"}), 404

    transaction = Transaction(
        category_id=data["category_id"],
        amount=data["amount"],
        type=data["type"],
        date=transaction_date,
        note=data.get("note")
    )
    db.session.add(transaction)
    db.session.commit()

    if transaction.type == "expense":
        check_budget_and_notify(transaction.category_id)

    return jsonify(transaction.to_dict()), 201


@app.route("/transactions/<int:transaction_id>", methods=["PUT"])
def update_transaction(transaction_id):
    transaction = db.session.get(Transaction, transaction_id)
    if not transaction:
        return jsonify({"error": "Транзакция не найдена"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Ожидается тело запроса в формате JSON"}), 400

    if "category_id" in data:
        category = db.session.get(Category, data["category_id"])
        if not category:
            return jsonify({"error": "Категория не найдена"}), 404
        transaction.category_id = data["category_id"]
    if "amount" in data:
        transaction.amount = data["amount"]
    if "type" in data:
        if data["type"] not in ("income", "expense"):
            return jsonify({"error": "Поле type должно быть income или expense"}), 400
        transaction.type = data["type"]
    if "date" in data:
        transaction_date = parse_date(data["date"])
        if not transaction_date:
            return jsonify({"error": "Поле date должно быть в формате ГГГГ-ММ-ДД"}), 400
        transaction.date = transaction_date
    if "note" in data:
        transaction.note = data["note"]

    db.session.commit()

    if transaction.type == "expense":
        check_budget_and_notify(transaction.category_id)

    return jsonify(transaction.to_dict())


@app.route("/transactions/<int:transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    transaction = db.session.get(Transaction, transaction_id)
    if not transaction:
        return jsonify({"error": "Транзакция не найдена"}), 404

    db.session.delete(transaction)
    db.session.commit()
    return jsonify({"message": "Транзакция удалена"}), 200


@app.route("/budgets", methods=["GET"])
def get_budgets():
    budgets = Budget.query.all()
    return jsonify([b.to_dict() for b in budgets])


@app.route("/budgets", methods=["POST"])
def create_budget():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Ожидается тело запроса в формате JSON"}), 400

    if "category_id" not in data or "monthly_limit" not in data:
        return jsonify({"error": "category_id и monthly_limit обязательны"}), 400

    if not isinstance(data["monthly_limit"], (int, float)) or data["monthly_limit"] <= 0:
        return jsonify({"error": "monthly_limit должен быть числом больше нуля"}), 400

    category = db.session.get(Category, data["category_id"])
    if not category:
        return jsonify({"error": "Категория не найдена"}), 404

    budget = Budget.query.filter_by(category_id=data["category_id"]).first()
    if budget:
        budget.monthly_limit = data["monthly_limit"]
    else:
        budget = Budget(category_id=data["category_id"], monthly_limit=data["monthly_limit"])
        db.session.add(budget)

    db.session.commit()
    return jsonify(budget.to_dict()), 201


def check_budget_and_notify(category_id):
    budget = Budget.query.filter_by(category_id=category_id).first()
    if not budget or not budget.monthly_limit:
        return

    start_of_month = date.today().replace(day=1)

    total_spent = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.category_id == category_id,
        Transaction.type == "expense",
        Transaction.date >= start_of_month
    ).scalar() or 0

    percent = (total_spent / budget.monthly_limit) * 100

    if percent >= 80:
        category = db.session.get(Category, category_id)
        send_telegram_message(
            f"⚠️ Бюджет по категории «{category.name}» израсходован на {percent:.0f}%: "
            f"{total_spent:.0f} из {budget.monthly_limit:.0f}"
        )


if __name__ == "__main__":
    app.run(debug=True)
