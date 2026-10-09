# Documentation du Projet ChocoBot - Maison Delcourt

Bienvenue dans la documentation technique et reglementaire du projet **ChocoBot**.

---

## Sommaire des Documents

| Document | Description |
| :--- | :--- |
| **[Rapport d'Audit Reglementaire](Rapport.md)** | Audit juridique complet : RGPD, AI Act, Reglement INCO (Allergenes), Droit de la consommation. |
| **[Registre de Traitement & Fiche AI Act](registre_de_traitement_et_fiche_conformite.md)** | Registre Art. 30 RGPD, Fiche de risque AI Act et Guide de defense pour le controle simule de la CNIL. |
| **[Plan de Mise en Conformite & Roadmap](plan_de_mise_en_conformite.md)** | Synthese d'avancement, analyse des ecarts et plan d'action technique. |
| **[Rapport d'Evaluation Initiale](../RapportEvaluation.md)** | Mesure d'etat initial (tokens, latence, empreinte CodeCarbon et Phoenix). |
| **[Rapport Correctifs Sobriete](../RapportCorrectifsSobriete.md)** | Les 3 leviers d'optimisation (Cache FAQ, routage de modele, fenetre glissante). |
| **[Post-Mortem & Runbook d'Incidents](../PostMortemIncidents.md)** | Supervision (Sentry, logs), resolution des 3 incidents et guide operationnel. |
| **[Securite des Acces & RGPD](securite_et_conformite_rgpd.md)** | Authentification BasicAuth du back-office, droit a l'effacement et consentement Art. 9. |
| **[Monitoring LLM avec Arize Phoenix](monitoring_arize_phoenix.md)** | Instrumentation OpenTelemetry, stockage des metriques et dashboard Phoenix. |
| **[Empreinte Carbone avec CodeCarbon](empreinte_carbone_codecarbon.md)** | Mesure energetique, baseline d'emissions (CO2eq) et dashboard Carbonboard. |
| **[Brief d'Audit Initial](RGPD.md)** | Perimetre et consignes initiales d'evaluation juridique. |

---

## Stack Technique

* **Serveur & API :** FastAPI, Uvicorn, Python 3.12+
* **Modele IA :** Ollama (`llama3.2:3b` / `llama3.2:1b`)
* **Base de donnees :** SQLite (`chocobot.db`)
* **Observabilite :** Arize Phoenix (`arize-phoenix`, OpenTelemetry)
* **Mesure Carbone :** CodeCarbon (`codecarbon`, Carbonboard)
