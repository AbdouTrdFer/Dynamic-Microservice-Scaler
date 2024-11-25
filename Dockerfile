FROM python:3.9-slim

# Installer les dépendances
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copier le code source
COPY . /app
WORKDIR /app

# Exposer le port 5000
EXPOSE 5000

# Démarrer Flask
CMD ["python", "app.py"]
