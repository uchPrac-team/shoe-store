from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    
    # Импортируем оба blueprint
    from app.routes.auth import auth_bp
    from app.routes.products import products_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    
    return app