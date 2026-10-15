"""Import et fiabilisation des trois exports CSV dans PostgreSQL.

À compléter : lire data/stations.csv, data/trajets.csv et data/incidents.csv,
appliquer les règles de fiabilisation (api/services/fiabilisation.py),
charger les lignes valides, journaliser les rejets et les avertissements.
Le script doit être idempotent : deux exécutions successives laissent la
base dans le même état.

Usage prévu : python scripts/importer.py [--dossier data]
"""

import pandas as pd 
import sys
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import MetaData, Table
from datetime import datetime
from pathlib import Path
from argparse import ArgumentParser

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.database import engine
from api.services.fiabilisation import (
nettoyage_capacite_station,
nettoyage_doublons, nettoyage_horodatage_obligatoire, nettoyage_trajets_invalides,
nettoyage_dates_resolution_incoherentes, nettoyage_pb_de_casse, nettoyage_ref_station_id_obligatoire,
nettoyage_ref_velo_id_optionnel, nettoyage_horodatage_optionnel, nettoyage_ref_station_id_optionnel,
nettoyage_ref_velo_id_obligatoire, nettoyage_station_arrivee_inconnue,
nettoyage_usager_ref_trajet, nettoyage_station_depart_inconnue,
nettoyage_cible_incident, nettoyage_coherence_date_resolution,
signaler_technicien_manquant)

#sert de registre SQL pour les tables qu'on va manipuler pendant l'insertion (donne les colonnes et types de données)
metadata = MetaData()


def lire_csv(file_path: str, dtype: dict[str, str] | None = None) -> pd.DataFrame:
    return pd.read_csv(file_path, dtype=dtype)




def preparation_stations(df: pd.DataFrame):
    logs_import_stations = []
    
    df, logs = nettoyage_capacite_station(df)
    logs_import_stations.extend(logs)

    df, logs = nettoyage_ref_station_id_obligatoire(df, "station_id")
    logs_import_stations.extend(logs)

    df, logs = nettoyage_doublons(df, "station_id")
    logs_import_stations.extend(logs)

    return df, logs_import_stations


def preparation_trajets(df: pd.DataFrame, station_ids: set[str]):
    logs_import_trajets = []
    
    df, logs = nettoyage_ref_velo_id_obligatoire(df)
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_horodatage_obligatoire(df, "depart_horodatage")
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_ref_station_id_obligatoire(df, "station_depart")
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_station_depart_inconnue(df, station_ids)
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_ref_station_id_optionnel(df, "station_arrivee")
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_station_arrivee_inconnue(df, station_ids)
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_trajets_invalides(df)
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_usager_ref_trajet(df)
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_doublons(df, "trajet_id")
    logs_import_trajets.extend(logs)

    return df, logs_import_trajets


def preparation_incidents(df: pd.DataFrame, station_ids: set[str]):
    logs_import_incidents = []
    
    df, logs = nettoyage_horodatage_obligatoire(df, "date_signalement")
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_horodatage_optionnel(df, "date_resolution")
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_pb_de_casse(df)
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_dates_resolution_incoherentes(df)
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_coherence_date_resolution(df)
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_ref_station_id_optionnel(df, "station_id" )
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_ref_velo_id_optionnel(df)
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_cible_incident(df, station_ids)
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_doublons(df, "incident_id")
    logs_import_incidents.extend(logs)

    df, logs = signaler_technicien_manquant(df)
    logs_import_incidents.extend(logs)


    return df, logs_import_incidents


# Insère les lignes sans modifier celles dont la clé primaire existe déjà.
def inserer_sans_doublons(df, nom_table, nom_colonne_pk):
    if df.empty:
        return 0
    
    #examine la table et l'inscrit dans le registre metadata pour récupérer les colonnes et types de données
    table = Table(nom_table,metadata,autoload_with=engine)

    #remplace les valeurs composées uniquement d'espace, tab ou retour ligne par None
    df = df.replace(r"^\s*$", None, regex=True) 

                                                    #.to_dict(orient="records") convertit en liste de dictionnaires
    lignes = df.astype(object).where(pd.notna(df), None).to_dict(orient="records")
                            # where(pd.notna(df), None) : garde si elle n'est pas NonApplicable, sinon remplace par None


    stmt = insert(table).values(lignes)

    stmt = stmt.on_conflict_do_nothing(index_elements=[nom_colonne_pk])

    stmt = stmt.returning(table.c[nom_colonne_pk])

    with engine.begin() as conn:
        result = conn.execute(stmt)
        affected_ids = result.scalars().all()

    return len(affected_ids)


