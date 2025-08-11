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
    df_raw = pd.read_csv(csv_file, sep=",", header=0, index_col=0, engine='python') # read csv
    calib_corr_df = df_raw.loc["calibration correction mbar"]
    sensor_heights_df = df_raw.loc["sensor height"] # store height data
    df_data_raspi = df_raw.drop(labels=["sensor number","sensor range","sensor height","calibration correction mbar"], axis=0) # drop non-pressure rows

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
        # s'assurer que timestr est bien une chaîne de caractères
        timestr = str(timestr)
        # protéger si la structure n'a pas d'espace
        try:
            time_part = timestr.split(" ")[1]
        except IndexError:
            time_part = timestr  # si pas d'espace, on prend tout
        time_array[i] = sum([a*b for a,b in zip([3600,60,1], map(float,time_part.split(':')))])
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
        timestr = str(timestr)
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

st.header("Traitement multiple CFM avec gas analyser")

csv_files = st.file_uploader("Importer un ou plusieurs fichiers CSV (RaPi)", accept_multiple_files=True, type=['csv'])

log_file_gasMeas_CR = st.file_uploader("Importer fichier gas analyser CR (.log)", type=['log'])
log_file_gasMeas_GR = st.file_uploader("Importer fichier gas analyser GR (.log)", type=['log'])

timestamps_manual = st.checkbox("Définir manuellement start/end pour gas analyser", value=False)

if csv_files:
    
    # Préparation zip en mémoire
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        
        # Chargement des gaz analyzers (une fois, hors boucle)
        df_GM_CR_raw = None
        df_GM_GR_raw = None
        
        if log_file_gasMeas_CR is not None:
            try:
                # On parse les logs avec sep \s+ (espace multiple)
                df_GM_CR_raw = pd.read_csv(log_file_gasMeas_CR, sep=r"\s+", engine='python', header=0)
                # Extraction colonnes Time et Ch1:Conce:Vol%
                df_GM_CR_raw = df_GM_CR_raw[["Time", "Ch1:Conce:Vol%"]]
                df_GM_CR_raw.columns = ["t", "CO2"]
                # Convertir % en fraction
                df_GM_CR_raw["CO2"] = df_GM_CR_raw["CO2"] / 100
                df_GM_CR_raw["CO2"] = df_GM_CR_raw["CO2"].round(9)
            except Exception as e:
                st.error(f"Erreur lecture fichier gas analyser CR: {e}")

        if log_file_gasMeas_GR is not None:
            try:
                df_GM_GR_raw = pd.read_csv(log_file_gasMeas_GR, sep=r"\s+", engine='python', header=0)
                df_GM_GR_raw = df_GM_GR_raw[["Time", "Ch2:Conce:ppm"]]
                df_GM_GR_raw.columns = ["t", "CO2"]
                df_GM_GR_raw["CO2"] = pd.to_numeric(df_GM_GR_raw["CO2"], errors='coerce')  # forcer float, NaN si échec
                df_GM_GR_raw = df_GM_GR_raw.dropna(subset=["CO2"])  # supprimer lignes invalides
                df_GM_GR_raw["CO2"] = df_GM_GR_raw["CO2"] / 1e6
                df_GM_GR_raw["CO2"] = df_GM_GR_raw["CO2"].round(9)

            except Exception as e:
                st.error(f"Erreur lecture fichier gas analyser GR: {e}")

        # Traiter chaque fichier CSV RasPi
        for csv_file in csv_files:
            try:
                # Lire dataframe (en utilisant BytesIO)
                df_p, df_data_raspi = calc_mean_pressures(BytesIO(csv_file.getvalue()))
                df_data_raspi, df_Vdot_stats, df_Vdots = calc_Vdots_out(df_data_raspi)

                # Déterminer temps pour découpe gas analyser
                if timestamps_manual and (df_GM_GR_raw is not None or df_GM_CR_raw is not None):
                    t_start_str = st.text_input(f"Start-time pour {csv_file.name} (format hh:mm:ss)", value="", key=f"start_{csv_file.name}")
                    t_end_str = st.text_input(f"End-time pour {csv_file.name} (format hh:mm:ss)", value="", key=f"end_{csv_file.name}")
                    if t_start_str == "" or t_end_str == "":
                        st.warning(f"Merci de définir start et end time pour le fichier {csv_file.name}")
                        continue
                    t_start_tot = sum([a*b for a,b in zip([3600,60,1], map(float,t_start_str.split(':')))])
                    t_end_tot = sum([a*b for a,b in zip([3600,60,1], map(float,t_end_str.split(':')))])
                else:
                    t_start_tot = df_data_raspi.iloc[0]["t_tot"]
                    t_end_tot = df_data_raspi.iloc[-1]["t_tot"]

                # Extraction et stats gas analyser si disponibles
                df_GM_CR = None
                df_GM_GR = None
                
                if df_GM_CR_raw is not None:
                    df_GM_CR = extract_gasAnalyser_section(df_GM_CR_raw, t_start_tot, t_end_tot)
                    GM_CR_stats = calc_gasAnalyser_stats(df_GM_CR)
                else:
                    GM_CR_stats = None
                
                if df_GM_GR_raw is not None:
                    df_GM_GR = extract_gasAnalyser_section(df_GM_GR_raw, t_start_tot, t_end_tot)
                    GM_GR_stats = calc_gasAnalyser_stats(df_GM_GR)
                else:
                    GM_GR_stats = None
                
                # Création Excel dans mémoire
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_p.to_excel(writer, sheet_name="p_mean_press")
                    df_data_raspi.to_excel(writer, sheet_name="raspi_data")
                    df_Vdot_stats.to_excel(writer, sheet_name="Vdot_stats")
                    df_Vdots.to_excel(writer, sheet_name="Vdots")

                    if df_GM_CR is not None:
                        df_GM_CR.to_excel(writer, sheet_name="gasAnalyser_CR")
                    if df_GM_GR is not None:
                        df_GM_GR.to_excel(writer, sheet_name="gasAnalyser_GR")

                    # Statistiques gas analyser
                    if GM_CR_stats is not None:
                        df_stats_CR = pd.DataFrame([GM_CR_stats], columns=["mean", "std", "min", "max"], index=["CO2_CR"])
                        df_stats_CR.to_excel(writer, sheet_name="Stats_gasAnalyser_CR")

                    if GM_GR_stats is not None:
                        df_stats_GR = pd.DataFrame([GM_GR_stats], columns=["mean", "std", "min", "max"], index=["CO2_GR"])
                        df_stats_GR.to_excel(writer, sheet_name="Stats_gasAnalyser_GR")

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



