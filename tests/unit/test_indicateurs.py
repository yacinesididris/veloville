"""Tests unitaires des agrégations SQL des indicateurs."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest

from api.services.indicateurs import (
    activite_par_jour,
    incidents_par_statut,
    stations_actives,
)


def resultat_mappings(lignes):
    resultat = Mock()
    resultat.mappings.return_value = lignes
    return resultat


def test_activite_par_jour_execute_aggregation_et_filtre_inclusif():
    session = Mock()
    session.execute.return_value = resultat_mappings(
        [{"jour": date(2026, 8, 24), "nb_trajets": 4}]
    )

    donnees = activite_par_jour(
        session, date(2026, 8, 24), date(2026, 8, 30)
    )

    assert donnees == [{"jour": date(2026, 8, 24), "nb_trajets": 4}]
    requete, parametres = session.execute.call_args.args
    assert "COUNT(*) AS nb_trajets" in str(requete)
    assert "GROUP BY CAST(depart_horodatage AS DATE)" in str(requete)
    assert parametres == {
        "debut": datetime(2026, 8, 24),
        "fin_exclue": datetime(2026, 8, 31),
    }


def test_activite_par_jour_sans_dates_ne_filtre_pas_la_periode():
    session = Mock()
    session.execute.return_value = resultat_mappings([])

    assert activite_par_jour(session) == []

    requete, parametres = session.execute.call_args.args
    assert "WHERE" not in str(requete)
    assert parametres == {}


def test_activite_par_jour_refuse_une_periode_inversee():
    session = Mock()

    with pytest.raises(ValueError, match="date de fin"):
        activite_par_jour(session, date(2026, 8, 30), date(2026, 8, 24))

    session.execute.assert_not_called()


def test_stations_actives_inclut_les_stations_arrivees_uniquement():
    session = Mock()
    session.execute.return_value = resultat_mappings(
        [
            {
                "station_id": "S002",
                "nom": "Arrivée seulement",
                "nb_departs": 0,
                "nb_arrivees": 3,
            }
        ]
    )

    donnees = stations_actives(session, limite=5)

    assert donnees[0]["station_id"] == "S002"
    requete, parametres = session.execute.call_args.args
    assert "LEFT JOIN arrivees" in str(requete)
    assert "FROM station AS s" in str(requete)
    assert "ORDER BY" in str(requete)
    assert parametres == {"limite": 5}


def test_stations_actives_refuse_limite_invalide():
    session = Mock()

    with pytest.raises(ValueError, match="limite"):
        stations_actives(session, limite=0)

    session.execute.assert_not_called()


def test_incidents_par_statut_agrege_statuts_et_delai_dans_postgresql():
    session = Mock()
    session.execute.side_effect = [
        resultat_mappings(
            [
                {"statut": "en_cours", "nb_incidents": 2},
                {"statut": "resolu", "nb_incidents": 3},
            ]
        ),
        Mock(scalar_one=Mock(return_value=Decimal("12.3"))),
    ]

    donnees = incidents_par_statut(session)

    assert donnees == {
        "donnees": [
            {"statut": "en_cours", "nb_incidents": 2},
            {"statut": "resolu", "nb_incidents": 3},
        ],
        "delai_moyen_resolution_heures": 12.3,
    }
    requete_delai = str(session.execute.call_args_list[1].args[0])
    assert "EXTRACT(EPOCH FROM" in requete_delai
    assert "ROUND(" in requete_delai


def test_incidents_par_statut_retourne_aucun_delai_si_aucun_incident_resolu():
    session = Mock()
    session.execute.side_effect = [
        resultat_mappings([{"statut": "ouvert", "nb_incidents": 1}]),
        Mock(scalar_one=Mock(return_value=None)),
    ]

    donnees = incidents_par_statut(session)

    assert donnees["delai_moyen_resolution_heures"] is None
