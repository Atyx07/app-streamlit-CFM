import streamlit as st
import pandas as pd
import numpy as np

st.title("CFM Analysis Extended Generator")

st.write("Téléversez un fichier GR data (.txt) et un fichier CFM data (.csv) pour générer un fichier Excel cfm_analysis_extended avec les 6 onglets.")

# Upload des fichiers
gr_file = st.file_uploader("Fichier GR data (.txt)", type=["txt"])
cfm_file = st.file_uploader("Fichier CFM data (.csv)", type=["csv"])

if gr_file and cfm_file:
    try:
        # Lecture des fichiers
        gr_df = pd.read_csv(gr_file, sep="\t")
        gr_df["datetime"] = pd.to_datetime(gr_df["# Date"] + " " + gr_df["Time"], errors="coerce")

        cfm_df = pd.read_csv(cfm_file, skiprows=4)
        time_col = cfm_df.columns[0]
        cfm_df[time_col] = pd.to_datetime(cfm_df[time_col], errors="coerce")

        # Onglet Raspi : données brutes du CFM_data
        raspi_df = cfm_df.copy()

        # Plage horaire de l'expérience
        start_time = cfm_df[time_col].min()
        end_time = cfm_df[time_col].max()

        # Filtrer GR data sur cette plage
        gr_filtered = gr_df[(gr_df["datetime"] >= start_time) & (gr_df["datetime"] <= end_time)]
        ch2_col = [col for col in gr_df.columns if "Ch2:Conce:ppm" in col][0]

        # ----- Onglet p_mean -----
        # Hypothèse : colonnes GF*, RIS*, etc. = capteurs de pression
        p_mean_df = pd.DataFrame({
            "Unnamed: 0": [col for col in cfm_df.columns if col.startswith("GF") or col.startswith("RIS")],
            "h/m": np.nan,  # hauteur : pas fournie, à compléter si dispo
            "p_mean/mbar": [cfm_df[col].mean() for col in cfm_df.columns if col.startswith("GF") or col.startswith("RIS")],
            "p_std/mbar": [cfm_df[col].std() for col in cfm_df.columns if col.startswith("GF") or col.startswith("RIS")],
            "p_mean_not_corr/mbar": [cfm_df[col].mean() for col in cfm_df.columns if col.startswith("GF") or col.startswith("RIS")]
        })

        # ----- Onglet Vdot_stats -----
        # Hypothèse : colonnes Vdot présentes
        vdot_cols = [col for col in cfm_df.columns if "Vdot" in col]
        vdot_stats_df = pd.DataFrame({
            "Variable": vdot_cols,
            "mean": [cfm_df[col].mean() for col in vdot_cols],
            "std": [cfm_df[col].std() for col in vdot_cols],
            "min": [cfm_df[col].min() for col in vdot_cols],
            "max": [cfm_df[col].max() for col in vdot_cols]
        })

        # ----- Onglet Vdot_raw -----
        vdot_raw_df = pd.DataFrame()  # vide comme demandé

        # ----- Onglet CO2_stats -----
        co2_mean = gr_filtered[ch2_col].mean()
        co2_min = gr_filtered[ch2_col].min()
        co2_max = gr_filtered[ch2_col].max()
        co2_rel_std = gr_filtered[ch2_col].std() / co2_mean if co2_mean != 0 else np.nan

        co2_stats_df = pd.DataFrame({
            "CO2_mean": [co2_mean],
            "CO2_rel_std": [co2_rel_std],
            "CO2_min": [co2_min],
            "CO2_max": [co2_max]
        })

        # ----- Onglet CO2_GR -----
        co2_gr_df = gr_filtered[["datetime", ch2_col]].copy()
        co2_gr_df.columns = ["Datetime", "CO2_ppm"]

        # Sauvegarde en Excel multi-onglets
        output_filename = "cfm_analysis_extended.xlsx"
        with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
            p_mean_df.to_excel(writer, sheet_name="p_mean", index=False)
            vdot_stats_df.to_excel(writer, sheet_name="Vdot_stats", index=False)
            vdot_raw_df.to_excel(writer, sheet_name="Vdot_raw", index=False)
            co2_stats_df.to_excel(writer, sheet_name="CO2_stats", index=False)
            co2_gr_df.to_excel(writer, sheet_name="CO2_GR", index=False)
            raspi_df.to_excel(writer, sheet_name="Raspi", index=False)

        # Bouton de téléchargement
        st.success("Fichier Excel généré avec succès.")
        st.download_button(
            label="Télécharger le fichier Excel",
            data=open(output_filename, "rb").read(),
            file_name=output_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Erreur lors du traitement : {e}")
        