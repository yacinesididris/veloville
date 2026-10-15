"""Point d'entrée de l'API VéloVille (FastAPI).

À compléter : créer l'application, inclure les routeurs (auth, stations, trajets,
incidents, indicateurs) et exposer GET /sante -> {"statut": "ok"}.

Lancement : uvicorn api.main:app --reload
"""


from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.database import init_db
from api.routers import auth, incidents, indicateurs, stations, trajets

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="API VéloVille", lifespan=lifespan)


@app.get("/sante", tags=["Sante"])
def verifier_sante():
    return {"statut": "ok"}

app.include_router(auth.router)
app.include_router(stations.router)
app.include_router(trajets.router)
app.include_router(incidents.router)
app.include_router(indicateurs.router)