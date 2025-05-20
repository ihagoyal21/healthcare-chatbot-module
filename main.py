import os
import sys
from flask import Flask, send_from_directory, jsonify

# Ensure backend/app is in the Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.routes import main as main_blueprint  # Import your Blueprint

# Set up Flask to serve static files from the frontend directory
app = Flask(__name__, static_folder="frontend")

# Register your API Blueprint
app.register_blueprint(main_blueprint)

# Serve the frontend index.html at root
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

# Serve static assets (CSS, JS, images, etc.)
@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(app.static_folder, path)

# (Optional) API info route at /api
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
