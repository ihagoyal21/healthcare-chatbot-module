from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import os
import sys

# Add backend to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.routes import main as main_blueprint  # <-- Import your blueprint

app = Flask(__name__, static_folder="frontend")

# Allow CORS for local development and your deployed frontend
CORS(app, origins=[
    "https://healthcare-chatbot-module.vercel.app"
    "http://127.0.0.1:15000",
    "http://localhost:15000",
    "https://healthcare-chatbot-module.onrender.com"
])

# Register your API blueprint!
app.register_blueprint(main_blueprint)

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(file_path):
        return send_from_directory(app.static_folder, path)
    else:
        # Fallback to index.html for SPA routes
        return send_from_directory(app.static_folder, "index.html")

@app.route("/api")
def api_info():
    return jsonify({
        "message": "Healthcare Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "health_check": "/api/health",
            "process_input": "/api/assessment/next",
            "quick_assessment": "/api/assessment/quick",
            "search_symptoms": "/api/symptoms/search",
            "start_assessment": "/api/assessment/start",
            "start_new": "/api/assessment/start_new"
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 15000))
    app.run(host="0.0.0.0", port=port)
