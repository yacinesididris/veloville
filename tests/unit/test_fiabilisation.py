"""Tests unitaires des règles de fiabilisation.

À compléter : un test par règle, cas nominal et cas de rejet.
"""

import pandas as pd
import pytest

from api.services.fiabilisation import (
    _motif_rejet_cible_incident,
    lever_erreur_rejet,
    nettoyage_capacite_station,
    nettoyage_coherence_date_resolution,
    nettoyage_cible_incident,
    nettoyage_dates_resolution_incoherentes,
    nettoyage_doublons,
    nettoyage_horodatage_obligatoire,
    nettoyage_horodatage_optionnel,
    nettoyage_pb_de_casse,
    nettoyage_ref_station_id_optionnel,
    nettoyage_ref_station_id_obligatoire,
    nettoyage_ref_velo_id_obligatoire,
    nettoyage_ref_velo_id_optionnel,
    nettoyage_station_arrivee_inconnue,
    nettoyage_station_depart_inconnue,
    nettoyage_trajets_invalides,
    nettoyage_usager_ref_trajet,
    signaler_technicien_manquant,
)

# À noter : ces fonctions sont pures, elles peuvent donc être testées sans accès à la BDD.
# On vérifie les rejets dans les logs sans avoir à les provoquer dans chaque test.

def verifier_erreurs_de_rejet(logs):
    rejets = [log for log in logs if log["décision"] == "rejeté"]
    assert rejets
    for log in rejets:
        with pytest.raises(
            ValueError,
            match=f"Ligne {log['numero-ligne']} rejetée",
        ):
            lever_erreur_rejet(log)

""" RG1 | Une station est identifiée de façon unique par `station_id`. Sa capacité est un entier strictement positif."""

#On vérifie les doublons dans le csv, un autre controle doublon est fait pendant l'import dans la BDD
def test_RG1(caplog):
    stations = pd.DataFrame(
        {
            "station_id": ["S001", "S002", None, "S001"],
            "capacite": ["20", "0", "10", "15"],
        },
        index=[1, 2, 3, 4],
    )

    with caplog.at_level("ERROR", logger="api.services.fiabilisation"):
        valides, logs_capacite = nettoyage_capacite_station(stations)
        valides, logs_id = nettoyage_ref_station_id_obligatoire(
            valides, "station_id"
        )
        valides, logs_doublons = nettoyage_doublons(valides, "station_id")

    logs = logs_capacite + logs_id + logs_doublons

    assert valides.index.tolist() == [1]
    assert len(logs) == 3
    assert all(log["décision"] == "rejeté" for log in logs)
    assert len(caplog.records) == 3
    assert all(record.levelname == "ERROR" for record in caplog.records)
    assert [record.message for record in caplog.records] == [
        "Ligne 2 rejetée : capacité invalide (doit être un entier strictement positif)",
        "Ligne 3 rejetée : station_id manquant",
        "Ligne 4 rejetée : doublon sur la clé station_id",
    ]
    verifier_erreurs_de_rejet(logs)

""" RG2 | Un trajet relie deux stations du référentiel : 
 - La station de départ est obligatoire et doit exister ; 
 - La station d'arrivée, lorsqu'elle est renseignée, doit exister."""

def test_RG2_rejet_station_depart_inconnue():
    trajets = pd.DataFrame({"station_depart": ["S999"]}, index=[10])

    valides, logs = nettoyage_station_depart_inconnue(trajets, {"S001"})

    assert valides.empty
    verifier_erreurs_de_rejet(logs)


""" RG3 | La station d'arrivée d'un trajet peut être inconnue (vélo non restitué au moment de l'export). 
Le trajet est conservé ; il ne compte pas comme arrivée pour aucune station. """

def test_RG3_arrivee_inconnue_est_conservee_sans_rejet():
    trajets = pd.DataFrame({"station_arrivee": ["S999"]}, index=[11])

    valides, logs = nettoyage_station_arrivee_inconnue(trajets, {"S001"})

    assert valides.index.tolist() == [11]
    assert pd.isna(valides.at[11, "station_arrivee"])
    assert logs[0]["décision"] == "référence mise à nul"

""" RG4 | La durée d'un trajet est un entier strictement positif, exprimé en secondes. """

def test_RG4_rejet_duree_invalide():
    trajets = pd.DataFrame({"duree_secondes": [0, 20]}, index=[12, 13])

    valides, logs = nettoyage_trajets_invalides(trajets)

    assert valides.index.tolist() == [13]
    verifier_erreurs_de_rejet(logs)

