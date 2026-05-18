# Інструкція з запуску та деплою

## Локальний запуск

Потрібен Python 3.12 або новіший. Якщо на Windows команда `python` відкриває Microsoft Store або не знайдена, встановіть Python з python.org і додайте його в PATH, або використовуйте `py -3.12`.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/generate_dataset.py
python src/train_model.py
python app/app.py
```

Відкрити: `http://127.0.0.1:5000`

## GitHub

```bash
git init
git add .
git commit -m "Initial diploma project prototype"
git branch -M main
git remote add origin <посилання-на-репозиторій>
git push -u origin main
```

Не потрібно пушити: `.venv`, `__pycache__`, `.env`, локальні `.db` файли, тимчасові файли.

## Render

1. Створити новий Web Service.
2. Підключити GitHub-репозиторій.
3. Build command:

```bash
pip install -r requirements.txt && python src/generate_dataset.py && python src/train_model.py
```

4. Start command:

```bash
gunicorn app.app:app
```

5. Додати змінну середовища `SECRET_KEY`.

## Railway

Railway також може використати `Procfile`. Потрібно встановити змінну `SECRET_KEY` і переконатися, що команда запуску використовує `gunicorn app.app:app`.

## Змінні середовища

- `SECRET_KEY` — секрет Flask session;
- `PORT` — порт, який автоматично надає платформа деплою.
