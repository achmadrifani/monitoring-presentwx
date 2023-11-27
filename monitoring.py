import streamlit as st
# from streamlit_folium import st_folium
import pandas as pd
import altair as alt
from ftplib import FTP
from datetime import datetime, timedelta
import json

FTP_CONFIG = {"host":"publik.bmkg.go.id","username":"amandemen","password":"bmkg2303"}
st.set_page_config(layout="wide")

def retrieve_file_dates():
    ftp = FTP(FTP_CONFIG["host"])
    ftp.login(FTP_CONFIG["username"], FTP_CONFIG["password"])
    ftp.cwd("data/status")
    file_list = []
    date_list = []
    search_pattern = "present_weather_status_*.json"
    ftp.retrlines(f"LIST {search_pattern}", file_list.append)
    for file in file_list:
        date_part = file.split("_")[3]
        date = datetime.strptime(date_part,"%Y%m%d.json")
        date_list.append(date)
    return date_list


def retrieve_prov_list():
    ftp = FTP(FTP_CONFIG["host"])
    ftp.login(FTP_CONFIG["username"], FTP_CONFIG["password"])
    ftp.cwd("data/eval")
    file_list = []
    prov_list = []
    search_pattern = "eval-presentweather-*.csv"
    ftp.retrlines(f"LIST {search_pattern}", file_list.append)
    for file in file_list:
        prov_part = file.split("-")[8]
        prov = prov_part.split(".")[0]
        prov_list.append(prov)
    return prov_list


def retrieve_logs_list():
    ftp = FTP(FTP_CONFIG["host"])
    ftp.login(FTP_CONFIG["username"], FTP_CONFIG["password"])
    ftp.cwd("data/status/log")
    # Dapatkan daftar file dalam direktori
    files = ftp.nlst()

    # Buat daftar file beserta timestamp mtime
    file_mtime_list = []
    for file in files[2:]:
        mtime = ftp.sendcmd('MDTM ' + file)  # Dapatkan mtime dari server FTP
        mtime = datetime.strptime(mtime[4:], '%Y%m%d%H%M%S')  # Konversi ke objek datetime
        file_mtime_list.append((file, mtime))

    # Urutkan daftar berdasarkan mtime
    file_mtime_list.sort(key=lambda x: x[1], reverse=True)

    # Ambil 10 file terakhir
    last_10_files = [file for file, mtime in file_mtime_list[:10]]


    return last_10_files

def get_log_file(log_file):
    ftp = FTP(FTP_CONFIG["host"])
    ftp.login(FTP_CONFIG["username"], FTP_CONFIG["password"])
    ftp.cwd("data/status/log")
    with open("log.txt", 'wb') as local_file:
        ftp.retrbinary('RETR ' + log_file, local_file.write)
    with open("log.txt", 'r') as file:
        file_content = file.read()

    return file_content

def highlight_done(s):
    styles = []
    for value in s:
        if value == 'done':
            styles.append('background-color: lightblue')
        elif value == 'failed':
            styles.append('background-color: lightcoral')
        else:
            styles.append('')
    return styles

