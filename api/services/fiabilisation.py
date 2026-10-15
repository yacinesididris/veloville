"""Règles de fiabilisation des données, sans accès à la base de données."""

import logging

import pandas as pd


logger = logging.getLogger(__name__)

PATTERN_STATION = r"^S\d{3}$"
PATTERN_VELO = r"^V\d{4}$"


class LigneRejeteeError(ValueError):
    """Erreur métier levée pour une ligne rejetée."""

    def __init__(self, log: dict):
        self.log = log
        super().__init__(
            f"Ligne {log['numero-ligne']} rejetée : {log['motif']}"
        )


def lever_erreur_rejet(log: dict) -> None:
    """Lève l'erreur correspondant à un rejet, notamment pour les tests."""
    raise LigneRejeteeError(log)


def _finaliser_nettoyage(dataframe: pd.DataFrame, logs: list[dict]):
    for log in logs:
        if log["décision"] != "rejeté":
            continue
        try:
            lever_erreur_rejet(log)
        except LigneRejeteeError as erreur:
            logger.error("%s", erreur)
    return dataframe, logs


#=== Règles universelles : éviter les doublons

def nettoyage_doublons(dataframe: pd.DataFrame, nom_colonne_pk: str):
    df = dataframe.copy()
    doublons = df.duplicated(subset=[nom_colonne_pk], keep="first")
    logs = [
        {
            "numero-ligne": index,
            "motif": f"doublon sur la clé {nom_colonne_pk}",
            "décision": "rejeté",
        }
        for index in df.index[doublons]
    ]
    return _finaliser_nettoyage(df.loc[~doublons], logs)


#=== RG1 : capacité positive entière et station_id obligatoire

def nettoyage_capacite_station(dataframe: pd.DataFrame):
    df = dataframe.copy()
    capacites_txt = df["capacite"].astype("string").str.strip()
    format_entier = capacites_txt.str.fullmatch(r"\d+").fillna(False)
    capacites = pd.Series(
        [
            int(valeur) if est_entier else None
            for valeur, est_entier in zip(
                capacites_txt.tolist(),
                format_entier.tolist(),
            )
        ],
        index=df.index,
        dtype=object,
    )
    capacite_valide = capacites.map(
        lambda valeur: valeur is not None and valeur > 0
    )

    logs = [
        {
            "numero-ligne": index,
            "motif": (
                "capacité manquante"
                if pd.isna(df.at[index, "capacite"])
                else "capacité invalide (doit être un entier strictement positif)"
            ),
            "décision": "rejeté",
        }
        for index in df.index[~capacite_valide]
    ]

    df = df.loc[capacite_valide].copy()
    df["capacite"] = capacites.loc[capacite_valide]
    return _finaliser_nettoyage(df, logs)


def nettoyage_ref_station_id_obligatoire(
    dataframe: pd.DataFrame,
    nom_colonne: str,
):
    """Valide l'identifiant de station; utilisé par RG1 et RG2."""
    df = dataframe.copy()
    brute = df[nom_colonne].astype("string")
    normalisee = brute.str.strip().str.upper()
    valide_avant = brute.str.fullmatch(PATTERN_STATION).fillna(False).astype(bool)
    valide_apres = normalisee.str.fullmatch(PATTERN_STATION).fillna(False).astype(bool)
    masque_corrige = ~valide_avant & valide_apres
    masque_rejete = ~valide_apres

    logs = [
        {
            "numero-ligne": index,
            "motif": "station_id mal formaté (casse/espaces)",
            "décision": "normalisé",
        }
        for index in df.index[masque_corrige]
    ]
    logs.extend(
        {
            "numero-ligne": index,
            "motif": (
                "station_id manquant"
                if pd.isna(brute.at[index])
                else "station_id invalide"
            ),
            "décision": "rejeté",
        }
        for index in df.index[masque_rejete]
    )

    df.loc[masque_corrige, nom_colonne] = normalisee[masque_corrige]
    return _finaliser_nettoyage(df.loc[~masque_rejete], logs)


def nettoyage_station_depart_inconnue(
    dataframe: pd.DataFrame,
    station_ids: set[str],
):
    """Rejette les trajets dont la station de départ n'existe pas (RG2)."""
    df = dataframe.copy()
    inconnue = ~df["station_depart"].isin(station_ids)
    logs = [
        {
            "numero-ligne": index,
            "motif": f"station_depart inconnue ({df.at[index, 'station_depart']})",
            "décision": "rejeté",
        }
        for index in df.index[inconnue]
    ]
    return _finaliser_nettoyage(df.loc[~inconnue], logs)


