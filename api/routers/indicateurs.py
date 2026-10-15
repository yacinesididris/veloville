"""Routes des indicateurs."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import ActiviteParJourReponse
from api.services.indicateurs import activite_par_jour

router = APIRouter(prefix="/indicateurs")


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
