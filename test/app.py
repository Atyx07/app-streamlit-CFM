import numpy as np
import pandas as pd
import streamlit as st
from io import BytesIO
import zipfile

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
    df_GM = df_GM_raw[df_GM_raw["t_tot"] > t_start_tot]
    df_GM = df_GM[df_GM["t_tot"] < t_end_tot]
    return df_GM

def calc_gasAnalyser_stats(df_GM):
    CO2_mean = df_GM["CO2"].mean()
    CO2_std = df_GM["CO2"].std()
    CO2_min = df_GM["CO2"].min()
    CO2_max = df_GM["CO2"].max()
    return [CO2_mean, CO2_std, CO2_min, CO2_max]



st.header("CFM data processing")

csv_files_raspi = st.file_uploader("Import raw data (.csv RaPi)", type=["csv"], accept_multiple_files=True, key="upload_raspi_multi")
txt_files_gasMeas_CR = st.file_uploader("Import raw data from gas analyser (CR)", type=["txt"], accept_multiple_files=True, key="upload_gasAnal_CR_multi")
txt_files_gasMeas_GR = st.file_uploader("Import raw data from gas analyser (GR)", type=["txt"], accept_multiple_files=True, key="upload_gasAnal_GR_multi")

timestamps_manual = st.checkbox("Define end/start time manually (gas analyser data)", value=False)

if csv_files_raspi:
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for i, csv_file_raspi in enumerate(csv_files_raspi):
            df_p, df_data_raspi = calc_mean_pressures(csv_file_raspi)
            df_data_raspi, df_Vdot_stats, df_Vdots = calc_Vdots_out(df_data_raspi)

            # Préparation du fichier gas analyser associé, si possible
            gas_CR_file = txt_files_gasMeas_CR[i] if (txt_files_gasMeas_CR and i < len(txt_files_gasMeas_CR)) else None
            gas_GR_file = txt_files_gasMeas_GR[i] if (txt_files_gasMeas_GR and i < len(txt_files_gasMeas_GR)) else None
            
            gas_analyser_included = False
            if gas_CR_file and gas_GR_file:
                df_GM_CR_raw = pd.read_csv(gas_CR_file, sep="\t", header=0, index_col=None, engine='python')
                df_GM_CR_raw = df_GM_CR_raw[["Time", "Ch1:Conce:Vol%"]]
                df_GM_CR_raw.columns = ["t", "CO2"]
                df_GM_CR_raw["CO2"] = df_GM_CR_raw["CO2"]/100
                df_GM_CR_raw["CO2"] = df_GM_CR_raw["CO2"].round(9)

                df_GM_GR_raw = pd.read_csv(gas_GR_file, sep="\t", header=0, index_col=None, engine='python')
                df_GM_GR_raw = df_GM_GR_raw[["Time", "Ch2:Conce:ppm"]]
                df_GM_GR_raw.columns = ["t", "CO2"]
                df_GM_GR_raw["CO2"] = df_GM_GR_raw["CO2"]/(10**6)
                df_GM_GR_raw["CO2"] = df_GM_GR_raw["CO2"].round(9)

                if timestamps_manual:
                    t_start_str = st.text_input(f"Start-time for file {csv_file_raspi.name}", value=df_GM_GR_raw.iloc[20]["t"], key=f"starttime_{i}")
                    t_end_str = st.text_input(f"End-time for file {csv_file_raspi.name}", value=df_GM_GR_raw.iloc[-20]["t"], key=f"endtime_{i}")
                    t_start_tot = sum([a*b for a,b in zip([3600,60,1], map(float,t_start_str.split(':')))])
                    t_end_tot = sum([a*b for a,b in zip([3600,60,1], map(float,t_end_str.split(':')))])
                else:
                    t_start_tot = df_data_raspi.iloc[0]["t_tot"]
                    t_end_tot = df_data_raspi.iloc[-1]["t_tot"]

                df_GM_CR = extract_gasAnalyser_section(df_GM_CR_raw, t_start_tot, t_end_tot)
                df_GM_GR = extract_gasAnalyser_section(df_GM_GR_raw, t_start_tot, t_end_tot)

                CO2_stats_CR = calc_gasAnalyser_stats(df_GM_CR)
                CO2_stats_GR = calc_gasAnalyser_stats(df_GM_GR)

                df_CO2_out = pd.DataFrame(index=["mean", "std", "min", "max"])
                df_CO2_out["CR"] = CO2_stats_CR
                df_CO2_out["GR"] = CO2_stats_GR

                gas_analyser_included = True

            # Création Excel output
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')

            df_p.to_excel(writer, sheet_name="p_mean", float_format="%.5f", startrow=0, index=True)
            df_Vdot_stats.to_excel(writer, sheet_name="Vdot_stats", float_format="%.5f", startrow=0, index=True)
            df_Vdots.to_excel(writer, sheet_name="Vdot_raw", float_format="%.5f", startrow=0, index=True)
            df_data_raspi.to_excel(writer, sheet_name="RasPi", float_format="%.5f", startrow=0, index=True)

            if gas_analyser_included:
                df_CO2_out.to_excel(writer, sheet_name="GasAnalyser_CO2_Stats", float_format="%.9f", startrow=0, index=True)
                df_GM_CR.to_excel(writer, sheet_name="GasAnalyser_CR", float_format="%.9f", startrow=0, index=False)
                df_GM_GR.to_excel(writer, sheet_name="GasAnalyser_GR", float_format="%.9f", startrow=0, index=False)

            writer.close()

            zip_file.writestr(f'cfm_analysis_{csv_file_raspi.name.split(".")[0]}.xlsx', output.getvalue())

    zip_buffer.seek(0)
    st.download_button(
        label="Export all results as ZIP",
        data=zip_buffer,
        file_name="cfm_analysis_all_results.zip",
        mime="application/zip"
    )
