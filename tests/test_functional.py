import pytest
from inf349 import app as flask_app
from models import db, Product, Order

@pytest.fixture
def app():
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

def test_get_products(client):
    """Vérifie que GET / retourne un code 200 et du JSON [cite: 33-35]"""
    response = client.get('/')
    assert response.status_code == 200
    assert "products" in response.json

def test_get_order_not_found(client):
    """Vérifie que GET /order/9999 retourne 404"""
    response = client.get('/order/9999')
    assert response.status_code == 404
    assert response.json["errors"]["order"]["code"] == "not-found"

def test_get_order_exists(client):
    """Vérifie que GET /order/<id> retourne 200 avec les bons champs"""
    # D'abord créer une commande via POST
    post_response = client.post('/order', json={
        "product": {"id": 1, "quantity": 1}
    })
    # Récupère l'ID depuis le redirect (302)
    order_id = post_response.headers['Location'].split('/')[-1]

    # Maintenant teste GET /order/<id>
    response = client.get(f'/order/{order_id}')
    assert response.status_code == 200

    order = response.json["order"]
    assert "id" in order
    assert "total_price" in order
    assert "total_price_tax" in order
    assert "shipping_price" in order
    assert "paid" in order
    assert order["paid"] == False
