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
import requests
import json

FTP_CONFIG = {"host": "publik.bmkg.go.id", "username": "amandemen", "password": "bmkg2303"}
API_RADAR = "https://radar.bmkg.go.id:8060/getRadarGeotif?token=19387e71e78522ae4172ec0fda640983b8438c9cfa0ca571623cb69d8327&radar=amandemenForecast&type=latest"
st.set_page_config(layout="wide")


def get_tif_pwx():
    ftp = FTP(FTP_CONFIG.get("host"))
    ftp.login(FTP_CONFIG.get("username"), FTP_CONFIG.get("password"))
    ftp.cwd("/data")
    filename = 'present_weather_grid_latest.tif'
    with open(filename, 'wb') as file:
        ftp.retrbinary('RETR ' + filename, file.write)

    modified_time = ftp.sendcmd('MDTM ' + filename)
    modified_time = datetime.strptime(modified_time[4:], '%Y%m%d%H%M%S')
    return filename, modified_time


def get_latest_radar():
    """
    Fetches the latest radar data from a server, parses the filename to get the timestamp,
    and prepares the data in the form of an xarray dataset.

    Returns:
        radar_data (xarray Dataset): The latest radar data.
        radar_time (datetime): The timestamp of the radar data.
    """
    try:
        print("Fetching latest radar merge data")
        response = requests.get(API_RADAR, verify=False)
        response.raise_for_status()  # Check if the request was successful
        with rasterio.open(response.json()['file']) as src:
            radar_data = rioxarray.open_rasterio(src)

        levels = [0.1, 1, 2, 5, 7, 9, 10, 12, 15, 20, 50, 100]
        colors = ["#4b4bd7", "#4ba0fe", "#6ed7fe", "#9ff0fe", "#fefefe", "#fef8d2", "#feec4b", "#fe9c4b", "#fe774b",
                  "#d74b4b", "#b44b4b", "#984b4b"]
        cmap = mcolors.LinearSegmentedColormap.from_list("mycmap", colors)

        lons, lats = np.meshgrid(radar_data.x, radar_data.y)
        fig, ax = plt.subplots(1, 1, figsize=(10, 10), subplot_kw={'projection': ccrs.Mercator()})
        ax.contourf(lons, lats, radar_data.data[0], levels, cmap=cmap, extend="max")

        ax.set_axis_off()
        png_file = "radar.png"
        plt.savefig(png_file, bbox_inches='tight', pad_inches=0, dpi=600, transparent=True)

        filename = response.json()["file"].split("/")[4]
        time_str = filename[13:25]
        radar_time = datetime.strptime(time_str,"%Y%m%d%H%M")
        return png_file, radar_time
    except Exception as e:
        print(f"An error occurred while fetching or processing the data: {e}")
        return None, None


def make_png(tif_file):
    ds = rioxarray.open_rasterio(tif_file)

    categories = [1, 2, 3, 4, 60, 61, 63, 95, 97]
    colors = ["#8eb2fa", "#6597fc", "#2a70fa", "#002a7d", "#faf564", "#faa264", "#f74f4f", "#fc35f2", "#fc35f2"]
    cmap = ListedColormap(colors)

    fig, ax = plt.subplots(1, 1, figsize=(10, 10), subplot_kw={'projection': ccrs.Mercator()})
    ax.imshow(ds.data[0], extent=(ds.x.min(), ds.x.max(), ds.y.min(), ds.y.max()), origin='upper', cmap=cmap)
    ax.set_axis_off()
    png_file = "pwx.png"
    plt.savefig(png_file, bbox_inches='tight', pad_inches=0, dpi=600, transparent=True)
    return png_file


def main():
    st.header("Monitoring Present Weather Grid")
    pwx_file, pwx_time = get_tif_pwx()
    rdr_file, rdr_time = get_latest_radar()
    png_file = make_png(pwx_file)
    ds = rioxarray.open_rasterio(pwx_file)
    lon_min, lat_max, lon_max, lat_min = ds.rio.bounds()

    st.write(f"Present Weather Last updated: {pwx_time} UTC")
    st.write(f"Radar Last updated: {rdr_time} UTC")

    m = folium.Map(location=[-2.4833826, 117.8902853], zoom_start=5)
    pwx = folium.FeatureGroup(name='Present Weather', show=False).add_to(m)
    folium.raster_layers.ImageOverlay(
        image=png_file,
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=0.7,
        interactive=True,
    ).add_to(pwx)

    rdr = folium.FeatureGroup(name='Radar Estimate', show=False).add_to(m)
    folium.raster_layers.ImageOverlay(
        image=rdr_file,
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=0.7,
        interactive=True,
    ).add_to(rdr)

    pwx.add_to(m)
    rdr.add_to(m)
    folium.LayerControl("topleft",collapsed=False).add_to(m)

    st_folium(m, key="fct-map", feature_group_to_add=[pwx,rdr], use_container_width=True, returned_objects=[])

if __name__ == "__main__":
    main()
