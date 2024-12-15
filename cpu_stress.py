import time

def stress_cpu():
    """Effectuer des calculs intensifs pour simuler une surcharge CPU."""
    while True:
        x = 0
        for i in range(1000000):
            x += i

if __name__ == "__main__":
    print("Surcharge CPU en cours...")
    stress_cpu()
