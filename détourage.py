import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io
import numpy as np
from streamlit_drawable_canvas import st_canvas

# --- Configuration de la page ---
st.set_page_config(
    page_title="Éditeur d'arrière-plan",
    page_icon="🎨",
    layout="wide"
)

# --- Initialisation du Session State ---
if 'original_image' not in st.session_state:
    st.session_state.original_image = None
if 'processed_image' not in st.session_state:
    st.session_state.processed_image = None
if 'final_image' not in st.session_state:
    st.session_state.final_image = None
if 'upload_key' not in st.session_state:
    st.session_state.upload_key = 0
if 'original_bytes' not in st.session_state:
    st.session_state.original_bytes = None

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
st.title("🎨 Éditeur d'arrière-plan avec Crayon de Retouche")
st.markdown(
    "**Comment ça marche ?**\n"
    "1. **Chargez** votre image.\n"
    "2. **Traitez-la** avec l'IA. Le résultat (parfois imparfait) s'affichera à droite.\n"
    "3. **Peignez en ROUGE** les zones à restaurer (comme du texte manquant).\n"
    "4. Cliquez sur **'Appliquer la retouche'** pour voir le résultat final."
)

st.divider()

# --- Colonnes principales ---
col1, col2 = st.columns(2)

# --- Colonne 1 : Originale et Contrôles ---
with col1:
    st.header("Étape 1 : Charger et Traiter")
    
    uploaded_file = st.file_uploader(
        "Choisissez une image...", 
        type=["png", "jpg", "jpeg", "webp"],
        key=f"uploader_{st.session_state.upload_key}"
    )
    
    if uploaded_file is not None:
        if uploaded_file.getvalue() != st.session_state.original_bytes:
            st.session_state.original_bytes = uploaded_file.getvalue()
            original_pil = Image.open(io.BytesIO(st.session_state.original_bytes))
            st.session_state.original_image = ImageOps.exif_transpose(original_pil).convert("RGBA")
            st.session_state.processed_image = None
            st.session_state.final_image = None
            
        st.image(st.session_state.original_image, caption="Image Originale", use_column_width=True)
        
        if st.button("🚀 Lancer le détourage IA", use_container_width=True):
            process_image(st.session_state.original_bytes)
            st.session_state.final_image = None # Réinitialiser l'aperçu final

# --- Colonne 2 : Résultat et Édition ---
with col2:
    st.header("Étape 2 : Retoucher")
    
    if st.session_state.processed_image is None:
        st.info("Le résultat du détourage et l'outil de retouche apparaîtront ici.")
    else:
        st.info("🎨 **Peignez en ROUGE** sur l'image pour marquer les zones à restaurer.")

        # On utilise la taille de l'image traitée pour le canvas
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
            fill_color="rgba(255, 0, 0, 0.3)",  # Couleur de remplissage (pour formes)
            stroke_width=20,                    # Taille du crayon
            stroke_color="rgba(255, 0, 0, 0.7)",# Crayon ROUGE semi-transparent
            background_image=st.session_state.processed_image,
            update_streamlit=False,             # IMPORTANT: On n'actualise pas en direct
            height=height_canvas,
            width=width_canvas,
            drawing_mode="freedraw",
            key="canvas",
        )

        # Bouton d'application
        if st.button("Appliquer la retouche", use_container_width=True):
            if canvas_result.image_data is not None:
                with st.spinner("Application de la retouche..."):
                    # 1. Le dessin de l'utilisateur (masque rouge)
                    mask_drawing_np_resized = canvas_result.image_data[:, :, 3] > 0
                    mask_restore_np_resized = (mask_drawing_np_resized * 255).astype('uint8')
                    
                    mask_restore_pil = Image.fromarray(mask_restore_np_resized, 'L')
                    
                    # 2. Taille de l'image originale traitée
                    original_size = st.session_state.processed_image.size
                    
                    # 3. Redimensionner le masque à la taille originale
                    mask_restore_pil_original_size = mask_restore_pil.resize(original_size, Image.Resampling.NEAREST)
                    mask_restore_np = np.array(mask_restore_pil_original_size)
                    
                    # 4. Masque alpha original de rembg
                    alpha_rembg_np = np.array(st.session_state.processed_image.split()[3])
                    
                    # 5. Fusionner les masques
                    final_alpha_np = np.maximum(alpha_rembg_np, mask_restore_np)
                    
                    # 6. Créer l'image finale
                    final_image = st.session_state.original_image.copy()
                    final_image.putalpha(Image.fromarray(final_alpha_np, 'L'))
                    
                    # 7. Stocker pour affichage et téléchargement
                    st.session_state.final_image = final_image
            else:
                st.warning("Vous n'avez rien dessiné.")
        
        # --- Affichage du résultat final (s'il existe) ---
        if st.session_state.final_image is not None:
            st.divider()
            st.subheader("Aperçu Final")
            st.image(st.session_state.final_image, caption="Résultat retouché", use_column_width=True)

            # Bouton de téléchargement
            st.download_button(
                label="📥 Télécharger le résultat final (PNG)",
                data=image_to_bytes(st.session_state.final_image),
                file_name=f"{uploaded_file.name.split('.')[0]}_retouched.png",
                mime="image/png",
                use_container_width=True
            )

# --- Pied de page ---
st.divider()
st.markdown("Créé avec [Streamlit](https://streamlit.io/), [rembg](https://github.com/danielgatis/rembg) & [Streamlit-Drawable-Canvas](https://github.com/andfanilo/streamlit-drawable-canvas).")
