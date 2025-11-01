# --- Logique de fusion ---
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
            mask_restore_pil_original_size = mask_restore_pil.resize(original_size, Image.NEAREST)
            
            # Convertir le masque redimensionné en NumPy
            mask_restore_np = np.array(mask_restore_pil_original_size)
            
            # 4. Le masque alpha original de rembg (a la bonne taille)
            alpha_rembg_np = np.array(st.session_state.processed_image.split()[3])
            
            # 5. On fusionne les deux masques (maintenant de même taille)
            # C'est la ligne 133 (corrigée)
            final_alpha_np = np.maximum(alpha_rembg_np, mask_restore_np)
            
            # 6. On crée la nouvelle image finale
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
