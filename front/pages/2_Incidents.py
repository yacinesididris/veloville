"""Écran de consultation et de mise à jour des incidents."""

import streamlit as st

from front.api_client import ErreurApi, get_incidents, put_incident_statut

st.title("Incidents")

token = st.session_state.get("token")
if not token:
    st.info("Connectez-vous depuis la page d'accueil pour consulter les incidents.")
    st.stop()

statut_choisi = st.selectbox(
    "Filtrer par statut",
    ["Tous", "ouvert", "en_cours", "resolu"],
)
statut = None if statut_choisi == "Tous" else statut_choisi
taille_page = st.selectbox("Incidents par page", [10, 20, 50, 100], index=1)
page = st.number_input("Page", min_value=1, value=1, step=1)

try:
    with st.spinner("Chargement des incidents..."):
        reponse = get_incidents(
            token,
            statut=statut,
            page=page,
            taille_page=taille_page,
        )
except ErreurApi as erreur:
    st.error(str(erreur))
    st.stop()

st.caption(
    f"Page {reponse['page']} — {reponse['total']} incident(s) au total."
)
incidents = reponse["resultats"]
if incidents:
    st.dataframe(incidents, use_container_width=True)
else:
    st.info("Aucun incident trouvé.")

if st.session_state.get("role") == "exploitant" and incidents:
    st.subheader("Mettre à jour un incident")
    identifiants = [incident["incident_id"] for incident in incidents]
    with st.form("formulaire_statut_incident"):
        incident_id = st.selectbox("Incident", identifiants)
        nouveau_statut = st.selectbox(
            "Nouveau statut",
            ["en_cours", "resolu"],
        )
        mise_a_jour = st.form_submit_button("Mettre à jour")

    if mise_a_jour:
        try:
            with st.spinner("Mise à jour en cours..."):
                put_incident_statut(token, incident_id, nouveau_statut)
        except ErreurApi as erreur:
            st.error(str(erreur))
        else:
            st.success("Le statut de l'incident a été mis à jour.")
            st.rerun()
