from app import app
from models import db, Category

with app.app_context():
    categories = ["Еда", "Транспорт", "Развлечения", "Здоровье", "Прочее"]
    for name in categories:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
    db.session.commit()

print("Категории добавлены")
