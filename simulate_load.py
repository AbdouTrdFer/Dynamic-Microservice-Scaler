import requests
import time
from concurrent.futures import ThreadPoolExecutor

def send_requests(url, num_requests):
    """Envoyer un grand nombre de requêtes pour simuler la charge."""
    with ThreadPoolExecutor(max_workers=100) as executor:
        for _ in range(num_requests):
            executor.submit(requests.get, url)

if __name__ == "__main__":
    api_url = "http://localhost/"  # URL de votre application
    print("Début de la simulation de charge...")
    send_requests(api_url, 10000)  # Envoi de 1000 requêtes
    print("Simulation terminée.")
