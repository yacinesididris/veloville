"""Page d'accueil Streamlit : connexion."""

import streamlit as st

from api_client import ErreurApi, post_login

st.title("VéloVille")

if st.session_state.get("token"):
    st.success(f"Connecté avec le rôle {st.session_state.get('role')}.")
    st.info("Utilisez le menu de navigation pour ouvrir les pages Stations, Incidents ou Indicateurs.")

    if st.button("Se déconnecter"):
        st.session_state.pop("token", None)
        st.session_state.pop("role", None)
        st.rerun()
else:
    st.write("Connectez-vous pour accéder aux données VéloVille.")

    with st.form("formulaire_connexion"):
        username = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type="password")
        connexion = st.form_submit_button("Se connecter")

    if connexion:
        try:
            with st.spinner("Connexion en cours..."):
                reponse = post_login(username, password)
        except ErreurApi as erreur:
            st.error(str(erreur))
        else:
            st.session_state["token"] = reponse["access_token"]
            st.session_state["role"] = reponse["role"]
            st.rerun()
