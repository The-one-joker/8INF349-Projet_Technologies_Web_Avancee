import pytest
import requests
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

def test_put_order_info_success(client):
    # 1. Création
    post_res = client.post('/order', json={"product": {"id": 1, "quantity": 1}})
    order_id = post_res.headers['Location'].split('/')[-1]

    # [cite_start]2. Mise à jour (QC = 15%) [cite: 116]
    payload = {
        "order": {
            "email": "test@uqac.ca",
            "shipping_information": {
                "country": "Canada",
                "address": "555 Blvd Université",
                "postal_code": "G7H 2B1",
                "city": "Chicoutimi",
                "province": "QC"
            }
        }
    }
    response = client.put(f'/order/{order_id}', json=payload)
    assert response.status_code == 200
    assert response.json["order"]["email"] == "test@uqac.ca"
    assert response.json["order"]["shipping_information"]["province"] == "QC"
    
    # [cite_start]Vérification du calcul de taxe (Total * 1.15) [cite: 116, 122]
    expected_taxed = round(response.json["order"]["total_price"] * 1.15, 2)
    assert response.json["order"]["total_price_tax"] == expected_taxed

def test_put_order_info_missing_fields(client):
    
    post_res = client.post('/order', json={"product": {"id": 1, "quantity": 1}})
    order_id = post_res.headers['Location'].split('/')[-1]

    # Manque 'city' et 'postal_code'
    payload = {
        "order": {
            "email": "test@uqac.ca",
            "shipping_information": {
                "country": "Canada",
                "address": "555 Blvd Université",
                "province": "QC"
            }
        }
    }
    response = client.put(f'/order/{order_id}', json=payload)
    assert response.status_code == 422
    assert response.json["errors"]["order"]["code"] == "missing-fields" 


def test_put_order_payment_before_info(client):
    post_res = client.post('/order', json={"product": {"id": 1, "quantity": 1}})
    order_id = post_res.headers['Location'].split('/')[-1]

    payload = {
        "credit_card": {
            "name": "John Doe",
            "number": "4242 4242 4242 4242",
            "expiration_year": 2026,
            "expiration_month": 12,
            "cvv": "123"
        }
    }
    response = client.put(f'/order/{order_id}', json=payload)
    assert response.status_code == 422
    assert "informations" in response.json["errors"]["order"]["name"].lower() 

def test_put_order_payment_declined(client, requests_mock):
    # 1. Création + Infos client
    post_res = client.post('/order', json={"product": {"id": 1, "quantity": 1}})
    order_id = post_res.headers['Location'].split('/')[-1]
    client.put(f'/order/{order_id}', json={"order": {"email":"a@a.ca", "shipping_information": {"country":"A","address":"A","postal_code":"A","city":"A","province":"QC"}}})

    # [cite_start]2. Mock de l'erreur du service distant [cite: 380]
    requests_mock.post("http://dimprojetu.uqac.ca/~jgnault/shops/pay/", 
                       json={"errors": {"credit_card": {"code": "card-declined", "name": "Déclinée"}}}, 
                       status_code=422)

    payload = {"credit_card": {"name": "J", "number": "4000 0000 0000 0002", "expiration_year": 2026, "expiration_month": 12, "cvv": "123"}}
    response = client.put(f'/order/{order_id}', json=payload)
    
    assert response.status_code == 422
    assert response.json["errors"]["credit_card"]["code"] == "card-declined" 

def test_put_order_already_paid(client, requests_mock):
    # 1. Création + Infos + Premier Paiement réussi
    post_res = client.post('/order', json={"product": {"id": 1, "quantity": 1}})
    order_id = post_res.headers['Location'].split('/')[-1]
    client.put(f'/order/{order_id}', json={"order": {"email":"a@a.ca", "shipping_information": {"country":"A","address":"A","postal_code":"A","city":"A","province":"QC"}}})
    
    # Mock succès
    requests_mock.post("http://dimprojetu.uqac.ca/~jgnault/shops/pay/", 
                       json={"credit_card": {"name":"J", "first_digits":"4242", "last_digits":"4242", "expiration_year":2026, "expiration_month":12},
                             "transaction": {"id": "tx123", "success": True, "amount_charged": 1000}}, 
                       status_code=200)

    payload = {"credit_card": {"name": "J", "number": "4242 4242 4242 4242", "expiration_year": 2026, "expiration_month": 12, "cvv": "123"}}
    client.put(f'/order/{order_id}', json=payload) # Premier paiement

    # 2. Deuxième tentative
    response = client.put(f'/order/{order_id}', json=payload)
    assert response.status_code == 422
    assert response.json["errors"]["order"]["code"] == "already-paid"

