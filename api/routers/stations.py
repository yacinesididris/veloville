"""Routes de consultation des stations."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Station
from api.schemas import PageReponse, StationReponse
from api.securite import get_current_user

router = APIRouter(
    prefix="/stations",
    tags=["Stations"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=PageReponse[StationReponse])
def lister_stations(
    commune: str | None = None,
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    filtres = []
    if commune is not None:
        filtres.append(Station.commune == commune)

    total = db.scalar(select(func.count()).select_from(Station).where(*filtres))
    requete = (
        select(Station)
        .where(*filtres)
        .order_by(Station.station_id)
        .offset((page - 1) * taille_page)
        .limit(taille_page)
    )
    return {
        "total": total or 0,
        "page": page,
        "taille_page": taille_page,
        "resultats": list(db.scalars(requete).all()),
    }


@router.get("/{station_id}", response_model=StationReponse)
def obtenir_station(
    station_id: str,
    db: Session = Depends(get_db),
) -> Station:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station introuvable")
    return station