#=== RG2 / RG3 / RG6 : reference station facultative

def nettoyage_ref_station_id_optionnel(
    dataframe: pd.DataFrame,
    nom_colonne: str,
):
    df = dataframe.copy()
    brute = df[nom_colonne].astype("string")
    normalisee = brute.str.strip().str.upper()
    valide_avant = brute.str.fullmatch(PATTERN_STATION).fillna(False).astype(bool)
    valide_apres = normalisee.str.fullmatch(PATTERN_STATION).fillna(False).astype(bool)
    masque_optionnel = brute.isna() | brute.str.strip().eq("")
    masque_corrige = ~valide_avant & valide_apres
    masque_rejete = ~valide_apres & ~masque_optionnel

    logs = [
        {
            "numero-ligne": index,
            "motif": "station_id mal formaté (casse/espaces)",
            "décision": "normalisé",
        }
        for index in df.index[masque_corrige]
    ]
    logs.extend(
        {
            "numero-ligne": index,
            "motif": "station_id invalide",
            "décision": "rejeté",
        }
        for index in df.index[masque_rejete]
    )

    df.loc[masque_corrige, nom_colonne] = normalisee[masque_corrige]
    return _finaliser_nettoyage(df.loc[~masque_rejete], logs)


#=== RG3 : une arrivée vers une station inconnue reste un trajet sans arrivée connue
def nettoyage_station_arrivee_inconnue(
    dataframe: pd.DataFrame,
    station_ids: set[str],
):
    df = dataframe.copy()
    arrivee_inconnue = (
        df["station_arrivee"].notna()
        & ~df["station_arrivee"].isin(station_ids)
    )
    logs = [
        {
            "numero-ligne": index,
            "motif": (
                "station_arrivee inconnue "
                f"({df.at[index, 'station_arrivee']})"
            ),
            "décision": "référence mise à nul",
        }
        for index in df.index[arrivee_inconnue]
    ]
    df.loc[arrivee_inconnue, "station_arrivee"] = None
    return _finaliser_nettoyage(df, logs)


#=== RG4 : validation des trajets

def nettoyage_ref_velo_id_obligatoire(dataframe: pd.DataFrame):
    df = dataframe.copy()
    brute = df["velo_id"].astype("string")
    normalisee = brute.str.strip().str.upper()
    valide_avant = brute.str.fullmatch(PATTERN_VELO).fillna(False).astype(bool)
    valide_apres = normalisee.str.fullmatch(PATTERN_VELO).fillna(False).astype(bool)
    masque_corrige = ~valide_avant & valide_apres
    masque_rejete = ~valide_apres

    logs = [
        {
            "numero-ligne": index,
            "motif": "velo_id mal formaté (casse/espaces)",
            "décision": "normalisé",
        }
        for index in df.index[masque_corrige]
    ]
    logs.extend(
        {
            "numero-ligne": index,
            "motif": (
                "velo_id manquant"
                if pd.isna(brute.at[index])
                else "velo_id invalide"
            ),
            "décision": "rejeté",
        }
        for index in df.index[masque_rejete]
    )

    df.loc[masque_corrige, "velo_id"] = normalisee[masque_corrige]
    return _finaliser_nettoyage(df.loc[~masque_rejete], logs)


def nettoyage_trajets_invalides(dataframe: pd.DataFrame):
    df = dataframe.copy()
    durees = pd.to_numeric(df["duree_secondes"], errors="coerce")
    duree_invalide = (
        durees.isna()
        | durees.le(0)
        | durees.gt(2_147_483_647)
        | durees.mod(1).ne(0)
    )
    logs = [
        {
            "numero-ligne": index,
            "motif": (
                "durée invalide (doit être un entier positif compatible avec INT)"
            ),
            "décision": "rejeté",
        }
        for index in df.index[duree_invalide]
    ]
    df["duree_secondes"] = durees
    df = df.loc[~duree_invalide].copy()
    df["duree_secondes"] = df["duree_secondes"].astype("int64")
    return _finaliser_nettoyage(df, logs)


