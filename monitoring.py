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
                            "task_duration.radar_time":"radar_time",
                            "task_duration.status":"status",
                            "task_duration.error_msg":"error_message"})

    # Mengganti format string kolom "start" menjadi objek datetime
    df['start'] = pd.to_datetime(df['start'])

    # Mengganti format string kolom "duration" menjadi objek timedelta
    df['duration'] = df['duration'].apply(lambda x: pd.to_timedelta(x))
    df['duration'] = (df['duration'].dt.total_seconds() / 60).round(1)

    return df

def make_bar_plot(df):
    bars = alt.Chart(df).mark_bar().encode(
        x=alt.X('start:T', axis=alt.Axis(title='Start Time', format='%H:%M')),
        y=alt.Y('duration:Q', axis=alt.Axis(title='Duration (mins)')),
        color=alt.Color('status:N', scale=alt.Scale(domain=['failed', 'done'], range=['red', 'blue']),
                        legend=alt.Legend(title='Status')),
        tooltip=[alt.Tooltip('start:T', title='Start', format='%H:%M'), 'duration:Q', 'status:N', 'error_message:N']
    ).properties(
        width=650,
        height=300
    )

    return bars


st.header("Monitoring Present Weather Run")

col1,col2 = st.columns(2)

with col1:
    date_select = st.selectbox('Tanggal',retrieve_file_dates(),index=None, placeholder="Pilih Tanggal ...")
    if date_select is not None:
        df = get_file(date_select)
        bars = make_bar_plot(df)
        st.write(bars)
        st.dataframe(df,use_container_width=True)

with col2:
    log_select = st.selectbox("File Log Terakhir", retrieve_logs_list(),index=None, placeholder="Pilih Log ...")
    if log_select is not None:
        log_content = get_log_file(log_select)
        st.text_area("LOGS",log_content, height=700)