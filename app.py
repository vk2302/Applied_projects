import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- Конфигурация страницы ---
st.set_page_config(page_title="Анализ Температурных Данных", layout="wide")

st.title("🌦️ Мониторинг Погоды и Анализ Исторических Данных")

# --- Вспомогательные функции ---

def get_season(month):
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"

def load_data(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            # Убедимся, что колонка с датой в правильном формате
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                # Если колонки season нет, создадим её
                if 'season' not in df.columns:
                    df['season'] = df['timestamp'].dt.month.map(get_season)
            return df
        except Exception as e:
            st.error(f"Ошибка при чтении файла: {e}")
            return None
    return None

def calculate_stats(df, city):
    city_data = df[df['city'] == city].copy()
    
    # Описательная статистика
    stats = city_data['temperature'].describe()
    
    # Сезонные профили (как в ноутбуке)
    seasonal_stats = city_data.groupby('season')['temperature'].agg(['mean', 'std']).reset_index()
    
    # Аномалии: вычисляем границы для каждой записи на основе сезона
    # Сначала мерджим сезонные статистики обратно к данным города
    city_data = city_data.merge(seasonal_stats, on='season', suffixes=('', '_season'))
    
    city_data['lower_bound'] = city_data['mean'] - 2 * city_data['std']
    city_data['upper_bound'] = city_data['mean'] + 2 * city_data['std']
    
    city_data['is_anomaly'] = (city_data['temperature'] < city_data['lower_bound']) | \
                              (city_data['temperature'] > city_data['upper_bound'])
    
    return city_data, stats, seasonal_stats

def get_current_weather(city, api_key):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric"
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 401:
        return {"cod": 401, "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info."}
    elif response.status_code != 200:
        return {"cod": response.status_code, "message": f"Error: {response.reason}"}
    
    return response.json()

# --- Боковая панель ---
st.sidebar.header("Настройки")

# 1. Загрузка файла
uploaded_file = st.sidebar.file_uploader("Загрузите файл с историческими данными (CSV)", type="csv")

# 2. API Key
api_key = st.sidebar.text_input("Введите API-ключ OpenWeatherMap", type="password")

# --- Основная логика ---

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        # 3. Выбор города
        cities = df['city'].unique()
        selected_city = st.selectbox("Выберите город", cities)
        
        # Обработка данных для города
        city_df, des_stats, seasonal_stats = calculate_stats(df, selected_city)
        
        # --- Раздел 1: Описательная статистика ---
        st.subheader(f"📊 Исторические данные: {selected_city}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Средняя темп.", f"{des_stats['mean']:.2f} °C")
        col2.metric("Мин. темп.", f"{des_stats['min']:.2f} °C")
        col3.metric("Макс. темп.", f"{des_stats['max']:.2f} °C")
        col4.metric("Станд. откл.", f"{des_stats['std']:.2f} °C")
        
        # --- Раздел 2: Визуализация временного ряда с аномалиями ---
        st.subheader("📈 Временной ряд температур")
        
        # Используем Plotly для интерактивности
        fig = go.Figure()
        
        # Линия обычной температуры
        fig.add_trace(go.Scatter(
            x=city_df['timestamp'], 
            y=city_df['temperature'],
            mode='lines',
            name='Температура',
            line=dict(color='blue', width=1),
            opacity=0.6
        ))
        
        # Выделение аномалий
        anomalies = city_df[city_df['is_anomaly']]
        fig.add_trace(go.Scatter(
            x=anomalies['timestamp'], 
            y=anomalies['temperature'],
            mode='markers',
            name='Аномалии',
            marker=dict(color='red', size=6, symbol='x')
        ))
        
        # Добавляем скользящее среднее (опционально, для красоты)
        city_df['rolling_mean'] = city_df['temperature'].rolling(window=30).mean()
        fig.add_trace(go.Scatter(
            x=city_df['timestamp'],
            y=city_df['rolling_mean'],
            mode='lines',
            name='Скользящее среднее (30д)',
            line=dict(color='orange', width=2)
        ))

        fig.update_layout(
            title=f"Температура в {selected_city} с выделением аномалий",
            xaxis_title="Дата",
            yaxis_title="Температура (°C)",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # --- Раздел 3: Сезонные профили ---
        st.subheader("🍂 Сезонные профили")
        
        # Подготовка данных для отображения
        seasonal_display = seasonal_stats.copy()
        seasonal_display.columns = ['Сезон', 'Средняя температура', 'Стандартное отклонение']
        
        # Отображение таблицы и графика рядом
        scol1, scol2 = st.columns([1, 2])
        
        with scol1:
            st.write("Статистика по сезонам:")
            st.dataframe(seasonal_display.style.format("{:.2f}", subset=['Средняя температура', 'Стандартное отклонение']))
            
        with scol2:
            # Бар-чарт сезонности
            fig_season = px.bar(
                seasonal_stats, 
                x='season', 
                y='mean', 
                error_y='std',
                title="Средняя температура по сезонам (с ошибкой std)",
                labels={'mean': 'Средняя температура (°C)', 'season': 'Сезон'},
                color='season'
            )
            st.plotly_chart(fig_season, use_container_width=True)

        # --- Раздел 4: Текущая погода (API) ---
        st.divider()
        st.subheader(f"🌍 Текущая погода: {selected_city}")
        
        if api_key:
            current_weather = get_current_weather(selected_city, api_key)
            
            if "cod" in current_weather and current_weather["cod"] == 401:
                st.error(f"Ошибка API: {current_weather['message']}")
            elif "cod" in current_weather and current_weather["cod"] != 200:
                st.error(f"Не удалось получить погоду: {current_weather.get('message', 'Unknown error')}")
            else:
                # Данные получены успешно
                curr_temp = current_weather['main']['temp']
                curr_humidity = current_weather['main']['humidity']
                curr_desc = current_weather['weather'][0]['description']
                
                # Определение текущего сезона
                current_month = datetime.now().month
                current_season = get_season(current_month)
                
                # Проверка на нормальность
                season_row = seasonal_stats[seasonal_stats['season'] == current_season]
                if not season_row.empty:
                    mean_temp = season_row['mean'].values[0]
                    std_temp = season_row['std'].values[0]
                    
                    lower_normal = mean_temp - 2 * std_temp
                    upper_normal = mean_temp + 2 * std_temp
                    
                    is_normal = lower_normal <= curr_temp <= upper_normal
                    
                    # Визуализация текущей погоды
                    wc1, wc2 = st.columns(2)
                    with wc1:
                        st.metric("Текущая температура", f"{curr_temp} °C", delta=None)
                        st.write(f"Погодные условия: **{curr_desc}**")
                        st.write(f"Влажность: **{curr_humidity}%**")
                        
                    with wc2:
                        st.write(f"Текущий сезон: **{current_season}**")
                        st.write(f"Исторический диапазон (норма): **{lower_normal:.1f} °C ... {upper_normal:.1f} °C**")
                        
                        if is_normal:
                            st.success("✅ Текущая температура в пределах нормы для сезона.")
                        else:
                            st.warning("⚠️ Текущая температура является аномальной для этого сезона!")
                else:
                    st.info("Недостаточно исторических данных для анализа текущего сезона.")
        else:
            st.info("Введите API-ключ OpenWeatherMap в меню слева, чтобы увидеть текущую погоду.")
            
    else:
        st.warning("Пожалуйста, убедитесь, что ваш CSV файл содержит необходимые колонки (city, timestamp, temperature).")
else:
    st.info("👈 Пожалуйста, загрузите CSV файл с историческими данными в меню слева для начала работы.")
    st.markdown("""
    **Ожидаемый формат файла:**
    * `city`: Название города
    * `timestamp`: Дата (YYYY-MM-DD)
    * `temperature`: Температура
    * `season`: Сезон (опционально, вычисляется автоматически)
    """)
