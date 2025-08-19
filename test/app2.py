import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile

# ================================
# Import de tes fonctions existantes
# ================================
from ton_module import (
    calc_mean_pressures,
    calc_Vdots_out,
    process_gas_analyser,
)

st.title("Analyse multi-fichiers CSV avec Gas Analyser")

# Upload de plusieurs CSV en entrée
csv_files = st.file_uploader(
    "Choisir un ou plusieurs fichiers CSV",
    type="csv",
    accept_multiple_files=True,
)

# Upload des fichiers log (toujours unique, commun à tous les CSV)
txt_file_gasMeas_CR = st.file_uploader(
    "Fichier log Gas Analyser CR", type="txt"
)
txt_file_gasMeas_GR = st.file_uploader(
    "Fichier log Gas Analyser GR", type="txt"
)

if csv_files:
    raspi_only_files = []   # fichiers Excel sans gas analyser
    extended_files = []     # fichiers Excel avec gas analyser

    for csv_file_raspi in csv_files:
        # ================================
        # Traitement principal Raspi
        # ================================
        df_out, df_data_raspi = calc_mean_pressures(csv_file_raspi)
        df_Vdots = calc_Vdots_out(df_out)

        # Sauvegarde version RaPi only
        output_raspi = BytesIO()
        with pd.ExcelWriter(output_raspi, engine="xlsxwriter") as writer:
            df_out.to_excel(writer, sheet_name="p_mean")
            df_data_raspi.to_excel(writer, sheet_name="raspi_data")
            df_Vdots.to_excel(writer, sheet_name="Vdot_stats")
        raspi_only_files.append(
            (csv_file_raspi.name.replace(".csv", "_raspi.xlsx"), output_raspi.getvalue())
        )

        # ================================
        # Traitement Extended si logs dispo
        # ================================
        if txt_file_gasMeas_CR or txt_file_gasMeas_GR:
            df_CO2, df_Vdots, df_summary = process_gas_analyser(
                txt_file_gasMeas_CR, txt_file_gasMeas_GR, df_out
            )

            output_extended = BytesIO()
            with pd.ExcelWriter(output_extended, engine="xlsxwriter") as writer:
                df_out.to_excel(writer, sheet_name="p_mean")
                df_data_raspi.to_excel(writer, sheet_name="raspi_data")
                df_Vdots.to_excel(writer, sheet_name="Vdot_stats")
                df_CO2.to_excel(writer, sheet_name="CO2_stats")
                df_summary.to_excel(writer, sheet_name="Summary")
            extended_files.append(
                (csv_file_raspi.name.replace(".csv", "_extended.xlsx"), output_extended.getvalue())
            )

    # ================================
    # ZIP des résultats RaPi only
    # ================================
    if raspi_only_files:
        zip_buffer_raspi = BytesIO()
        with zipfile.ZipFile(zip_buffer_raspi, "w") as zip_file:
            for fname, fdata in raspi_only_files:
                zip_file.writestr(fname, fdata)
        st.download_button(
            label="Télécharger résultats RaPi only (ZIP)",
            data=zip_buffer_raspi.getvalue(),
            file_name="results_raspi_only.zip",
            mime="application/zip",
        )

    # ================================
    # ZIP des résultats Extended
    # ================================
    if extended_files:
        zip_buffer_extended = BytesIO()
        with zipfile.ZipFile(zip_buffer_extended, "w") as zip_file:
            for fname, fdata in extended_files:
                zip_file.writestr(fname, fdata)
        st.download_button(
            label="Télécharger résultats Extended (ZIP)",
            data=zip_buffer_extended.getvalue(),
            file_name="results_extended.zip",
            mime="application/zip",
        )

        # ================================
        # Tableau récapitulatif unique
        # ================================
        recap_data = []
        for fname, fdata in extended_files:
            xls = pd.ExcelFile(BytesIO(fdata))

            # Lecture des feuilles
            df_co2 = pd.read_excel(xls, sheet_name="CO2_stats", index_col=0)
            df_pmean = pd.read_excel(xls, sheet_name="p_mean", index_col=0)
            df_vdot = pd.read_excel(xls, sheet_name="Vdot_stats", index_col=0)

            # Extraction des valeurs demandées
            moyenne_co2 = df_co2.iloc[0, 0]   # cellule B2
            max_co2 = df_co2.iloc[3, 0]       # cellule B5
            dp1 = df_pmean.iloc[32, 2]        # cellule C33
            vdot_gr = df_vdot.iloc[0, 2]      # cellule C2

            recap_data.append([fname, moyenne_co2, max_co2, dp1, vdot_gr])

        df_recap = pd.DataFrame(
            recap_data,
            columns=["Nom du fichier", "Moyenne CO2", "CO2 max", "dp1", "Débit volumique GR"]
        )

        output_recap = BytesIO()
        with pd.ExcelWriter(output_recap, engine="xlsxwriter") as writer:
            df_recap.to_excel(writer, sheet_name="Résumé", index=False)

        st.download_button(
            label="Télécharger le tableau récapitulatif (Extended)",
            data=output_recap.getvalue(),
            file_name="recap_extended.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
