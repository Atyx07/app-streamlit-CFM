import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io
import numpy as np
import platform # Importé pour le débogage
import streamlit_drawable_canvas # Importé pour le débogage

# --- Configuration de la page ---
st.set_page_config(
    page_title="Éditeur d'arrière-plan",
    page_icon="🎨",
    layout="wide"
)

# --- PANNEAU DE DÉBOGAGE (NOUVEAU) ---
with st.sidebar:
    st.header("🕵️‍♂️ Panneau de Débogage")
    st.info(
        "Ce panneau vérifie si l'environnement est correct "
        "pour que le crayon de retouche fonctionne."
    )
    
    # Vérifier la version de Python
    py_version = platform.python_version()
    st.markdown(f"**Version Python :** `{py_version}`")
    if py_version.startswith("3.11"):
        st.success("Version Python OK (devrait être 3.11)")
    else:
        st.error("ERREUR: Python doit être 3.11. Votre build a échoué.")

    # Vérifier la version de Streamlit
    st_version = st.__version__
    st.markdown(f"**Version Streamlit :** `{st_version}`")
    if st_version == "1.29.0":
        st.success("Version Streamlit OK (doit être 1.29.0)")
    else:
        st.error("ERREUR: Streamlit doit être 1.29.0. Votre build a échoué.")
        
    # Vérifier la version de Canvas
    try:
        canvas_version = streamlit_drawable_canvas.__version__
        st.markdown(f"**Version Canvas :** `{canvas_version}`")
        st.success("Canvas est installé.")
    except Exception as e:
        st.error("ERREUR: Streamlit-Drawable-Canvas n'est PAS installé.")

# --- Initialisation du Session State ---
if 'original_image' not in st.session_state:
    st.session_state.original_image = None
if 'processed_image' not in st.session_state:
    st.session_state.processed_image = None
# ... (le reste du session state) ...

# (Le reste de votre script est identique à la version précédente)
# --- Fonctions Utiles ---
def process_image(image_bytes):
    """Lance rembg sur l'image et la stocke dans le session state."""
    with st.spinner("Magie en cours... L'IA analyse l'image..."):
        try:
            output_bytes = remove(image_bytes)
            st.session_state.processed_image = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
            st.session_state.final_image = None # Réinitialise l'image finale
        except Exception as e:
            st.error(f"Erreur lors du traitement automatique : {e}")
            st.session_state.processed_image = None

