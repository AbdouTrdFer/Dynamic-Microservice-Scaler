from flask import Blueprint, jsonify, request, render_template
import docker
import time
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter # reportlab pdf , letter le format de page a4...
from reportlab.pdfgen import canvas
import io
import matplotlib.pyplot as plt # permet de sauvegarder les graphe au format png
import numpy as np  # Bibliothèque pour les calculs mathématiques et le traitement de données scientifiques
import os #interagir avec os
import itertools #optimiser les boucles imbrique pour reduire le complexite
import subprocess
import yaml #manipulation des fichiers .yml

routes_bp = Blueprint('routes', __name__)  # Définir un blueprint

# Initialisation du client Docker
client = docker.from_env()
CPU_THRESHOLD = 85  # Seuil pour l'utilisation CPU en pourcentage
RAM_THRESHOLD = 85  # Seuil pour l'utilisation RAM en pourcentage

# Chemin du fichier de configuration NGINX

# Liste des conteneurs actifs pour le load balancing
active_containers = []

# Initialisation du round robin
round_robin = itertools.cycle(active_containers) #parcourir containers si il atteint la fin de iterable

def send_email_with_multiple_alerts(containers_data):
    try:
        # Configuration de l'email
        sender_email = "arthurneo52@gmail.com"
        receiver_email = "ferhanabdelali@gmail.com"
        password = "private"

        # Création du message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f"ALERT: Multiple Containers Exceeded Usage Limits"
        
        # corps de l'email
        body = "The following containers have exceeded the resource usage limits:\n\n"
        for container in containers_data:
            body += f"- {container['name']}: CPU = {container['cpu_usage']}%, RAM = {container['mem_usage']}%\n"
        msg.attach(MIMEText(body, 'plain'))

        #  graphique combiné
        pdf_buffer = generate_combined_graph_pdf(containers_data)

        # Attacher le PDF
        pdf_attachment = MIMEApplication(pdf_buffer.getvalue(), 'pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename="alert_multiple_containers.pdf")
        msg.attach(pdf_attachment)

        # Connexion au serveur SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        
        print(f"Email sent to {receiver_email} regarding multiple containers usage.")

    except Exception as e:
        print(f"Failed to send email: {str(e)}")

def generate_pdf(container_name, cpu_usage, mem_usage):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, f"ALERT for Container: {container_name}")
    c.drawString(100, 730, f"CPU Usage: {cpu_usage}%")
    c.drawString(100, 710, f"Memory Usage: {mem_usage}%")
    
    # Générer un graphique
    fig, ax = plt.subplots()
    labels = ['CPU Usage', 'Memory Usage']
    values = [cpu_usage, mem_usage]
    ax.bar(labels, values, color=['red', 'blue'])
    ax.set_ylim([0, 100])
    
    # Sauvegarder le graphique dans le PDF
    plt.savefig('C:\\Users\\Lenovo\\Desktop\\Flask_project\\app\\alert_graph.png')
    c.drawImage('C:\\Users\\Lenovo\\Desktop\\Flask_project\\app\\alert_graph.png', 100, 400, width=400, height=300)

    c.save()
    buffer.seek(0)
    return buffer

def generate_combined_graph_pdf(containers_data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "ALERT for Multiple Containers")
    
    # Générer un graphique combiné
    fig, ax = plt.subplots(figsize=(8, 6))
    names = [container['name'] for container in containers_data]
    cpu_usages = [container['cpu_usage'] for container in containers_data]
    mem_usages = [container['mem_usage'] for container in containers_data]

    bar_width = 0.35
    indices = np.arange(len(names))

    # Dessiner les barres
    cpu_bars = ax.bar(indices, cpu_usages, bar_width, label='CPU Usage (%)', color='red')
    mem_bars = ax.bar(indices + bar_width, mem_usages, bar_width, label='Memory Usage (%)', color='blue')

    # Ajouter les annotations (valeurs de pourcentage) sur chaque barre
    for bar, cpu in zip(cpu_bars, cpu_usages):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f'{cpu:.2f}%', ha='center', fontsize=10, color='red')

    for bar, mem in zip(mem_bars, mem_usages):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f'{mem:.2f}%', ha='center', fontsize=10, color='blue')

    # Configurer les étiquettes et légendes
    ax.set_xlabel('Containers')
    ax.set_ylabel('Usage (%)')
    ax.set_title('Resource Usage of Containers Exceeding Limits')
    ax.set_xticks(indices + bar_width / 2)
    ax.set_xticklabels(names, rotation=45)
    ax.legend()

    # Sauvegarder le graphique dans un fichier temporaire
    plt.tight_layout()
    plt.savefig('C:\\Users\\Lenovo\\Desktop\\Flask_project\\app\\combined_alert_graph.png')
    c.drawImage('C:\\Users\\Lenovo\\Desktop\\Flask_project\\app\\combined_alert_graph.png', 50, 400, width=500, height=300)

    c.save()
    buffer.seek(0)
    return buffer

