"""Routes des indicateurs."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import (
    ActiviteParJourReponse,
    IncidentsParStatutReponse,
    StationsActivesReponse,
)
from api.services.indicateurs import (
    activite_par_jour,
    incidents_par_statut,
    stations_actives,
)
from api.securite import utilisateur_courant

router = APIRouter(
    prefix="/indicateurs",
    tags=["Indicateurs"],
    dependencies=[Depends(utilisateur_courant)],
)


@router.get("/activite-par-jour", response_model=ActiviteParJourReponse)
def get_activite_par_jour(
    date_debut: date | None = None,
    date_fin: date | None = None,
    db: Session = Depends(get_db),
):
    try:
        donnees = activite_par_jour(db, date_debut, date_fin)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"donnees": donnees}


@router.get("/stations-actives", response_model=StationsActivesReponse)
def get_stations_actives(
    limite: int = Query(default=10, ge=1),
    db: Session = Depends(get_db),
):
    try:
        donnees = stations_actives(db, limite)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"donnees": donnees}


@router.get("/incidents-par-statut", response_model=IncidentsParStatutReponse,)
def get_incidents_par_statut(
    db: Session = Depends(get_db),
):
    return incidents_par_statut(db)
