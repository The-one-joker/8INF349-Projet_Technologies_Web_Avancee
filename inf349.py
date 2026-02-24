from flask import Flask
from models import db, Product, Order
from services import fetch_products 
from routes import api_bp  # Importation du Blueprint

def create_app():
    app = Flask(__name__)
    
    # Enregistrement des routes
    app.register_blueprint(api_bp)

    @app.cli.command('init-db')
    def init_db():
        db.connect()
        db.create_tables([Product, Order])
        print("Base de données initialisée.")

    return app

app = create_app()

# Logique de peuplement au lancement [cite: 442]
import sys
if 'init-db' not in sys.argv:
    with app.app_context():
        try:
            if Product.table_exists():
                fetch_products()
        except Exception:
            pass