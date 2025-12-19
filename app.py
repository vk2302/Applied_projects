import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
import plotly.express as px


def validate_openweather_key(api_key):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": 0, "lon": 0, "appid": api_key}
    r = requests.get(url, params=params, timeout=10)

    if r.status_code == 401:
        return False, r.json()

    try:
        r.raise_for_status()
    except Exception:
        try:
            return False, r.json()
        except Exception:
            return False, {"status_code": r.status_code, "text": r.text}

    return True, None


def get_current_temp_sync(city, api_key: str, country_code=None):
    geo_url = "https://api.openweathermap.org/geo/1.0/direct"
    city_info = {"q": f"{city},{country_code}" if country_code else city, "limit": 1, "appid": api_key}
    geo_request = requests.get(geo_url, params=city_info, timeout=10)
    geo_request.raise_for_status()
    data = geo_request.json()
    if not data:
        raise ValueError("нет результатов")

    lat = data[0]["lat"]
    lon = data[0]["lon"]

    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    weather_params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
    current_weather = requests.get(weather_url, params=weather_params, timeout=10)
    current_weather.raise_for_status()
    w_json = current_weather.json()

    return w_json["main"]["temp"]


st.set_page_config(page_title="Climate Monitor", layout="wide")
st.title("🌡️ Climate Monitor: загрузка исторических данных")
st.write("Загрузите CSV с колонками: **city, timestamp, temperature, season**.")

EXPECTED_COLS = {"city", "timestamp", "temperature", "season"}

with st.sidebar:
    st.subheader("Подключение к OpenWeatherMap")

    with st.form("api_key"):
        api_key_input = st.text_input(
            "API Key",
            value=st.session_state.get("OPENWEATHER_API_KEY", ""),
            type="password",
            help="Ключ хранится только в session_state (в памяти)."
        )
        submitted = st.form_submit_button("Сохранить и проверить")

    if submitted:
        api_key_input = api_key_input.strip()
        st.session_state["OPENWEATHER_API_KEY"] = api_key_input

        if not api_key_input:
            st.session_state["OWM_VALID"] = False
            st.session_state["OWM_ERROR"] = None
        else:
            ok, err = validate_openweather_key(api_key_input)
            st.session_state["OWM_VALID"] = ok
            st.session_state["OWM_ERROR"] = err

        st.rerun() 

    api_key_saved = st.session_state.get("OPENWEATHER_API_KEY", "").strip()
    owm_valid = st.session_state.get("OWM_VALID", False)
    owm_err = st.session_state.get("OWM_ERROR", None)

    if not api_key_saved:
        st.info("Введите API key — текущая погода не будет показана без него.")
    elif owm_valid:
        st.success("API key корректный ✅")
    else:
        st.error("API key некорректный ❌")
        if owm_err:
            st.json(owm_err)


uploaded = st.file_uploader("Загрузите temperature_data.csv", type=["csv"], help="Файл читается прямо из памяти (не по пути на диске).")

@st.cache_data(show_spinner=False)
def read_temperature_csv(file) -> pd.DataFrame:
    return pd.read_csv(file, parse_dates=["timestamp"])

@st.cache_data(show_spinner=False)
def compute_city_features(df_city: pd.DataFrame, window: int, mode: str):
    """
    mode:
      - "seasonal": аномалии по season_mean ± 2σ
      - "rolling":  аномалии по rolling_mean ± 2σ (бонус)
    """
    dfc = df_city.sort_values("timestamp").copy()

    # rolling
    dfc["rolling_mean"] = dfc["temperature"].rolling(window=window, min_periods=window).mean()
    dfc["rolling_std"]  = dfc["temperature"].rolling(window=window, min_periods=window).std(ddof=0)

    # seasonal stats
    season_stats = (
        dfc.groupby("season")["temperature"]
           .agg(season_mean="mean", season_std=lambda s: s.std(ddof=0), n="size")
           .reset_index()
    )
    dfc = dfc.merge(season_stats[["season", "season_mean", "season_std"]], on="season", how="left")

    # bounds + anomaly
    if mode == "rolling":
        dfc["low_lim"] = dfc["rolling_mean"] - 2 * dfc["rolling_std"]
        dfc["hi_lim"]  = dfc["rolling_mean"] + 2 * dfc["rolling_std"]
    else:  # "seasonal"
        dfc["low_lim"] = dfc["season_mean"] - 2 * dfc["season_std"]
        dfc["hi_lim"]  = dfc["season_mean"] + 2 * dfc["season_std"]

    dfc["anomaly"] = np.logical_or(dfc["temperature"] < dfc["low_lim"],
                                   dfc["temperature"] > dfc["hi_lim"]).fillna(False)

    return dfc, season_stats

if uploaded is None:
    st.info("Пока файл не загружен. Перетащите CSV сюда или нажмите «Browse files».")
    st.stop()

df = read_temperature_csv(uploaded)

missing = EXPECTED_COLS - set(df.columns)
if missing:
    st.error(f"В файле не хватает колонок: {sorted(missing)}")
    st.stop()

