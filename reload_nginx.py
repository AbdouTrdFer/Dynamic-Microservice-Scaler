import subprocess

def reload_nginx():
    try:
        result = subprocess.run(['nginx', '-s', 'reload'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.decode())  # Afficher la sortie standard
    except FileNotFoundError:
        print("Erreur : NGINX n'est pas installé ou n'est pas dans le chemin d'exécution.")
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du rechargement de NGINX : {e.stderr.decode()}")
