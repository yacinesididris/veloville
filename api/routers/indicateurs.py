"""Routes des indicateurs."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import ActiviteParJourReponse, StationsActivesReponse
from api.services.indicateurs import activite_par_jour, stations_actives

router = APIRouter(prefix="/indicateurs")


@router.get("/activite-par-jour", response_model=ActiviteParJourReponse)
def get_activite_par_jour(
    date_debut: date | None = None,
    date_fin: date | None = None,
    db: Session = Depends(get_db),
):
    try:
        donnees = activite_par_jour(db, date_debut, date_fin)
    except ValueError as exc: #on récupère l'exeption value error déjà configurée dans activite_par_jour()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not donnees:
        raise HTTPException(
            status_code=404,
            detail="Pas de données pour ces valeurs de dates"
        )
    return {"donnees": donnees}




@router.get("/stations-actives", response_model=StationsActivesReponse)
def get_activite_par_jour(
    limit: int =10,
    db: Session = Depends(get_db),
):
    try:
        donnees = stations_actives(db, limit)
    except ValueError as exc: #on récupère l'exeption value error déjà configurée dans activite_par_jour()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not donnees:
        raise HTTPException(
            status_code=404,
            detail="Pas de données trouvées"
        )
    return {"donnees": donnees}

