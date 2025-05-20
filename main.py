from flask import Flask, send_from_directory
from app.routes import main as main_blueprint  # Import your Blueprint
import os

app = Flask(__name__, static_folder="frontend")

# Register your API routes
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
