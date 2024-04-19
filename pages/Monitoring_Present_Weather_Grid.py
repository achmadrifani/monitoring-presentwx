import rioxarray
import streamlit as st
from streamlit_folium import st_folium
from ftplib import FTP
from PIL import Image
import folium
import matplotlib.colors as mcolors
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import rasterio
import numpy as np
from datetime import datetime

FTP_CONFIG = {"host":"publik.bmkg.go.id","username":"amandemen","password":"bmkg2303"}
st.set_page_config(layout="wide")

def get_tif_data():
    ftp = FTP(FTP_CONFIG.get("host"))
    ftp.login(FTP_CONFIG.get("username"),FTP_CONFIG.get("password"))
    ftp.cwd("/data")
    filename = 'present_weather_grid_latest.tif'
    with open(filename, 'wb') as file:
        ftp.retrbinary('RETR ' + filename, file.write)

    modified_time = ftp.sendcmd('MDTM ' + filename)
    modified_time = datetime.strptime(modified_time[4:], '%Y%m%d%H%M%S')
    return filename, modified_time

def make_png(tif_file):
    ds = rioxarray.open_rasterio(tif_file)

    categories = [1, 2, 3, 4, 60, 61, 63, 95, 97]
    colors = ["#8eb2fa", "#6597fc", "#2a70fa", "#ffffff", "#faf564", "#faa264", "#f74f4f", "#fc35f2", "#fc35f2"]
    cmap = ListedColormap(colors)

    fig, ax = plt.subplots(1, 1, figsize=(10, 10), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.imshow(ds.data[0], extent=(ds.x.min(), ds.x.max(), ds.y.min(), ds.y.max()), origin='upper', cmap=cmap)
    ax.set_axis_off()
    png_file = "pwx.png"
    plt.savefig(png_file, bbox_inches='tight', pad_inches=0,dpi=600)
    return png_file

st.header("Monitoring Present Weather Grid")
tif_file, tif_time = get_tif_data()
png_file = make_png(tif_file)
ds = rioxarray.open_rasterio(tif_file)
lon_min, lat_max, lon_max, lat_min = ds.rio.bounds()

st.write(f"Last updated: {tif_time}")

m = folium.Map(location=[-2.4833826, 117.8902853], zoom_start=5)
raster = folium.FeatureGroup(name='raster').add_to(m)
folium.raster_layers.ImageOverlay(
    image=png_file,
    bounds=[[lat_min, lon_min], [lat_max, lon_max]],
    opacity=0.7,
    interactive=True
).add_to(raster)
raster.add_to(m)

st_folium(m, key="fct-map", feature_group_to_add=[raster], use_container_width=True, returned_objects=[])