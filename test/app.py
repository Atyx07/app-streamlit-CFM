# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 09:46:34 2025

@author: Gregor
"""

import numpy as np
import pandas as pd
import streamlit as st
from io import BytesIO
import zipfile

# --- Tes fonctions calc_mean_pressures, gm_signal_to_Vdot, calc_Vdots_out, extract_gasAnalyser_section, calc_gasAnalyser_stats restent identiques ---

# (Tu peux copier-coller toutes tes fonctions ici, inchangées)

# === Streamlit app ===

st.header("CFM data processing - multi file batch")

# multi-upload Raspi CSV files
csv_files_raspi = st.file_uploader(
    "Import raw data (.csv-export file from RaPi) - multiple selection allowed",
    accept_multiple_files=True,
    key="upload_raspi_multi"
)

# single upload for gas analyser CR and GR txt files (on suppose une seule paire pour simplifier)
txt_file_gasMeas_CR = st.file_uploader("Import raw data from gas analyser (CR) - optional", key="upload_gasAnal_CR")
txt_file_gasMeas_GR = st.file_uploader("Import raw data from gas analyser (GR) - optional", key="upload_gasAnal_GR")
timestamps_manual = st.checkbox("Define end- and start-time manually (for gas analyser data extraction)", value=False)

if csv_files_raspi and len(csv_files_raspi) > 0:

    # Prepare in-memory ZIP archive
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:

        # Read gas analyser data once, if provided
        df_GM_CR_raw = None
        df_GM_GR_raw = None
        if txt_file_gasMeas_CR is not None:
            df_GM_CR_raw = pd.read_csv(txt_file_gasMeas_CR, sep="\t", header=0, engine='python')
            df_GM_CR_raw = df_GM_CR_raw[["Time", "Ch1:Conce:Vol%"]]
            df_GM_CR_raw.columns = ["t", "CO2"]
            df_GM_CR_raw["CO2"] = df_GM_CR_raw["CO2"]/100
            df_GM_CR_raw["CO2"] = df_GM_CR_raw["CO2"].round(9)
        if txt_file_gasMeas_GR is not None:
            df_GM_GR_raw = pd.read_csv(txt_file_gasMeas_GR, sep="\t", header=0, engine='python')
            df_GM_GR_raw = df_GM_GR_raw[["Time", "Ch2:Conce:ppm"]]
            df_GM_GR_raw.columns = ["t", "CO2"]
            df_GM_GR_raw["CO2"] = df_GM_GR_raw["CO2"]/(10**6)
            df_GM_GR_raw["CO2"] = df_GM_GR_raw["CO2"].round(9)

        for file_raspi in csv_files_raspi:
            # Traitement pour chaque fichier Raspi
            df_p, df_data_raspi = calc_mean_pressures(file_raspi)
            df_data_raspi, df_Vdot_stats, df_Vdots = calc_Vdots_out(df_data_raspi)

            # Gas analyser traitement uniquement si on a les fichiers
            df_GM_stats = None
            df_GM_CR = None
            df_GM_GR = None

            if df_GM_CR_raw is not None or df_GM_GR_raw is not None:

                # calcul timestamps
                if timestamps_manual:
                    # Une seule fois par batch ? Sinon tu peux améliorer ici avec des inputs spécifiques par fichier
                    t_start_str = st.text_input(f"Start-time for {file_raspi.name}", value=None, key=f"start_{file_raspi.name}")
                    t_end_str = st.text_input(f"End-time for {file_raspi.name}", value=None, key=f"end_{file_raspi.name}")
                    if t_start_str and t_end_str:
                        t_start_tot = sum([a*b for a,b in zip([3600,60,1], map(float,t_start_str.split(':')))])
                        t_end_tot = sum([a*b for a,b in zip([3600,60,1], map(float,t_end_str.split(':')))])
                    else:
                        # si pas saisi, par défaut 0-0 pour ne rien extraire
                        t_start_tot = 0
                        t_end_tot = 0
                else:
                    t_start_tot = df_data_raspi.iloc[0]["t_tot"]
                    t_end_tot = df_data_raspi.iloc[-1]["t_tot"]

                # Extraction gas analyser CR
                if df_GM_CR_raw is not None:
                    df_GM_CR = extract_gasAnalyser_section(df_GM_CR_raw, t_start_tot, t_end_tot)
                    GM_CR_stats = calc_gasAnalyser_stats(df_GM_CR)
                else:
                    GM_CR_stats = [np.nan]*4

                # Extraction gas analyser GR
                if df_GM_GR_raw is not None:
                    df_GM_GR = extract_gasAnalyser_section(df_GM_GR_raw, t_start_tot, t_end_tot)
                    GM_GR_stats = calc_gasAnalyser_stats(df_GM_GR)
                else:
                    GM_GR_stats = [np.nan]*4

                df_GM_stats = pd.DataFrame(
                    index=['CO2_mean / mol/mol', 'CO2_std / mol/mol', 'CO2_min / mol/mol', 'CO2_max / mol/mol']
                )
                df_GM_stats["CR"] = GM_CR_stats
                df_GM_stats["GR"] = GM_GR_stats

            # Générer Excel en mémoire pour ce fichier
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')

            df_p.to_excel(writer, sheet_name="p_mean", float_format="%.5f", startrow=0, index=True)
            df_Vdot_stats.to_excel(writer, sheet_name="Vdot_stats", float_format="%.5f", startrow=0, index=True)
            df_Vdots.to_excel(writer, sheet_name="Vdot_raw", float_format="%.5f", startrow=0, index=True)
            df_data_raspi.to_excel(writer, sheet_name="RasPi", float_format="%.5f", startrow=0, index=True)

            if df_GM_stats is not None:
                df_GM_stats.to_excel(writer, sheet_name="CO2_stats", float_format="%.9f", startrow=0, index=True)
            if df_GM_CR is not None:
                df_GM_CR.to_excel(writer, sheet_name="CO2_CR", float_format="%.9f", startrow=0, index=False)
            if df_GM_GR is not None:
                df_GM_GR.to_excel(writer, sheet_name="CO2_GR", float_format="%.9f", startrow=0, index=False)

            writer.close()

            # Ajouter ce fichier Excel au zip
            zip_file.writestr(f'cfm_analysis_{file_raspi.name.split(".")[0]}.xlsx', output.getvalue())

    # Proposer le téléchargement du ZIP
    st.download_button(
        label="Export all results as ZIP",
        data=zip_buffer.getvalue(),
        file_name="cfm_analysis_batch.zip"
    )
