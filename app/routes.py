from flask import Blueprint, jsonify, request, render_template
import docker
import time
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import matplotlib.pyplot as plt
import numpy as np


routes_bp = Blueprint('routes', __name__)  # Définir un blueprint

# Initialisation du client Docker
client = docker.from_env()


# Seuils d'utilisation du CPU et de la RAM
CPU_THRESHOLD = 90  # Seuil pour l'utilisation CPU en pourcentage
RAM_THRESHOLD = 90  # Seuil pour l'utilisation RAM en pourcentage

def send_email_with_multiple_alerts(containers_data):
    try:
        # Configuration de l'email
        sender_email = "arthurneo52@gmail.com"
        receiver_email = "ferhanabdelali@gmail.com"
        password = "hnbt kgrc hlhq tptt"

        # Création du message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f"ALERT: Multiple Containers Exceeded Usage Limits"
        
        # Générer le contenu du corps de l'email
        body = "The following containers have exceeded the resource usage limits:\n\n"
        for container in containers_data:
            body += f"- {container['name']}: CPU = {container['cpu_usage']}%, RAM = {container['mem_usage']}%\n"
        msg.attach(MIMEText(body, 'plain'))

        # Générer un graphique combiné
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

@routes_bp.route('/stats', methods=['GET'])
def get_container_metrics():
    try:
        metrics = []
        alert_containers = []  # Liste pour regrouper les conteneurs qui dépassent les seuils

        for container in client.containers.list():
            stats = container.stats(stream=False)
            cpu_stats = stats['cpu_stats']
            precpu_stats = stats['precpu_stats']

            # Calcul du pourcentage d'utilisation du CPU
            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
            cpu_usage_percentage = 0.0
            if system_delta > 0 and cpu_delta >= 0:
                cpu_usage_percentage = (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100

            # Calcul du pourcentage d'utilisation de la mémoire
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_usage_percentage = (memory_usage / memory_limit) * 100

            # Ajout des métriques pour tous les conteneurs
            metrics.append({
                "id": container.short_id,
                "name": container.name,
                "cpu_usage_percentage": round(cpu_usage_percentage, 2),
                "memory_usage_percentage": round(memory_usage_percentage, 2),
                "status": container.status
            })

            # Vérification des seuils
            if cpu_usage_percentage > CPU_THRESHOLD or memory_usage_percentage > RAM_THRESHOLD:
                alert_containers.append({
                    "name": container.name,
                    "cpu_usage": round(cpu_usage_percentage, 2),
                    "mem_usage": round(memory_usage_percentage, 2),
                })

        # Si des conteneurs dépassent les seuils, envoyer un email consolidé
        if alert_containers:
            send_email_with_multiple_alerts(alert_containers)

        # Retourner les métriques et alertes au format JSON
        return jsonify({"metrics": metrics, "alerts": alert_containers}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@routes_bp.route('/stats-debug', methods=['GET'])  
def get_container_metrics_debug():
    try:
        metrics = []
        for container in client.containers.list():
            stats = container.stats(stream=False)
            metrics.append({
                "id": container.short_id,
                "name": container.name,
                "cpu_stats": stats['cpu_stats'],
                "precpu_stats": stats['precpu_stats'],
                "memory_stats": stats['memory_stats'],
                "pids_stats": stats['pids_stats']
            })
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        
        # Si la commande a échoué, une exception sera levée
        if result.returncode != 0:
            return jsonify({"error": "Impossible d'exécuter la commande Docker"}), 500
        
        lines = result.stdout.splitlines()
        processes = []
        for line in lines[1:]:  # Ignorer l'en-tête
            parts = line.split(maxsplit=5)
            if len(parts) < 6:
                continue
            processes.append({
                "pid": parts[0],
                "ppid": parts[1],  # ID du processus parent
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



# horizontal scaling automatique
@routes_bp.route('/scale-containers', methods=['POST'])
def scale_containers():
    try:
        # Obtenir les conteneurs actifs
        containers = client.containers.list()
        alert_containers = []  # Conteneurs à surveiller

        for container in containers:
            stats = container.stats(stream=False)
            # Calcul des seuils pour chaque conteneur
            cpu_stats = stats['cpu_stats']
            precpu_stats = stats['precpu_stats']
            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
            cpu_usage = (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100 if system_delta > 0 else 0

            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_usage_percentage = (memory_usage / memory_limit) * 100

            # Vérifiez si le conteneur dépasse les seuils
            if cpu_usage > CPU_THRESHOLD or memory_usage_percentage > RAM_THRESHOLD:
                alert_containers.append({
                    "name": container.name,
                    "cpu_usage": round(cpu_usage, 2),
                    "memory_usage": round(memory_usage_percentage, 2),
                })

        # Scaling horizontal si des conteneurs dépassent les seuils
        if alert_containers:
            for container_alert in alert_containers:
                # Répliquer un conteneur concerné
                container_to_scale = client.containers.get(container_alert["name"])
                new_container = client.containers.run(
                    container_to_scale.image.tags[0],  # Réutiliser la même image
                    detach=True,  # Mode détaché
                    name=f"{container_to_scale.name}_scaled_{int(time.time())}",
                    environment=container_to_scale.attrs['Config']['Env'],  # Copier les variables d'environnement
                    ports=container_to_scale.attrs['NetworkSettings']['Ports']
                )
                print(f"New container {new_container.name} created due to scaling.")

        return jsonify({"message": "Scaling action completed", "alerts": alert_containers}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
