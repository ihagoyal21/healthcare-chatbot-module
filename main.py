from flask import Flask, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder="frontend")

# Allow CORS for local development and your deployed frontend
CORS(app, origins=[
    "http://127.0.0.1:15000",
    "http://localhost:15000",
    "https://healthcare-chatbot-module.onrender.com"
])

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(file_path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 15000))
    app.run(host="0.0.0.0", port=port)
