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

# --- Titre et description ---
st.title("✂️ Suppresseur d'arrière-plan d'image")
st.markdown(
    "Téléchargez une image et l'IA enlèvera l'arrière-plan automatiquement, "
    "en utilisant le modèle [U-2-Net](https://github.com/xuebinqin/U-2-Net) via la bibliothèque `rembg`."
)
st.info("Le résultat sera une image PNG avec un fond transparent.")

# --- Colonnes pour l'affichage ---
col1, col2 = st.columns(2)

# --- Colonne 1 : Téléchargement et Image Originale ---
with col1:
    st.header("1. Votre Image")
    
    # Widget de téléchargement de fichier
    uploaded_file = st.file_uploader("Choisissez une image...", type=["png", "jpg", "jpeg", "webp"])
    
    if uploaded_file is not None:
        # Lire l'image téléchargée
        # Nous avons besoin des 'bytes' pour 'rembg' et d'un objet Image pour l'affichage
        input_bytes = uploaded_file.getvalue()
        input_image = Image.open(io.BytesIO(input_bytes))
        
        st.image(input_image, caption="Image Originale", use_column_width=True)

# --- Colonne 2 : Résultat et Téléchargement ---
with col2:
    st.header("2. Résultat")
    
    if uploaded_file is not None:
        # Si un fichier a été téléchargé, on lance le traitement
        with st.spinner("Magie en cours... L'IA analyse l'image..."):
            try:
                # L'opération magique : suppression de l'arrière-plan
                output_bytes = remove(input_bytes)
                
                # Convertir les bytes de sortie en objet Image pour l'affichage
                output_image = Image.open(io.BytesIO(output_bytes))
                
                st.image(output_image, caption="Arrière-plan supprimé", use_column_width=True)
                
                # Préparer le nom du fichier de sortie
                # Enlève l'extension originale et ajoute _no_bg.png
                file_name = f"{uploaded_file.name.split('.')[0]}_no_bg.png"
                
                # Bouton de téléchargement
                st.download_button(
                    label="📥 Télécharger le résultat (PNG)",
                    data=output_bytes,
                    file_name=file_name,
                    mime="image/png"
                )
            except Exception as e:
                st.error(f"Une erreur est survenue lors du traitement : {e}")
                st.error("L'image est peut-être corrompue ou dans un format non supporté par le modèle.")
                
    else:
        # Message par défaut si rien n'est téléchargé
        st.info("Veuillez télécharger une image dans le panneau de gauche pour voir le résultat ici.")

# --- Pied de page ---
st.markdown("---")
st.markdown("Créé avec [Streamlit](https://streamlit.io/) & [rembg](https://github.com/danielgatis/rembg).")
