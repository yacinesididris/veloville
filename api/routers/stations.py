"""Routes de consultation des stations."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Station
from api.schemas import StationReponse
from api.securite import utilisateur_courant

router = APIRouter(
    prefix="/stations",
    tags=["Stations"],
    dependencies=[Depends(utilisateur_courant)],
)


@router.get("", response_model=list[StationReponse])
def lister_stations(
    commune: str | None = None,
    db: Session = Depends(get_db),
) -> list[Station]:
    requete = select(Station)
    if commune is not None:
        requete = requete.where(Station.commune == commune)
    requete = requete.order_by(Station.station_id)
    return list(db.scalars(requete).all())


@router.get("/{station_id}", response_model=StationReponse)
def obtenir_station(
    station_id: str,
    db: Session = Depends(get_db),
) -> Station:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station introuvable")
    return station
