"""Écran de consultation des stations."""

import streamlit as st

from front.api_client import ErreurApi, get_stations

st.title("Stations")

token = st.session_state.get("token")
if not token:
    st.info("Connectez-vous depuis la page d'accueil pour consulter les stations.")
    st.stop()

commune = st.text_input("Filtrer par commune")
taille_page = st.selectbox("Stations par page", [10, 20, 50, 100], index=1)
page = st.number_input("Page", min_value=1, value=1, step=1)

try:
    with st.spinner("Chargement des stations..."):
        reponse = get_stations(
            token,
            commune=commune or None,
            page=page,
            taille_page=taille_page,
        )
except ErreurApi as erreur:
    st.error(str(erreur))
else:
    st.caption(
        f"Page {reponse['page']} — {reponse['total']} station(s) au total."
    )
    if reponse["resultats"]:
        st.dataframe(reponse["resultats"], use_container_width=True)
    else:
        st.info("Aucune station trouvée.")
