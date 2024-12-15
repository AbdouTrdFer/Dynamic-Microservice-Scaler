import docker
import time
from reload_nginx import reload_nginx

client = docker.from_env()  # Connexion au client Docker
NGINX_CONF_PATH = './nginxs/nginx.conf'

CPU_THRESHOLD = 80
RAM_THRESHOLD = 85


def create_new_instance(container):
    try:
        new_container = container.client.containers.run(
            container.image,
            detach=True,
            name=f"{container.name}_scale",
            environment=container.environment,  # Si vous avez des variables d'environnement
        )
        return new_container
    except docker.errors.APIError as e:
        print(f"Erreur lors de la création d'une nouvelle instance : {e}")
        return None


def get_active_containers():
    """Récupère tous les conteneurs actifs"""
    containers = client.containers.list()
    active = []
    for container in containers:
        if "5002/tcp" in container.attrs['NetworkSettings']['Ports']:
            active.append(container)
    return active

def update_nginx_config(containers):
    """Met à jour la configuration NGINX avec les nouvelles instances"""
    try:
        with open(NGINX_CONF_PATH, 'w') as f:
            f.write("events {}\n\n")
            f.write("http {\n")
            f.write("    upstream backend {\n")
            for container in containers:
                ip = container.attrs['NetworkSettings'].get('IPAddress', None)
                ports = container.attrs['NetworkSettings'].get('Ports', {})
                if ip and ports:
                    port = list(ports.keys())[0].split("/")[0]
                    f.write(f"        server {ip}:{port};\n")
            f.write("    }\n\n")
            f.write("    server {\n")
            f.write("        listen 80;\n")
            f.write("        location / {\n")
            f.write("            proxy_pass http://backend;\n")
            f.write("            proxy_set_header Host $host;\n")
            f.write("            proxy_set_header X-Real-IP $remote_addr;\n")
            f.write("            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n")
            f.write("        }\n")
            f.write("    }\n")
            f.write("}\n")
        reload_nginx()  # Recharger NGINX après modification de la config
    except Exception as e:
        print(f"Error updating NGINX config: {e}")

def scale_containers():
    """Surveille les conteneurs et effectue un scaling horizontal si nécessaire"""
    alert_containers = []

    for container in client.containers.list():
        stats = container.stats(stream=False)
        cpu_stats = stats['cpu_stats']
        precpu_stats = stats['precpu_stats']

        cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
        system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
        cpu_usage_percentage = 0
        if system_delta > 0:
            cpu_usage_percentage = (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100

        memory_usage = stats['memory_stats']['usage']
        memory_limit = stats['memory_stats']['limit']
        memory_usage_percentage = (memory_usage / memory_limit) * 100

        if cpu_usage_percentage > CPU_THRESHOLD or memory_usage_percentage > RAM_THRESHOLD:
            alert_containers.append(container)

    if alert_containers:
        for container in alert_containers:
            create_new_instance(container)

        active_containers = get_active_containers()
        update_nginx_config(active_containers)

    return "Scaling completed"
