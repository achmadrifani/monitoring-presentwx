import streamlit as st
# from streamlit_folium import st_folium
import pandas as pd
import altair as alt
from ftplib import FTP
from datetime import datetime, timedelta
import json

FTP_CONFIG = {"host":"publik.bmkg.go.id","username":"situs","password":"bmkg2303"}
st.set_page_config(layout="wide")

def retrieve_files_in_ftp():
    ftp = FTP(FTP_CONFIG["host"])
    ftp.login(FTP_CONFIG["username"], FTP_CONFIG["password"])
    ftp.cwd("/event/source/dwt")
    files = ftp.nlst()
    return files


def list_files_ftp(FTP_CONFIG, directory="/event/source/dwt"):
    with FTP(FTP_CONFIG["host"]) as ftp:
        ftp.login(FTP_CONFIG["username"], FTP_CONFIG["password"])
        ftp.cwd(directory)  # Ganti direktori FTP jika perlu

        files = []
        ftp.dir(files.append)

        file_info_list = []
        for file_info in files:
            # Proses informasi file dari string hasil ftp.dir()
            file_info_list.append(process_file_info(file_info))

        return file_info_list

def get_status_file(FTP_CONFIG, directory="/event/source/dwt"):
    with FTP(FTP_CONFIG["host"]) as ftp:
        ftp.login(FTP_CONFIG["username"], FTP_CONFIG["password"])
        ftp.cwd(directory)  # Ganti direktori FTP jika perlu

        with open("road_risk_status.json", "wb") as fp:
            ftp.retrbinary("RETR road_risk_status.json", fp.write)

    df_stat = pd.read_json("road_risk_status.json", orient="index")
    df_stat["initTime"] = df_stat["initTime"].apply(lambda x: datetime.strptime(str(x),"%Y%m%d%H%M%S"))
    df_stat["validTime"] = df_stat["validTime"].apply(lambda x: datetime.strptime(str(x),"%Y%m%d%H%M%S"))
    return df_stat

def process_file_info(file_info):
    # Contoh format hasil ftp.dir(): "-rw-r--r--   1 user group      12345 Jan  1 10:00 filename.txt"
    # Sesuaikan dengan format di server FTP Anda
    info_list = file_info.split()

    # Dapatkan nama file dan waktu modifikasi
    filename = info_list[-1]
    modified_time_str = " ".join(info_list[-4:-1])
    modified_time = datetime.strptime(modified_time_str, "%b %d %H:%M")

    return {"filename": filename, "modified_time": modified_time}

file_info_list = list_files_ftp(FTP_CONFIG)
df_flist = pd.DataFrame(file_info_list)
df_flist["modified_time"] = df_flist["modified_time"].dt.strftime("%d %b %H:%M:%S LT")

df_stat = get_status_file(FTP_CONFIG)
df_stat = df_stat.merge(df_flist, left_index=True, right_on="filename")
df_stat.rename(columns={"filename":"File Name",
                        "modified_time":"Last Modified",
                        "initTime":"Initial Time",
                        "validTime":"Valid Time",
                        "leadTime":"Lead Time (+hrs)"}, inplace=True)
df_stat = df_stat[["File Name","Last Modified","Initial Time","Valid Time","Lead Time (+hrs)"]]

st.title("Monitoring IBF Road Risk")
st.header("FTP File List")
st.dataframe(df_stat,use_container_width=True)