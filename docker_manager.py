import docker
import threading
import time

# Client Docker
client = docker.from_env()

def check_container_usage():
    """Vérifie l'utilisation des ressources des conteneurs."""
    for container in client.containers.list():
        stats = container.stats(stream=False)
        cpu_percent = stats["cpu_stats"]["cpu_usage"]["total_usage"]
        memory_usage = stats["memory_stats"]["usage"]
        memory_limit = stats["memory_stats"]["limit"]
        memory_percent = (memory_usage / memory_limit) * 100

        print(f"Container: {container.name}, CPU: {cpu_percent}%, Memory: {memory_percent}%")

        # Si utilisation CPU ou RAM dépasse une limite, créer un nouveau conteneur
        if cpu_percent > 80 or memory_percent > 80:
            scale_up_container()

def scale_up_container():
    """Crée un nouveau conteneur Flask en cas de surcharge."""
    try:
        new_container = client.containers.run(
            "flask-image",  # Nom de l'image Docker
            detach=True,
            ports={"5002/tcp": None}  # Attribue un port aléatoire
        )
        print(f"New container created: {new_container.name}")
    except Exception as e:
        print(f"Error creating container: {e}")

def start_monitoring():
    """Lance la vérification des conteneurs toutes les 10 secondes."""
    while True:
        check_container_usage()
        time.sleep(10)

# Démarrage dans un thread
monitoring_thread = threading.Thread(target=start_monitoring, daemon=True)
monitoring_thread.start()