""" RG5 | Un trajet d'abonné porte un pseudonyme d'usager (`usager_ref`) ;
     un trajet d'usager occasionnel n'en porte pas. 
     Aucune donnée directement identifiante n'est conservée. """

def test_RG5_rejet_coherence_type_usager_ref():
    trajets = pd.DataFrame(
        {
            "type_usager": ["abonne", "occasionnel"],
            "usager_ref": [None, "PSEUDO001"],
        },
        index=[14, 15],
    )

    valides, logs = nettoyage_usager_ref_trajet(trajets)

    assert valides.empty
    verifier_erreurs_de_rejet(logs)

""" RG6 | Un incident vise soit un vélo, soit une station, jamais les deux ni aucun :
 `cible` détermine laquelle des deux références est renseignée. 
 Une station visée doit exister dans le référentiel. """

def test_RG6_rejet_cible_sans_reference_correspondante():
    incidents = pd.DataFrame(
        {"cible": ["velo"], "velo_id": [None], "station_id": [None]},
        index=[16],
    )

    valides, logs = nettoyage_cible_incident(incidents, {"S001"})

    assert valides.empty
    verifier_erreurs_de_rejet(logs)

""" RG7 | Un incident est dans l'un des trois statuts `ouvert`, `en_cours`, `resolu`. 
Les transitions autorisées sont `ouvert -> en_cours`, `ouvert -> resolu` et `en_cours -> resolu`. 
Un incident résolu n'évolue plus.  """

def test_RG7_rejet_statut_non_autorise():
    incidents = pd.DataFrame({"statut": ["termine"]}, index=[17])

    valides, logs = nettoyage_pb_de_casse(incidents)

    assert valides.empty
    verifier_erreurs_de_rejet(logs)



def test_RG8_rejet_coherence_date_resolution():
    incidents = pd.DataFrame(
        {
            "statut": ["resolu", "ouvert"],
            "date_resolution": [pd.NaT, pd.Timestamp("2026-01-02")],
        },
        index=[18, 19],
    )

    valides, logs = nettoyage_coherence_date_resolution(incidents)

    assert valides.empty
    verifier_erreurs_de_rejet(logs)

""" RG8 | La date de résolution est renseignée si et seulement si l'incident est résolu, 
et elle est postérieure ou égale à la date de signalement. 
Le nom du technicien est attendu dès la prise en charge ; 
son absence est signalée mais n'empêche pas l'enregistrement. """

def test_RG8_absence_technicien_est_un_avertissement_non_bloquant():
    incidents = pd.DataFrame(
        {"statut": ["en_cours"], "technicien": [" "]},
        index=[20],
    )

    valides, logs = signaler_technicien_manquant(incidents)

    assert valides.index.tolist() == [20]
    assert logs[0]["décision"] == "avertissement"
    assert not [log for log in logs if log["décision"] == "rejeté"]


# RG2 / RG3 | Une station d'arrivée facultative peut être absente.
# Si elle est renseignée, on normalise son format ou on rejette la ligne si elle est invalide.
def test_reference_station_optionnelle_normalise_rejette_et_conserve_absence():
    trajets = pd.DataFrame(
        {"station_arrivee": [" s001 ", None, " ", "invalide"]},
        index=[21, 22, 23, 24],
    )

    valides, logs = nettoyage_ref_station_id_optionnel(
        trajets, "station_arrivee"
    )

    assert valides.index.tolist() == [21, 22, 23]
    assert valides.at[21, "station_arrivee"] == "S001"
    assert pd.isna(valides.at[22, "station_arrivee"])
    assert logs[0]["décision"] == "normalisé"
    assert logs[-1]["décision"] == "rejeté"
    verifier_erreurs_de_rejet(logs)


# RG6 | La référence du vélo est obligatoire dans un trajet.
# Les espaces et la casse sont corrigés ; une référence manquante ou mal formée est rejetée.
def test_reference_velo_obligatoire_normalise_et_rejette_valeurs_invalides():
    trajets = pd.DataFrame(
        {"velo_id": [" v0001 ", "V0002", None, "vélo"]},
        index=[25, 26, 27, 28],
    )

    valides, logs = nettoyage_ref_velo_id_obligatoire(trajets)

    assert valides.index.tolist() == [25, 26]
    assert valides.at[25, "velo_id"] == "V0001"
    assert [log["décision"] for log in logs] == [
        "normalisé",
        "rejeté",
        "rejeté",
    ]
    verifier_erreurs_de_rejet(logs)


