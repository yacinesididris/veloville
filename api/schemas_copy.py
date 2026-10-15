"""Schémas Pydantic d'import et de lecture des données métier."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field



class StationAjout(BaseModel):
    station_id: str = Field(max_length=10)
    nom: str = Field(max_length=100)
    commune: str = Field(max_length=100)
    capacite: int = Field(ge=1)
    latitude: Decimal = Field(
        max_digits=8, decimal_places=5, ge=-90, le=90
    )
    longitude: Decimal = Field(
        max_digits=8, decimal_places=5, ge=-180, le=180
    )
    date_mise_en_service: date


class StationReponse(StationAjout):
    model_config = ConfigDict(from_attributes=True)


class TrajetAjout(BaseModel):
    trajet_id: str = Field(max_length=12)
    velo_id: str = Field(max_length=8)
    depart_horodatage: datetime
    station_depart: str = Field(max_length=10)
    station_arrivee: str | None = Field(default=None, max_length=10)
    duree_secondes: int = Field(gt=0)
    type_usager: Literal["abonne", "occasionnel"]
    usager_ref: str | None = Field(default=None, max_length=9)

    #La contrainte type_usager/usager_ref est déjà vérifiée à l'import CSV


class TrajetReponse(TrajetAjout):
    model_config = ConfigDict(from_attributes=True)


class IncidentAjout(BaseModel):
    incident_id: str = Field(max_length=12)
    date_signalement: datetime
    cible: Literal["velo", "station"]
    velo_id: str | None = Field(default=None, max_length=8)
    station_id: str | None = Field(default=None, max_length=10)
    type_incident: Literal[
        "vandalisme",
        "selle abimee",
        "eclairage HS",
        "chaine deraillee",
        "ecran borne illisible",
        "pneu creve",
        "frein defectueux",
        "borne hors service",
    ]
    statut: Literal["ouvert", "en_cours", "resolu"]
    date_resolution: datetime | None = None
    technicien: str | None = Field(default=None, max_length=100)

    # Les contraintes entre cible, références et dates sont vérifiées à l'import CSV.


class IncidentReponse(IncidentAjout):
    model_config = ConfigDict(from_attributes=True)


class IncidentUpdate(BaseModel):
    pass
