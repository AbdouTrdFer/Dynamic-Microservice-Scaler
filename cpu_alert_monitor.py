import docker
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import matplotlib.pyplot as plt
from io import BytesIO

# Initialisation du client Docker
client = docker.from_env()

# Fonction pour récupérer l'utilisation du CPU
"""
def check_cpu_usage(container):
    stats = container.stats(stream=False)
    cpu_percent = stats['cpu_stats']['cpu_usage']['total_usage']
    system_cpu = stats['cpu_stats']['system_cpu_usage']
    return (cpu_percent / system_cpu) * 100  # Pourcentage d'utilisation du CPU

# Fonction pour envoyer un e-mail avec le graphique
def send_email(chart_img, container_name, cpu_usage):
    sender_email = "ferhanabdelali@gmail.com"
    receiver_email = "arthurneo52@gmail.com"
    password = "your_email_password"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"ALERT: {container_name} CPU Usage Exceeded"

    # Corps du message
    body = f"Alert: {container_name} exceeded 95% CPU usage! Current CPU usage: {cpu_usage}%"
    msg.attach(MIMEText(body, 'plain'))

    # Attacher l'image du graphique
    img_attachment = MIMEText(chart_img, 'base64', 'png')
    img_attachment.add_header('Content-Disposition', 'attachment', filename='cpu_usage_chart.pdf')
    msg.attach(img_attachment)

    # Envoi de l'email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

# Fonction pour créer un graphique CPU
def generate_cpu_chart(container_name, cpu_usage):
    fig, ax = plt.subplots()
    ax.bar([container_name], [cpu_usage], color='red')
    ax.set_ylabel('CPU Usage (%)')
    ax.set_title(f"CPU Usage for {container_name}")
    buf = BytesIO()
    plt.savefig(buf, format='pdf')
    buf.seek(0)
    return buf.read()

# Vérification des conteneurs et envoi d'alerte
for container in client.containers.list():
    cpu_usage = check_cpu_usage(container)
    if cpu_usage > 95:
        chart_img = generate_cpu_chart(container.name, cpu_usage)
        send_email(chart_img, container.name, cpu_usage)
        print(f"Alert sent for {container.name}: {cpu_usage}% CPU usage.")
"""