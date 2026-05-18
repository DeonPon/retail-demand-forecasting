# Інтелектуальна система прогнозування попиту на товари

## Тема дипломної роботи
«Розробка інтелектуальної системи прогнозування попиту на товари для автоматизації процесів ритейлу»

## Автор
Чесніший Денис Юрійович  
Група ІПЗ-22-401  
Спеціальність: F2 / 121 «Інженерія програмного забезпечення»

## Опис проєкту
Це дипломний програмний прототип інформаційної системи для менеджера ритейлу. Система аналізує історичні продажі, формує ознаки для машинного навчання, порівнює кілька ML-моделей, прогнозує попит і формує рекомендації закупівель через зручний web-інтерфейс.

## Мета
Автоматизувати частину процесів ритейлу, пов’язаних з аналізом продажів, прогнозуванням попиту, контролем запасів і підтримкою рішень щодо закупівель.

## Основні можливості
- завантаження та імпорт CSV у SQLite;
- аналіз історичних продажів по 74 товарах і 12 категоріях;
- прогнозування попиту на 7, 14 або 30 днів;
- пояснення прогнозу через фактори впливу;
- рекомендації закупівель з пріоритетами;
- перегляд метрик MAE, RMSE, MAPE;
- порівняння моделей RandomForest, GradientBoosting та ExtraTrees;
- dashboard для менеджера;
- авторизація демо-користувача;
- REST API для інтеграції та перевірки стану системи.

## Технології
- Python
- Flask
- Pandas
- NumPy
- Scikit-learn
- SQLite
- HTML/CSS
- Canvas API для локальних графіків без зовнішніх CDN
- Gunicorn

## Структура проєкту
```text
app/                 Flask-додаток, шаблони, стилі, авторизація
data/                Демонстраційний CSV-датасет та опис структури
docs/                Документація для дипломної записки та деплою
models/              Навчена модель і метрики
screenshots/         Скріншоти для записки та презентації
src/                 Генерація даних, preprocessing, ML, прогноз, SQLite
tests/               Тести API, імпорту, моделі та рекомендацій
requirements.txt     Залежності
render.yaml          Конфігурація деплою на Render
Procfile             Команда запуску через Gunicorn
runtime.txt          Версія Python для хостингу
```

## Дані
Система використовує демонстраційний, але реалістично згенерований датасет:
- 74 товари;
- 12 категорій;
- близько року історії продажів;
- плавна зміна цін;
- акції, свята, сезонність, затримки постачальника;
- додаткові поля: `product_icon`, `base_demand`, `seasonality_type`, `shelf_life_days`, `supplier_name`, `region`.

Опис CSV: [data/README.md](data/README.md)

## Встановлення
Потрібен Python 3.12 або новіший.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск локально
```bash
python src/generate_dataset.py
python src/train_model.py
python app/app.py
```

Після запуску відкрийте: `http://127.0.0.1:5000`

## Демо-доступ
Логін: `admin`  
Пароль: `admin123`

## API endpoints
- `GET /health`
- `GET /api/products`
- `GET /api/products/<id>`
- `GET /api/categories`
- `GET /api/forecast/<product_id>?days=14`
- `GET /api/recommendation/<product_id>?days=14`
- `GET /api/recommendations?days=14`
- `GET /api/metrics`
- `GET /api/feature-importance`
- `POST /api/upload`
- `POST /api/retrain`
- `GET /api/imports`
- `GET /api/system-info`

## CSV імпорт
Обов’язкові колонки:
- `date`
- `product_id`
- `product_name`
- `category`
- `sales_quantity`
- `price`
- `stock_quantity`
- `promo`
- `holiday`
- `supplier_delay_days`

Додаткові колонки:
- `product_icon`
- `shelf_life_days`
- `supplier_name`
- `region`

Після успішного імпорту система:
1. перевіряє структуру CSV;
2. очищає та нормалізує дані;
3. імпортує товари у `products`;
4. імпортує продажі у `sales`;
5. записує історію у `imports`;
6. перенавчає модель або готує систему до перенавчання.

## Деплой
Проєкт підготовлений для Render:
- `render.yaml` описує web-сервіс;
- `Procfile` запускає Gunicorn;
- `runtime.txt` фіксує Python runtime;
- `PORT` і `SECRET_KEY` беруться з середовища.

Деталі: [docs/deployment_guide.md](docs/deployment_guide.md)

## GitHub
```bash
git add .
git commit -m "Improve realism, dataset, UI and forecasting explanations"
git push
```

Не потрібно пушити:
- `.venv/`
- `__pycache__/`
- `.env`
- `*.db`
- `.pytest_cache/`
- тимчасові логи

## Скріншоти
Для дипломної варто підготувати:
- login;
- dashboard;
- products;
- forecast;
- recommendations;
- metrics;
- about;
- приклад імпорту CSV;
- відповіді API `/health`, `/api/metrics`, `/api/recommendations`.

## Подальший розвиток
- підключення реальних даних з POS або ERP;
- ролі користувачів та розширення авторизації;
- асинхронне перенавчання моделі;
- richer analytics для категорій і сезонних звітів;
- CI/CD, Docker і production-grade логування.