# RG6 | La référence du vélo est facultative dans un incident.
# None et une chaîne vide restent acceptés et deviennent null ; une valeur présente invalide est rejetée.
def test_reference_velo_optionnelle_conserve_vide_normalise_et_rejette():
    incidents = pd.DataFrame(
        {"velo_id": [" v0001 ", None, " ", "V12"]},
        index=[29, 30, 31, 32],
    )

    valides, logs = nettoyage_ref_velo_id_optionnel(incidents)

    assert valides.index.tolist() == [29, 30, 31]
    assert valides.at[29, "velo_id"] == "V0001"
    assert pd.isna(valides.at[30, "velo_id"])
    assert pd.isna(valides.at[31, "velo_id"])
    assert [log["décision"] for log in logs] == ["normalisé", "rejeté"]
    verifier_erreurs_de_rejet(logs)


# RG4 | On vérifie plusieurs causes de rejet : absence, texte non numérique,
# valeur négative, décimale et dépassement de la capacité de stockage.
def test_RG4_rejette_durees_manquantes_decimales_et_hors_limites():
    trajets = pd.DataFrame(
        {"duree_secondes": [None, "invalide", -1, 1.5, 2_147_483_648, "30"]},
        index=[33, 34, 35, 36, 37, 38],
    )

    valides, logs = nettoyage_trajets_invalides(trajets)

    assert valides.index.tolist() == [38]
    assert valides.at[38, "duree_secondes"] == 30
    assert len(logs) == 5
    verifier_erreurs_de_rejet(logs)


# RG5 | Un abonné doit avoir une référence ; un occasionnel ne doit pas en avoir.
# Un type d'usager non reconnu est rejeté même si une référence est présente.
def test_RG5_conserve_coherents_et_rejette_type_usager_inconnu():
    trajets = pd.DataFrame(
        {
            "type_usager": ["abonne", "occasionnel", "inconnu"],
            "usager_ref": ["U12345678", " ", "U87654321"],
        },
        index=[39, 40, 41],
    )

    valides, logs = nettoyage_usager_ref_trajet(trajets)

    assert valides.index.tolist() == [39, 40]
    assert pd.isna(valides.at[40, "usager_ref"])
    assert logs[0]["motif"] == "type_usager manquant ou invalide"
    verifier_erreurs_de_rejet(logs)


# RG6 | La cible décide quelle référence doit être présente.
# On teste aussi la cible inconnue, les références manquantes ou doubles,
# et une station qui n'existe pas dans le référentiel.
def test_RG6_cible_incident_couvre_references_valides_et_rejets():
    incidents = pd.DataFrame(
        {
            "cible": [
                " VELO ",
                "station",
                "autre",
                "velo",
                "station",
                "velo",
                "station",
            ],
            "velo_id": ["V0001", None, None, None, None, "V0002", None],
            "station_id": [None, "S001", None, None, None, "S001", "S999"],
        },
        index=[42, 43, 44, 45, 46, 47, 48],
    )

    valides, logs = nettoyage_cible_incident(incidents, {"S001"})

    assert valides.index.tolist() == [42, 43]
    assert valides.at[42, "cible"] == "velo"
    assert [log["décision"] for log in logs] == [
        "normalisé",
        "rejeté",
        "rejeté",
        "rejeté",
        "rejeté",
        "rejeté",
    ]
    motifs = [log["motif"] for log in logs if log["décision"] == "rejeté"]
    assert "cible d'incident manquante ou invalide" in motifs
    assert "incident visant un vélo sans velo_id" in motifs
    assert "incident visant une station sans station_id" in motifs
    assert "incident renseignant à la fois velo_id et station_id" in motifs
    assert "station d'incident inconnue (S999)" in motifs
    verifier_erreurs_de_rejet(logs)


# RG6 | Cette combinaison est normalement impossible : le rejet ne correspond
# à aucune règle connue. Le test vérifie qu'on lève une erreur au lieu de
# l'enregistrer comme un rejet métier normal.
def test_RG6_etat_de_rejet_inattendu_declenche_une_erreur():
    with pytest.raises(RuntimeError, match="État incohérent.*ligne 49"):
        _motif_rejet_cible_incident(
            index=49,
            cible_velo=True,
            cible_station=False,
            velo_present=True,
            station_present=False,
            station_existante=True,
            station_id=None,
        )


