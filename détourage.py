import streamlit as st
from rembg import remove, new_session  # <-- Importer new_session
from PIL import Image
import io

# --- Configuration de la page ---
st.set_page_config(
    page_title="Suppresseur d'arrière-plan",
    page_icon="✂️",
    layout="wide"
)

# --- Barre latérale pour les options ---
st.sidebar.title("🛠️ Options de Détourage")
model_name = st.sidebar.selectbox(
    "Choisissez le modèle d'IA :",
    [
        "u2net",                # Rapide, qualité moyenne (le défaut d'origine)
        "isnet-general-use",    # Très haute qualité, plus lent
        "u2net_human_seg",    # Spécialisé pour les humains (cheveux)
        "silueta",              # Un autre modèle généraliste
        "isnet-anime",          # Spécialisé pour les dessins/animes
    ],
    index=1  # Sélectionne "isnet-general-use" par défaut
)
st.sidebar.info(
    "**Note :** `isnet-general-use` offre souvent la meilleure qualité "
    "pour les photos. `u2net_human_seg` est excellent pour les portraits."
)


# --- Fonction pour charger le modèle (mise en cache) ---
# st.cache_resource garantit que nous ne chargeons le modèle qu'une seule fois
@st.cache_resource
def load_model_session(model):
    """Charge et met en cache la session du modèle rembg."""
    st.info(f"Chargement du modèle '{model}'... Veuillez patienter.")
    return new_session(model_name=model)

# Charge la session sélectionnée
session = load_model_session(model_name)


# --- Titre et description ---
st.title("✂️ Suppresseur d'arrière-plan (Qualité Améliorée)")
st.markdown(
    f"Utilisation actuelle du modèle **`{model_name}`**."
)


# --- Colonnes pour l'affichage ---
col1, col2 = st.columns(2)

# --- Colonne 1 : Téléchargement et Image Originale ---
with col1:
    st.header("1. Votre Image")
    uploaded_file = st.file_uploader("Choisissez une image...", type=["png", "jpg", "jpeg", "webp"])
    
    if uploaded_file is not None:
        input_bytes = uploaded_file.getvalue()
        input_image = Image.open(io.BytesIO(input_bytes))
        st.image(input_image, caption="Image Originale", use_column_width=True)

# --- Colonne 2 : Résultat et Téléchargement ---
with col2:
    st.header("2. Résultat")
    
    if uploaded_file is not None:
        with st.spinner(f"Détourage en cours avec '{model_name}'..."):
            try:
                # --- L'OPÉRATION MAGIQUE (MISE À JOUR) ---
                # On passe les bytes ET la session du modèle
                output_bytes = remove(input_bytes, session=session)
                
                output_image = Image.open(io.BytesIO(output_bytes))
                st.image(output_image, caption="Arrière-plan supprimé", use_column_width=True)
                
                file_name = f"{uploaded_file.name.split('.')[0]}_{model_name}_no_bg.png"
                
                st.download_button(
                    label="📥 Télécharger le résultat (PNG)",
                    data=output_bytes,
                    file_name=file_name,
                    mime="image/png"
                )
            except Exception as e:
                st.error(f"Une erreur est survenue : {e}")
                st.error(
                    "Cela peut arriver si le modèle n'a pas pu être chargé "
                    "ou si l'image est corrompue."
                )
                
    else:
        st.info("Veuillez télécharger une image pour voir le résultat.")
