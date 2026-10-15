"""Route de consultation des trajets."""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Trajet
from api.schemas import TrajetReponse
from api.securite import utilisateur_courant

router = APIRouter(
    prefix="/trajets",
    tags=["Trajets"],
    dependencies=[Depends(utilisateur_courant)],
)


@router.get("", response_model=list[TrajetReponse])
def lister_trajets(
    date_debut: date | None = None,
    date_fin: date | None = None,
    station: str | None = None,
    db: Session = Depends(get_db),
) -> list[Trajet]:
    if date_debut is not None and date_fin is not None and date_fin < date_debut:
        raise HTTPException(
            status_code=422,
            detail="La date de fin doit être égale ou postérieure à la date de début.",
        )

    requete = select(Trajet)
    if date_debut is not None:
        requete = requete.where(
            Trajet.depart_horodatage >= datetime.combine(date_debut, time.min)
        )
    if date_fin is not None:
        lendemain = datetime.combine(date_fin + timedelta(days=1), time.min)
        requete = requete.where(Trajet.depart_horodatage < lendemain)
    if station is not None:
        requete = requete.where(
            or_(
                Trajet.station_depart == station,
                Trajet.station_arrivee == station,
            )
        )

    requete = requete.order_by(Trajet.depart_horodatage)
    return list(db.scalars(requete).all())
