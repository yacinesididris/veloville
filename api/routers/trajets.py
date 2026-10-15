"""Route de consultation des trajets."""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Trajet
from api.schemas import PageReponse, TrajetReponse
from api.securite import get_current_user

router = APIRouter(
    prefix="/trajets",
    tags=["Trajets"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=PageReponse[TrajetReponse])
def lister_trajets(
    date_debut: date | None = None,
    date_fin: date | None = None,
    station: str | None = None,
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    if date_debut is not None and date_fin is not None and date_fin < date_debut:
        raise HTTPException(
            status_code=422,
            detail="La date de fin doit être égale ou postérieure à la date de début.",
        )

    filtres = []
    if date_debut is not None:
        filtres.append(
            Trajet.depart_horodatage >= datetime.combine(date_debut, time.min)
        )
    if date_fin is not None:
        lendemain = datetime.combine(date_fin + timedelta(days=1), time.min)
        filtres.append(Trajet.depart_horodatage < lendemain)
    if station is not None:
        filtres.append(
            or_(
                Trajet.station_depart == station,
                Trajet.station_arrivee == station,
            )
        )

    total = db.scalar(select(func.count()).select_from(Trajet).where(*filtres))
    requete = (
        select(Trajet)
        .where(*filtres)
        .order_by(Trajet.depart_horodatage, Trajet.trajet_id)
        .offset((page - 1) * taille_page)
        .limit(taille_page)
    )
    return {
        "total": total or 0,
        "page": page,
        "taille_page": taille_page,
        "resultats": list(db.scalars(requete).all()),
    }
