"""Gestionnaire d'incidents, de supervision (Sentry) et de résilience pour ChocoBot.
Permet la journalisation structurée, la notification d'alerte et le mode dégradé (fallback).
"""
import os, json, time, logging, traceback
from datetime import datetime

# Dossier des logs
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configuration du logging structuré local
LOG_FILE = os.path.join(LOG_DIR, "incidents.log")
logger = logging.getLogger("chocobot.incidents")
logger.setLevel(logging.INFO)

if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "event": %(message)s}')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

# Initialisation Sentry (si configuré dans .env)
SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
SENTRY_ACTIVE = False

if SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=1.0,
            environment=os.getenv("ENVIRONMENT", "production"),
            send_default_pii=False,  # Conformité RGPD : jamais de PII envoyée à Sentry
        )
        SENTRY_ACTIVE = True
        print(f"[Monitoring] Sentry connecté avec succès (DSN actif)")
    except Exception as e:
        print(f"[Monitoring] Erreur initialisation Sentry : {e}")
else:
    print("[Monitoring] Sentry non configuré (SENTRY_DSN absent). Mode supervision locale actif dans logs/incidents.log.")


def record_incident(incident_type: str, message: str, session_id: str = None, exc: Exception = None) -> dict:
    """Enregistre un incident dans Sentry, dans le fichier de logs local et en base de données."""
    stack = traceback.format_exc() if exc else None
    short_sid = session_id[:8] if session_id else "system"

    incident_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": incident_type,
        "message": str(message),
        "session": short_sid,
        "stacktrace": stack if exc else None,
        "sentry_reported": SENTRY_ACTIVE
    }

    # 1. Envoi Sentry (si actif)
    if SENTRY_ACTIVE:
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("incident_type", incident_type)
                scope.set_tag("session_id", short_sid)
                if exc:
                    sentry_sdk.capture_exception(exc)
                else:
                    sentry_sdk.capture_message(f"[{incident_type}] {message}", level="error")
        except Exception as se:
            print(f"[Monitoring] Échec transmission Sentry : {se}")

    # 2. Journalisation structurée locale
    logger.error(json.dumps(incident_data, ensure_ascii=False))

    # 3. Écriture dans logs/incidents.jsonl pour audit immédiat
    try:
        with open(os.path.join(LOG_DIR, "incidents.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(incident_data, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return incident_data


def get_fallback_recommendation(customer: dict = None) -> str:
    """
    RÉSOLUTION D'INCIDENT · Mode dégradé de secours (Fallback gracieux).
    Garantit une réponse sûre sans dépendre du LLM en cas de panne d'API (503).
    """
    allergies = (customer.get("allergies") or "").lower() if customer else ""

    if "coque" in allergies or "noisette" in allergies or "noix" in allergies:
        return (
            "⚠️ *Information de service : Notre assistant d'échange en direct est momentanément indisponible.*\n\n"
            "Pour respecter strictement vos allergies aux fruits à coque, nous vous orientons vers notre sélection garantie sans noix :\n"
            "• **Coffret Sans Noix (C04 - 28 €)** : ganache vanille, framboise, menthe.\n\n"
            "Nos chocolatiers en boutique à Lille (03 20 00 00 00) sont à votre disposition pour vous conseiller."
        )

    return (
        "⚠️ *Information de service : Notre assistant d'échange en direct est momentanément indisponible.*\n\n"
        "Voici notre sélection incontournable de la Maison Delcourt :\n"
        "• **Coffret Beffroi (C01 - 24 €)** : notre grand classique chocolat au lait et praliné.\n"
        "• **Coffret Ch'ti Noir (C02 - 32 €)** : chocolat noir intense 72% et orange confite.\n"
        "• **Coffret Gaufre de Lille (C03 - 18 €)** : gourmand aux gaufres vergeoises et spéculoos.\n\n"
        "N'hésitez pas à vérifier les allergènes sur nos emballages ou à contacter nos boutiques lilloises."
    )