df = df.sort_values(["city", "timestamp"]).reset_index(drop=True)
st.session_state["df_hist"] = df

st.subheader("Выбор города")
cities = sorted(df["city"].dropna().unique().tolist())
selected_city = st.selectbox("Город", options=cities, index=0)
st.session_state["selected_city"] = selected_city

df_city = df[df["city"] == selected_city].copy()
st.session_state["df_city"] = df_city

c1, c2, c3 = st.columns(3)
c1.metric("Строк (город)", f"{len(df_city):,}")
c2.metric("Диапазон дат (город)", f'{df_city["timestamp"].min().date()} → {df_city["timestamp"].max().date()}')
c3.metric("Сезонов (город)", df_city["season"].nunique())

st.subheader(f"Превью данных: {selected_city}")
st.dataframe(df_city.head(30), use_container_width=True)
# --- Настройки анализа (лучше в sidebar, но только после загрузки CSV) ---
with st.sidebar:
    st.subheader("Настройки анализа")
    window = st.slider("Окно rolling (дней)", min_value=7, max_value=90, value=30, step=1)
    mode = st.radio(
        "Правило аномалий",
        options=["seasonal", "rolling"],
        format_func=lambda x: "По сезону (mean ± 2σ)" if x == "seasonal" else "По rolling (mean ± 2σ)",
        index=0
    )

dfc, season_stats = compute_city_features(df_city, window=window, mode=mode)

# --- Табы ---
tab1, tab2, tab3 = st.tabs(["📊 Статистика", "📈 Ряд + аномалии", "🍂 Сезонные профили"])

with tab1:
    st.subheader(f"Описательная статистика: {selected_city}")

    desc = dfc["temperature"].describe().to_frame(name="temperature").T
    st.dataframe(desc, use_container_width=True)

    n_anom = int(dfc["anomaly"].sum())
    pct_anom = 100.0 * n_anom / len(dfc) if len(dfc) else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Аномалий", n_anom)
    c2.metric("% аномалий", f"{pct_anom:.2f}%")
    c3.metric("Rolling окно", f"{window} дней")

    st.write("Сезонная сводка (mean ± std):")
    st.dataframe(season_stats, use_container_width=True)

with tab2:
    st.subheader(f"Температура во времени + аномалии: {selected_city}")

    fig = go.Figure()

    # Температура (серым)
    fig.add_trace(go.Scatter(
        x=dfc["timestamp"], y=dfc["temperature"],
        mode="lines", name="Температура",
        line=dict(color="gray"), opacity=0.5
    ))

    # Rolling mean (синим)
    fig.add_trace(go.Scatter(
        x=dfc["timestamp"], y=dfc["rolling_mean"],
        mode="lines", name=f"Rolling mean ({window}d)",
        line=dict(color="blue")
    ))

    # Нормальный диапазон (заливка между low и high)
    fig.add_trace(go.Scatter(
        x=dfc["timestamp"], y=dfc["low_lim"],
        mode="lines", line=dict(width=0),
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=dfc["timestamp"], y=dfc["hi_lim"],
        mode="lines", line=dict(width=0),
        fill="tonexty",
        name="Нормальный диапазон (±2σ)",
        fillcolor="rgba(0,0,255,0.12)"
    ))

    # Аномалии (красные точки)
    anom = dfc[dfc["anomaly"]]
    fig.add_trace(go.Scatter(
        x=anom["timestamp"], y=anom["temperature"],
        mode="markers", name="Аномалии",
        marker=dict(color="red", size=6)
    ))

    fig.update_layout(
        height=520,
        xaxis_title="Дата",
        yaxis_title="Температура (°C)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )

    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader(f"Сезонные профили: {selected_city}")

    season_order = ["winter", "spring", "summer", "autumn"]
    season_stats_plot = season_stats.copy()
    season_stats_plot["season"] = pd.Categorical(season_stats_plot["season"], categories=season_order, ordered=True)
    season_stats_plot = season_stats_plot.sort_values("season")

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=season_stats_plot["season"],
        y=season_stats_plot["season_mean"],
        error_y=dict(type="data", array=season_stats_plot["season_std"], visible=True),
        name="Mean ± Std"
    ))
    fig2.update_layout(
        height=420,
        xaxis_title="Сезон",
        yaxis_title="Температура (°C)",
    )

    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Текущая погода")

api_key_saved = st.session_state.get("OPENWEATHER_API_KEY", "").strip()
owm_valid = st.session_state.get("OWM_VALID", False)
owm_err = st.session_state.get("OWM_ERROR", None)

if not api_key_saved:
    st.info("API key не введён — текущая погода не отображается.")
elif not owm_valid:
    st.error("Некорректный API key. Ответ API:")
    if owm_err:
        st.json(owm_err)
else:
    country_code = st.text_input("Country code (опционально, например RU/DE/AE)", value="")
    if st.button("Получить текущую температуру"):
        try:
            temp_now = get_current_temp_sync(selected_city, api_key_saved, country_code or None)
            st.success(f"Сейчас в {selected_city}: **{temp_now:.1f} °C**")
        except Exception as e:
            st.exception(e)



