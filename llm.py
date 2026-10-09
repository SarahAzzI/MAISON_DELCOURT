import os, random, time

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:

    pass

# Monitoring avec Arize Phoenix (serveur local sur http://localhost:6006)
try:
    from phoenix.otel import register
    from openinference.instrumentation.openai import OpenAIInstrumentor

    tracer_provider = register(project_name="chocobot")
    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
except Exception as e:
    print(f"[Monitoring] Info Phoenix : {e}")

# Par défaut : Ollama installé sur votre machine (aucun réglage nécessaire)
BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.getenv("LLM_API_KEY", "ollama")
BIG_MODEL = os.getenv("LLM_MODEL_BIG", "llama3.2:3b")
SMALL_MODEL = os.getenv("LLM_MODEL_SMALL", "llama3.2:1b")


def chat(model, messages, max_tokens=1500):
    """Retourne (texte, usage). Peut lever une exception (Ollama arrêté, modèle absent, panne simulée)."""
    # Simulation d'incidents (optionnelle, voir .env.example)
    time.sleep(float(os.getenv("EXTRA_LATENCY", "0")))
    if random.random() < float(os.getenv("FAIL_RATE", "0")):
        raise RuntimeError("Panne simulée : 503 service unavailable")

    start_time = time.time()
    from openai import OpenAI
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=180)
    r = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens, temperature=0.7)
    duration = time.time() - start_time
    u = r.usage
    p_tokens = getattr(u, "prompt_tokens", 0) if u else 0
    c_tokens = getattr(u, "completion_tokens", 0) if u else 0
    return r.choices[0].message.content, {
        "model": model,
        "prompt_tokens": p_tokens,
        "completion_tokens": c_tokens,
        "total_tokens": p_tokens + c_tokens,
        "latency_seconds": round(duration, 3)
    }

