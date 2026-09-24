from flask import Flask, request, jsonify, render_template, redirect, url_for
from datetime import datetime, date
from sqlalchemy import func
from models import db, Category, Transaction, Budget
from telegram_notify import send_telegram_message
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for

def create_app(db_uri=None):
    app = Flask(__name__)

    db_uri = db_uri or os.getenv('DATABASE_URL', 'sqlite:///finance_tracker.db')
    # Render отдаёт адрес в формате postgres://, а SQLAlchemy ожидает postgresql://
    if db_uri.startswith('postgres://'):
        db_uri = db_uri.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    db.init_app(app)

def create_app(db_uri='sqlite:///finance_tracker.db'):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    db.init_app(app)

    with app.app_context():
        db.create_all()

    def check_budget_and_notify(category_id):
        budget = Budget.query.filter_by(category_id=category_id).first()
        if not budget:
            return
        start_of_month = date.today().replace(day=1)
        total_spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.category_id == category_id,
            Transaction.type == "expense",
            Transaction.date >= start_of_month
        ).scalar() or 0
        percent = (total_spent / budget.monthly_limit) * 100
        if percent >= 80:
            category = Category.query.get(category_id)
            send_telegram_message(
                f"⚠️ Бюджет по категории «{category.name}» израсходован на {percent:.0f}%: "
                f"{total_spent:.0f} из {budget.monthly_limit:.0f}"
            )

    @app.route("/health")
    def helth():
        return "Finance Tracker API работает!"
    
    @app.route("/", methods=["GET"])
    def index():
        transactions = Transaction.query.order_by(Transaction.date.desc()).all()
        categories = Category.query.all()
        budgets = {b.category_id: b.monthly_limit for b in Budget.query.all()}

        start_of_month = date.today().replace(day=1)
        spending = {}
        for cat in categories:
            total = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.category_id == cat.id,
                Transaction.type == "expense",
                Transaction.date >= start_of_month
            ).scalar() or 0
            spending[cat.id] = total

        return render_template(
            "index.html",
            transactions=transactions,
            categories=categories,
            budgets=budgets,
            spending=spending
        )

    @app.route("/add", methods=["POST"])
    def add_transaction_form():
        category_id = int(request.form["category_id"])
        amount = float(request.form["amount"])
        type_ = request.form["type"]
        date_str = request.form["date"]
        note = request.form.get("note", "")

        transaction = Transaction(
            category_id=category_id,
            amount=amount,
            type=type_,
            date=datetime.strptime(date_str, "%Y-%m-%d").date(),
            note=note
        )
        db.session.add(transaction)
        db.session.commit()

        if type_ == "expense":
            check_budget_and_notify(category_id)

        return redirect(url_for("index"))

    @app.route("/delete/<int:transaction_id>", methods=["POST"])
    def delete_transaction_form(transaction_id):
        transaction = Transaction.query.get(transaction_id)
        if transaction:
            db.session.delete(transaction)
            db.session.commit()
        return redirect(url_for("index"))

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

        if transaction.type == "expense":
            check_budget_and_notify(transaction.category_id)

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

    @app.route("/budgets", methods=["GET"])
    def get_budgets():
        budgets = Budget.query.all()
        return jsonify([b.to_dict() for b in budgets])

    @app.route("/budgets", methods=["POST"])
    def create_budget():
        data = request.get_json()
        if "category_id" not in data or "monthly_limit" not in data:
            return jsonify({"error": "category_id и monthly_limit обязательны"}), 400
        category = Category.query.get(data["category_id"])
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

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
    