def generer_rapport_import(logs_stations, 
                           logs_trajets, 
                           logs_incidents,
                           nb_stations,
                           nb_trajets,
                           nb_incidents,
                           fichiers_absents,
                           dossier_rapports):
    date_rapport = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    dossier_rapports.mkdir(parents=True, exist_ok=True)
    chemin_rapport = dossier_rapports / f"rapport_importation_{date_rapport}.txt"

    with open(chemin_rapport, "w", encoding="utf-8") as f:

        f.write("=============== RAPPORT DE FIABILISATION ===============\n\n")
        f.write("=============== Stations\n\n")

        for log in logs_stations:
            f.write(
                f"Ligne {log.get('numero-ligne')} | "
                f"Décision : {log.get('décision')} | "
                f"Motif : {log.get('motif')}\n"
            )

        f.write("\n\n")

        f.write("=============== Trajets\n\n")

        for log in logs_trajets:
            f.write(
                f"Ligne {log.get('numero-ligne')} | "
                f"Décision : {log.get('décision')} | "
                f"Motif : {log.get('motif')}\n"
            )

        f.write("\n\n")

        f.write("=============== Incidents\n\n")

        for log in logs_incidents:
            f.write(
                f"Ligne {log.get('numero-ligne')} | "
                f"Décision : {log.get('décision')} | "
                f"Motif : {log.get('motif')}\n"
            )
        f.write("\n\n")

        f.write("=============== RAPPORT D'IMPORT ===============\n\n")

        f.write(f"Stations insérées : {nb_stations}\n")
        f.write(f"Trajets insérés : {nb_trajets}\n")
        f.write(f"Incidents insérés : {nb_incidents}\n\n")

        if fichiers_absents:
            f.write("=============== FICHIERS ABSENTS ===============\n\n")
            for fichier in fichiers_absents:
                f.write(f"Fichier absent : {fichier}\n")

    return chemin_rapport


def importer_csv(dossier_donnees: Path):
    fichiers_absents = []
    dossier_donnees = Path(dossier_donnees)
    stations_path = dossier_donnees / "stations.csv"
    trajets_path = dossier_donnees / "trajets.csv"
    incidents_path = dossier_donnees / "incidents.csv"

    if Path(stations_path).is_file():
        df_stations, logs_stations = preparation_stations(
            lire_csv(stations_path, dtype={"capacite": "string"})
        )
    else:
        df_stations, logs_stations = pd.DataFrame(), []
        fichiers_absents.append(stations_path)

    station_ids = set(df_stations["station_id"]) if "station_id" in df_stations else set()

    if Path(trajets_path).is_file():
        df_trajets, logs_trajets = preparation_trajets(
            lire_csv(trajets_path),
            station_ids,
        )
    else:
        df_trajets, logs_trajets = pd.DataFrame(), []
        fichiers_absents.append(trajets_path)

    if Path(incidents_path).is_file():
        df_incidents, logs_incidents = preparation_incidents(
            lire_csv(incidents_path),
            station_ids,
        )
    else:
        df_incidents, logs_incidents = pd.DataFrame(), []
        fichiers_absents.append(incidents_path)


    nb_stations = inserer_sans_doublons(df_stations, "station", "station_id")
    nb_trajets = inserer_sans_doublons(df_trajets, "trajet", "trajet_id")
    nb_incidents = inserer_sans_doublons(
        df_incidents, "incident", "incident_id"
    )

    chemin_rapport = generer_rapport_import(
        logs_stations,
        logs_trajets,
        logs_incidents,
        nb_stations,
        nb_trajets,
        nb_incidents,
        fichiers_absents,
        ROOT_DIR / "docs" / "rapports",
    )

    print(f"Import terminé. Rapport généré : {chemin_rapport}")



def main():
    parser = ArgumentParser(description="Importe et fiabilise les fichiers CSV VéloVille.")
    parser.add_argument(
        "--dossier",
        type=Path,
        default=ROOT_DIR / "data",
        help="Dossier contenant stations.csv, trajets.csv et incidents.csv (défaut : data).",
    )
    args = parser.parse_args()
    importer_csv(args.dossier)


if __name__ == "__main__":
    main()