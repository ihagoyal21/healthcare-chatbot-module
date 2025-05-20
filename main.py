import sys
import os
from flask import Flask, send_from_directory

# Add backend/ to the Python path so you can import app
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.routes import main as main_blueprint

app = Flask(__name__, static_folder="frontend")

# Register your API Blueprint
app.register_blueprint(main_blueprint)

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(app.static_folder, path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
