# API Документация Pselu

## Общая информация
Приложение использует TCP-сокеты для связи с сервером. Все запросы и ответы передаются в формате JSON.

## Формат запросов
Каждый запрос должен содержать следующие поля:
- `action`: строка, определяющая тип запроса
- `data`: объект с данными запроса

## Доступные endpoints

### 1. Авторизация
```json
Запрос:
{
    "action": "login",
    "data": {
        "username": "string",
        "password": "string"
    }
}

Ответ:
{
    "status": "success/error",
    "message": "string",
    "data": {
        "student_id": "integer"
    }
}
```

### 2. Регистрация
```json
Запрос:
{
    "action": "register",
    "data": {
        "username": "string",
        "password": "string",
        "group": "string"
    }
}

Ответ:
{
    "status": "success/error",
    "message": "string"
}
```

### 3. Получение списка лабораторных работ
```json
Запрос:
{
    "action": "get_lab_works",
    "data": {}
}

Ответ:
{
    "status": "success/error",
    "message": "string",
    "data": {
        "lab_works": [
            {
                "id": "integer",
                "theme": "string",
                "time": "integer"
            }
        ]
    }
}
```

### 4. Проверка статуса лабораторной работы
```json
Запрос:
{
    "action": "check_lab_completed",
    "data": {
        "student_id": "integer",
        "lab_id": "integer"
    }
}

Ответ:
{
    "status": "success/error",
    "message": "string",
    "data": {
        "completed": "boolean",
        "score": "integer"
    }
}
```

### 5. Получение вопросов
```json
Запрос:
{
    "action": "get_questions",
    "data": {
        "lab_id": "integer"
    }
}

Ответ:
{
    "status": "success/error",
    "message": "string",
    "data": {
        "questions": [
            {
                "id": "integer",
                "text": "string",
                "options": ["string"],
                "time": "integer"
            }
        ]
    }
}
```

### 6. Отправка ответов
```json
Запрос:
{
    "action": "submit_answers",
    "data": {
        "student_id": "integer",
        "lab_id": "integer",
        "answers": [
            {
                "question_id": "integer",
                "answer": "string"
            }
        ]
    }
}

Ответ:
{
    "status": "success/error",
    "message": "string",
    "data": {
        "score": "integer",
        "passed": "boolean"
    }
}
```
