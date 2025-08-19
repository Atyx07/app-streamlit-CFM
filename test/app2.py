import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile

# =========================================
# Fonctions existantes à conserver
# (remplace 'pass' par tes vraies implémentations)
# =========================================
def calc_mean_pressures(csv_file_raspi):
    # Retourne df_p, df_data_raspi
    pass

def calc_Vdots_out(df_data_raspi):
    # Retourne df_data_raspi, df_Vdot_stats, df_Vdots
    pass

def extract_gasAnalyser_section(df_gm, t_start_tot, t_end_tot):
    pass

def calc_gasAnalyser_stats(df_gm):
    pass


# =========================================
# Interface Streamlit
# =========================================
st.title("CFM Analysis Tool - Multi CSV Support")

# Upload multiples CSV
csv_files_raspi = st.file_uploader(
    "Import raw data (.csv-export file from RaPi)",
    key="upload_raspi_multi",
    accept_multiple_files=True
)

# Upload unique pour logs
txt_file_gasMeas_CR = st.file_uploader("Import raw data from gas analyser (CR)", key="upload_gasAnal_CR")
txt_file_gasMeas_GR = st.file_uploader("Import raw data from gas analyser (GR)", key="upload_gasAnal_GR")

# Option temps manuel
timestamps_manual = st.checkbox(
    "Define end - and start-time manually (for gas analyser data extraction)",
    value=False
)

# Stockage fichiers
raspi_only_files = []
extended_files = []

# =========================================
# Boucle traitement CSVs
# =========================================
if csv_files_raspi:
    for csv_file_raspi in csv_files_raspi:
        # ---- 1) Calcul RaPi only ----
        df_p, df_data_raspi = calc_mean_pressures(csv_file_raspi)
        df_data_raspi, df_Vdot_stats, df_Vdots = calc_Vdots_out(df_data_raspi)

        output_raspi = BytesIO()
        writer = pd.ExcelWriter(output_raspi, engine='xlsxwriter')
        df_p.to_excel(writer, sheet_name="p_mean", float_format="%.5f", startrow=0, index=True)
        df_Vdot_stats.to_excel(writer, sheet_name="Vdot_stats", float_format="%.5f", startrow=0, index=True)
        df_Vdots.to_excel(writer, sheet_name="Vdot_raw", float_format="%.5f", startrow=0, index=True)
        df_data_raspi.to_excel(writer, sheet_name="RasPi", float_format="%.5f", startrow=0, index=True)
        writer.close()
        raspi_only_files.append((f'cfm_analysis_{csv_file_raspi.name.split(".")[0]}.xlsx', output_raspi.getvalue()))

        # ---- 2) Calcul Extended si logs dispo ----
        if txt_file_gasMeas_CR is not None and txt_file_gasMeas_GR is not None:
            df_GM_CR_raw = pd.read_csv(txt_file_gasMeas_CR, sep="\t", header=0, index_col=None, engine='python')
            df_GM_CR_raw = df_GM_CR_raw[["Time", "Ch1:Conce:Vol%"]]
            df_GM_CR_raw.columns = ["t", "CO2"]
            df_GM_CR_raw["CO2"] = (df_GM_CR_raw["CO2"]/100).round(9)

            df_GM_GR_raw = pd.read_csv(txt_file_gasMeas_GR, sep="\t", header=0, index_col=None, engine='python')
            df_GM_GR_raw = df_GM_GR_raw[["Time", "Ch2:Conce:ppm"]]
            df_GM_GR_raw.columns = ["t", "CO2"]
            df_GM_GR_raw["CO2"] = (df_GM_GR_raw["CO2"]/(10**6)).round(9)

            if timestamps_manual:
                t_start_str = st.text_input("start-time", value=df_GM_GR_raw.iloc[20]["t"])
                t_end_str = st.text_input("end-time", value=df_GM_GR_raw.iloc[-20]["t"])
                t_start_tot = sum([a*b for a,b in zip([3600,60,1], map(float,t_start_str.split(':')))])
                t_end_tot = sum([a*b for a,b in zip([3600,60,1], map(float,t_end_str.split(':')))])
            else:
                t_start_tot = df_data_raspi.iloc[0]["t_tot"]
                t_end_tot = df_data_raspi.iloc[-1]["t_tot"]

            df_GM_CR = extract_gasAnalyser_section(df_GM_CR_raw, t_start_tot, t_end_tot)
            df_GM_GR = extract_gasAnalyser_section(df_GM_GR_raw, t_start_tot, t_end_tot)

            GM_CR_stats = calc_gasAnalyser_stats(df_GM_CR)
            GM_GR_stats = calc_gasAnalyser_stats(df_GM_GR)

            df_GM_stats = pd.DataFrame(
                index=['CO2_mean / mol/mol', 'CO2_std / mol/mol', 'CO2_min / mol/mol', 'CO2_max / mol/mol']
            )
            df_GM_stats["CR"] = GM_CR_stats
            df_GM_stats["GR"] = GM_GR_stats

            output_ext = BytesIO()
            writer = pd.ExcelWriter(output_ext, engine='xlsxwriter')
            df_p.to_excel(writer, sheet_name="p_mean", float_format="%.5f", startrow=0, index=True)
            df_Vdot_stats.to_excel(writer, sheet_name="Vdot_stats", float_format="%.5f", startrow=0, index=True)
            df_Vdots.to_excel(writer, sheet_name="Vdot_raw", float_format="%.5f", startrow=0, index=True)
            df_GM_stats.to_excel(writer, sheet_name="CO2_stats", float_format="%.9f", startrow=0, index=True)
            df_GM_CR.to_excel(writer, sheet_name="CO2_CR", float_format="%.9f", startrow=0, index=True)
            df_GM_GR.to_excel(writer, sheet_name="CO2_GR", float_format="%.9f", startrow=0, index=True)
            df_data_raspi.to_excel(writer, sheet_name="RasPi", float_format="%.5f", startrow=0, index=True)
            writer.close()
            extended_files.append((f'cfm_analysis_extended_{csv_file_raspi.name.split(".")[0]}.xlsx', output_ext.getvalue()))