def test_put_order_payment_success(client, requests_mock):
    """Vérifie le cycle complet de paiement réussi (Scénario B)"""
    
    # 1. Préparation : Créer une commande et lui ajouter des infos client
    post_res = client.post('/order', json={"product": {"id": 1, "quantity": 1}})
    order_id = post_res.headers['Location'].split('/')[-1]
    
    client.put(f'/order/{order_id}', json={
        "order": {
            "email": "etudiant@uqac.ca",
            "shipping_information": {
                "country": "Canada", "address": "201 Kennedy", 
                "postal_code": "G7X 3Y7", "city": "Chicoutimi", "province": "QC"
            }
        }
    })

    # 2. Mock du service de paiement (on simule la réponse de l'UQAC)
    payment_url = "http://dimprojetu.uqac.ca/~jgnault/shops/pay/"
    requests_mock.post(payment_url, json={
        "credit_card": {
            "name": "John Doe",
            "first_digits": "4242",
            "last_digits": "4242",
            "expiration_year": 2026,
            "expiration_month": 12
        },
        "transaction": {
            "id": "trans_abc_123",
            "success": True,
            "amount_charged": 10520.20
        }
    }, status_code=200)

    # 3. Action : Envoyer le paiement
    payload = {
        "credit_card": {
            "name": "John Doe",
            "number": "4242 4242 4242 4242",
            "expiration_year": 2026,
            "expiration_month": 12,
            "cvv": "123"
        }
    }
    response = client.put(f'/order/{order_id}', json=payload)

    # 4. Vérifications
    assert response.status_code == 200
    order_data = response.json["order"]
    
    assert order_data["paid"] is True
    assert order_data["transaction"]["id"] == "trans_abc_123"
    assert order_data["transaction"]["success"] is True
    assert order_data["credit_card"]["first_digits"] == "4242"
    assert order_data["credit_card"]["last_digits"] == "4242"
    
    # Vérifier que les infos de livraison sont toujours là
    assert order_data["shipping_information"]["city"] == "Chicoutimi"

def test_put_order_payment_timeout(client, requests_mock):
    """Vérifie que l'API retourne 503 si le service de paiement ne répond pas"""
    
    # 1. Préparation (Création + Infos client)
    post_res = client.post('/order', json={"product": {"id": 1, "quantity": 1}})
    order_id = post_res.headers['Location'].split('/')[-1]
    client.put(f'/order/{order_id}', json={
        "order": {
            "email": "test@uqac.ca",
            "shipping_information": {
                "country": "Canada", "address": "A", "postal_code": "A", "city": "A", "province": "QC"
            }
        }
    })

    # 2. Mock d'une exception réseau (Timeout)
    payment_url = "http://dimprojetu.uqac.ca/~jgnault/shops/pay/"
    requests_mock.post(payment_url, exc=requests.exceptions.ConnectTimeout)

    # 3. Action
    payload = {
        "credit_card": {
            "name": "John Doe", "number": "4242 4242 4242 4242",
            "expiration_year": 2026, "expiration_month": 12, "cvv": "123"
        }
    }
    response = client.put(f'/order/{order_id}', json=payload)

    # 4. Vérification
    assert response.status_code == 503
    assert response.json["errors"]["payment"]["code"] == "timeout"
    
def test_shipping_price_calculation(client):
    # [cite_start]Produit ID 1 fait 400g [cite: 44]
    # [cite_start]Quantité 1 (400g) -> 5$ (500 cents) [cite: 126]
    res1 = client.post('/order', json={"product": {"id": 1, "quantity": 1}})
    id1 = res1.headers['Location'].split('/')[-1]
    assert client.get(f'/order/{id1}').json["order"]["shipping_price"] == 500

    # [cite_start]Quantité 2 (800g) -> 10$ (1000 cents) [cite: 127]
    res2 = client.post('/order', json={"product": {"id": 1, "quantity": 2}})
    id2 = res2.headers['Location'].split('/')[-1]
    assert client.get(f'/order/{id2}').json["order"]["shipping_price"] == 1000

    # [cite_start]Quantité 6 (2400g) -> 25$ (2500 cents) [cite: 128]
    res3 = client.post('/order', json={"product": {"id": 1, "quantity": 6}})
    id3 = res3.headers['Location'].split('/')[-1]
    assert client.get(f'/order/{id3}').json["order"]["shipping_price"] == 2500