import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Prakiraan Cuaca Wilayah Sulawesi Bagian Utara", layout="wide")

# Judul dan identitas
st.title("📡 Global Forecast System Viewer (Realtime via NOMADS)")
st.markdown("""
<div style='text-align: center; font-style: italic;'>
    <h4>oleh: Sazali Udjir</h4>
    <p>Kelas: Meteorologi 8TB</p>
</div>
""", unsafe_allow_html=True)
st.header("Web Hasil Pembelajaran Pengelolaan Informasi Meteorologi")

@st.cache_data
def load_dataset(run_date, run_hour):
    base_url = (
        f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/"
        f"gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    )
    ds = xr.open_dataset(base_url, decode_times=True)
    return ds

# Input dari sidebar
st.sidebar.title("⚙️ Pengaturan")
today = datetime.utcnow()
run_date = st.sidebar.date_input("Tanggal Run GFS (UTC)", today.date())
run_hour = st.sidebar.selectbox("Jam Run GFS (UTC)", ["00", "06", "12", "18"])
forecast_hour = st.sidebar.slider("Jam ke depan", 0, 240, 0, step=1)
parameter = st.sidebar.selectbox("Parameter", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

if st.sidebar.button("🔎 Tampilkan Visualisasi"):
    try:
        ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
        st.success("Dataset berhasil dimuat.")
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        st.stop()

    # Pilih variabel sesuai parameter
    is_contour = False
    is_vector = False

    if "pratesfc" in parameter:
        var = ds["pratesfc"][forecast_hour] * 3600
        label, cmap = "Curah Hujan (mm/jam)", "Blues"
    elif "tmp2m" in parameter:
        var = ds["tmp2m"][forecast_hour] - 273.15
        label, cmap = "Suhu (°C)", "coolwarm"
    elif "ugrd10m" in parameter:
        u = ds["ugrd10m"][forecast_hour]
        v = ds["vgrd10m"][forecast_hour]
        var = (u**2 + v**2)**0.5 * 1.94384
        label, cmap = "Kecepatan Angin (knot)", plt.cm.get_cmap("RdYlGn_r", 10)
        is_vector = True
    elif "prmsl" in parameter:
        var = ds["prmslmsl"][forecast_hour] / 100
        label, cmap = "Tekanan Permukaan Laut (hPa)", "cool"
        is_contour = True
    else:
        st.warning("Parameter tidak dikenali.")
        st.stop()

    # Subset wilayah 2° LU – 5° LS dan 122° BT – 133° BT
    lat_min, lat_max = -5, 2
    lon_min, lon_max = 122, 133
    var = var.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
    if is_vector:
        u = u.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
        v = v.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    # Visualisasi
    fig = plt.figure(figsize=(10, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], ccrs.PlateCarree())

    valid_dt = pd.to_datetime(ds.time[forecast_hour].values)
    valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    ax.set_title(f"{label} – Valid {valid_str}", loc="left", fontsize=10, fontweight="bold")
    ax.set_title(f"GFS t+{forecast_hour:03d}", loc="right", fontsize=10, fontweight="bold")

    if is_contour:
        cs = ax.contour(var.lon, var.lat, var.values, levels=15,
                        colors="black", linewidths=0.8, transform=ccrs.PlateCarree())
        ax.clabel(cs, fmt="%d", colors="black", fontsize=8)
    else:
        im = ax.pcolormesh(var.lon, var.lat, var.values,
                           cmap=cmap, vmin=0 if "Curah" in label else None,
                           transform=ccrs.PlateCarree())
        cbar = plt.colorbar(im, ax=ax, orientation="vertical", pad=0.02)
        cbar.set_label(label)
        if is_vector:
            ax.quiver(var.lon[::5], var.lat[::5],
                      u.values[::5, ::5], v.values[::5, ::5],
                      transform=ccrs.PlateCarree(), scale=700,
                      width=0.002, color="black")

    # Menandai kota (Ternate dan Ambon saja)
    kota = {
        "Ternate": (0.7893, 127.3877),
        "Ambon": (-3.695, 128.181)
    }
    for nama, (lat, lon) in kota.items():
        ax.plot(lon, lat, "ro", markersize=5, transform=ccrs.PlateCarree())
        ax.text(lon + 0.1, lat + 0.1, nama,
                transform=ccrs.PlateCarree(),
                fontsize=8, fontweight="bold", color="red")

    ax.coastlines(resolution="10m", linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=":")
    ax.add_feature(cfeature.LAND, facecolor="lightgray")

    st.pyplot(fig)