#=== RG5 : cohérence entre le type d'usager et son pseudonyme
def nettoyage_usager_ref_trajet(dataframe: pd.DataFrame):
    df = dataframe.copy()
    type_usager = df["type_usager"].astype("string")
    usager_ref = df["usager_ref"].astype("string")
    ref_absente = usager_ref.isna() | usager_ref.str.strip().eq("").fillna(False)
    abonne = type_usager.eq("abonne").fillna(False)
    occasionnel = type_usager.eq("occasionnel").fillna(False)
    type_valide = abonne | occasionnel
    ligne_valide = type_valide & ((abonne & ~ref_absente) | (occasionnel & ref_absente))
    lignes_rejetees = ~ligne_valide

    logs = []
    for index in df.index[lignes_rejetees]:
        if not type_valide.at[index]:
            motif = "type_usager manquant ou invalide"
        elif abonne.at[index]:
            motif = "usager_ref manquant pour un abonné"
        else:
            motif = "usager_ref renseigné pour un usager occasionnel"

        logs.append({
            "numero-ligne": index,
            "motif": motif,
            "décision": "rejeté",
        })

    df.loc[occasionnel & ref_absente, "usager_ref"] = None
    return _finaliser_nettoyage(df.loc[~lignes_rejetees], logs)


#=== RG6 : cible d'incident et référence correspondante

def _motif_rejet_cible_incident(
    index: int,
    cible_velo: bool,
    cible_station: bool,
    velo_present: bool,
    station_present: bool,
    station_existante: bool,
    station_id: object,
) -> str:
    if not (cible_velo or cible_station):
        return "cible d'incident manquante ou invalide"
    if cible_velo and not velo_present:
        return "incident visant un vélo sans velo_id"
    if cible_station and not station_present:
        return "incident visant une station sans station_id"
    if velo_present and station_present:
        return "incident renseignant à la fois velo_id et station_id"
    if cible_station and not station_existante:
        return f"station d'incident inconnue ({station_id})"
    raise RuntimeError(
        f"État incohérent lors du rejet de la ligne {index} d'incident"
    )


def nettoyage_cible_incident(
    dataframe: pd.DataFrame,
    station_ids: set[str],
):
    df = dataframe.copy()
    cible_brute = df["cible"].astype("string")
    cible = cible_brute.str.strip().str.lower()
    cible_corrigee = cible_brute.notna() & cible_brute.ne(cible).fillna(False)
    df["cible"] = cible

    velo_brut = df["velo_id"].astype("string")
    station_brute = df["station_id"].astype("string")
    velo_present = velo_brut.notna() & velo_brut.str.strip().ne("").fillna(False)
    station_present = (
        station_brute.notna() & station_brute.str.strip().ne("").fillna(False)
    )
    cible_velo = cible.eq("velo").fillna(False)
    cible_station = cible.eq("station").fillna(False)

    references_coherentes = (
        (cible_velo & velo_present & ~station_present)
        | (cible_station & station_present & ~velo_present)
    )
    station_existante = ~cible_station | df["station_id"].isin(station_ids)
    valide = references_coherentes & station_existante
    rejete = ~valide

    logs = [
        {
            "numero-ligne": index,
            "motif": "cible d'incident normalisée (casse/espaces)",
            "décision": "normalisé",
        }
        for index in df.index[cible_corrigee]
    ]
    for index in df.index[rejete]:
        motif = _motif_rejet_cible_incident(
            index=index,
            cible_velo=cible_velo.at[index],
            cible_station=cible_station.at[index],
            velo_present=velo_present.at[index],
            station_present=station_present.at[index],
            station_existante=station_existante.at[index],
            station_id=df.at[index, "station_id"],
        )

        logs.append({
            "numero-ligne": index,
            "motif": motif,
            "décision": "rejeté",
        })

    df.loc[~velo_present, "velo_id"] = None
    df.loc[~station_present, "station_id"] = None
    return _finaliser_nettoyage(df.loc[~rejete], logs)


#=== RG6 : format des références facultatives aux vélos dans les incidents

def nettoyage_ref_velo_id_optionnel(dataframe: pd.DataFrame):
    df = dataframe.copy()
    brute = df["velo_id"].astype("string")
    normalisee = brute.str.strip().str.upper()
    valide_avant = brute.str.fullmatch(PATTERN_VELO).fillna(False).astype(bool)
    valide_apres = normalisee.str.fullmatch(PATTERN_VELO).fillna(False).astype(bool)
    masque_optionnel = brute.isna() | brute.str.strip().eq("")
    masque_corrige = ~valide_avant & valide_apres
    masque_rejete = ~valide_apres & ~masque_optionnel

    logs = [
        {
            "numero-ligne": index,
            "motif": "velo_id mal formaté (casse/espaces)",
            "décision": "normalisé",
        }
        for index in df.index[masque_corrige]
    ]
    logs.extend(
        {
            "numero-ligne": index,
            "motif": "velo_id invalide",
            "décision": "rejeté",
        }
        for index in df.index[masque_rejete]
    )

    df.loc[masque_corrige, "velo_id"] = normalisee[masque_corrige]
    df.loc[masque_optionnel, "velo_id"] = None
    return _finaliser_nettoyage(df.loc[~masque_rejete], logs)


