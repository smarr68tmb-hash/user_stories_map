# Backend - AI User Story Mapper

## Установка

1. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env и добавьте ваш OPENAI_API_KEY
# Или установите переменную окружения:
# export OPENAI_API_KEY=sk-your-key-here
```

4. Запустите сервер:
```bash
python main.py
```

Сервер будет доступен на http://127.0.0.1:8000

API документация: http://127.0.0.1:8000/docs

