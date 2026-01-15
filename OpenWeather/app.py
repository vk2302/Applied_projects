import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# заголовок
st.set_page_config(page_title="Анализ Температурных Данных", layout="wide")

st.title("🌦️ Текущая погода и Исторические тренды по городам")

# функции

def get_season(month):
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"

def load_data(uploaded_file): # чтение файла, создание столбца с текущим временем и сезоном
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                if 'season' not in df.columns:
                    df['season'] = df['timestamp'].dt.month.map(get_season)
            return df
        except Exception as e:
            st.error(f"Ошибка при чтении файла: {e}")
            return None
    return None

# повторение того, что в ноутбуке: статистика температуры по сезонам, определение интервала для аномалий
def calculate_stats(df, city):
    city_data = df[df['city'] == city].copy()

    # для выбранного города выведем основную базовую информацию
    stats = city_data['temperature'].describe()
    
    # Сезонные профили (как в ноутбуке)
    seasonal_stats = city_data.groupby('season')['temperature'].agg(['mean', 'std']).reset_index()
    
    # Аномалии: вычисляем границы для каждой записи на основе сезона по каждому городу
    city_data = city_data.merge(seasonal_stats, on='season', suffixes=('', '_season'))
    
    city_data['lower_bound'] = city_data['mean'] - 2 * city_data['std']
    city_data['upper_bound'] = city_data['mean'] + 2 * city_data['std']
    
    city_data['is_anomaly'] = (city_data['temperature'] < city_data['lower_bound']) | \
                              (city_data['temperature'] > city_data['upper_bound'])
    
    return city_data, stats, seasonal_stats

# повторение функции из тренировочного ноутбука + проверка АПИ
def get_current_weather(city, api_key):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}
    response = requests.get(url, params=params)
    
    if response.status_code == 401:
        return {"cod": 401, "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info."}
    elif response.status_code != 200:
        return {"cod": response.status_code, "message": f"Error: {response.reason}"}
    
    return response.json()

# сбоку будет находиться форма для загрузки csv файла и ввода АПИ-ключа
st.sidebar.header("Настройки")

uploaded_file = st.sidebar.file_uploader("Загрузите CSV-файл с историческими данными", type="csv")

api_key = st.sidebar.text_input("Введите API-ключ OpenWeatherMap", type="password")


if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        # Выбор города из выпадающего списка, затем статистика по нему
        cities = df['city'].unique()
        selected_city = st.selectbox("Выберите город", cities)
        
        city_df, des_stats, seasonal_stats = calculate_stats(df, selected_city)
        
        st.subheader(f"📊 Исторические данные для города: {selected_city}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Средняя темп.", f"{des_stats['mean']:.2f} °C")
        col2.metric("Мин. темп.", f"{des_stats['min']:.2f} °C")
        col3.metric("Макс. темп.", f"{des_stats['max']:.2f} °C")
        col4.metric("Станд. откл.", f"{des_stats['std']:.2f} °C")
        
        st.subheader("📈 История температуры за 10 лет")

        # используем plotly, в отличие от ноутбука
        fig = go.Figure()
        
        # температура посуточная
        fig.add_trace(go.Scatter(
            x=city_df['timestamp'], 
            y=city_df['temperature'],
            mode='lines',
            name='Температура',
            line=dict(color='blue', width=1),
            opacity=0.6
        ))
        
        # обозначение красным цветом точек аномалий
        anomalies = city_df[city_df['is_anomaly']]
        fig.add_trace(go.Scatter(
            x=anomalies['timestamp'], 
            y=anomalies['temperature'],
            mode='markers',
            name='Аномалии',
            marker=dict(color='red', size=5, symbol='star')
        ))
        
        # скользящее среднее - основная линия
        city_df['rolling_mean'] = city_df['temperature'].rolling(window=30).mean()
        fig.add_trace(go.Scatter(
            x=city_df['timestamp'],
            y=city_df['rolling_mean'],
            mode='lines',
            name='Средняя Т, за 30сут',
            line=dict(color='orange', width=2)
        ))

        fig.update_layout(
            title=f"{selected_city}: температурный тренд 2010-2020",
            xaxis_title="Год измерений",
            yaxis_title="Температура (°C)",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Профили температур (среднее и стандартотклон) по сезонам
        st.subheader("🍂 Сезонные профили")

        seasonal_display = seasonal_stats.copy()
        seasonal_display.columns = ['Сезон', 'Средняя температура', 'Стандартное отклонение']
        
        # Отображение таблицы и графика рядом
        scol1, scol2 = st.columns([1, 2])
        
        with scol1:
            st.write("Статистика по сезонам:")
            st.dataframe(seasonal_display.style.format("{:.2f}", subset=['Средняя температура', 'Стандартное отклонение']))
            
        with scol2:
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

        # вывод текущей температуры для города
        st.divider()
        st.subheader(f"🌍 Текущая погода: {selected_city}")
        
        if api_key:
            current_weather = get_current_weather(selected_city, api_key)
            # проверка ключа 
            if "cod" in current_weather and current_weather["cod"] == 401:
                st.error(f"Ошибка API: {current_weather['message']}")
            elif "cod" in current_weather and current_weather["cod"] != 200:
                st.error(f"Не удалось получить погоду: {current_weather.get('message', 'Unknown error')}")
            else:
                curr_temp = current_weather['main']['temp']
                curr_humidity = current_weather['main']['humidity']
                curr_desc = current_weather['weather'][0]['description']
                
                # Как в ноутбуке, определеним текущий сезон
                current_month = datetime.now().month
                current_season = get_season(current_month)
                
                # Проверка на аномалию
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
                            st.warning("⚠️ Текущая температура аномальна для этого сезона!")
                else:
                    st.info("Недостаточно исторических данных для анализа текущего сезона.")
        else:
            st.info("Введите API-ключ OpenWeatherMap в меню слева, чтобы увидеть текущую погоду.")
            
    else:
        st.warning("Пожалуйста, убедитесь, что ваш CSV файл содержит необходимые колонки (city, timestamp, temperature).")
else:
    st.info("Пожалуйста, загрузите CSV файл с историческими данными в меню слева для начала работы.")
    st.markdown("""
    **Ожидаемый формат файла:**
    * `city`: Название города
    * `timestamp`: Дата (YYYY-MM-DD)
    * `temperature`: Температура
    * `season`: Сезон (опционально, вычисляется автоматически)
    """)
