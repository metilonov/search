# Anime Hybrid Bot

Telegram-бот для поиска аниме по фото с гибридной логикой:

1. **trace.moe** — основной поиск точного кадра, серии и таймкода.
2. **AnimeTrace** — дополнительный AI-поиск названия и персонажа.
3. **SauceNAO** — поиск артов, постеров, похожих источников и ссылок.

Также бот умеет:
- автоматически обрезать чёрные рамки;
- пробовать зеркальный вариант изображения;
- отправлять несколько результатов из разных движков;
- работать через `.env`;
- запускаться локально, на сервере и через Docker.

---

## Структура

```text
anime_hybrid_bot/
├── app/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── anime_trace.py
│   │   ├── hybrid_search.py
│   │   ├── preprocess.py
│   │   ├── saucenao.py
│   │   ├── trace_moe.py
│   │   └── types.py
│   ├── __init__.py
│   ├── config.py
│   ├── handlers.py
│   ├── keyboards.py
│   ├── main.py
│   ├── models.py
│   └── utils.py
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── docker-compose.yml
├── main.py
└── requirements.txt
```

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env`:

```env
BOT_TOKEN=ВАШ_ТОКЕН
TRACE_MOE_API_KEY=
ANIME_TRACE_API_KEY=
SAUCENAO_API_KEY=
```

## Запуск

Вариант 1:

```bash
python -m app.main
```

Вариант 2:

```bash
python main.py
```

## Команда запуска для сервера

```bash
python main.py
```

или

```bash
python -m app.main
```

## Что обязательно заполнить

Обязательно:
- `BOT_TOKEN`

Можно оставить пустым:
- `TRACE_MOE_API_KEY`
- `ANIME_TRACE_API_KEY`
- `SAUCENAO_API_KEY`

## Переменные

### trace.moe
- `TRACE_CONFIDENT_SCORE=0.80` — если совпадение выше, поиск считается успешным.
- `TRACE_MIN_SCORE=0.65` — минимальный порог показа результата.
- `TRACE_MAX_RESULTS=3`

### AnimeTrace
- `ANIME_TRACE_ENABLED=true`
- `ANIME_TRACE_API_URL=https://api.animedb.cn/v1/search`
- `ANIME_TRACE_MODEL=`
- `ANIME_TRACE_MIN_SCORE=0.55`

### SauceNAO
- `SAUCENAO_ENABLED=true`
- `SAUCENAO_MIN_SCORE=0.60`
- `SAUCENAO_NUM_RESULTS=3`

### Автоварианты
- `USE_AUTO_VARIANTS=true`

## Как работает поиск

1. Пользователь отправляет изображение.
2. Бот создаёт варианты:
   - оригинал;
   - обрезанный кадр без чёрных рамок;
   - зеркальный вариант.
3. Бот запускает поиск через trace.moe.
4. Если результат уверенный — показывает его и завершает поиск.
5. Если уверенности не хватает — запускает AnimeTrace и SauceNAO.
6. Пользователь получает лучшие совпадения из всех движков.

## Важное замечание

`trace.moe` стабильно подходит для кадров из аниме.
`SauceNAO` часто лучше работает для артов, постеров и изображений персонажей.
`AnimeTrace` API со временем может менять формат ответа, поэтому в проекте
сделан гибкий парсер ответа, но при серьёзных изменениях API может потребоваться корректировка.

## Termux

```bash
pkg update
pkg install python
cd anime_hybrid_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python main.py
```

## Docker

```bash
docker compose up -d --build
```

## Безопасность

Не загружайте `.env` в GitHub.
Если токен бота утёк — отзовите его через @BotFather и создайте новый.
