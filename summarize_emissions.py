"""Résume les runs CodeCarbon d'une série et enregistre le résultat.
Usage : python summarize_emissions.py <project_name> <messages_par_run> [nb_runs]
Exemple : python summarize_emissions.py chocobot-baseline 25 3
"""
import csv, json, sys, statistics

project = sys.argv[1]
n_msgs = int(sys.argv[2])
n_runs = int(sys.argv[3]) if len(sys.argv) > 3 else 3

with open("data/emissions.csv") as f:
    rows = [r for r in csv.DictReader(f) if r["project_name"] == project][-n_runs:]
if not rows:
    sys.exit(f"Aucun run trouvé pour '{project}'")

def stats(col):
    vals = [float(r[col]) for r in rows]
    return {"moyenne": statistics.mean(vals), "min": min(vals), "max": max(vals)}

emissions_moy = statistics.mean(float(r["emissions"]) for r in rows)  # kg
summary = {
    "project_name": project,
    "nb_runs": len(rows),
    "messages_par_run": n_msgs,
    "runs_timestamps": [r["timestamp"] for r in rows],
    "codecarbon_version": rows[0]["codecarbon_version"],
    "machine": rows[0]["cpu_model"],
    "pays": rows[0]["country_name"],
    "duration_s": stats("duration"),
    "energy_kwh": stats("energy_consumed"),
    "emissions_kg": stats("emissions"),
    "mg_co2eq_par_message": emissions_moy * 1e6 / n_msgs,
}

out = f"data/summary_{project}.json"
with open(out, "w") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
print(json.dumps(summary, indent=2, ensure_ascii=False))
print(f"\nRésumé enregistré dans {out}")