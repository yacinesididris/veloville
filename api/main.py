"""Point d'entrée de l'API VéloVille (FastAPI).

À compléter : créer l'application, inclure les routeurs (auth, stations, trajets,
incidents, indicateurs) et exposer GET /sante -> {"statut": "ok"}.

Lancement : uvicorn api.main:app --reload
"""


from fastapi import FastAPI
from api.database import init_db
from contextlib import asynccontextmanager
from api.routers import indicateurs

@asynccontextmanager
async def lifespan(app : FastAPI):
	init_db()
	yield

app = FastAPI(title="Titre de l'API", lifespan=lifespan)

@app.get("/sante", tags=["Santé"])
def verifier_sante():
    return {"statut" : "ok"}

app.include_router(indicateurs.router)