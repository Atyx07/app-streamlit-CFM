import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io
import numpy as np
from streamlit_drawable_canvas import st_canvas

# --- Configuration de la page ---
st.set_page_config(
    page_title="Studio de Détourage",
    page_icon="🎨",
    layout="wide"
)

# --- Initialisation du Session State ---
# C'est crucial pour l'outil de retouche
if 'original_image' not in st.session_state:
    st.session_state.original_image = None
if 'original_bytes' not in st.session_state:
    st.session_state.original_bytes = None
if 'processed_image' not in st.session_state: # Pour le canevas
    st.session_state.processed_image = None
if 'final_image' not in st.session_state: # Pour l'aperçu final
    st.session_state.final_image = None
if 'last_file_name' not in st.session_state:
    st.session_state.last_file_name = None

# --- Fonctions Utiles ---
def image_to_bytes(image):
    """Convertit une image PIL en bytes pour le téléchargement."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

# --- Interface Principale ---
st.title("🎨 Studio de Détourage IA")
st.markdown("Chargez votre image, puis choisissez votre outil d'affinage.")
st.divider()

# --- Colonne 1 : Chargement ---
col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. Votre Image")
    uploaded_file = st.file_uploader(
        "Choisissez une image...", 
        type=["png", "jpg", "jpeg", "webp"]
    )
    
    if uploaded_file:
        if st.session_state.last_file_name != uploaded_file.name:
            st.session_state.last_file_name = uploaded_file.name
            input_bytes = uploaded_file.getvalue()
            st.session_state.original_bytes = input_bytes
            original_pil = Image.open(io.BytesIO(input_bytes))
            st.session_state.original_image = ImageOps.exif_transpose(original_pil).convert("RGBA")
            # Réinitialiser les images traitées si on change de fichier
            st.session_state.processed_image = None
            st.session_state.final_image = None
        
        st.image(st.session_state.original_image, caption="Image Originale", use_column_width=True)
    else:
        # Vider le session state si aucun fichier n'est chargé
        st.session_state.original_image = None
        st.session_state.original_bytes = None
        st.session_state.last_file_name = None
        st.session_state.processed_image = None
        st.session_state.final_image = None


# --- Colonne 2 : Outils ---
with col2:
    st.header("2. Outils de Détourage")
    
    if st.session_state.original_image is None:
        st.info("Les outils apparaîtront ici une fois qu'une image sera chargée.")
    else:
        tab1, tab2 = st.tabs(["🤖 IA Avancée (Curseurs)", "🖌️ Retouche Manuelle (Crayon)"])

        # --- ONGLET 1 : IA AVANCÉE (votre "V2") ---
        with tab1:
            st.subheader("Réglages fins de l'IA (Alpha Matting)")
            st.info("Utilisez ces curseurs pour affiner le détourage global de l'IA. Utile pour les cheveux, la fourrure, ou les sujets semi-transparents.")
            
            use_alpha_matting = st.checkbox("Activer l'affinage des bords (Plus lent)", value=True)
            
            fg_threshold = 240
            bg_threshold = 10
            
            if use_alpha_matting:
                fg_threshold = st.slider(
                    "Tolérance du Premier Plan (Sujet) :", 0, 255, 240,
                    help="Plus cette valeur est BASSE, plus l'IA inclura de pixels 'incertains' (texte, cheveux fins) dans le sujet."
                )
                bg_threshold = st.slider(
                    "Sensibilité de l'Arrière-Plan :", 0, 255, 10,
                    help="Plus cette valeur est HAUTE, plus l'IA sera agressive pour supprimer les pixels du fond."
                )
            
            if st.button("🚀 Lancer le détourage IA (Avancé)", use_container_width=True):
                with st.spinner("L'IA analyse avec les réglages fins..."):
                    try:
                        output_bytes_ia = remove(
                            st.session_state.original_bytes,
                            alpha_matting=use_alpha_matting,
                            alpha_matting_foreground_threshold=fg_threshold,
                            alpha_matting_background_threshold=bg_threshold
                        )
                        st.image(output_bytes_ia, caption="Résultat IA (Avancé)", use_column_width=True)
                        st.download_button(
                            label="📥 Télécharger le résultat (IA Avancé)",
                            data=output_bytes_ia,
                            file_name=f"{st.session_state.last_file_name.split('.')[0]}_ia_advanced.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Erreur lors du traitement IA : {e}")

        # --- ONGLET 2 : RETOUCHE MANUELLE (votre "V5") ---
        with tab2:
            st.subheader("Retouche Manuelle au Crayon")
            st.info("Idéal pour les cas difficiles (comme du texte) où l'IA se trompe. L'IA fait une première passe, puis vous corrigez au crayon.")
            
            if st.button("Étape 1 : Lancer le détourage IA (Initial)", use_container_width=True):
                with st.spinner("L'IA fait la première passe..."):
                    try:
                        # On lance une passe IA simple
                        output_bytes_v5 = remove(st.session_state.original_bytes)
                        # On stocke le résultat pour le canevas
                        st.session_state.processed_image = Image.open(io.BytesIO(output_bytes_v5)).convert("RGBA")
                        st.session_state.final_image = None # Réinitialiser l'aperçu
                    except Exception as e:
                        st.error(f"Erreur lors du traitement IA : {e}")

            if st.session_state.processed_image is not None:
                st.markdown("---")
                st.info("🎨 **Étape 2 : Peignez en ROUGE** les zones à restaurer (comme votre texte).")

                # Calcul de la taille du canevas
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
                    stroke_color="rgba(255, 0, 0, 0.7)",
                    background_image=st.session_state.processed_image,
                    update_streamlit=False,
                    height=height_canvas,
                    width=width_canvas,
                    drawing_mode="freedraw",
                    key="canvas_v5",
                )

                if st.button("Étape 3 : Appliquer la retouche", use_container_width=True):
                    if canvas_result.image_data is not None:
                        with st.spinner("Application de la retouche..."):
                            # 1. Masque dessiné (redimensionné)
                            mask_drawing_np_resized = canvas_result.image_data[:, :, 3] > 0
                            mask_restore_np_resized = (mask_drawing_np_resized * 255).astype('uint8')
                            mask_restore_pil = Image.fromarray(mask_restore_np_resized, 'L')
                            
                            # 2. Taille originale
                            original_size = st.session_state.processed_image.size
                            
                            # 3. Redimensionner le masque à la taille originale
                            mask_restore_pil_original_size = mask_restore_pil.resize(original_size, Image.Resampling.NEAREST)
                            mask_restore_np = np.array(mask_restore_pil_original_size)
                            
                            # 4. Masque alpha original de l'IA
                            alpha_rembg_np = np.array(st.session_state.processed_image.split()[3])
                            
                            # 5. Fusionner les masques
                            final_alpha_np = np.maximum(alpha_rembg_np, mask_restore_np)
                            
                            # 6. Créer l'image finale
                            final_image = st.session_state.original_image.copy()
                            final_image.putalpha(Image.fromarray(final_alpha_np, 'L'))
                            
                            st.session_state.final_image = final_image
                    else:
                        st.warning("Vous n'avez rien dessiné.")
                
                if st.session_state.final_image is not None:
                    st.divider()
                    st.subheader("Aperçu Final de la Retouche")
                    st.image(st.session_state.final_image, caption="Résultat retouché", use_column_width=True)

                    st.download_button(
                        label="📥 Télécharger le résultat retouché",
                        data=image_to_bytes(st.session_state.final_image),
                        file_name=f"{st.session_state.last_file_name.split('.')[0]}_retouched.png",
                        mime="image/png",
                        use_container_width=True
                    )
