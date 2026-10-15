"""Écran de consultation des indicateurs."""

import streamlit as st

from front.api_client import (
    ErreurApi,
    get_activite_par_jour,
    get_incidents_par_statut,
    get_stations_actives,
)

st.title("Indicateurs")

token = st.session_state.get("token")
if not token:
    st.info("Connectez-vous depuis la page d'accueil pour consulter les indicateurs.")
    st.stop()

filtrer_periode = st.checkbox("Filtrer l'activité par période")
date_debut = None
date_fin = None
if filtrer_periode:
    date_debut = st.date_input("Date de début")
    date_fin = st.date_input("Date de fin")

try:
    with st.spinner("Chargement des indicateurs..."):
        activite = get_activite_par_jour(token, date_debut, date_fin)
        stations = get_stations_actives(token)
        incidents = get_incidents_par_statut(token)
except ErreurApi as erreur:
    st.error(str(erreur))
else:
    donnees_activite = activite["donnees"]
    donnees_stations = stations["donnees"]
    donnees_incidents = incidents["donnees"]
    total_trajets = sum(jour["nb_trajets"] for jour in donnees_activite)
    delai_moyen = incidents["delai_moyen_resolution_heures"]

    colonnes = st.columns(3)
    colonnes[0].metric("Trajets sur la période", total_trajets)
    colonnes[1].metric("Stations actives retournées", len(donnees_stations))
    colonnes[2].metric(
        "Délai moyen de résolution (heures)",
        delai_moyen if delai_moyen is not None else "N/A",
    )

    st.subheader("Activité par jour")
    if donnees_activite:
        st.dataframe(donnees_activite, use_container_width=True)
    else:
        st.info("Aucune activité trouvée pour cette période.")

    st.subheader("Stations les plus actives")
    if donnees_stations:
        st.dataframe(donnees_stations, use_container_width=True)
    else:
        st.info("Aucune station trouvée.")

    st.subheader("Incidents par statut")
    if donnees_incidents:
        st.dataframe(donnees_incidents, use_container_width=True)
    else:
        st.info("Aucun incident trouvé.")
