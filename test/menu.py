import streamlit as st

st.set_page_config(page_title="CFM data Menu")
st.title("CFM data Menu")
st.write("Select an app to launch :")

# Crée deux colonnes pour organiser les apps
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("App 1 (Original)")
    st.write("This app processes unique Raspi files and returns the processed files")
    if st.button("Open App 1"):
        js = "window.open('https://cfmdataprocessingst-dupsgjztrwwvcedwrivyeb.streamlit.app/')"
        st.components.v1.html(f"<script>{js}</script>")
with col2:
    st.subheader("App 2")
    st.write("This app processes multiple Raspi files and returns a Zip with the processed files")
    if st.button("Open App 2"):
        js = "window.open('https://app-app-cfm-hnm3xzambasqhe8wmustbo.streamlit.app/')"
        st.components.v1.html(f"<script>{js}</script>")

with col3:
    st.subheader("App 3")
    st.write("This app processes multiple Raspi files and returns a Zip with the processed files and a recap Excel file containing mean and max CO2, mean Vdot and mean dp1")
    if st.button("Open App 3"):
        js = "window.open('https://app2-app-cfm-jujxzt5sesafcn38bzubtr.streamlit.app/')"
        st.components.v1.html(f"<script>{js}</script>")
