"""Routes de consultation et de mise à jour des incidents."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Incident
from api.schemas import IncidentReponse, IncidentUpdate, PageReponse
from api.securite import get_current_user, require_role

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get(
    "",
    response_model=PageReponse[IncidentReponse],
    dependencies=[Depends(get_current_user)],
)
def lister_incidents(
    statut: Literal["ouvert", "en_cours", "resolu"] | None = None,
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    filtres = []
    if statut is not None:
        filtres.append(Incident.statut == statut)

    total = db.scalar(select(func.count()).select_from(Incident).where(*filtres))
    requete = (
        select(Incident)
        .where(*filtres)
        .order_by(Incident.date_signalement.desc(), Incident.incident_id)
        .offset((page - 1) * taille_page)
        .limit(taille_page)
    )
    return {
        "total": total or 0,
        "page": page,
        "taille_page": taille_page,
        "resultats": list(db.scalars(requete).all()),
    }


@router.put(
    "/{incident_id}/statut",
    response_model=IncidentReponse,
    dependencies=[Depends(require_role("exploitant"))],
)
def modifier_statut_incident(
    incident_id: str,
    requete: IncidentUpdate,
    db: Session = Depends(get_db),
) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident introuvable")

    transitions_autorisees = {
        "ouvert": {"en_cours", "resolu"},
        "en_cours": {"resolu"},
    }
    if requete.statut not in transitions_autorisees.get(incident.statut, set()):
        raise HTTPException(
            status_code=422,
            detail="Transition de statut non autorisee",
        )

    incident.statut = requete.statut
    if requete.statut == "resolu" and incident.date_resolution is None:
        incident.date_resolution = datetime.now()

    db.commit()
    db.refresh(incident)
    return incident
