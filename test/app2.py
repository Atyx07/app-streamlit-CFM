# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 09:46:34 2025
Edited on Tue Aug 19 10:20:42 2025
@author: Gregor
Edited to to process multiple raspi files at once and give an Excel recap with CO2 mean, max, dp1, Vdot Mean
"""

import numpy as np
import pandas as pd
import streamlit as st
from io import BytesIO
import zipfile

# =========================
# Fonctions existantes
# =========================

def calc_mean_pressures(csv_file):
    df_raw = pd.read_csv(csv_file, sep=",", header=0, index_col=0, engine='python')
    calib_corr_df = df_raw.loc["calibration correction mbar"]
    sensor_heights_df = df_raw.loc["sensor height"]
    df_data_raspi = df_raw.drop(labels=["sensor number","sensor range","sensor height","calibration correction mbar"], axis=0)

    p_mean = df_data_raspi.mean().to_frame()
    p_std = df_data_raspi.std().to_frame()
    p_mean_not_corr = (df_data_raspi.mean()+calib_corr_df).to_frame()

    df_out = pd.merge(sensor_heights_df, p_mean, left_index=True, right_index=True)
    df_out = pd.merge(df_out, p_std, left_index=True, right_index=True)
    df_out = pd.merge(df_out, p_mean_not_corr, left_index=True, right_index=True)
    df_out.columns = ["h/m", "p_mean/mbar", "p_std/mbar", "p_mean_not_corr/mbar"]

    df_out["index"] = df_out.index
    df_out = df_out.drop(["gm_ZR", "gm_ZL"])
    df_out["sort1"] = df_out['index'].str.extract(r'([a-zA-Z]*)')
    df_out["sort2"] = df_out['index'].str.extract('(\d+)', expand=False).astype(int)
    df_out = df_out.sort_values(['sort1', 'sort2'], ascending=[True, True])
    df_out = df_out.drop(labels=["index","sort1","sort2"], axis=1)
    
    return df_out, df_data_raspi


def gm_signal_to_Vdot(time_array, signal_array):
    pulses = signal_array - np.roll(signal_array, 1)
    pulses_ind = np.where(pulses[1:] > 30)[0] + 1
    pulse_times = time_array[pulses_ind]
    pulse_dts = pulse_times[1:] - pulse_times[:-1]
    pulse_dt_glob = sum(pulse_dts)
    V_dots = (0.1 / pulse_dts * 3600)
    V_dot_mean = V_dots.mean()
    V_dot_std = V_dots.std()
    n_V_dot = V_dots.size
    V_dot_glob = len(pulse_dts) * 0.1 / pulse_dt_glob * 3600
    return V_dots, V_dot_mean, V_dot_std, n_V_dot, V_dot_glob


def calc_Vdots_out(df_in):
    time_array_str = list(df_in.index)
    time_array = np.zeros(len(time_array_str))
    for i,timestr in enumerate(time_array_str):
        time_array[i] = sum([a*b for a,b in zip([3600,60,1], map(float,timestr.split(" ")[1].split(':')))])
    df_in["t_tot"] = time_array
    time_array = time_array - time_array[0]
    df_in.index = time_array  
    df_out = df_in
    time_array = np.array(time_array)

    gm_zr_signal = np.array(list(df_out["gm_ZR"]))
    V_dots_CR, V_dot_CR_mean, V_dot_CR_std, n_V_dot_CR, V_dot_CR_glob = gm_signal_to_Vdot(time_array, gm_zr_signal)

    gm_zl_signal = np.array(list(df_out["gm_ZL"]))
    V_dots_GR, V_dot_GR_mean, V_dot_GR_std, n_V_dot_GR, V_dot_GR_glob = gm_signal_to_Vdot(time_array, gm_zl_signal)

    df_Vdot_stats = pd.DataFrame(index=['Vdot_mean / m^3/h', 'Vdot_std / m^3/h', 'n_V_dot / -', 'V_dot_glob / m^3/h'])
    df_Vdot_stats["CR"] = [V_dot_CR_mean, V_dot_CR_std, n_V_dot_CR, V_dot_CR_glob]
    df_Vdot_stats["GR"] = [V_dot_GR_mean, V_dot_GR_std, n_V_dot_GR, V_dot_GR_glob]

    df_V_dots = pd.DataFrame()
    df_V_dots["CR"] = V_dots_CR
    df_V_dots["GR"] = pd.Series(V_dots_GR)
    
    return df_out, df_Vdot_stats, df_V_dots


def extract_gasAnalyser_section(df_GM_raw, t_start_tot, t_end_tot):
    time_array_str = list(df_GM_raw["t"])
    time_array = np.zeros(len(time_array_str))
    for i,timestr in enumerate(time_array_str):
        time_array[i] = sum([a*b for a,b in zip([3600,60,1], map(float,timestr.split(':')))])
    df_GM_raw["t_tot"] = time_array
    df_GM = df_GM_raw[(df_GM_raw["t_tot"] > t_start_tot) & (df_GM_raw["t_tot"] < t_end_tot)]
    return df_GM


def calc_gasAnalyser_stats(df_GM):
    CO2_mean = df_GM["CO2"].mean()
    CO2_std = df_GM["CO2"].std()
    CO2_min = df_GM["CO2"].min()
    CO2_max = df_GM["CO2"].max()
    return [CO2_mean, CO2_std, CO2_min, CO2_max]


# =========================
# Streamlit App
# =========================

st.header("CFM data processing")

csv_files_raspi = st.file_uploader("Import raw data (.csv) from RaPi", accept_multiple_files=True)
txt_file_gasMeas_CR = st.file_uploader("Gas analyser CR", key="CR")
txt_file_gasMeas_GR = st.file_uploader("Gas analyser GR", key="GR")
timestamps_manual = st.checkbox("Define start/end time manually", value=False)

df_GM_CR_raw_global = None
df_GM_GR_raw_global = None

if txt_file_gasMeas_CR:
    df_GM_CR_raw_global = pd.read_csv(txt_file_gasMeas_CR, sep="\t", header=0, engine='python')
    df_GM_CR_raw_global = df_GM_CR_raw_global[["Time", "Ch1:Conce:Vol%"]]
    df_GM_CR_raw_global.columns = ["t", "CO2"]
    df_GM_CR_raw_global["CO2"] = (df_GM_CR_raw_global["CO2"]/100).round(9)

if txt_file_gasMeas_GR:
    df_GM_GR_raw_global = pd.read_csv(txt_file_gasMeas_GR, sep="\t", header=0, engine='python')
    df_GM_GR_raw_global = df_GM_GR_raw_global[["Time", "Ch2:Conce:ppm"]]
    df_GM_GR_raw_global.columns = ["t", "CO2"]
    df_GM_GR_raw_global["CO2"] = (df_GM_GR_raw_global["CO2"]/(10**6)).round(9)

t_start_tot_manual = None
t_end_tot_manual = None
if timestamps_manual and df_GM_GR_raw_global is not None and len(df_GM_GR_raw_global) >= 40:
    t_start_str = st.text_input("start-time", value=df_GM_GR_raw_global.iloc[20]["t"])
    t_end_str = st.text_input("end-time", value=df_GM_GR_raw_global.iloc[-20]["t"])
    t_start_tot_manual = sum([a*b for a,b in zip([3600,60,1], map(float,t_start_str.split(':')))])
    t_end_tot_manual = sum([a*b for a,b in zip([3600,60,1], map(float,t_end_str.split(':')))])

# =========================
# Traitement fichiers
# =========================

extended_files = []
recap_rows = []

if csv_files_raspi:
    for csv_file_raspi in csv_files_raspi:
        # 1) Calcul RaPi
        df_p, df_data_raspi = calc_mean_pressures(csv_file_raspi)
        df_data_raspi, df_Vdot_stats, df_Vdots = calc_Vdots_out(df_data_raspi)

        # 2) Extended (si gas analyser dispo)
        if (df_GM_CR_raw_global is not None) or (df_GM_GR_raw_global is not None):
            if timestamps_manual and (t_start_tot_manual is not None) and (t_end_tot_manual is not None):
                t_start_tot, t_end_tot = t_start_tot_manual, t_end_tot_manual
            else:
                t_start_tot, t_end_tot = df_data_raspi.iloc[0]["t_tot"], df_data_raspi.iloc[-1]["t_tot"]

            GM_stats_dict = {}
            df_GM_CR_section, df_GM_GR_section = None, None

            if df_GM_CR_raw_global is not None:
                df_GM_CR_section = extract_gasAnalyser_section(df_GM_CR_raw_global.copy(), t_start_tot, t_end_tot)
                GM_stats_dict["CR"] = calc_gasAnalyser_stats(df_GM_CR_section)
            if df_GM_GR_raw_global is not None:
                df_GM_GR_section = extract_gasAnalyser_section(df_GM_GR_raw_global.copy(), t_start_tot, t_end_tot)
                GM_stats_dict["GR"] = calc_gasAnalyser_stats(df_GM_GR_section)

            if GM_stats_dict:
                df_GM_stats = pd.DataFrame(GM_stats_dict, index=['CO2_mean / mol/mol', 'CO2_std / mol/mol', 'CO2_min / mol/mol', 'CO2_max / mol/mol'])

                output_ext = BytesIO()
                writer = pd.ExcelWriter(output_ext, engine='xlsxwriter')
                df_p.to_excel(writer, sheet_name="p_mean")
                df_Vdot_stats.to_excel(writer, sheet_name="Vdot_stats")
                df_Vdots.to_excel(writer, sheet_name="Vdot_raw")
                df_GM_stats.to_excel(writer, sheet_name="CO2_stats")
                if df_GM_CR_section is not None: df_GM_CR_section.to_excel(writer, sheet_name="CO2_CR")
                if df_GM_GR_section is not None: df_GM_GR_section.to_excel(writer, sheet_name="CO2_GR")
                df_data_raspi.to_excel(writer, sheet_name="RasPi")
                writer.close()
                extended_files.append((f'cfm_analysis_extended_{csv_file_raspi.name.split(".")[0]}.xlsx', output_ext.getvalue()))

                # ==== Construction recap selon consignes ====
                # Nom fichier
                nom_fichier = f'cfm_analysis_extended_{csv_file_raspi.name.split(".")[0]}'

                # Moyenne CO2 = B2 (ligne 1, col 0)
                co2_mean = df_GM_stats.iloc[0,0]
                co2_max = df_GM_stats.iloc[3,0]   # B5 (ligne 4, col 1)
                dp1 = df_p.iloc[31,1]             # C33 (ligne 32, col 2)
                debit_vol_GR = df_Vdot_stats.iloc[0,1]  # C2 (ligne 1, col 2)

                recap_rows.append({
                    "File name": nom_fichier,
                    "CO2 Mean": co2_mean,
                    "CO2 Max": co2_max,
                    "dp1": dp1,
                    "Vdot GR Mean": debit_vol_GR
                })

# =========================
# Téléchargements
# =========================

# 1) Zip fichiers
if extended_files:
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for fname, fdata in extended_files:
            zip_file.writestr(fname, fdata)

    st.download_button(
        label="⬇ Download all files Extended (zip)",
        data=zip_buffer.getvalue(),
        file_name="extended_files.zip",
        mime="application/zip"
    )

# 2) Fichier récapitulatif unique
if recap_rows:
    df_recap = pd.DataFrame(recap_rows)
    recap_output = BytesIO()
    df_recap.to_excel(recap_output, index=False, sheet_name="Récapitulatif")
    
    st.download_button(
        label="⬇ Download the global recap file",
        data=recap_output.getvalue(),
        file_name="recapitulatif_global.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
