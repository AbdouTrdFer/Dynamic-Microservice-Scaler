
from routes import send_email_with_multiple_alerts

if __name__ == "__main__":
    try:
        # Liste pour stocker les conteneurs dépassant les seuils
        alert_containers = []

        # Simuler des conteneurs de test
        test_containers = [
            {"name": "test-container1", "cpu_usage": 95, "mem_usage": 92},
            {"name": "test-container2", "cpu_usage": 90, "mem_usage": 100}
        ]

        # Filtrer les conteneurs qui dépassent les seuils
        for container in test_containers:
                alert_containers.append(container)

        # Si des conteneurs dépassent les seuils, envoyer un email
        if alert_containers:
            send_email_with_multiple_alerts(alert_containers)

    except Exception as e:
        print(f"Error during execution: {e}")
