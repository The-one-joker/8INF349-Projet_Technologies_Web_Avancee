import pytest
from inf349 import app as flask_app
from models import db, Product

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