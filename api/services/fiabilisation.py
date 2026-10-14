"""Règles de fiabilisation des données (module métier testé).

À compléter : fonctions pures, sans accès à la base, qui normalisent ou rejettent
une valeur ou une ligne : horodatages, identifiants de vélo, statuts
d'incident, durées, références de station, cohérence des dates,
doublons. Chaque fonction retourne la valeur normalisée ou signale le
motif de rejet. Ces fonctions sont appelées par scripts/importer.py et
couvertes par tests/unit/.
"""


import pandas as pd


PATTERN_STATION = r"^S\d{3}$"
PATTERN_VELO = r"^V\d{4}$" 


def nettoyage_doublons(dataframe: pd.DataFrame, nom_colonne_pk: str):
    df = dataframe.copy()  #.copy : pour travailler sur une copie interne à la fonction du Dataframe
    logs = []

    # subset : se concentre sur la colonne pour les doublons, demande une liste
    # keep='first' : la première occurrence est gardée, les suivantes sont marquées True
    doublon = df.duplicated(subset=[nom_colonne_pk], keep='first')

    if doublon.any():
        lignes_doublons = df[doublon]

        for index in lignes_doublons.index:
            logs.append({
                "numero-ligne": index,
                "motif": f"doublon sur la clé {nom_colonne_pk}",
                "décision": "rejeté"
            })

        df = df[~doublon]

    return df, logs


def nettoyage_trajets_invalides(dataframe: pd.DataFrame):
    df = dataframe.copy()
    logs = []

    # errors='coerce' : le texte illisible devient NaN, comme une durée manquante
    durees = pd.to_numeric(df['duree_secondes'], errors='coerce')

    # ~(durees > 0) couvre : durée <= 0, durée manquante (NaN) et durée illisible
    trajet_invalide = ~(durees > 0)

    if trajet_invalide.any():
        for index in df.index[trajet_invalide]:
            logs.append({"numero-ligne": index,
                            "motif" : "trajet invalide (durée nulle, négative, manquante ou illisible)",
                            "décision": "rejeté"})

    df['duree_secondes'] = durees
    df = df[~trajet_invalide]

    return df, logs


def nettoyage_dates_resolution_incoherentes(dataframe: pd.DataFrame):
    df = dataframe.copy()
    date_resolution_incoherente =  df[(df['date_resolution'] < df['date_signalement']) & (df['date_resolution'].notnull())]
    logs = []
    if not date_resolution_incoherente.empty:
        for index in date_resolution_incoherente.index:
            logs.append({"numero-ligne": index,
                            "motif" : "date de résolution incohérente",
                            "décision": "rejeté"})
        df = df[(df['date_resolution'] >= df['date_signalement']) | (df['date_resolution'].isnull())]

    return df, logs


def nettoyage_pb_de_casse(dataframe: pd.DataFrame):
    df = dataframe.copy()
    statuts_valides = ['ouvert', 'en cours', 'resolu']

    brute = df['statut'].astype("string")    #converti en string pour éviter les erreurs en cas de NotaNumber (NaN)
    apres_normalisation = brute.str.strip().str.lower()

    #On teste la version normalisée et la version brute pour distinguer si la normalisation corrige le problème
    valide_avant = brute.isin(statuts_valides)
    valide_apres = apres_normalisation.isin(statuts_valides)

    masque_corrige = ~valide_avant & valide_apres     # réparées par la normalisation
    masque_rejete = ~valide_apres                     # ne remonte pas même après normalisation

    logs = []
    for index in df.index[masque_corrige]:
        logs.append({
            "numero-ligne": index,
            "motif": "statut mal formaté (casse/espaces)",
            "décision": "normalisé"
        })

    for index in df.index[masque_rejete]:
        logs.append({
            "numero-ligne": index,
            "motif": "statut manquant" if pd.isna(brute.at[index]) else "statut invalide",
            "décision": "rejeté"
        })

    df.loc[masque_corrige, 'statut'] = apres_normalisation[masque_corrige]  # on ne modifie que les lignes ciblées
    df = df.loc[~masque_rejete]

    return df, logs


