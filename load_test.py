import requests
import time
from concurrent.futures import ThreadPoolExecutor

# Configuration
url = "http://localhost/"  # Remplacez par votre URL
total_requests = 100       # Nombre total de requêtes
concurrent_requests = 1   # Nombre de requêtes simultanées

# Fonction pour envoyer une requête GET et afficher le conteneur qui répond
def send_request():
    try:
        response = requests.get(url)
        return response.text  # Retourner la réponse complète pour vérifier le conteneur
    except Exception as e:
        return f"Erreur: {e}"

# Test de charge
def load_test():
    print(f"Envoi de {total_requests} requêtes avec {concurrent_requests} simultanées vers {url}")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        results = list(executor.map(lambda _: send_request(), range(total_requests)))

    end_time = time.time()
    duration = end_time - start_time

    # Résultats
    print(f"Test terminé en {duration:.2f} secondes")
    
    # Affichage des résultats pour voir quel conteneur a répondu
    print(f"Réponses des conteneurs: {results}")

if __name__ == "__main__":
    load_test()
