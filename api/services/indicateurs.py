"""Calcul des indicateurs par agrégation en base de données."""

from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def activite_par_jour(
    session: Session,
    date_debut: date | None = None,
    date_fin: date | None = None,
) -> list[dict[str, Any]]:
    if date_debut is not None and date_fin is not None and date_fin < date_debut:
        raise ValueError(
            "La date de fin doit être égale ou postérieure à la date de début."
        )

    conditions = []
    parametres: dict[str, datetime] = {}

    if date_debut is not None:
        conditions.append("depart_horodatage >= :debut")
        parametres["debut"] = datetime.combine(date_debut, time.min)
    if date_fin is not None:
        conditions.append("depart_horodatage < :fin_exclue")
        parametres["fin_exclue"] = datetime.combine(
            date_fin + timedelta(days=1), time.min
        )

    filtre_dates = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    resultat = session.execute(
        text(
            f"""
            SELECT CAST(depart_horodatage AS DATE) AS jour,
                   COUNT(*) AS nb_trajets
            FROM trajet
            {filtre_dates}
            GROUP BY CAST(depart_horodatage AS DATE)
            ORDER BY jour
            """
        ),
        parametres,
    ).mappings()
    return [dict(ligne) for ligne in resultat]


def stations_actives(
    session: Session, limite: int = 10
) -> list[dict[str, Any]]:
    if limite < 1:
        raise ValueError("La limite doit être supérieure ou égale à 1.")

    resultat = session.execute(
        text(
            """
            WITH departs AS (
                SELECT station_depart AS station_id, COUNT(*) AS nb_departs
                FROM trajet
                GROUP BY station_depart
            ),
            arrivees AS (
                SELECT station_arrivee AS station_id, COUNT(*) AS nb_arrivees
                FROM trajet
                WHERE station_arrivee IS NOT NULL
                GROUP BY station_arrivee
            )
            SELECT s.station_id,
                   s.nom,
                   COALESCE(d.nb_departs, 0) AS nb_departs,
                   COALESCE(a.nb_arrivees, 0) AS nb_arrivees
            FROM station AS s
            LEFT JOIN departs AS d ON d.station_id = s.station_id
            LEFT JOIN arrivees AS a ON a.station_id = s.station_id
            ORDER BY
                COALESCE(d.nb_departs, 0) + COALESCE(a.nb_arrivees, 0) DESC,
                s.station_id ASC
            LIMIT :limite
            """
        ),
        {"limite": limite},
    ).mappings()
    return [dict(ligne) for ligne in resultat]


def incidents_par_statut(session: Session) -> dict[str, Any]:
    incidents = session.execute(
        text(
            """
            SELECT statut, COUNT(*) AS nb_incidents
            FROM incident
            GROUP BY statut
            ORDER BY statut
            """
        )
    ).mappings()

    delai_moyen = session.execute(
        text(
            """
            SELECT ROUND(
                AVG(
                    EXTRACT(EPOCH FROM (date_resolution - date_signalement))
                    / 3600
                )::numeric,
                1
            ) AS delai_moyen_resolution_heures
            FROM incident
            WHERE statut = 'resolu'
              AND date_resolution IS NOT NULL
            """
        )
    ).scalar_one()

    return {
        "donnees": [dict(ligne) for ligne in incidents],
        "delai_moyen_resolution_heures": (
            float(delai_moyen) if delai_moyen is not None else None
        ),
    }
