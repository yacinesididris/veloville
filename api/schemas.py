"""Schémas Pydantic d'import et de lecture des données métier."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConnexionRequete(BaseModel):
    username: str = Field(max_length=50)
    password: str


class ConnexionReponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    role: Literal["exploitant", "direction"]


class StationsActivesParametres(BaseModel):
    limite: int = Field(default=10, ge=1)


class StationReponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class TrajetReponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trajet_id: str = Field(max_length=12)
    velo_id: str = Field(max_length=8)
    depart_horodatage: datetime
    station_depart: str = Field(max_length=10)
    station_arrivee: str | None = Field(default=None, max_length=10)
    duree_secondes: int = Field(gt=0)
    type_usager: Literal["abonne", "occasionnel"]
    usager_ref: str | None = Field(default=None, max_length=9)


class IncidentReponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class IncidentUpdate(BaseModel):
    statut: Literal["en_cours", "resolu"]


class ActiviteJourReponse(BaseModel):
    jour: date
    nb_trajets: int = Field(ge=0)


class ActiviteParJourReponse(BaseModel):
    donnees: list[ActiviteJourReponse]


class StationActiveReponse(BaseModel):
    station_id: str = Field(max_length=10)
    nom: str = Field(max_length=100)
    nb_departs: int = Field(ge=0)
    nb_arrivees: int = Field(ge=0)


class StationsActivesReponse(BaseModel):
    reponse: list[StationActiveReponse]


class IncidentsParStatutItem(BaseModel):
    statut: Literal["ouvert", "en_cours", "resolu"]
    nb_incidents: int = Field(ge=0)


class IncidentsParStatutReponse(BaseModel):
    reponse: list[IncidentsParStatutItem]
    delai_moyen_resolution_heures: float | None
