"""Import et fiabilisation des trois exports CSV dans PostgreSQL.

À compléter : lire data/stations.csv, data/trajets.csv et data/incidents.csv,
appliquer les règles de fiabilisation (api/services/fiabilisation.py),
charger les lignes valides, journaliser les rejets et les avertissements.
Le script doit être idempotent : deux exécutions successives laissent la
base dans le même état.

Usage prévu : python scripts/importer.py [--dossier data]
"""

import pandas as pd 
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import MetaData, Table, select
from api.database import engine
from datetime import datetime
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


def preparation_trajets(df: pd.DataFrame, station_ids: set[str]):
    logs_import_trajets = []
    
    df, logs = nettoyage_ref_velo_id_obligatoire(df)
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_horodatage_obligatoire(df, "depart_horodatage")
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_ref_station_id_obligatoire(df, "station_depart")
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_ref_station_id_optionnel(df, "station_arrivee")
    logs_import_trajets.extend(logs)

    arrivee_inconnue = df["station_arrivee"].notna() & ~df["station_arrivee"].isin(station_ids)
    for index in df.index[arrivee_inconnue]:
        logs_import_trajets.append({
            "numero-ligne": index,
            "motif": f"station_arrivee inconnue ({df.at[index, 'station_arrivee']})",
            "décision": "référence mise à nul",
        })
    df.loc[arrivee_inconnue, "station_arrivee"] = None

    df, logs = nettoyage_trajets_invalides(df)
    logs_import_trajets.extend(logs)

    df, logs = nettoyage_doublons(df, "trajet_id")
    logs_import_trajets.extend(logs)

    return df, logs_import_trajets

# permet d'UPDATE et INSERT en controlant les doublons dans la table (update choisit si on ignore ou on update)
def upsert(df, nom_table, nom_colonne_pk, update=False):
    
    if df.empty:
        return 0, 0
    
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

    stmt = stmt.returning(table.c[nom_colonne_pk])

    with engine.begin() as conn:
        existing_ids = set()
        if update:
            existing_ids = set(
                conn.execute(
                    select(table.c[nom_colonne_pk]).where(
                        table.c[nom_colonne_pk].in_(df[nom_colonne_pk].tolist())
                    )
                ).scalars()
            )
        result = conn.execute(stmt)
        affected_ids = result.scalars().all()

    if not update:
        return len(affected_ids), 0

    updated = sum(id_ in existing_ids for id_ in affected_ids)
    return len(affected_ids) - updated, updated


def generer_rapport_import(logs_stations, 
                           logs_trajets, 
                           logs_incidents,
                           nb_stations,
                           nb_trajets,
                           nb_incidents_inseres,
                           nb_incidents_mis_a_jour):
    date_rapport = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

    with open(f"./docs/rapports/rapport_importation_{date_rapport}.txt", "w", encoding="utf-8") as f:

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
        f.write(f"Incidents insérés : {nb_incidents_inseres}\n")
        f.write(f"Incidents mis à jour : {nb_incidents_mis_a_jour}\n\n")
            
            

def importer_csv():
    df_stations, logs_stations = preparation_stations(lire_csv(stations_path))
    station_ids = set(df_stations["station_id"])
    df_trajets, logs_trajets = preparation_trajets(
        lire_csv(trajets_path),
        station_ids,
    )
    df_incidents, logs_incidents = preparation_incidents(lire_csv(incidents_path))


    nb_stations, _ = upsert(df_stations,"station","station_id",update=False)
    nb_trajets, _ = upsert(df_trajets,"trajet","trajet_id",update=False)
    nb_incidents_inseres, nb_incidents_mis_a_jour = upsert(
        df_incidents,
        "incident",
        "incident_id",
        update=True,
    )

    generer_rapport_import(
        logs_stations,
        logs_trajets,
        logs_incidents,
        nb_stations,
        nb_trajets,
        nb_incidents_inseres,
        nb_incidents_mis_a_jour,
    )

    print("Import terminé. Rapport généré dans docs/rapport_importation_csv.txt")




def main():
    importer_csv()


if __name__ == "__main__":
    main()