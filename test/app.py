# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 09:46:34 2025
Edited on Wed Aug 13 09:23:44 2025
@author: Gregor
Edited to to process multiple raspi files at once
"""

import numpy as np
import pandas as pd
import streamlit as st
from io import BytesIO
import zipfile


# =========================
# Existing functions (unchanged)
# =========================

def calc_mean_pressures(csv_file):
    df_raw = pd.read_csv(csv_file, sep=",", header=0, index_col=0, engine='python') # read csv
    calib_corr_df = df_raw.loc["calibration correction mbar"]
    sensor_heights_df = df_raw.loc["sensor height"] # store height data
    df_data_raspi = df_raw.drop(labels=["sensor number","sensor range","sensor height","calibration correction mbar"], axis=0) # drop non-pressure rows

    # calculate mean values of pressure values and convert to df
    p_mean = df_data_raspi.mean().to_frame() # mean values of measured an corrected (auto calib) values
    p_std = df_data_raspi.std().to_frame() # mean values of measured an corrected (auto calib) values
    p_mean_not_corr = (df_data_raspi.mean()+calib_corr_df).to_frame() # mean values of measured values (not corrected)

    # merge dfs
    df_out = pd.merge(sensor_heights_df, p_mean, left_index=True, right_index=True) # add heights
    df_out = pd.merge(df_out, p_std, left_index=True, right_index=True) # add std
    df_out = pd.merge(df_out, p_mean_not_corr, left_index=True, right_index=True) # add calib corr
    df_out.columns = ["h/m", "p_mean/mbar", "p_std/mbar", "p_mean_not_corr/mbar"]
    # sort according to name
    df_out["index"] = df_out.index
    df_out = df_out.drop(["gm_ZR", "gm_ZL"])
    df_out["sort1"] = df_out['index'].str.extract(r'([a-zA-Z]*)')
    df_out["sort2"] = df_out['index'].str.extract('(\d+)', expand=False).astype(int)
    df_out = df_out.sort_values(['sort1', 'sort2'], ascending=[True, True])
    df_out = df_out.drop(labels=["index","sort1","sort2"], axis=1)
    
    return df_out, df_data_raspi


def gm_signal_to_Vdot(time_array, signal_array):
    pulses = signal_array - np.roll(signal_array, 1) # extract signal changes (pulses)
    pulses_ind = np.where(pulses[1:] > 30)[0] + 1 # extract indexes of positive (ramp-up) signal changes
    pulse_times = time_array[pulses_ind] # get timestamps from pulses
    pulse_dts = pulse_times[1:] - pulse_times[:-1] # get time intervals between pulses
    pulse_dt_glob = sum(pulse_dts) # get time intervall between first and last pulse
    V_dots = (0.1 / pulse_dts * 3600) # V_dot measurements (m^3/h) from pulses
    V_dot_mean = V_dots.mean() # mean V_dot (m^3/h) from pulses
    V_dot_std = V_dots.std() # std from V_dots (m^3/h)
    n_V_dot = V_dots.size # number of V_dot measurements
    V_dot_glob = len(pulse_dts) * 0.1 / pulse_dt_glob * 3600 # mean V_dot (m^3/h) from first and last pulse
    return V_dots, V_dot_mean, V_dot_std, n_V_dot, V_dot_glob
    


def calc_Vdots_out(df_in):
    # adjust timestamps (index of df_in) to start with 0
    time_array_str = list(df_in.index)
    time_array = np.zeros(len(time_array_str))
    for i,timestr in enumerate(time_array_str):
        time_array[i] = sum([a*b for a,b in zip([3600,60,1], map(float,timestr.split(" ")[1].split(':')))])
    df_in["t_tot"] = time_array
    time_array = time_array-time_array[0]
    df_in.index = time_array  
    df_out = df_in
    time_array = np.array(time_array)
    
    # gm ZR
    gm_zr_signal = np.array(list(df_out["gm_ZR"])) # signal
    V_dots_CR, V_dot_CR_mean, V_dot_CR_std, n_V_dot_CR, V_dot_CR_glob = gm_signal_to_Vdot(time_array, gm_zr_signal)
    
    # gm ZL
    gm_zl_signal = np.array(list(df_out["gm_ZL"])) # signal
    V_dots_GR, V_dot_GR_mean, V_dot_GR_std, n_V_dot_GR, V_dot_GR_glob = gm_signal_to_Vdot(time_array, gm_zl_signal) 
    # stats dataframe
    df_Vdot_stats = pd.DataFrame(index =['Vdot_mean / m^3/h', 'Vdot_std / m^3/h', 'n_V_dot / -', 'V_dot_glob / m^3/h'])
    df_Vdot_stats["CR"] = [V_dot_CR_mean, V_dot_CR_std, n_V_dot_CR, V_dot_CR_glob]
    df_Vdot_stats["GR"] = [V_dot_GR_mean, V_dot_GR_std, n_V_dot_GR, V_dot_GR_glob]
    # all Vdots dataframe
    df_V_dots = pd.DataFrame()
    df_V_dots["CR"] = V_dots_CR
    df_V_dots["GR"] = pd.Series(V_dots_GR)
    
    return df_out, df_Vdot_stats, df_V_dots


def extract_gasAnalyser_section(df_GM_raw, t_start_tot, t_end_tot):
    time_array_str = list(df_GM_raw["t"])
    time_array = np.zeros(len(time_array_str))
    for i,timestr in enumerate(time_array_str):
        time_array[i] = sum([a*b for a,b in zip([3600,60,1], map(float,timestr.split(':')))])
    # time_array = time_array-time_array[0]
    df_GM_raw["t_tot"] = time_array
    df_GM = df_GM_raw[df_GM_raw["t_tot"] > t_start_tot]
    df_GM = df_GM[df_GM["t_tot"] < t_end_tot]
    
    return df_GM


def calc_gasAnalyser_stats(df_GM):
    CO2_mean = df_GM["CO2"].mean()
    CO2_std = df_GM["CO2"].std()
    CO2_min = df_GM["CO2"].min()
    CO2_max = df_GM["CO2"].max()
    return [CO2_mean, CO2_std, CO2_min, CO2_max]


# =========================
# Streamlit Application (multi-CSV + ZIP)
# =========================

st.header("CFM data processing")

# --- Uploader MULTI-CSV (multiple files) ---
csv_files_raspi = st.file_uploader(
    "Import raw data (.csv-export file from RaPi)",
    key="upload_raspi_multi",
    accept_multiple_files=True
)

# --- logs upload (unique, used for ALL CSV) ---
txt_file_gasMeas_CR = st.file_uploader("Import raw data from gas analyser (CR)", key="upload_gasAnal_CR")
txt_file_gasMeas_GR = st.file_uploader("Import raw data from gas analyser (GR)", key="upload_gasAnal_GR")
timestamps_manual = st.checkbox("Define end - and start-time manually (for gas analyser data extraction)", value=False)

# Read logs only once (otherwise, in a loop, file pointers arrive at the end of the file)
df_GM_CR_raw_global = None
df_GM_GR_raw_global = None

if txt_file_gasMeas_CR is not None:
    df_GM_CR_raw_global = pd.read_csv(txt_file_gasMeas_CR, sep="\t", header=0, index_col=None, engine='python') # read txt
    df_GM_CR_raw_global = df_GM_CR_raw_global[["Time", "Ch1:Conce:Vol%"]]
    df_GM_CR_raw_global.columns = ["t", "CO2"]
    df_GM_CR_raw_global["CO2"] = df_GM_CR_raw_global["CO2"]/100
    df_GM_CR_raw_global["CO2"] = df_GM_CR_raw_global["CO2"].round(9)

if txt_file_gasMeas_GR is not None:
    df_GM_GR_raw_global = pd.read_csv(txt_file_gasMeas_GR, sep="\t", header=0, index_col=None, engine='python') # read txt
    df_GM_GR_raw_global = df_GM_GR_raw_global[["Time", "Ch2:Conce:ppm"]]
    df_GM_GR_raw_global.columns = ["t", "CO2"]
    df_GM_GR_raw_global["CO2"] = df_GM_GR_raw_global["CO2"]/(10**6)
    df_GM_GR_raw_global["CO2"] = df_GM_GR_raw_global["CO2"].round(9)

# If manual timestamps are requested, enter them here (default values as in your code: lines 20 and -20 of the GR)
t_start_tot_manual = None
t_end_tot_manual = None
if timestamps_manual and df_GM_GR_raw_global is not None and len(df_GM_GR_raw_global) >= 40:
    t_start_str = st.text_input("start-time", value=df_GM_GR_raw_global.iloc[20]["t"])
    t_end_str = st.text_input("end-time", value=df_GM_GR_raw_global.iloc[-20]["t"])
    t_start_tot_manual = sum([a*b for a,b in zip([3600,60,1], map(float,t_start_str.split(':')))])
    t_end_tot_manual = sum([a*b for a,b in zip([3600,60,1], map(float,t_end_str.split(':')))])

# Containers to group Excel files by type
raspi_only_files = []
extended_files = []

# --- Multi-CSV processing ---
if csv_files_raspi:
    for csv_file_raspi in csv_files_raspi:

        # ========== 1) "RaPi only" calculation (identical to the original) ==========
        df_p, df_data_raspi = calc_mean_pressures(csv_file_raspi)
        df_data_raspi, df_Vdot_stats, df_Vdots = calc_Vdots_out(df_data_raspi)

        # Excel RaPi creation only (identical sheets)
        output_raspi = BytesIO()
        writer = pd.ExcelWriter(output_raspi, engine = 'xlsxwriter')
        df_p.to_excel(writer, sheet_name="p_mean", float_format="%.5f", startrow=0, index=True)
        df_Vdot_stats.to_excel(writer, sheet_name="Vdot_stats", float_format="%.5f", startrow=0, index=True)
        df_Vdots.to_excel(writer, sheet_name="Vdot_raw", float_format="%.5f", startrow=0, index=True)
        df_data_raspi.to_excel(writer, sheet_name="RasPi", float_format="%.5f", startrow=0, index=True)
        writer.close()
        raspi_only_files.append((f'cfm_analysis_{csv_file_raspi.name.split(".")[0]}.xlsx', output_raspi.getvalue()))

        # ========== 2) "Extended" calculation (identical to the original) ==========
        # Cas CR + GR
        if (df_GM_CR_raw_global is not None) and (df_GM_GR_raw_global is not None):
            if timestamps_manual and (t_start_tot_manual is not None) and (t_end_tot_manual is not None):
                t_start_tot = t_start_tot_manual
                t_end_tot = t_end_tot_manual
            else:
                t_start_tot = df_data_raspi.iloc[0]["t_tot"]
                t_end_tot = df_data_raspi.iloc[-1]["t_tot"]

            df_GM_CR = extract_gasAnalyser_section(df_GM_CR_raw_global.copy(), t_start_tot, t_end_tot)
            df_GM_GR = extract_gasAnalyser_section(df_GM_GR_raw_global.copy(), t_start_tot, t_end_tot)

            GM_CR_stats = calc_gasAnalyser_stats(df_GM_CR)
            GM_GR_stats = calc_gasAnalyser_stats(df_GM_GR)
            df_GM_stats = pd.DataFrame(index =['CO2_mean / mol/mol', 'CO2_std / mol/mol', 'CO2_min / mol/mol', 'CO2_max / mol/mol'])
            df_GM_stats["CR"] = GM_CR_stats
            df_GM_stats["GR"] = GM_GR_stats

            output_ext = BytesIO()
            writer = pd.ExcelWriter(output_ext, engine = 'xlsxwriter')
            df_p.to_excel(writer, sheet_name="p_mean", float_format="%.5f", startrow=0, index=True)
            df_Vdot_stats.to_excel(writer, sheet_name="Vdot_stats", float_format="%.5f", startrow=0, index=True)
            df_Vdots.to_excel(writer, sheet_name="Vdot_raw", float_format="%.5f", startrow=0, index=True)
            df_GM_stats.to_excel(writer, sheet_name="CO2_stats", float_format="%.9f", startrow=0, index=True)
            df_GM_CR.to_excel(writer, sheet_name="CO2_CR", float_format="%.9f", startrow=0, index=True)
            df_GM_GR.to_excel(writer, sheet_name="CO2_GR", float_format="%.9f", startrow=0, index=True)
            df_data_raspi.to_excel(writer, sheet_name="RasPi", float_format="%.5f", startrow=0, index=True)
            writer.close()
            extended_files.append((f'cfm_analysis_extended_{csv_file_raspi.name.split(".")[0]}.xlsx', output_ext.getvalue()))

        #GR case only (identical to the original)
        elif (df_GM_CR_raw_global is None) and (df_GM_GR_raw_global is not None):
            if timestamps_manual and (t_start_tot_manual is not None) and (t_end_tot_manual is not None):
                t_start_tot = t_start_tot_manual
                t_end_tot = t_end_tot_manual
            else:
                t_start_tot = df_data_raspi.iloc[0]["t_tot"]
                t_end_tot = df_data_raspi.iloc[-1]["t_tot"]

            df_GM_GR = extract_gasAnalyser_section(df_GM_GR_raw_global.copy(), t_start_tot, t_end_tot)

            GM_GR_stats = calc_gasAnalyser_stats(df_GM_GR)
            df_GM_stats = pd.DataFrame(index =['CO2_mean / mol/mol', 'CO2_std / mol/mol', 'CO2_min / mol/mol', 'CO2_max / mol/mol'])
            df_GM_stats["GR"] = GM_GR_stats

            output_ext = BytesIO()
            writer = pd.ExcelWriter(output_ext, engine = 'xlsxwriter')
            df_p.to_excel(writer, sheet_name="p_mean", float_format="%.5f", startrow=0, index=True)
            df_Vdot_stats.to_excel(writer, sheet_name="Vdot_stats", float_format="%.5f", startrow=0, index=True)
            df_Vdots.to_excel(writer, sheet_name="Vdot_raw", float_format="%.5f", startrow=0, index=True)
            df_GM_stats.to_excel(writer, sheet_name="CO2_stats", float_format="%.9f", startrow=0, index=True)
            df_GM_GR.to_excel(writer, sheet_name="CO2_GR", float_format="%.9f", startrow=0, index=True)
            df_data_raspi.to_excel(writer, sheet_name="RasPi", float_format="%.5f", startrow=0, index=True)
            writer.close()
            extended_files.append((f'cfm_analysis_extended_{csv_file_raspi.name.split(".")[0]}.xlsx', output_ext.getvalue()))

        # If CR alone without GR -> no extended (unchanged behavior with respect to your code)
        # Minimal display (optional)
        st.dataframe(df_p)
        st.dataframe(df_Vdot_stats)

# ------------------------
# ZIP Download
# ------------------------
if raspi_only_files:
    zip_buffer_raspi = BytesIO()
    with zipfile.ZipFile(zip_buffer_raspi, "w") as zf:
        for fname, fdata in raspi_only_files:
            zf.writestr(fname, fdata)
    st.download_button(
        label="Download all the results (RasPi seul)",
        data=zip_buffer_raspi.getvalue(),
        file_name="results_raspi_only.zip",
        mime="application/zip"
    )

if extended_files:
    zip_buffer_ext = BytesIO()
    with zipfile.ZipFile(zip_buffer_ext, "w") as zf:
        for fname, fdata in extended_files:
            zf.writestr(fname, fdata)
    st.download_button(
        label="Download all the results (étendu)",
        data=zip_buffer_ext.getvalue(),
        file_name="results_extended.zip",
        mime="application/zip"
    )


