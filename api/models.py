from api.database import Base
from sqlalchemy.orm import Mapped, mapped_column

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    ForeignKey, CheckConstraint, 
    String, Numeric, DateTime, Integer)

class Station(Base):
    __tablename__ = "station"

    station_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    commune: Mapped[str] = mapped_column(String(100))
    capacite: Mapped[int]
    latitude: Mapped[Decimal] = mapped_column(Numeric(8, 5))
    longitude: Mapped[Decimal] = mapped_column(Numeric(8, 5))
    date_mise_en_service: Mapped[date]

    __table_args__ = (
    CheckConstraint("capacite > 0", name="station_capacite_check"),
    CheckConstraint("latitude >= -90 AND latitude <= 90", name="station_latitude_check"),
    CheckConstraint("longitude >= -180 AND longitude <= 180", name="station_longitude_check"),
	)


class Trajet(Base):
    __tablename__ = "trajet"

    trajet_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    velo_id: Mapped[str] = mapped_column(String(8))
    depart_horodatage: Mapped[datetime] = mapped_column(DateTime)
    station_depart: Mapped[str] = mapped_column(String(10), 
                                                ForeignKey("station.station_id"))
    station_arrivee: Mapped[str | None ] = mapped_column(String(10), 
                                                ForeignKey("station.station_id"))
    
    duree_secondes: Mapped[int] = mapped_column(Integer)
    type_usager: Mapped[str] = mapped_column(String(50))
    usager_ref:Mapped[str | None] = mapped_column(String(9))

    __table_args__ = (
    CheckConstraint("duree_secondes > 0", name="trajet_duree_secondes_check"),
    CheckConstraint("type_usager IN ('abonne', 'occasionnel')", name="trajet_type_usager_check"),
    CheckConstraint(("(type_usager = 'occasionnel' AND usager_ref IS NULL)"
    " OR (type_usager = 'abonne' AND usager_ref IS NOT NULL)"),
      name="chk_usager_ref"),)

    class Incident(Base):
        __tablename__ = "incident"

    incident_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    date_signalement: Mapped[datetime] = mapped_column(DateTime)
    cible: Mapped[str] = mapped_column(String(50))
    velo_id: Mapped[str | None] = mapped_column(String(8))
    station_id: Mapped[str] = mapped_column(String(10), 
                                                ForeignKey("station.station_id"))
    type_incident: Mapped[str] = mapped_column(String(50))
    statut: Mapped[str] = mapped_column(String(10))
    date_resolution: Mapped[datetime | None] = mapped_column(DateTime)
    technicien: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (
    CheckConstraint(
        "type_incident IN ("
        "'vandalisme', "
        "'selle abimee', "
        "'eclairage HS', "
        "'chaine deraillee', "
        "'ecran borne illisible', "
        "'pneu creve', "
        "'frein defectueux', "
        "'borne hors service'"
        ")",
        name="incident_type_incident_check"
    ),

    CheckConstraint(
        "statut IN ('ouvert', 'en_cours', 'resolu')",
        name="incident_statut_check"
    ),

    CheckConstraint(
        "(cible = 'velo' AND velo_id IS NOT NULL) "
        "OR "
        "(cible = 'station' AND velo_id IS NULL)",
        name="chk_velo_id"
    ),

    CheckConstraint(
        "(cible = 'station' AND station_id IS NOT NULL) "
        "OR "
        "(cible = 'velo' AND station_id IS NULL)",
        name="chk_station_id"
    ),

    CheckConstraint(
        "(statut = 'resolu' "
        "AND date_resolution >= date_signalement "
        "AND date_resolution IS NOT NULL) "
        "OR "
        "(statut IN ('ouvert', 'en_cours') "
        "AND date_resolution IS NULL)",
        name="chk_date_resolution"
    ),
)


class Utilisateur(Base):
    __tablename__ = "utilisateur"

    id_utilisateur: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))

    __table_args__= (
    CheckConstraint(
        "role IN ('exploitant', 'direction')",
        name="utilisateur_role_check"
    ),

    )