#=== RG7 : statuts d'incident autorisés et normalisés

def nettoyage_pb_de_casse(dataframe: pd.DataFrame):
    df = dataframe.copy()
    brute = df["statut"].astype("string")
    normalisee = brute.str.strip().str.lower()
    normalisee = normalisee.replace({"en cours": "en_cours"})
    valide_avant = brute.isin(["ouvert", "en_cours", "resolu"])
    valide_apres = normalisee.isin(["ouvert", "en_cours", "resolu"])
    masque_corrige = ~valide_avant & valide_apres
    masque_rejete = ~valide_apres

    logs = [
        {
            "numero-ligne": index,
            "motif": "statut mal formaté (casse/espaces)",
            "décision": "normalisé",
        }
        for index in df.index[masque_corrige]
    ]
    logs.extend(
        {
            "numero-ligne": index,
            "motif": (
                "statut manquant"
                if pd.isna(brute.at[index])
                else "statut invalide"
            ),
            "décision": "rejeté",
        }
        for index in df.index[masque_rejete]
    )

    df.loc[masque_corrige, "statut"] = normalisee[masque_corrige]
    return _finaliser_nettoyage(df.loc[~masque_rejete], logs)


#=== RG8 : dates de signalement, résolution et cohérence chronologique

def nettoyage_horodatage_obligatoire(
    dataframe: pd.DataFrame,
    nom_colonne: str,
):
    df = dataframe.copy()
    dates_converties = pd.to_datetime(df[nom_colonne], errors="coerce")
    date_invalide = dates_converties.isna()

    logs = [
        {
            "numero-ligne": index,
            "motif": (
                f"horodatage manquant dans la colonne {nom_colonne}"
                if pd.isna(valeur)
                else f"horodatage invalide dans la colonne {nom_colonne}"
            ),
            "décision": "rejeté",
        }
        for index, valeur in df.loc[date_invalide, nom_colonne].items()
    ]
    df[nom_colonne] = dates_converties
    return _finaliser_nettoyage(df.loc[~date_invalide], logs)


def nettoyage_horodatage_optionnel(
    dataframe: pd.DataFrame,
    nom_colonne: str,
):
    df = dataframe.copy()
    dates_converties = pd.to_datetime(df[nom_colonne], errors="coerce")
    date_invalide = dates_converties.isna() & df[nom_colonne].notna()
    logs = [
        {
            "numero-ligne": index,
            "motif": (
                f"horodatage invalide ou illisible dans la colonne "
                f"{nom_colonne} (converti en nul)"
            ),
            "décision": "normalisé",
        }
        for index in df.index[date_invalide]
    ]
    df[nom_colonne] = dates_converties
    return _finaliser_nettoyage(df, logs)


def nettoyage_dates_resolution_incoherentes(dataframe: pd.DataFrame):
    df = dataframe.copy()
    incoherente = (
        (df["date_resolution"] < df["date_signalement"])
        & df["date_resolution"].notna()
    )
    logs = [
        {
            "numero-ligne": index,
            "motif": "date de résolution incohérente",
            "décision": "rejeté",
        }
        for index in df.index[incoherente]
    ]
    df = df.loc[~incoherente]
    return _finaliser_nettoyage(df, logs)


def nettoyage_coherence_date_resolution(dataframe: pd.DataFrame):
    """La date de résolution est présente exactement quand le statut est résolu (RG8)."""
    df = dataframe.copy()
    resolu = df["statut"].eq("resolu")
    date_presente = df["date_resolution"].notna()
    incoherente = resolu.ne(date_presente)

    logs = [
        {
            "numero-ligne": index,
            "motif": (
                "date_resolution manquante pour un incident résolu"
                if resolu.at[index]
                else "date_resolution renseignée pour un incident non résolu"
            ),
            "décision": "rejeté",
        }
        for index in df.index[incoherente]
    ]
    return _finaliser_nettoyage(df.loc[~incoherente], logs)


def signaler_technicien_manquant(dataframe: pd.DataFrame):
    """Journalise l'absence de technicien après prise en charge sans rejeter la ligne (RG8)."""
    df = dataframe.copy()
    technicien = df["technicien"].astype("string")
    absent = technicien.isna() | technicien.str.strip().eq("").fillna(False)
    pris_en_charge = df["statut"].isin(["en_cours", "resolu"])
    avertissement = absent & pris_en_charge

    logs = [
        {
            "numero-ligne": index,
            "motif": "technicien manquant pour un incident pris en charge",
            "décision": "avertissement",
        }
        for index in df.index[avertissement]
    ]
    return _finaliser_nettoyage(df, logs)
