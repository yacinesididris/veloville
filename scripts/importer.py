"""Import et fiabilisation des trois exports CSV dans PostgreSQL.

À compléter : lire data/stations.csv, data/trajets.csv et data/incidents.csv,
appliquer les règles de fiabilisation (api/services/fiabilisation.py),
charger les lignes valides, journaliser les rejets et les avertissements.
Le script doit être idempotent : deux exécutions successives laissent la
base dans le même état.

Usage prévu : python scripts/importer.py [--dossier data]
"""

import sys
import os
from sqlalchemy.dialects.postgresql import insert
from api.database import engine
from sqlalchemy import MetaData, Table

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd 
from api.services.fiabilisation import (
nettoyage_doublons, nettoyage_horodatage_obligatoire, nettoyage_trajets_invalides,
nettoyage_dates_resolution_incoherentes, nettoyage_pb_de_casse, nettoyage_ref_station_id_obligatoire,
nettoyage_ref_velo_id_optionnel, nettoyage_horodatage_optionnel, nettoyage_ref_station_id_optionnel,
nettoyage_ref_velo_id_obligatoire)

incidents_path = "data/incidents.csv"
stations_path = "data/stations.csv"
trajets_path = "data/trajets.csv"

#sert de registre SQL pour les tables qu'on va manipuler pendant l'insertion (donne les colonnes et types de données)
metadata = MetaData()


def lire_csv(file_path: str) -> pd.DataFrame:
    return pd.read_csv(file_path)




def preparation_incidents(df: pd.DataFrame):
    logs_import_incidents = []
    
    df, logs = nettoyage_horodatage_obligatoire(df, "date_signalement")
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_horodatage_optionnel(df, "date_resolution")
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_dates_resolution_incoherentes(df)
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_pb_de_casse(df)
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_ref_station_id_optionnel(df, "station_id" )
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_ref_velo_id_optionnel(df)
    logs_import_incidents.extend(logs)

    df, logs = nettoyage_doublons(df, "incident_id")
    logs_import_incidents.extend(logs)


    return df, logs_import_incidents



def preparation_stations(df: pd.DataFrame):
    logs_import_stations = []
    
    df, logs = nettoyage_ref_station_id_obligatoire(df, "station_id")
    logs_import_stations.extend(logs)

    df, logs = nettoyage_doublons(df, "station_id")
    logs_import_stations.extend(logs)

    return df, logs_import_stations


def preparation_trajets(df: pd.DataFrame):
    logs_import_trajets = []
    
    df, logs = nettoyage_ref_velo_id_obligatoire(df)
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_horodatage_obligatoire(df, "depart_horodatage")
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_ref_station_id_obligatoire(df, "station_depart")
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_ref_station_id_optionnel(df, "station_arrivee")
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_trajets_invalides(df)
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_doublons(df, "trajet_id")
    logs_import_trajets.extend(logs)

    return df, logs_import_trajets


def upsert(df, nom_table, nom_colonne_pk, update=False):
    
    if df.empty:
        return 0 #nombre de lignes modifiées
    
    #examine la table et l'inscrit dans le registre metadata pour récupérer les colonnes et types de données
    table = Table(nom_table,metadata,autoload_with=engine)
    
    #remplace les valeurs composées uniquement d'espace, tab ou retour ligne par None
    df = df.replace(r"^\s*$", None, regex=True) 

     #.to_dict(orient="records") convertit en liste de dictionnaires
    lignes = df.astype(object).where(pd.notna(df), None).to_dict(orient="records")
    # where(pd.notna(df), None) : garde si elle n'est pas NonApplicable, sinon remplace par None


    stmt = insert(table).values(lignes)

    #permet de choisir si on veut mettre à jour ou ignorer les doublons
    if update:

        colonnes_en_doublon = [
            c for c in df.columns
            if c != nom_colonne_pk
        ]

        stmt = stmt.on_conflict_do_update(
            #index_elements = fait partie de la methode on_conflict_do_update, permet de spécifier la colonne qui est la clé primaire
            index_elements=[nom_colonne_pk], 
            # génére un dict à partir d'une boucle.
            set_={
                c: stmt.excluded[c]      #{ clé: valeur for x in iterable } 
                for c in colonnes_en_doublon
            }
        )

    else:

        stmt = stmt.on_conflict_do_nothing(
            index_elements=[nom_colonne_pk]
        )

    with engine.begin() as conn:
        result = conn.execute(stmt)

    return result.rowcount


def generer_rapport_import(logs_stations, 
                           logs_trajets, 
                           logs_incidents,
                           nb_stations,
                           nb_trajets,
                           nb_incidents):

    with open("./data/rapport_importation_csv.txt", "w", encoding="utf-8") as f:

        f.write("=============== RAPPORT DE FIABILISATION ===============\n\n")
        f.write("=============== Stations\n")

        for log in logs_stations:
            f.write(
                f"Ligne {log.get('numero-ligne')} | "
                f"Décision : {log.get('décision')} | "
                f"Motif : {log.get('motif')}\n"
            )

        f.write("\n")

        f.write("=============== Trajets\n")

        for log in logs_trajets:
            f.write(
                f"Ligne {log.get('numero-ligne')} | "
                f"Décision : {log.get('décision')} | "
                f"Motif : {log.get('motif')}\n"
            )

        f.write("\n")

        f.write("=============== Incidents\n")

        for log in logs_incidents:
            f.write(
                f"Ligne {log.get('numero-ligne')} | "
                f"Décision : {log.get('décision')} | "
                f"Motif : {log.get('motif')}\n"
            )
            
        f.write("=============== RAPPORT D'IMPORT ===============\n\n")

        f.write(f"Stations insérées : {nb_stations}\n")
        f.write(f"Trajets insérés : {nb_trajets}\n")
        f.write(f"Incidents insérés ou mis à jour : {nb_incidents}\n\n")    
            
            

def importer_csv():
    df_incidents, logs_incidents = preparation_incidents(lire_csv(incidents_path))
    df_stations, logs_stations = preparation_stations(lire_csv(stations_path))
    df_trajets, logs_trajets = preparation_trajets(lire_csv(trajets_path))

    nb_stations = upsert(df_stations,"station","station_id",update=False)
    nb_trajets = upsert(df_trajets,"trajet","trajet_id",update=False)
    nb_incidents = upsert(df_incidents,"incident","incident_id",update=True)

    generer_rapport_import(
        logs_stations,
        logs_trajets,
        logs_incidents,
        nb_stations,
        nb_trajets,
        nb_incidents
    )

    print("Import terminé. Rapport généré dans data/rapport_importation_csv.txt")




def main():
    importer_csv()


if __name__ == "__main__":
    main()