def nettoyage_ref_station_id_obligatoire (dataframe: pd.DataFrame, nom_colonne: str):
    df = dataframe.copy()

    brute = df[nom_colonne].astype("string")    #converti en string pour éviter les erreurs en cas de NotaNumber (NaN)
    apres_normalisation = brute.str.strip().str.upper()

    #On teste la version normalisée et la version brute pour distinguer si la normalisation corrige le problème
    valide_avant = brute.str.fullmatch(PATTERN_STATION).fillna(False).astype(bool)
    valide_apres = apres_normalisation.str.fullmatch(PATTERN_STATION).fillna(False).astype(bool)

    masque_corrige = ~valide_avant & valide_apres     # réparées par la normalisation
    masque_rejete = ~valide_apres                     # ne remonte pas même après normalisation

    logs = [{"numero-ligne": index,      # compréhension de liste [expression for variable in iterable]
             "motif": "station_id mal formaté (casse/espaces)", 
             "décision": "normalisé"}
        for index in df.index[masque_corrige]  #df.index[masque_corrige] : index des lignes où masque_corrige vaut True
    ]
    logs += [
        {
            "numero-ligne": index,
            "motif": "station_id manquant" if pd.isna(brute.at[index]) else "station_id invalide",
            "décision": "rejeté",
        }
        for index in df.index[masque_rejete]
    ]

    df.loc[masque_corrige, nom_colonne] = apres_normalisation[masque_corrige]
    df = df.loc[~masque_rejete]

    return df, logs


def nettoyage_ref_station_id_optionnel(dataframe: pd.DataFrame, nom_colonne: str):
    df = dataframe.copy()

    brute = df[nom_colonne].astype("string")    #converti en string pour éviter les erreurs en cas de NotaNumber (NaN)
    apres_normalisation = brute.str.strip().str.upper()

    #On teste la version normalisée et la version brute pour distinguer si la normalisation corrige le problème
    valide_avant = brute.str.fullmatch(PATTERN_STATION).fillna(False).astype(bool)
    valide_apres = apres_normalisation.str.fullmatch(PATTERN_STATION).fillna(False).astype(bool)

    masque_optionnel = brute.isna() | brute.str.strip().eq("")    #valeur absente ou vide : champ optionnel
    masque_corrige = ~valide_avant & valide_apres     # réparées par la normalisation
    masque_rejete = ~valide_apres & ~masque_optionnel # ne remonte pas même après normalisation

    logs = [{"numero-ligne": index,      # compréhension de liste [expression for variable in iterable]
             "motif": "station_id mal formaté (casse/espaces)", 
             "décision": "normalisé"}
        for index in df.index[masque_corrige]  #df.index[masque_corrige] : index des lignes où masque_corrige vaut True
    ]
    logs += [
        {
            "numero-ligne": index,
            "motif": "station_id invalide",
            "décision": "rejeté",
        }
        for index in df.index[masque_rejete]
    ]

    df.loc[masque_corrige, nom_colonne] = apres_normalisation[masque_corrige]
    df = df.loc[~masque_rejete]

    return df, logs

def nettoyage_ref_velo_id_obligatoire(dataframe: pd.DataFrame):
    df = dataframe.copy()

    brute = df["velo_id"].astype("string")    #converti en string pour éviter les erreurs en cas de NotaNumber (NaN)
    apres_normalisation = brute.str.strip().str.upper()

    #On teste la version normalisée et la version brute pour distinguer si la normalisation corrige le problème
    valide_avant = brute.str.fullmatch(PATTERN_VELO).fillna(False).astype(bool)
    valide_apres = apres_normalisation.str.fullmatch(PATTERN_VELO).fillna(False).astype(bool)

    masque_corrige = ~valide_avant & valide_apres     # réparées par la normalisation
    masque_rejete = ~valide_apres                     # ne remonte pas même après normalisation

    logs = [{"numero-ligne": index,      # compréhension de liste [expression for variable in iterable]
             "motif": "velo_id mal formaté (casse/espaces)", 
             "décision": "normalisé"}
        for index in df.index[masque_corrige]  #df.index[masque_corrige] : index des lignes où masque_corrige vaut True
    ]
    logs += [
        {
            "numero-ligne": index,
            "motif": "velo_id manquant" if pd.isna(brute.at[index]) else "velo_id invalide",
            "décision": "rejeté",
        }
        for index in df.index[masque_rejete]
    ]

    df.loc[masque_corrige, "velo_id"] = apres_normalisation[masque_corrige]
    df = df.loc[~masque_rejete]

    return df, logs