def get_file(date):
    ftp = FTP(FTP_CONFIG["host"])
    ftp.login(FTP_CONFIG["username"], FTP_CONFIG["password"])
    ftp.cwd("data/status")
    file_name = f"present_weather_status_{date:%Y%m%d}.json"

    # Mengunduh file JSON ke sistem lokal
    with open("status_file.json", 'wb') as local_file:
        ftp.retrbinary('RETR ' + file_name, local_file.write)

    # Sekarang Anda memiliki file JSON di sistem lokal yang dapat Anda baca seperti ini:
    with open("status_file.json", 'r') as json_file:
        data = json.load(json_file)

    df = pd.json_normalize(data)
    df = df.rename(columns={"task_duration.start": "start", "task_duration.duration": "duration",
                            "task_duration.radar_time":"radar_time UTC",
                            "task_duration.sat_time": "sat_time UTC",
                            "task_duration.status":"status",
                            "task_duration.error_msg":"error_msg"})

    # Mengganti format string kolom "start" menjadi objek datetime
    df['start'] = pd.to_datetime(df['start'])
    df['radar_time UTC'] = pd.to_datetime((df['radar_time UTC'])).dt.strftime("%H:%M")
    try:
        df['sat_time UTC'] = pd.to_datetime((df['sat_time UTC'])).dt.strftime("%H:%M")
    except KeyError:
        pass


    # Mengganti format string kolom "duration" menjadi objek timedelta
    df['duration'] = df['duration'].apply(lambda x: pd.to_timedelta(x))
    df['duration'] = (df['duration'].dt.total_seconds() / 60).round(1)

    df['end'] = df['start'] + pd.to_timedelta(df['duration'], unit='m')
    df['start'] = df['start'].dt.strftime("%H:%M")
    df['end'] = df['end'].dt.strftime("%H:%M")
    try:
        df = df[['start','end','duration','status','radar_time UTC','sat_time UTC','error_msg']]
    except KeyError:
        df = df[['start', 'end', 'duration', 'status', 'radar_time UTC']]
    df = df.sort_values(by='start', ascending=True)
    df_style = df.style.apply(highlight_done, subset=['status'])
    return df, df_style

def make_bar_plot(df):
    bars = alt.Chart(df.reset_index()).mark_bar().encode(
        x=alt.X('index:N', axis=alt.Axis(title='Task Number')),
        y=alt.Y('duration:Q', axis=alt.Axis(title='Duration (mins)')),
        color=alt.Color('status:N', scale=alt.Scale(domain=['failed', 'done'], range=['red', 'blue']),
                        legend=alt.Legend(title='Status')),
        tooltip=[alt.Tooltip('start:N', title='Start'), 'duration:Q', 'status:N', 'error_message:N']
    ).properties(
        width=650,
        height=300
    )

    return bars


def get_prov_df(prov):
    ftp = FTP(FTP_CONFIG["host"])
    ftp.login(FTP_CONFIG["username"], FTP_CONFIG["password"])
    ftp.cwd("data/eval")
    file_name = f"eval-presentweather-{prov}.csv"

    with open(f"{prov}.csv", 'wb') as local_file:
        ftp.retrbinary('RETR ' + file_name, local_file.write)

    df = pd.read_csv(f"{prov}.csv",sep=";")
    try:
        df = df[["AREA_ID","DATE","KEC","WEATHER","CMAX","LDN"]]
    except KeyError:
        try:
            df = df[["AREA_ID", "DATE", "KEC", "WEATHER", "RR"]]
        except KeyError:
            return df
    return df

def calculate_metrics(df):
    total_data = len(df)
    done_count = df['status'].value_counts().get('done', 0)
    fail_count = df['status'].value_counts().get('failed', 0)
    pdone = (done_count / total_data) * 100 if total_data > 0 else 0
    return total_data,done_count,fail_count,pdone


st.header("Monitoring Present Weather Run")


tab1,tab2 = st.tabs(["Run Monitor","Data Monitor"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        date_select = st.selectbox('Tanggal',retrieve_file_dates(),index=None, placeholder="Pilih Tanggal ...")
        if date_select is not None:
            df, df_style = get_file(date_select)
            bars = make_bar_plot(df)
            total_data, done_count, fail_count, pdone = calculate_metrics(df)
            col11,col12,col13,col14 = st.columns(4)
            col11.metric("Total Task", total_data)
            col12.metric("Done", done_count)
            col13.metric("Failed", fail_count)
            col14.metric("% Done", value=f"{pdone.round(1)}%")
            st.write(bars)
            st.dataframe(df_style,use_container_width=True)

    with col2:
        log_select = st.selectbox("File Log Terakhir", retrieve_logs_list(), index=None, placeholder="Pilih Log ...")
        if log_select is not None:
            log_content = get_log_file(log_select)
            st.text_area("LOGS", log_content, height=700)

with tab2:
    col3,col4 = st.columns([0.2,0.8])
    with col3:
        prov_select = st.selectbox('Evaluasi Present Wx', retrieve_prov_list(), index=None, placeholder="Pilih Provinsi ...")
    with col4:
        if prov_select is not None:
            df_eval = get_prov_df(prov_select)
            st.dataframe(df_eval)

