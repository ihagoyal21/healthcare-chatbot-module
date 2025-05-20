
from flask import Flask
from flask_cors import CORS
from config import config
from flask_caching import Cache

# Create cache instance at module level
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize cache with app
    cache.init_app(app)
    
    # Enable CORS
    CORS(app)
    
    # Register routes
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app
