import streamlit as st
import pandas as pd
import requests

def validate_openweather_key(api_key: str):
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

# --- Sidebar: ввод API key (должен быть ДО использования ключа) ---
with st.sidebar:
    st.subheader("OpenWeatherMap")

    with st.form("owm_key_form"):
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

        st.rerun()  # чтобы сразу обновить интерфейс после проверки

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

# --- Upload CSV ---
uploaded = st.file_uploader(
    "Загрузите temperature_data.csv",
    type=["csv"],
    help="Файл читается прямо из памяти (не по пути на диске)."
)

@st.cache_data(show_spinner=False)
def read_temperature_csv(file) -> pd.DataFrame:
    return pd.read_csv(file, parse_dates=["timestamp"])

if uploaded is None:
    st.info("Пока файл не загружен. Перетащите CSV сюда или нажмите «Browse files».")
    st.stop()

# --- Read + validate CSV ---
df = read_temperature_csv(uploaded)

missing = EXPECTED_COLS - set(df.columns)
if missing:
    st.error(f"В файле не хватает колонок: {sorted(missing)}")
    st.stop()

df = df.sort_values(["city", "timestamp"]).reset_index(drop=True)
st.session_state["df_hist"] = df

# --- City selector ---
st.subheader("Выбор города")
cities = sorted(df["city"].dropna().unique().tolist())
selected_city = st.selectbox("Город", options=cities, index=0)
st.session_state["selected_city"] = selected_city

df_city = df[df["city"] == selected_city].copy()
st.session_state["df_city"] = df_city

# --- Preview ---
c1, c2, c3 = st.columns(3)
c1.metric("Строк (город)", f"{len(df_city):,}")
c2.metric("Диапазон дат (город)", f'{df_city["timestamp"].min().date()} → {df_city["timestamp"].max().date()}')
c3.metric("Сезонов (город)", df_city["season"].nunique())

st.subheader(f"Превью данных: {selected_city}")
st.dataframe(df_city.head(30), use_container_width=True)

# --- Current weather (показываем только когда ключ введен/валиден) ---
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


