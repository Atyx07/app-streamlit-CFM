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

# --- Fonctions de calcul ---

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
    
    df_Vdot_stats = pd.DataFrame(index =['Vdot_mean / m^3/h', 'Vdot_std / m^3/h', 'n_V_dot / -', 'V_dot_glob / m^3/h'])
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


# --- Interface Streamlit ---

st.header("Traitement multiple CFM avec gas analyser (fichier .log)")

csv_files = st.file_uploader("Importer un ou plusieurs fichiers CSV (RaPi)", accept_multiple_files=True, type=['csv'])

log_file_gasMeas = st.file_uploader("Importer fichier gas analyser (.log)", type=['log', 'txt'])

timestamps_manual = st.checkbox("Définir manuellement start/end pour gas analyser", value=False)

if csv_files:

    # Préparation du zip en mémoire
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        
        df_GM_raw = None
        if log_file_gasMeas is not None:
            try:
                # Lecture du fichier log gas analyser
                # On essaye d'abord sep='\t', sinon sep=' ' (espace multiple)
                try:
                    df_GM_raw = pd.read_csv(log_file_gasMeas, sep='\t', engine='python')
                except Exception:
                    log_file_gasMeas.seek(0)
                    df_GM_raw = pd.read_csv(log_file_gasMeas, delim_whitespace=True, engine='python')

                # On vérifie les colonnes : il faut au moins 'Time' et une colonne CO2 (ex: 'CO2', 'Concentration' etc)
                # Adaptation possible selon ton fichier, ici on cherche une colonne avec "CO2" dans son nom
                co2_cols = [col for col in df_GM_raw.columns if "CO2" in col.upper()]
                if len(co2_cols) == 0:
                    st.warning("Le fichier gas analyser ne contient pas de colonne CO2 reconnue.")
                    df_GM_raw = None
                else:
                    # Renommer colonnes pour uniformiser
                    df_GM_raw = df_GM_raw.rename(columns={co2_cols[0]: "CO2"})
                    if "Time" not in df_GM_raw.columns:
                        st.warning("Le fichier gas analyser ne contient pas de colonne 'Time' reconnue.")
                        df_GM_raw = None
                    else:
                        # Convertir CO2 en fraction (si c’est en %, diviser par 100)
                        if df_GM_raw["CO2"].max() > 10:
                            df_GM_raw["CO2"] = df_GM_raw["CO2"] / 100
                        df_GM_raw["CO2"] = df_GM_raw["CO2"].round(9)
                        df_GM_raw["t"] = df_GM_raw["Time"].astype(str)
                        df_GM_raw = df_GM_raw[["t","CO2"]]
            except Exception as e:
                st.warning(f"Erreur lecture fichier gas analyser: {e}")
                df_GM_raw = None

        for csv_file in csv_files:
            try:
                df_p, df_data_raspi = calc_mean_pressures(BytesIO(csv_file.getvalue()))
                df_data_raspi, df_Vdot_stats, df_Vdots = calc_Vdots_out(df_data_raspi)

                # Temps pour découpe gas analyser
                if timestamps_manual and df_GM_raw is not None:
                    t_start_str = st.text_input(f"Start-time pour {csv_file.name}", value=None, key=f"start_{csv_file.name}")
                    t_end_str = st.text_input(f"End-time pour {csv_file.name}", value=None, key=f"end_{csv_file.name}")
                    if (not t_start_str) or (not t_end_str):
                        st.warning(f"Merci de définir start et end time pour {csv_file.name}")
                        continue
                    t_start_tot = sum([a*b for a,b in zip([3600,60,1], map(float,t_start_str.split(':')))])
                    t_end_tot = sum([a*b for a,b in zip([3600,60,1], map(float,t_end_str.split(':')))])
                else:
                    t_start_tot = df_data_raspi.iloc[0]["t_tot"]
                    t_end_tot = df_data_raspi.iloc[-1]["t_tot"]

                # Extraction et stats gas analyser si présent
                if df_GM_raw is not None:
                    df_GM = extract_gasAnalyser_section(df_GM_raw, t_start_tot, t_end_tot)
                    GM_stats = calc_gasAnalyser_stats(df_GM)
                else:
                    df_GM = None
                    GM_stats = None

                # Création Excel en mémoire
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_p.to_excel(writer, sheet_name="p_mean_press")
                    df_data_raspi.to_excel(writer, sheet_name="raspi_data")
                    df_Vdot_stats.to_excel(writer, sheet_name="Vdot_stats")
                    df_Vdots.to_excel(writer, sheet_name="Vdots")

                    if df_GM is not None:
                        df_GM.to_excel(writer, sheet_name="gasAnalyser")

                    if GM_stats is not None:
                        df_stats = pd.DataFrame([GM_stats], columns=["mean", "std", "min", "max"], index=["CO2"])
                        df_stats.to_excel(writer, sheet_name="Stats_gasAnalyser")

                output.seek(0)
                zipf.writestr(f"results_{csv_file.name.split('.')[0]}.xlsx", output.read())

            except Exception as e:
                st.error(f"Erreur traitement fichier {csv_file.name}: {e}")

    st.download_button(
        label="Télécharger tous les résultats en ZIP",
        data=zip_buffer.getvalue(),
        file_name="resultats_cfm.zip",
        mime="application/zip"
    )
