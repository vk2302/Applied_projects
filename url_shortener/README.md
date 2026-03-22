В данном проекте реализован сервис сокращения ссылок. 

Запустить проект локально: docker compose up —build, затем открыть http://localhost:8000

Ссылка на сервис: https://url-shortener-fqgc.onrender.com
Swagger: https://url-shortener-fqgc.onrender.com/docs

Функции:
	•	создание короткой ссылки из длинного URL
	•	переход по короткой ссылке с автоматическим редиректом
	•	просмотр статистик по ссылке
	•	поиск короткой ссылки по исходной (длинной) ссылке
	•	обновление ссылки;
	•	удаление ссылки.

Дополнительные возможности:
	•	создание персональных кастомных ссылок 
	•	указание срока жизни ссылки: expires_at
	•	хранение информации о пользователе
	•	архив, удаление устаревших ссылок, вручную удаленные или истекшие ссылки хранятся в архиве
	•	группировка ссылок по проектам
	•	хранение в кэше недавних данных (Redis): short_code -> original_url, статистика по ссылке. Кеш очищается при изменении или удалении ссылок

Директории проекта:
	•	models — таблицы базы данных
	•	schemas — структуры запросов и ответов
	•	routes — HTTP-endpoints
	•	services — бизнес-логика
	•	core — настройки
	•	db — подключение к базе данных

Ссылки
	•	POST /links/shorten — создание короткой ссылки
	•	GET /{short_code} — перейти по ней
	•	GET /links/{short_code}/stats — получить статистику
	•	GET /links/search?original_url=... — найти ссылку по начальному URL
	•	PUT /links/{short_code} — обновить ссылку
	•	DELETE /links/{short_code} — удалить ссылку

Проекты
	•	POST /projects — создать проект
	•	GET /projects — получить список проектов

Архив
	•	GET /links/expired-history — посмотреть архив удаленных ссылок

Авторизация
	•	POST /auth/register — регистрация 
	•	POST /auth/login — логин и получение токена. Изменение и удаление ссылки доступны только авторизованному пользователю

Ссылки
	•	POST /links/shorten — создать короткую ссылку
	•	GET /{short_code} — перейти по короткой ссылке
	•	GET /links/{short_code}/stats — получить статистику
	•	GET /links/search?original_url=... — найти ссылку по оригинальному URL
	•	PUT /links/{short_code} — обновить ссылку
	•	DELETE /links/{short_code} — удалить ссылку

Проекты
	•	POST /projects — создать проект
	•	GET /projects — получить список проектов

Архив
	•	GET /links/expired-history — посмотреть архив удалённых и истёкших ссылок

База данных: PostgreSQL, таблицы: users, projects, links, archived links


К чекпойнту 4: добавлены Unit, функциональные тесты на pytest и FastAPI TestClient, для кэша используется mock

База: тестовая SQLite in-memory база.
Нагрузочное тестирование выполнено с помощью Locust.

### Load testing

нагрузочный тест был проведен с помощью команды:
docker compose exec app locust -f locustfile.py --host=http://localhost:8000 --headless -u 20 -r 2 -t 30s
	•	Total requests: 344
	•	Failures: 0
	•	Average response time:
	•	GET /health: ~3-4 ms
	•	POST /links/shorten: ~10 ms
	•	Throughput: ~11.53 req/s

Вывод: сервис справляется с конкурирующими запросами по созданию ссылок + health checks

Все основные тесты сработали хорошо, coverage 91%. Команды: 
coverage run -m pytest tests
coverage report -m
coverage html

Результаты:
Name                               Stmts   Miss  Cover   Missing
----------------------------------------------------------------
app/__init__.py                        0      0   100%
app/api/deps.py                       25      5    80%   14-18, 31
app/api/routes/auth.py                24      0   100%
app/api/routes/links.py               98     18    82%   59, 63-71, 139, 167, 170, 173-179, 185-187, 208, 211
app/api/routes/projects.py            18      0   100%
app/core/config.py                    15      0   100%
app/core/security.py                  19      2    89%   40-41
app/db/base.py                         2      0   100%
app/db/session.py                      5      0   100%
app/main.py                           62     13    79%   38-48, 65, 82, 86
app/models/archived_link.py           16      0   100%
app/models/link.py                    19      0   100%
app/models/project.py                 12      0   100%
app/models/user.py                    12      0   100%
app/schemas/auth.py                   17      0   100%
app/schemas/link.py                   42      0   100%
app/schemas/project.py                10      0   100%
app/services/cache.py                 19      1    95%   27
app/services/cleanup.py               34     22    35%   18-32, 36-60, 64-72, 76-77
app/services/shortener.py             11      0   100%
tests/conftest.py                     63      0   100%
tests/test_auth.py                    22      0   100%
tests/test_links_api.py               78      0   100%
tests/test_search_and_history.py      17      0   100%
tests/test_shortener_unit.py          20      0   100%
----------------------------------------------------------------
TOTAL                                660     61    91%