# RG7 | Les statuts autorisés sont normalisés ; un statut absent est rejeté.
def test_RG7_normalise_statuts_et_rejette_statut_manquant():
    incidents = pd.DataFrame(
        {"statut": [" EN COURS ", "OUVERT", None]},
        index=[49, 50, 51],
    )

    valides, logs = nettoyage_pb_de_casse(incidents)

    assert valides["statut"].tolist() == ["en_cours", "ouvert"]
    assert logs[0]["décision"] == "normalisé"
    assert logs[1]["décision"] == "normalisé"
    assert logs[2]["motif"] == "statut manquant"
    verifier_erreurs_de_rejet(logs)


# RG8 | La date de signalement est obligatoire : une date lisible est convertie,
# une date absente ou illisible entraîne le rejet de la ligne.
def test_horodatage_obligatoire_convertit_et_rejette_manquant_ou_invalide():
    incidents = pd.DataFrame(
        {"date_signalement": ["2026-08-24 10:30", None, "pas-une-date"]},
        index=[52, 53, 54],
    )

    valides, logs = nettoyage_horodatage_obligatoire(
        incidents, "date_signalement"
    )

    assert valides.index.tolist() == [52]
    assert valides.at[52, "date_signalement"] == pd.Timestamp("2026-08-24 10:30")
    assert "manquant" in logs[0]["motif"]
    assert "invalide" in logs[1]["motif"]
    verifier_erreurs_de_rejet(logs)


# RG8 | La date de résolution est facultative à cette étape.
# Une date illisible est remplacée par null et signalée comme normalisée,
# sans supprimer l'incident.
def test_horodatage_optionnel_convertit_invalide_en_null_sans_rejet():
    incidents = pd.DataFrame(
        {"date_resolution": ["2026-08-24 10:30", None, "illisible"]},
        index=[55, 56, 57],
    )

    valides, logs = nettoyage_horodatage_optionnel(
        incidents, "date_resolution"
    )

    assert pd.isna(valides.at[57, "date_resolution"])
    assert valides.index.tolist() == [55, 56, 57]
    assert len(logs) == 1
    assert logs[0]["décision"] == "normalisé"


# RG8 | Une résolution ne peut pas précéder le signalement.
# Une date égale est valide ; une date absente ne permet pas de comparer et reste conservée.
def test_dates_resolution_rejette_resolution_anterieure_au_signalement():
    incidents = pd.DataFrame(
        {
            "date_signalement": pd.to_datetime(
                ["2026-08-24 10:00", "2026-08-24 10:00", "2026-08-24 10:00"]
            ),
            "date_resolution": pd.to_datetime(
                ["2026-08-24 09:59", "2026-08-24 10:00", None]
            ),
        },
        index=[58, 59, 60],
    )

    valides, logs = nettoyage_dates_resolution_incoherentes(incidents)

    assert valides.index.tolist() == [59, 60]
    assert len(logs) == 1
    assert logs[0]["décision"] == "rejeté"
    verifier_erreurs_de_rejet(logs)


# RG8 | Un incident non résolu n'a pas de date de résolution ;
# un incident résolu en a une. Ces trois lignes respectent la règle.
def test_coherence_date_resolution_conserve_statuts_et_dates_coherents():
    incidents = pd.DataFrame(
        {
            "statut": ["ouvert", "en_cours", "resolu"],
            "date_resolution": [None, None, pd.Timestamp("2026-08-24")],
        },
        index=[61, 62, 63],
    )

    valides, logs = nettoyage_coherence_date_resolution(incidents)

    assert valides.index.tolist() == [61, 62, 63]
    assert logs == []


# RG8 | L'absence du technicien est un avertissement non bloquant
# lorsque l'incident est pris en charge, pas lorsqu'il est encore ouvert.
def test_avertissement_technicien_ne_concerne_pas_incident_ouvert():
    incidents = pd.DataFrame(
        {
            "statut": ["ouvert", "resolu"],
            "technicien": [" ", None],
        },
        index=[64, 65],
    )

    valides, logs = signaler_technicien_manquant(incidents)

    assert valides.index.tolist() == [64, 65]
    assert len(logs) == 1
    assert logs[0]["numero-ligne"] == 65
    assert logs[0]["décision"] == "avertissement"