def nettoyage_ref_velo_id_optionnel(dataframe: pd.DataFrame):
    df = dataframe.copy()

    brute = df["velo_id"].astype("string")    #converti en string pour éviter les erreurs en cas de NotaNumber (NaN)
    apres_normalisation = brute.str.strip().str.upper()

    #On teste la version normalisée et la version brute pour distinguer si la normalisation corrige le problème
    valide_avant = brute.str.fullmatch(PATTERN_VELO).fillna(False).astype(bool)
    valide_apres = apres_normalisation.str.fullmatch(PATTERN_VELO).fillna(False).astype(bool)

    masque_optionnel = brute.isna() | brute.str.strip().eq("")    #valeur absente ou vide : champ optionnel
    masque_corrige = ~valide_avant & valide_apres     # réparées par la normalisation
    masque_rejete = ~valide_apres & ~masque_optionnel # ne remonte pas même après normalisation

    logs = [{"numero-ligne": index,      # compréhension de liste [expression for variable in iterable]
             "motif": "velo_id mal formaté (casse/espaces)", 
             "décision": "normalisé"}
        for index in df.index[masque_corrige]  #df.index[masque_corrige] : index des lignes où masque_corrige vaut True
    ]
    logs += [
        {
            "numero-ligne": index,
            "motif": "velo_id invalide",
            "décision": "rejeté",
        }
        for index in df.index[masque_rejete]
    ]

    df.loc[masque_corrige, "velo_id"] = apres_normalisation[masque_corrige]
    df = df.loc[~masque_rejete]

    return df, logs


def nettoyage_horodatage_obligatoire(dataframe: pd.DataFrame, nom_colonne: str):
    df = dataframe.copy()
    logs = []

    # errors='coerce' transforme les dates impossibles à lire en NaT (Not a Time)
    dates_converties = pd.to_datetime(df[nom_colonne], errors='coerce')

    # Champ obligatoire : une date NaT après conversion est invalide, qu'elle soit illisible OU manquante
    date_invalide = dates_converties.isna()

    if date_invalide.any():
        lignes_invalides = df[date_invalide]

        for index, valeur in lignes_invalides[nom_colonne].items():
            if pd.isna(valeur):
                motif = f"horodatage manquant dans la colonne {nom_colonne}"
            else:
                motif = f"horodatage invalide dans la colonne {nom_colonne}"

            logs.append({
                "numero-ligne": index,
                "motif": motif,
                "décision": "rejeté"
            })

        df[nom_colonne] = dates_converties
        df = df[~date_invalide]
    else:
        df[nom_colonne] = dates_converties

    return df, logs


def nettoyage_horodatage_optionnel(dataframe: pd.DataFrame, nom_colonne: str):
    df = dataframe.copy()
    logs = []
    dates_converties = pd.to_datetime(df[nom_colonne], errors='coerce')

    # Les cellules déjà vides ne sont pas des erreurs
    date_invalide = dates_converties.isna() & df[nom_colonne].notna()

    if date_invalide.any():
        lignes_invalides = df[date_invalide]

        for index in lignes_invalides.index:
            logs.append({
                "numero-ligne": index,
                "motif": f"horodatage invalide ou illisible dans la colonne {nom_colonne} (converti en nul)",
                "décision": "normalisé"
            })

    df[nom_colonne] = dates_converties
    return df, logs