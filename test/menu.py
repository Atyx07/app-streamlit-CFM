import streamlit as st

st.set_page_config(page_title="Menu principal")
st.title("Menu principal")

st.write("Sélectionnez une app à lancer :")

# Boutons pour rediriger vers vos apps existantes
if st.button("Ouvrir App 1"):
    js = "window.open('https://app-app-cfm-hnm3xzambasqhe8wmustbo.streamlit.app/')"  # Ouvre dans un nouvel onglet
    st.components.v1.html(f"<script>{js}</script>")

if st.button("Ouvrir App 2"):
    js = "window.open('https://app2-app-cfm-jujxzt5sesafcn38bzubtr.streamlit.app/')"
    st.components.v1.html(f"<script>{js}</script>")