def image_to_bytes(image):
    """Convertit une image PIL en bytes pour le téléchargement."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

# --- Interface Principale ---
st.title("✂️🎨 Éditeur d'arrière-plan IA (avec/sans retouche)")
st.markdown(
    "1. **Chargez** votre image.\n"
    "2. **Lancez** le détourage IA.\n"
    "3. **Choisissez** votre résultat : 'Sans Retouche' (rapide) ou 'Avec Retouche' (pour corriger)."
)
st.info("Utilisez la flèche `>` en haut à gauche pour ouvrir le panneau de débogage si l'onglet 'Avec Retouche' ne s'affiche pas.")
st.divider()

# --- Colonnes principales ---
col1, col2 = st.columns(2)

# --- Colonne 1 : Originale et Contrôles ---
with col1:
    st.header("Étape 1 : Charger et Traiter")
    
    uploaded_file = st.file_uploader(
        "Choisissez une image...", 
        type=["png", "jpg", "jpeg", "webp"],
        key=f"uploader_{st.session_state.get('upload_key', 0)}"
    )
    
    if uploaded_file is not None:
        st.session_state.file_name = uploaded_file.name
        if uploaded_file.getvalue() != st.session_state.get('original_bytes', None):
            st.session_state.original_bytes = uploaded_file.getvalue()
            original_pil = Image.open(io.BytesIO(st.session_state.original_bytes))
            st.session_state.original_image = ImageOps.exif_transpose(original_pil).convert("RGBA")
            st.session_state.processed_image = None
            st.session_state.final_image = None
            
        st.image(st.session_state.original_image, caption="Image Originale", use_column_width=True)
        
        if st.button("🚀 Lancer le détourage IA", use_container_width=True):
            process_image(st.session_state.original_bytes)
            st.session_state.final_image = None 

# --- Colonne 2 : Résultat (avec Onglets) ---
with col2:
    st.header("Étape 2 : Résultat")
    
    if st.session_state.processed_image is None:
        st.info("Le résultat du détourage apparaîtra ici.")
    else:
        # --- CRÉATION DES ONGLETS ---
        tab1, tab2 = st.tabs(["Résultat (Sans Retouche)", "Résultat (Avec Retouche)"])

        # --- Onglet 1 : Version Simple (v2) ---
        with tab1:
            st.subheader("Résultat IA simple")
            st.info("Voici le résultat brut de l'IA. Rapide et simple.")
            
            st.image(st.session_state.processed_image, caption="Arrière-plan supprimé (IA)", use_column_width=True)
            
            st.download_button(
                label="📥 Télécharger le résultat (PNG)",
                data=image_to_bytes(st.session_state.processed_image),
                file_name=f"{st.session_state.file_name.split('.')[0]}_ia.png",
                mime="image/png",
                use_container_width=True
            )

        # --- Onglet 2 : Version Retouche (v5) ---
        with tab2:
            st.subheader("Outil de Retouche Manuelle")
            st.info("🎨 **Peignez en ROUGE** sur l'image pour marquer les zones à restaurer (ex: texte manquant).")
            
            # Calcul de la taille du canvas
            width_orig = st.session_state.processed_image.width
            height_orig = st.session_state.processed_image.height
            max_width = 700
            if width_orig > max_width:
                ratio = max_width / width_orig
                width_canvas = max_width
                height_canvas = int(height_orig * ratio)
            else:
                width_canvas = width_orig
                height_canvas = height_orig

            canvas_result = st_canvas(
                fill_color="rgba(255, 0, 0, 0.3)",
                stroke_width=20,
                stroke_color="rgba(255, 0, 0, 0.7)", # Crayon ROUGE
                background_image=st.session_state.processed_image, # L'image de l'IA va ici
                update_streamlit=False,
                height=height_canvas,
                width=width_canvas,
                drawing_mode="freedraw",
                key="canvas",
            )

            # Bouton d'application
            if st.button("Appliquer la retouche", use_container_width=True):
                if canvas_result.image_data is not None:
                    with st.spinner("Application de la retouche..."):
                        mask_drawing_np_resized = canvas_result.image_data[:, :, 3] > 0
                        mask_restore_np_resized = (mask_drawing_np_resized * 255).astype('uint8')
                        mask_restore_pil = Image.fromarray(mask_restore_np_resized, 'L')
                        original_size = st.session_state.processed_image.size
                        mask_restore_pil_original_size = mask_restore_pil.resize(original_size, Image.Resampling.NEAREST)
                        mask_restore_np = np.array(mask_restore_pil_original_size)
                        alpha_rembg_np = np.array(st.session_state.processed_image.split()[3])
                        final_alpha_np = np.maximum(alpha_rembg_np, mask_restore_np)
                        final_image = st.session_state.original_image.copy()
                        final_image.putalpha(Image.fromarray(final_alpha_np, 'L'))
                        st.session_state.final_image = final_image
                else:
                    st.warning("Vous n'avez rien dessiné.")
            
            if st.session_state.final_image is not None:
                st.divider()
                st.subheader("Aperçu Final Retouché")
                st.image(st.session_state.final_image, caption="Résultat retouché", use_column_width=True)

                st.download_button(
                    label="📥 Télécharger le résultat final (PNG)",
                    data=image_to_bytes(st.session_state.final_image),
                    file_name=f"{st.session_state.file_name.split('.')[0]}_retouched.png",
                    mime="image/png",
                    use_container_width=True
                )
