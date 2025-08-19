import streamlit as st

st.set_page_config(page_title="Menu principal")
st.title("Menu principal")
st.write("Sélectionnez une app à lancer :")

# Crée deux colonnes pour organiser les apps
col1, col2 = st.columns(2)

with col1:
    st.subheader("App 1")
    st.write("Description détaillée de l'App 1 : cette app permet de faire X, Y et Z.")
    if st.button("Ouvrir App 1"):
        js = "window.open('https://app-app-cfm-hnm3xzambasqhe8wmustbo.streamlit.app/')"
        st.components.v1.html(f"<script>{js}</script>")

with col2:
    st.subheader("App 2")
    st.write("Description détaillée de l'App 2 : cette app permet de gérer A, B et C.")
    if st.button("Ouvrir App 2"):
        js = "window.open('https://app2-app-cfm-jujxzt5sesafcn38bzubtr.streamlit.app/')"
        st.components.v1.html(f"<script>{js}</script>")
