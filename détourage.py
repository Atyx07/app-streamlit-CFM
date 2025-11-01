import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io
import numpy as np

# --- Configuration de la page ---
st.set_page_config(
    page_title="Détourage Express",
    page_icon="✨",
    layout="wide"
)

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
    # Convertir l'image en RGBA (si elle ne l'est pas) et en NumPy
    img = image.convert("RGBA")
    img_np = np.array(img)
    
    # Obtenir la couleur cible en RGB
    target_color_rgb = hex_to_rgb(color_to_remove_hex)
    
    # Calculer la tolérance. 
    # Une tolérance de 0-100% est mappée sur une distance de 0-255
    tolerance = (tolerance_percent / 100) * 255
    
    # Séparer les canaux R, G, B (ignorer l'alpha pour la comparaison)
    r, g, b, a = img_np.T
    
    # Calculer la distance absolue pour chaque canal
    r_dist = np.abs(r - target_color_rgb[0])
    g_dist = np.abs(g - target_color_rgb[1])
    b_dist = np.abs(b - target_color_rgb[2])
    
    # Créer le masque : True si TOUS les canaux sont dans la tolérance
    mask = (r_dist <= tolerance) & (g_dist <= tolerance) & (b_dist <= tolerance)
    
    # Appliquer le masque : Mettre l'alpha à 0 (transparent) là où le masque est True
    img_np[mask, 3] = 0
    
    # Reconvertir en image PIL
    return Image.fromarray(img_np)

# --- Interface Principale ---
st.title("✨ Détourage Express : IA ou Couleur Unie")
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
        input_bytes = uploaded_file.getvalue()
        # Corriger l'orientation (EXIF) et s'assurer qu'elle est en RGBA
        original_pil = Image.open(io.BytesIO(input_bytes))
        original_image = ImageOps.exif_transpose(original_pil).convert("RGBA")
        
        st.image(original_image, caption="Image Originale", use_column_width=True)
    else:
        st.info("Veuillez charger une image pour commencer.")


# --- Colonne de Traitement (à droite) ---
with col2:
    st.header("2. Outils de Détourage")
    
    if uploaded_file:
        # Créer les onglets pour les deux méthodes
        tab1, tab2 = st.tabs(["🤖 Automatique (IA)", "🎨 Couleur Unie (Manuel)"])

        # --- Outil 1: IA (rembg) ---
        with tab1:
            st.subheader("Détourage par Intelligence Artificielle")
            st.info("Idéal pour les photos (personnes, animaux, objets) et les arrière-plans complexes.")
            
            if st.button("🚀 Lancer le détourage IA", use_container_width=True):
                with st.spinner("L'IA analyse l'image..."):
                    try:
                        output_bytes_ia = remove(input_bytes)
                        st.image(output_bytes_ia, caption="Résultat IA", use_column_width=True)
                        st.download_button(
                            label="📥 Télécharger le résultat (IA)",
                            data=output_bytes_ia,
                            file_name=f"{uploaded_file.name.split('.')[0]}_ia.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Erreur lors du traitement IA : {e}")

        # --- Outil 2: Couleur Unie (Chroma Key) ---
        with tab2:
            st.subheader("Suppression par Couleur (Fond Uni)")
            st.info("Idéal pour les logos et les graphiques avec un fond uni. (Ex: fond vert, fond blanc...)")
            
            # Essayer de deviner la couleur du fond (pixel en haut à gauche)
            try:
                guessed_color = original_image.getpixel((0, 0))
                default_color_hex = '#%02x%02x%02x' % guessed_color[:3]
            except Exception:
                default_color_hex = '#FFFFFF' # Blanc par défaut

            # Sélecteur de couleur
            color_to_remove = st.color_picker(
                "Cliquez pour choisir la couleur à supprimer :", 
                default_color_hex
            )
            
            # Curseur de Tolérance
            tolerance = st.slider(
                "Tolérance (%) :", 
                min_value=0, 
                max_value=100, 
                value=10,
                help=(
                    "À 0%, seule la couleur exacte est supprimée. "
                    "Augmentez la tolérance si le fond a des nuances légères. "
                    "Attention : une tolérance trop élevée peut effacer des parties de votre sujet !"
                )
            )
            
            if st.button("🚀 Lancer la suppression par couleur", use_container_width=True):
                with st.spinner("Application du filtre de couleur..."):
                    result_image_color = remove_color_background(
                        original_image, 
                        color_to_remove, 
                        tolerance
                    )
                    
                    st.image(result_image_color, caption="Résultat (Couleur)", use_column_width=True)
                    
                    # Préparer le téléchargement
                    output_bytes_color = image_to_bytes(result_image_color)
                    st.download_button(
                        label="📥 Télécharger le résultat (Couleur)",
                        data=output_bytes_color,
                        file_name=f"{uploaded_file.name.split('.')[0]}_color.png",
                        mime="image/png",
                        use_container_width=True
                    )
    else:
        st.info("Les outils apparaîtront ici une fois qu'une image sera chargée.")