@routes_bp.route('/containers', methods=['GET'])  
def get_containers():
    try:
        containers = []
        for container in client.containers.list(all=True):
            containers.append({
                "id": container.short_id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "ports": container.attrs['NetworkSettings']['Ports']
            })
        return jsonify(containers), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@routes_bp.route('/metrics', methods=['GET'])  
def get_global_metrics():
    try:
        # Initialisation des variables pour les métriques globales
        total_containers = 0
        total_ram_used = 0  # En octets
        total_cpu_usage = 0

        # Parcourir les conteneurs actifs
        for container in client.containers.list():
            stats = container.stats(stream=False)  # Récupération des stats

            # RAM utilisée
            memory_usage = stats['memory_stats']['usage']
            total_ram_used += memory_usage

            # Calcul de l'utilisation CPU
            cpu_stats = stats['cpu_stats']
            precpu_stats = stats['precpu_stats']
            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
            if system_delta > 0 and cpu_delta >= 0:
                total_cpu_usage += (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100

            total_containers += 1  # Compter le conteneur

        # Conversion de la RAM utilisée en GB
        total_ram_gb = round(total_ram_used / (1024 ** 3), 2)

        # Création de la réponse JSON
        
        metrics = {
            "totalContainers": total_containers,
            "totalRAM": f"{total_ram_gb} GB",
            "cpuUsage": f"{round(total_cpu_usage, 2)}%"
        }
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#load balancing fcts
# Fonction pour créer une nouvelle instance du conteneur
NGINX_CONF_PATH = 'C:\\Users\\Lenovo\\Desktop\\Flask_project\\nginx\\sites\\app.conf'


def get_active_containers():
    """Récupère tous les conteneurs actifs"""
    containers = client.containers.list()
    active = []
    for container in containers:
        if "5002/tcp" in container.attrs['NetworkSettings']['Ports']:
            active.append(container)
    return active


@routes_bp.route('/stats', methods=['GET'])
def get_container_metrics():
    try:
        metrics = []
        alert_containers = []
        containers_to_scale = []

        for container in client.containers.list():
            stats = container.stats(stream=False)
            cpu_stats = stats.get('cpu_stats', {})
            precpu_stats = stats.get('precpu_stats', {})
            memory_stats = stats.get('memory_stats', {})

            # Calcul du pourcentage d'utilisation du CPU
            cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - \
                        precpu_stats.get('cpu_usage', {}).get('total_usage', 0)
            system_delta = cpu_stats.get('system_cpu_usage', 0) - precpu_stats.get('system_cpu_usage', 0)
            cpu_usage_percentage = 0.0
            if system_delta > 0:
                cpu_usage_percentage = (cpu_delta / system_delta) * \
                                        len(cpu_stats.get('cpu_usage', {}).get('percpu_usage', [])) * 100

            # Calcul du pourcentage d'utilisation de la mémoire
            memory_usage = memory_stats.get('usage', 0)
            memory_limit = memory_stats.get('limit', 1)
            memory_usage_percentage = (memory_usage / memory_limit) * 100

            metrics.append({
                "id": container.short_id,
                "name": container.name,
                "cpu_usage_percentage": round(cpu_usage_percentage, 2),
                "memory_usage_percentage": round(memory_usage_percentage, 2),
                "status": container.status
            })

            if cpu_usage_percentage > CPU_THRESHOLD or memory_usage_percentage > RAM_THRESHOLD:
                alert_containers.append({
                    "name": container.name,
                    "cpu_usage": round(cpu_usage_percentage, 2),
                    "mem_usage": round(memory_usage_percentage, 2),
                })
                containers_to_scale.append(container)

        # Envoi des alertes si nécessaire
        if alert_containers:
            try:
                send_email_with_multiple_alerts(alert_containers)
            except Exception as email_error:
                print(f"Erreur lors de l'envoi des emails : {email_error}")

        # Scaling horizontal : création de nouveaux conteneurs
        new_containers = []
        for container in containers_to_scale:
            new_container = create_new_instance(container)
            if new_container:
                new_containers.append(new_container)

        # Mise à jour de la configuration NGINX
        try:
            active_containers = get_active_containers()
            update_nginx_config(active_containers + new_containers)
        except Exception as nginx_error:
            print(f"Erreur lors de la mise à jour de NGINX : {nginx_error}")

        return jsonify({"metrics": metrics, "alerts": alert_containers}), 200

    except docker.errors.APIError as docker_error:
        return jsonify({"error": f"Erreur Docker : {str(docker_error)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Erreur inconnue : {str(e)}"}), 500

def update_docker_compose_file(new_container_name, build_context):
    """Met à jour le fichier docker-compose.yml pour ajouter une nouvelle instance avec build."""
    try:
        # Charger le fichier docker-compose existant
        with open('C:\\Users\\Lenovo\\Desktop\\Flask_project\\docker-compose.yml', 'r') as f:
            compose_data = yaml.safe_load(f)

        # Vérifier si 'services' existe dans le fichier
        if 'services' not in compose_data:
            compose_data['services'] = {}

        # Créer une entrée de service dynamique avec un build
        new_service = {
            new_container_name: {
                'build': build_context,  # Chemin vers le répertoire contenant le Dockerfile
                'container_name': new_container_name,
                'networks': ['backend'],  # Réseau à utiliser
                'environment': [
                    'FLASK_APP=app.py',
                    'FLASK_ENV=production',
                ],
            }
        }

        # Ajouter le nouveau service à la section "services"
        compose_data['services'].update(new_service)

        # Sauvegarder les modifications dans docker-compose.yml
        with open('C:\\Users\\Lenovo\\Desktop\\Flask_project\\docker-compose.yml', 'w') as f:
            yaml.dump(compose_data, f, default_flow_style=False)

        print(f"Service {new_container_name} ajouté avec succès à docker-compose.yml avec build.")

    except Exception as e:
        print(f"Erreur lors de la mise à jour du fichier docker-compose.yml : {e}")
def create_new_instance(container):
    """Crée une nouvelle instance du conteneur via Docker Compose."""
    try:
        new_container_name = f"{container.name}_scaled"
        build_context = "C:\\Users\\Lenovo\\Desktop\\Flask_project\\flask-app3"  

        update_docker_compose_file(new_container_name, build_context)

        # Exécution de docker-compose pour démarrer les conteneurs
        
        result = subprocess.run(['docker-compose', 'up', '-d'], check=True, capture_output=True, text=True)
        print(result.stdout)
        return new_container_name
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de docker-compose : {e.stderr}")
        return None

def update_nginx_config(active_containers):
    """Met à jour le fichier de configuration NGINX sans supprimer les valeurs existantes."""
    try:
        # Ouvrir le fichier de configuration NGINX en mode lecture et écriture
        with open('C:\\Users\\Lenovo\\Desktop\\Flask_project\\nginx\\sites\\app.conf', 'r+') as f:
            config = f.read()

            # Trouver le bloc upstream
            start_index = config.find("upstream flask_app {")
            if start_index == -1:
                print("Bloc 'upstream flask_app' non trouvé dans le fichier.")
                return

            # Trouver la fin du bloc upstream
            end_index = config.find("}", start_index)
            if end_index == -1:
                print("Fin du bloc 'upstream flask_app' non trouvée.")
                return

            # Extraire le bloc upstream existant
            upstream_block = config[start_index:end_index + 1]

            # Créer une nouvelle liste pour les  eserveurs existants et ajouter les nouveaux serveurs
            new_upstream = upstream_block

            # Ajouter les nouveaux serveurs sans supprimer les anciens
            for container in active_containers:
                # Vérifiez si le serveur existe déjà pour éviter les doublons
                if f"server {container}:5000;" not in new_upstream:
                    new_upstream += f"    server {container}:8000;\n"

            # Remplacer l'ancien bloc upstream par le nouveau
            config = config[:start_index] + new_upstream + config[end_index + 1:]

            # Revenir au début du fichier et écraser l'ancien contenu
            f.seek(0)
            f.write(config)
            f.truncate()

        # Redémarrer NGINX pour appliquer les changements
        subprocess.run(['nginx', '-s', 'reload'], check=True)
        print("Configuration NGINX mise à jour et rechargée avec succès.")

    except Exception as e:
        print(f"Erreur lors de la mise à jour de la configuration NGINX : {e}")

@routes_bp.route('/stop-container', methods=['POST'])  
def stop_container():
    try:
        data = request.get_json()
        container_id = data.get("id")
        container = client.containers.get(container_id)
        container.stop()
        return jsonify({"message": f"Container {container_id} stopped successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@routes_bp.route('/create-container', methods=['POST'])  
def create_container():
    try:
        data = request.get_json()
        image = data.get("image")
        name = data.get("name")
        container = client.containers.run(image, name=name, detach=True)
        return jsonify({"message": f"Container {name} created successfully", "id": container.short_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@routes_bp.route('/delete-container', methods=['POST'])  
def delete_container():
    try:
        data = request.get_json()
        container_id = data.get("id")
        container = client.containers.get(container_id)
        container.remove()
        return jsonify({"message": f"Container {container_id} removed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#graphe dernier 

# API pour obtenir les informations des processus de tous les conteneurs actifs
# Fonction pour obtenir les informations des processus dans un conteneur Docker



@routes_bp.route('/processes', methods=['GET'])
def get_processes():
    try:
        all_processes = []
        containers = client.containers.list()  # Liste les conteneurs actifs

        for container in containers:
            container_name = container.name
            processes = get_process_info(container_name)

            if isinstance(processes, dict) and "error" in processes:
                continue

            # Ajout des processus à la liste finale
            for process in processes:
                # Validation avant de convertir en float
                try:
                    cpu = float(process["cpu"]) if process["cpu"].replace('.', '', 1).isdigit() else 0.0
                    mem = float(process["mem"]) if process["mem"].replace('.', '', 1).isdigit() else 0.0
                except ValueError:
                    cpu = 0.0
                    mem = 0.0

                all_processes.append({
                    "container": container_name,
                    "pid": process["pid"],
                    "ppid": process["ppid"],  # Inclure le PPID
                    "user": process["user"],
                    "cpu": cpu,  # Assurez-vous que c'est un float
                    "mem": mem,  # Assurez-vous que c'est un float
                    "command": process["command"]
                })

        if not all_processes:
            return jsonify({"message": "Aucun processus trouvé dans les conteneurs actifs"}), 404

        # Trie des processus par %CPU
        all_processes = sorted(all_processes, key=lambda x: x["cpu"], reverse=True)

        # Limiter à 5 processus les plus gourmands
        top_processes = all_processes[:5]

        return jsonify(top_processes), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_process_info(container_name):
    try:
        # Récupérer les processus du conteneur via l'API Docker Python
        container = client.containers.get(container_name)
        top_info = container.top()

        processes = []
        for process in top_info['Processes']:
            # Extraire les informations sur chaque processus
            pid = process[0]
            ppid = process[1]
            user = process[2]
            cpu = process[3]
            mem = process[4]
            command = " ".join(process[5:])  # Le reste de la ligne est la commande complète

            # Créer une entrée de processus
            processes.append({
                "pid": pid,
                "ppid": ppid,  # ID du processus parent
                "user": user,
                "cpu": cpu,
                "mem": mem,
                "command": command
            })
        
        return processes

    except Exception as e:
        return {"error": str(e)}

    
@routes_bp.route('/containers/<container_id>/top', methods=['GET'])
def get_container_processes(container_id):
    try:
        # Commande docker pour obtenir les processus
        cmd = f"docker exec {container_id} ps -eo pid,ppid,user,%cpu,%mem,comm --sort=-%cpu"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        
        if result.returncode != 0:
            return jsonify({"error": "Impossible d'exécuter la commande Docker"}), 500
        
        lines = result.stdout.splitlines()
        processes = []
        for line in lines[1:]:  # Ignorer l'en-tête
            parts = line.split(maxsplit=5)
            if len(parts) < 6:
                continue
            processes.append({
                "pid": int(parts[0]),  # Assurez-vous que le PID est un entier
                "ppid": int(parts[1]),  # ID du processus parent
                "user": parts[2],
                "cpu": float(parts[3]) if parts[3].replace('.', '', 1).isdigit() else 0.0,
                "mem": float(parts[4]) if parts[4].replace('.', '', 1).isdigit() else 0.0,
                "command": parts[5]  # Nom du processus
            })
        
        return jsonify({"Processes": processes}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Erreur lors de l'exécution de la commande : {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500