from flask import Flask, jsonify
from models import db, Product, Order
from services import fetch_products 

def create_app():
    app = Flask(__name__)

    # Commande obligatoire pour initialiser la DB 
    @app.cli.command('init-db')
    def init_db():
        db.connect()
        db.create_tables([Product, Order])
        print("Base de données initialisée.")

    # Route GET / demandée [cite: 33, 58]
    @app.route('/', methods=['GET'])
    def list_products():
        products = list(Product.select().dicts())
        return jsonify({"products": products}), 200

    return app

app = create_app()

# Au lancement (flask run), on tente de peupler la base [cite: 440, 441]
# On vérifie si on n'est pas en train d'exécuter une commande CLI (comme init-db)
import sys
if 'init-db' not in sys.argv:
    with app.app_context():
        try:
            if Product.table_exists():
                fetch_products()
        except Exception:
            pass