from flask import Flask, render_template
from flask_cors import CORS
from app.routes import routes_bp  # Import du blueprint depuis routes.py
from app.containers import containers_bp  # Import d'un autre blueprint (containers)

app = Flask(__name__)
CORS(app)  # Activer les requêtes cross-origin (pour le frontend)

# Enregistrer les blueprints avec le bon préfixe
app.register_blueprint(routes_bp, url_prefix="/api")  # Blueprint des routes principales
app.register_blueprint(containers_bp, url_prefix="/api/containers")  # Blueprint pour les conteneurs

# Route pour la page d'accueil
@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)  # Écouter sur toutes les interfaces réseau
