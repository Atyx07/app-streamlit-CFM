import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io
import numpy as np
# Importation de la nouvelle bibliothèque pour la pipette
from streamlit_image_coordinates import streamlit_image_coordinates

# --- Configuration de la page ---
st.set_page_config(
    page_title="Détourage Express",
    page_icon="✨",
    layout="wide"
)

# --- Initialisation du Session State ---
# C'est crucial pour garder en mémoire l'image et la couleur choisie
if 'original_image' not in st.session_state:
    st.session_state.original_image = None
if 'input_bytes' not in st.session_state:
    st.session_state.input_bytes = None
if 'last_file_name' not in st.session_state:
    st.session_state.last_file_name = None
if 'picked_color' not in st.session_state:
    st.session_state.picked_color = None

# --- Fonctions Utiles ---

def image_to_bytes(image):
    """Convertit une image PIL en bytes pour le téléchargement."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

def hex_to_rgb(hex_color):
    """Convertit un code hexadécimal #RRGGBB en tuple (R, G, B)."""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def remove_color_background(image, color_to_remove_hex, tolerance_percent):
    """
    Supprime un fond de couleur unie d'une image PIL.
    """
    img = image.convert("RGBA")
    img_np = np.array(img)
    target_color_rgb = hex_to_rgb(color_to_remove_hex)
    
    # La tolérance est une distance "carrée" (plus simple que la distance euclidienne)
    tolerance = (tolerance_percent / 100) * 255
    
    r, g, b, a = img_np.T
    
    r_dist = np.abs(r - target_color_rgb[0])
    g_dist = np.abs(g - target_color_rgb[1])
    b_dist = np.abs(b - target_color_rgb[2])
    
    mask = (r_dist <= tolerance) & (g_dist <= tolerance) & (b_dist <= tolerance)
    
    img_np[mask, 3] = 0 # Mettre l'alpha à 0 (transparent)
    
    return Image.fromarray(img_np)

# --- Interface Principale ---
st.title("✨ Détourage Express : IA ou Pipette")
st.markdown("Chargez votre image, puis choisissez la méthode de détourage ci-dessous.")
st.divider()

# --- Colonne de Téléchargement (à gauche) ---
col1, col2 = st.columns([1, 2]) # Colonne de gauche plus petite

with col1:
    st.header("1. Votre Image")
    uploaded_file = st.file_uploader(
        "Choisissez une image...", 
        type=["png", "jpg", "jpeg", "webp"]
    )
    
    if uploaded_file:
        # Si c'est un nouveau fichier, on le charge dans le session state
        if st.session_state.last_file_name != uploaded_file.name:
            st.session_state.last_file_name = uploaded_file.name
            input_bytes = uploaded_file.getvalue()
            st.session_state.input_bytes = input_bytes
            original_pil = Image.open(io.BytesIO(input_bytes))
            st.session_state.original_image = ImageOps.exif_transpose(original_pil).convert("RGBA")
            st.session_state.picked_color = None # Réinitialiser la couleur
        
        st.image(st.session_state.original_image, caption="Image Originale", use_column_width=True)
    else:
        # Vider le session state si aucun fichier n'est chargé
        st.session_state.original_image = None
        st.session_state.input_bytes = None
        st.session_state.last_file_name = None
        st.session_state.picked_color = None


# --- Colonne de Traitement (à droite) ---
with col2:
    st.header("2. Outils de Détourage")
    
    # On vérifie si une image est chargée via le session state
    if st.session_state.original_image is not None:
        
        tab1, tab2 = st.tabs(["🤖 Automatique (IA)", "🎨 Couleur Unie (Pipette)"])

        # --- Outil 1: IA (rembg) ---
        with tab1:
            st.subheader("Détourage par Intelligence Artificielle")
            st.info("Idéal pour les photos (personnes, animaux, objets) et les arrière-plans complexes.")
            
            if st.button("🚀 Lancer le détourage IA", use_container_width=True):
                with st.spinner("L'IA analyse l'image..."):
                    try:
                        output_bytes_ia = remove(st.session_state.input_bytes)
                        st.image(output_bytes_ia, caption="Résultat IA", use_column_width=True)
                        st.download_button(
                            label="📥 Télécharger le résultat (IA)",
                            data=output_bytes_ia,
                            file_name=f"{st.session_state.last_file_name.split('.')[0]}_ia.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Erreur lors du traitement IA : {e}")

        # --- Outil 2: Couleur Unie (Pipette) ---
        with tab2:
            st.subheader("Suppression par Couleur (Fond Uni)")
            st.info("Cliquez sur l'image ci-dessous pour choisir la couleur avec la pipette.")
            
            # --- C'EST LA MAGIE ---
            # On affiche l'image avec le composant "streamlit_image_coordinates"
            with st.container():
                coordinates = streamlit_image_coordinates(
                    st.session_state.original_image, 
                    key="picker"
                )
            
            # Si l'utilisateur a cliqué, 'coordinates' contient {'x': ..., 'y': ...}
            if coordinates:
                try:
                    # On récupère le pixel cliqué depuis l'image originale
                    color_tuple = st.session_state.original_image.getpixel(
                        (coordinates['x'], coordinates['y'])
                    )
                    # On le convertit en hexadécimal et on le stocke
                    st.session_state.picked_color = '#%02x%02x%02x' % color_tuple[:3]
                except Exception as e:
                    st.error(f"Erreur lors de la sélection du pixel : {e}")

            # Le sélecteur de couleur utilise la couleur stockée (ou blanc par défaut)
            default_color = st.session_state.picked_color if st.session_state.picked_color else '#FFFFFF'
            
            color_to_remove = st.color_picker(
                "Couleur à supprimer (mise à jour par la pipette) :", 
                default_color
            )
            
            tolerance = st.slider(
                "Tolérance (%) :", 
                min_value=0, 
                max_value=100, 
                value=10,
                help="Augmentez si le fond a des nuances légères."
            )
            
            if st.button("🚀 Lancer la suppression par couleur", use_container_width=True):
                with st.spinner("Application du filtre de couleur..."):
                    result_image_color = remove_color_background(
                        st.session_state.original_image, 
                        color_to_remove, 
                        tolerance
                    )
                    
                    st.image(result_image_color, caption="Résultat (Couleur)", use_column_width=True)
                    
                    output_bytes_color = image_to_bytes(result_image_color)
                    st.download_button(
                        label="📥 Télécharger le résultat (Couleur)",
                        data=output_bytes_color,
                        file_name=f"{st.session_state.last_file_name.split('.')[0]}_color.png",
                        mime="image/png",
                        use_container_width=True
                    )
    else:
        st.info("Les outils apparaîtront ici une fois qu'une image sera chargée.")
