import os, json, secrets
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
from chatbot import handle_chat
import db
import llm
import incidents


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Purge automatique des sessions inactives > 30 jours (RGPD Art. 5.1.e)
    try:
        db.purge_old_sessions(max_age_seconds=30 * 86400)
        print("[RGPD] Purge automatique des données expirées exécutée avec succès.")
    except Exception as e:
        print(f"[RGPD] Erreur lors de la purge automatique : {e}")
    yield


app = FastAPI(title="ChocoBot - Maison Delcourt", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="images"), name="images")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Diagnostique et journalise l'incident 'Donnée corrompue'."""
    incidents.record_incident(
        "DONNEE_CORROMPUE",
        f"Format de données invalide sur {request.url.path} : {exc.errors()}",
        exc=exc
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Données envoyées invalides ou corrompues.", "errors": exc.errors()}
    )


# Authentification d'administration (identifiants configurables via variables d'environnement)
security = HTTPBasic()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "delcourt2026!")


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    is_user_ok = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    is_pass_ok = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (is_user_ok and is_pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants d'administration incorrects",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class ChatIn(BaseModel):
    session_id: str
    message: str


class ProfileIn(BaseModel):
    session_id: str
    name: str = ""
    email: str = ""
    allergies: str = ""
    children_ages: str = ""
    family_friendly: bool = False
    consent_data: bool = True  # Consentement explicite au traitement des données (RGPD Art. 9)


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.post("/profile")
def profile(body: ProfileIn):
    if body.allergies and not body.consent_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le consentement explicite est obligatoire pour le traitement des données relatives aux allergies (RGPD Art. 9)."
        )
    # Si le champ family_friendly est activé et children_ages non spécifié, on note l'usage familial
    kids_info = body.children_ages if body.children_ages else ("oui (sélection familiale)" if body.family_friendly else "")
    db.save_customer(body.session_id, body.name, body.email, body.allergies, kids_info)
    return {"status": "saved"}


@app.delete("/profile/{session_id}")
def delete_profile(session_id: str):
    """Exercice du droit à l'effacement (RGPD Art. 17)."""
    db.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@app.post("/chat")
def chat(body: ChatIn):
    return handle_chat(body.session_id, body.message)


# Back-office de l'équipe Delcourt : protégé par authentification HTTP Basic
@app.get("/admin")
def admin(_: str = Depends(verify_admin)):
    return FileResponse("static/admin.html")


@app.get("/admin/data")
def admin_data(_: str = Depends(verify_admin)):
    data = db.get_all()
    data["llm"] = {"big": llm.BIG_MODEL, "small": llm.SMALL_MODEL}
    # Récupération des logs récents d'incidents
    try:
        incidents_list = []
        log_jsonl = os.path.join(os.path.dirname(__file__), "logs", "incidents.jsonl")
        if os.path.exists(log_jsonl):
            with open(log_jsonl, encoding="utf-8") as f:
                incidents_list = [json.loads(line) for line in f if line.strip()][-20:]
                incidents_list.reverse()
        data["recent_incidents"] = incidents_list
    except Exception:
        data["recent_incidents"] = []
    return data


@app.get("/admin/incidents")
def get_incidents(_: str = Depends(verify_admin)):
    """Consulte le journal des incidents supervisés (Sentry & local)."""
    log_file = os.path.join(os.path.dirname(__file__), "logs", "incidents.jsonl")
    if not os.path.exists(log_file):
        return {"incidents": []}
    with open(log_file, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]
    return {"incidents": list(reversed(items[-50:]))}


@app.get("/health")
def health():
    return {"status": "ok"}

