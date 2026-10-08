# Documentation du Projet ChocoBot · Maison Delcourt

Bienvenue dans la documentation technique et réglementaire du projet **ChocoBot**.

---

## 📚 Sommaire des Documents

| Document | Description |
| :--- | :--- |
| **[Rapport d'Audit Réglementaire](Rapport.md)** | Audit juridique complet : RGPD, AI Act, Règlement INCO (Allergènes), Droit de la consommation. |
| **[Brief d'Audit Initial](RGPD.md)** | Périmètre et consignes initiales d'évaluation juridique. |
| **[Monitoring LLM avec Arize Phoenix](monitoring_arize_phoenix.md)** | Instrumentation OpenTelemetry, stockage des métriques et dashboard Phoenix. |
| **[Empreinte Carbone avec CodeCarbon](empreinte_carbone_codecarbon.md)** | Mesure énergétique, baseline d'émissions (CO₂eq) et dashboard Carbonboard. |
| **[Sécurité des Accès & RGPD](securite_et_conformite_rgpd.md)** | Authentification BasicAuth du back-office, droit à l'effacement et consentement Art. 9. |

---

## 🛠️ Stack Technique

* **Serveur & API :** FastAPI, Uvicorn, Python 3.12+
* **Modèle IA :** Ollama (`llama3.2:3b` / `llama3.2:1b`)
* **Base de données :** SQLite (`chocobot.db`)
* **Observabilité :** Arize Phoenix (`arize-phoenix`, OpenTelemetry)
* **Mesure Carbone :** CodeCarbon (`codecarbon`, Carbonboard)
