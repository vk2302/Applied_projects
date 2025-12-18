import streamlit as st
import pandas as pd

st.set_page_config(page_title="Climate Monitor", layout="wide")

st.title("🌡️ Climate Monitor: загрузка исторических данных")
st.write("Загрузите CSV с колонками: **city, timestamp, temperature, season**.")

uploaded = st.file_uploader(
    "Загрузите temperature_data.csv",
    type=["csv"],
    help="Файл читается прямо из памяти (не по пути на диске)."
)

EXPECTED_COLS = {"city", "timestamp", "temperature", "season"}

@st.cache_data(show_spinner=False)
def read_temperature_csv(file) -> pd.DataFrame:
    # file — это UploadedFile (в памяти), его можно сразу читать через pandas
    df = pd.read_csv(file, parse_dates=["timestamp"])
    return df

if uploaded is None:
    st.info("Пока файл не загружен. Перетащите CSV сюда или нажмите «Browse files».")
else:
    try:
        df = read_temperature_csv(uploaded)

        missing = EXPECTED_COLS - set(df.columns)
        if missing:
            st.error(f"В файле не хватает колонок: {sorted(missing)}")
            st.stop()

        # базовая “санитарная” очистка/подготовка
        df = df.sort_values(["city", "timestamp"]).reset_index(drop=True)

        # сохраним в session_state, чтобы другие вкладки/части приложения могли использовать
        st.session_state["df_hist"] = df

        # краткая сводка
        c1, c2, c3 = st.columns(3)
        c1.metric("Строк", f"{len(df):,}")
        c2.metric("Городов", df["city"].nunique())
        c3.metric("Диапазон дат", f'{df["timestamp"].min().date()} → {df["timestamp"].max().date()}')

        st.subheader("Превью данных")
        st.dataframe(df.head(30), use_container_width=True)

    except Exception as e:
        st.exception(e)

