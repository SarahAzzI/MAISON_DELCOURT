"""Envoie une série de messages réalistes à ChocoBot (serveur lancé sur le port 8000).
Usage : python load_test.py [nombre_de_conversations]   (défaut : 2, soit 10 messages)
Avec un vrai LLM chaque message prend plusieurs secondes : commencez petit."""
import json, sys, time, urllib.request
from codecarbon import EmissionsTracker
BASE = "http://localhost:8000"
SCENARIO = [
    "Quels sont vos horaires ?",
    "Je cherche un coffret pour 30 euros, mon fils est allergique aux noisettes.",
    "Et pour les enfants, vous avez quoi ?",
    "Quels sont vos horaires ?",
    "Merci, je prends le coffret sans noix !",
]


def post(path, payload):
    req = urllib.request.Request(BASE + path, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
RUN = int(time.time())  # sessions neuves à chaque lancement : mesures comparables
warm_sid = f"warmup-{RUN}"
post("/profile", {"session_id": warm_sid, "name": "Warmup", "email": "warmup@example.com",
                  "allergies": "", "children_ages": ""})
post("/chat", {"session_id": warm_sid, "message": "Bonjour"})

tracker = EmissionsTracker(
    project_name="chocobot-baseline",
    output_dir="data",
    output_file="emissions.csv",
    log_level="error",
)

nb_messages = n * len(SCENARIO)
tracker.start()
try:
    for i in range(n):
        sid = f"test-{RUN}-{i}"
        post("/profile", {"session_id": sid, "name": f"Client Test {i}",
                          "email": f"client{i}@example.com",
                          "allergies": "noisettes", "children_ages": "6, 9"})
        for msg in SCENARIO:
            post("/chat", {"session_id": sid, "message": msg})
finally:
    emissions = tracker.stop()  # kg CO2eq pour tout le test

print(f"{nb_messages} messages envoyés.")
print(f"Émissions totales : {emissions * 1000:.4f} g CO2eq")
print(f"Par message : {emissions * 1000 / nb_messages:.4f} g CO2eq")
