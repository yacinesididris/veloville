"""Routes de consultation et de mise à jour des incidents."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Incident
from api.schemas import IncidentReponse, IncidentUpdate
from api.securite import exiger_role, utilisateur_courant

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get(
    "",
    response_model=list[IncidentReponse],
    dependencies=[Depends(utilisateur_courant)],
)
def lister_incidents(
    statut: Literal["ouvert", "en_cours", "resolu"] | None = None,
    db: Session = Depends(get_db),
) -> list[Incident]:
    requete = select(Incident)
    if statut is not None:
        requete = requete.where(Incident.statut == statut)
    requete = requete.order_by(Incident.date_signalement.desc())
    return list(db.scalars(requete).all())


@router.put(
    "/{incident_id}/statut",
    response_model=IncidentReponse,
    dependencies=[Depends(exiger_role("exploitant"))],
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
