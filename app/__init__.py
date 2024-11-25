from flask import Flask

app = Flask(__name__)

# Import des routes après l'initialisation
from app import routes
