import pytest
from app import create_app
from models import db, Category


@pytest.fixture
def client():
    app = create_app(db_uri="sqlite:///:memory:")
    app.config["TESTING"] = True

    with app.app_context():
        db.session.add(Category(name="Тест"))
        db.session.commit()

        with app.test_client() as client:
            yield client

        db.session.remove()
        db.drop_all()


def test_get_categories(client):
    response = client.get("/categories")
    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_create_transaction(client):
    response = client.post("/transactions", json={
        "category_id": 1,
        "amount": 500,
        "type": "expense",
        "date": "2026-09-17"
    })
    assert response.status_code == 201
    assert response.get_json()["amount"] == 500


def test_create_transaction_missing_field(client):
    response = client.post("/transactions", json={"category_id": 1, "amount": 500})
    assert response.status_code == 400


def test_get_nonexistent_transaction(client):
    response = client.get("/transactions/9999")
    assert response.status_code == 404


def test_update_transaction(client):
    created = client.post("/transactions", json={
        "category_id": 1, "amount": 500, "type": "expense", "date": "2026-09-17"
    }).get_json()

    response = client.put(f"/transactions/{created['id']}", json={"amount": 750})
    assert response.status_code == 200
    assert response.get_json()["amount"] == 750


def test_delete_transaction(client):
    created = client.post("/transactions", json={
        "category_id": 1, "amount": 500, "type": "expense", "date": "2026-09-17"
    }).get_json()

    delete_response = client.delete(f"/transactions/{created['id']}")
    assert delete_response.status_code == 200

    get_response = client.get(f"/transactions/{created['id']}")
    assert get_response.status_code == 404
    