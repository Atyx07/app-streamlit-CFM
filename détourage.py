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
# C'est crucial pour garder les images en mémoire entre les interactions
if 'original_image' not in st.session_state:
    st.session_state.original_image = None
if 'processed_image' not in st.session_state:
    st.session_state.processed_image = None
if 'final_image' not in st.session_state:
    st.session_state.final_image = None
if 'upload_key' not in st.session_state:
    st.session_state.upload_key = 0  # Pour forcer le reset si on change d'image
if 'original_bytes' not in st.session_state:
    st.session_state.original_bytes = None

# --- Fonctions Utiles ---
def process_image(image_bytes):
    """Lance rembg sur l'image et la stocke dans le session state."""
    with st.spinner("Magie en cours... L'IA analyse l'image..."):
        try:
            output_bytes = remove(image_bytes)
            # Stocker le résultat RGBA (avec transparence)
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
    "2. **Traitez-la** avec l'IA. Le résultat (imparfait) s'affichera à droite.\n"
    "3. **Dessinez** sur l'image de droite avec le **crayon blanc** pour restaurer les zones effacées par erreur (comme votre texte).\n"
    "4. **Téléchargez** le résultat final."
)

st.divider()

# --- Colonnes principales ---
col1, col2 = st.columns(2)

# --- Colonne 1 : Originale et Contrôles ---
with col1:
    st.header("Étape 1 : Charger et Traiter")
    
    # Le 'key' est important pour détecter les changements de fichier
    uploaded_file = st.file_uploader(
        "Choisissez une image...", 
        type=["png", "jpg", "jpeg", "webp"],
        key=f"uploader_{st.session_state.upload_key}"
    )
    
    if uploaded_file is not None:
        # Si c'est une nouvelle image, on réinitialise tout
        if uploaded_file.getvalue() != st.session_state.original_bytes:
            st.session_state.original_bytes = uploaded_file.getvalue()
            # Utiliser ImageOps.exif_transpose pour corriger l'orientation (problème courant JPG)
            original_pil = Image.open(io.BytesIO(st.session_state.original_bytes))
            st.session_state.original_image = ImageOps.exif_transpose(original_pil).convert("RGBA")
            # Réinitialiser les images traitées
            st.session_state.processed_image = None
            st.session_state.final_image = None
            
        st.image(st.session_state.original_image, caption="Image Originale", use_column_width=True)
        
        # Bouton pour lancer le traitement
        if st.button("🚀 Lancer le détourage IA", use_container_width=True):
            process_image(st.session_state.original_bytes)

# --- Colonne 2 : Résultat et Édition ---
with col2:
    st.header("Étape 2 : Retoucher et Télécharger")
    
    if st.session_state.processed_image is None:
        st.info("Le résultat du détourage et l'outil de retouche apparaîtront ici.")
    else:
        # Configuration du crayon
        st.markdown("Utilisez le **crayon (blanc)** pour **restaurer** les zones manquantes.")
        
        # On utilise la taille de l'image traitée pour le canvas
        width_orig = st.session_state.processed_image.width
        height_orig = st.session_state.processed_image.height
        
        # Limiter la taille max pour l'affichage (garder le ratio)
        max_width = 700
        if width_orig > max_width:
            ratio = max_width / width_orig
            width_canvas = max_width
            height_canvas = int(height_orig * ratio)
        else:
            width_canvas = width_orig
            height_canvas = height_orig

        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)",  # Crayon blanc
            stroke_width=20,                      # Taille du crayon
            stroke_color="#FFFFFF",               # Couleur du crayon
            background_image=st.session_state.processed_image,
            update_streamlit=True,
            height=height_canvas,
            width=width_canvas,
            drawing_mode="freedraw",
            key="canvas",
        )

        # --- Logique de fusion (CORRIGÉE) ---
        if canvas_result.image_data is not None:
            # 1. Le dessin de l'utilisateur (le "masque de restauration")
            # Il a la taille redimensionnée du canvas (ex: 700x700)
            mask_drawing_np_resized = canvas_result.image_data[:, :, 3] > 0
            mask_restore_np_resized = (mask_drawing_np_resized * 255).astype('uint8')
            
            # Convertir ce masque en image PIL pour le redimensionner
            mask_restore_pil = Image.fromarray(mask_restore_np_resized, 'L')
            
            # 2. Obtenir la taille de l'image ORIGINALE traitée
            original_size = st.session_state.processed_image.size # (largeur, hauteur)
            
            # 3. Redimensionner le masque du dessin à la taille originale
            # On utilise Image.NEAREST pour garder des bords nets
            mask_restore_pil_original_size = mask_restore_pil.resize(original_size, Image.Resampling.NEAREST)
            
            # Convertir le masque redimensionné en NumPy
            mask_restore_np = np.array(mask_restore_pil_original_size)
            
            # 4. Le masque alpha original de rembg (a la bonne taille)
            alpha_rembg_np = np.array(st.session_state.processed_image.split()[3])
            
            # 5. On fusionne les deux masques (maintenant de même taille)
            final_alpha_np = np.maximum(alpha_rembg_np, mask_restore_np)
            
            # 6. On crée la nouvelle image finale
            # On part de l'image originale (qui a les bonnes couleurs)
            final_image = st.session_state.original_image.copy()
            # On applique le nouveau masque alpha combiné
            final_image.putalpha(Image.fromarray(final_alpha_np, 'L'))
            
            # On stocke l'image finale pour le téléchargement
            st.session_state.final_image = final_image
            
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