# =========================================
# Création du ZIP pour RaPi only
# =========================================
if raspi_only_files:
    zip_buffer_raspi = BytesIO()
    with zipfile.ZipFile(zip_buffer_raspi, "w") as zf:
        for fname, fdata in raspi_only_files:
            zf.writestr(fname, fdata)
    st.download_button(
        label="Télécharger tous les résultats (RaPi only)",
        data=zip_buffer_raspi.getvalue(),
        file_name="results_raspi_only.zip",
        mime="application/zip"
    )

# =========================================
# Création du ZIP pour Extended
# =========================================
if extended_files:
    zip_buffer_ext = BytesIO()
    with zipfile.ZipFile(zip_buffer_ext, "w") as zf:
        for fname, fdata in extended_files:
            zf.writestr(fname, fdata)
    st.download_button(
        label="Télécharger tous les résultats (Extended)",
        data=zip_buffer_ext.getvalue(),
        file_name="results_extended.zip",
        mime="application/zip"
    )

    # =========================================
    # Tableau récapitulatif unique des Extended
    # =========================================
    recap_data = []

    for fname, fdata in extended_files:
        xls = pd.ExcelFile(BytesIO(fdata))

        df_co2 = pd.read_excel(xls, sheet_name="CO2_stats", index_col=0)
        df_pmean = pd.read_excel(xls, sheet_name="p_mean", index_col=0)
        df_vdot = pd.read_excel(xls, sheet_name="Vdot_stats", index_col=0)

        moyenne_co2 = df_co2.iloc[0, 0]   # B2
        max_co2 = df_co2.iloc[3, 0]       # B5
        dp1 = df_pmean.iloc[32, 2]        # C33
        vdot_gr = df_vdot.iloc[0, 2]      # C2

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
