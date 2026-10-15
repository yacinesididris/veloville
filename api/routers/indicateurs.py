"""Routeur indicateurs.

À compléter : GET /indicateurs/activite-par-jour,
GET /indicateurs/stations-actives et
GET /indicateurs/incidents-par-statut.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session
from api.database import get_db

from fastapi import APIRouter, Depends

@router.get("/", response_model=list[VenteOut])
def get_ventes(db: Session = Depends(get_db)):
    stmt = select(VenteModel)
    return db.scalars(stmt).all()