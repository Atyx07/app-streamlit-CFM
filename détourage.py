import streamlit as st
from rembg import remove  # Bibliothèque principale pour le détourage
from PIL import Image     # Pour manipuler les images
import io                 # Pour gérer les bytes (données binaires)

# --- Configuration de la page ---
st.set_page_config(
    page_title="Suppresseur d'arrière-plan",
    page_icon="✂️",
    layout="wide"
)

# --- Barre Latérale (Sidebar) pour les réglages ---
st.sidebar.header("⚙️ Réglages de précision")
st.sidebar.info(
    "Activez l'affinage pour un meilleur traitement des détails "
    "(comme les cheveux), mais le traitement sera plus lent."
)

# Case à cocher pour activer l'Alpha Matting
use_alpha_matting = st.sidebar.checkbox("Activer l'affinage des bords (Alpha Matting)", value=True)

# Valeurs par défaut
fg_threshold = 240  # Seuil de premier plan (défaut rembg)
bg_threshold = 10   # Seuil d'arrière-plan (défaut rembg)

if use_alpha_matting:
    st.sidebar.subheader("Réglages de l'affinage :")
    
    # NOUVEAU CURSEUR : Seuil de Premier Plan
    fg_threshold = st.sidebar.slider(
        "Tolérance du Premier Plan (Sujet) :",
        min_value=0,
        max_value=255,
        value=240,
        help=(
            "Plus cette valeur est BASSE, plus l'IA inclura de pixels 'incertains' "
            "(comme le texte ou les cheveux fins) dans le sujet principal. "
            "Essayez de BAISSER cette valeur pour garder le texte."
        )
    )
    
    # CURSEUR EXISTANT : Seuil d'Arrière-plan
    bg_threshold = st.sidebar.slider(
        "Sensibilité de l'Arrière-Plan :",
        min_value=0,
        max_value=255,
        value=10,
        help=(
            "Plus cette valeur est HAUTE, plus l'IA sera agressive pour supprimer "
            "les pixels de l'arrière-plan. (Défaut: 10)"
        )
    )
    st.sidebar.markdown(
        "**Astuce :** Pour garder votre texte, essayez de **baisser** la 'Tolérance du Premier Plan' (ex: à 150) "
        "et de garder la 'Sensibilité de l'Arrière-Plan' basse (ex: à 10)."
    )

# --- Interface Principale ---
st.title("✂️ Suppresseur d'arrière-plan d'image")
st.markdown(
    "Téléchargez une image et l'IA enlèvera l'arrière-plan automatiquement."
)

if use_alpha_matting:
    st.warning("Mode 'Affinage des bords' activé. Le traitement sera plus lent mais plus précis.")
else:
    st.info("Mode rapide activé. Pour des réglages fins (cheveux, texte), activez l'affinage dans les réglages à gauche.")


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
        spinner_message = ("Magie en cours... L'IA analyse l'image..." 
                           if not use_alpha_matting 
                           else "Affinage en cours... (plus lent)...")
        
        with st.spinner(spinner_message):
            try:
                # 
                # --- MODIFICATION CLÉ ---
                # On passe les DEUX seuils à la fonction remove()
                #
                output_bytes = remove(
                    input_bytes,
                    alpha_matting=use_alpha_matting,
                    alpha_matting_foreground_threshold=fg_threshold, # Valeur du NOUVEAU curseur
                    alpha_matting_background_threshold=bg_threshold  # Valeur du curseur existant
                )
                
                output_image = Image.open(io.BytesIO(output_bytes))
                
                st.image(output_image, caption="Arrière-plan supprimé", use_column_width=True)
                
                file_name = f"{uploaded_file.name.split('.')[0]}_no_bg.png"
                
                st.download_button(
                    label="📥 Télécharger le résultat (PNG)",
                    data=output_bytes,
                    file_name=file_name,
                    mime="image/png"
                )
            except Exception as e:
                st.error(f"Une erreur est survenue lors du traitement : {e}")
                
    else:
        st.info("Veuillez télécharger une image dans le panneau de gauche pour voir le résultat ici.")

# --- Pied de page ---
st.markdown("---")
st.markdown("Créé avec [Streamlit](https://streamlit.io/) & [rembg](https://github.com/danielgatis/rembg).")
