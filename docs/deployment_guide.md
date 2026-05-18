# Інструкція з деплою

## Локальний запуск
```bash
pip install -r requirements.txt
python src/generate_dataset.py
python src/train_model.py
python app/app.py
```

## Запуск у браузері
Відкрити:

`http://127.0.0.1:5000`

## GitHub
```bash
git init
git add .
git commit -m "Improve realism, dataset, UI and forecasting explanations"
git branch -M main
git remote add origin <посилання-на-репозиторій>
git push -u origin main
```

## Які файли не треба пушити
- `.venv/`
- `__pycache__/`
- `.env`
- `*.db`
- `.pytest_cache/`
- локальні тимчасові логи

## Render
### Build command
```bash
pip install -r requirements.txt && python src/generate_dataset.py && python src/train_model.py
```

### Start command
```bash
gunicorn app.app:app
```

## Потрібні змінні середовища
- `SECRET_KEY` — секретний ключ Flask;
- `PORT` — порт, який надає Render.

## Поради для Render
- не використовувати абсолютні локальні шляхи;
- не тягнути критичні frontend-залежності з CDN;
- важкі обчислення виконувати лише при імпорті або retrain;
- після `git push` Render може автоматично виконати redeploy.
