# Telegram-бот для поиска аниме по фото

Бот принимает кадр из аниме, отправляет его в бесплатный API
trace.moe и показывает наиболее вероятные совпадения.

## Возможности

- приём изображения как фотографии или файла;
- название на английском, ромадзи и японском;
- номер эпизода;
- примерный таймкод сцены;
- процент сходства;
- превью найденного кадра;
- ссылка на AniList, MyAnimeList и видеофрагмент;
- обработка ошибок и лимитов API;
- защита от одновременных запросов одного пользователя;
- запуск обычной командой или через Docker.

## Структура

```text
anime_photo_bot/
├── app/
│   ├── services/
│   │   ├── __init__.py
│   │   └── trace_moe.py
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
├── docker-compose.yml
├── README.md
└── requirements.txt
```

## Быстрый запуск

Требуется Python 3.11 или новее.

```bash
python -m venv .venv
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

Создайте `.env`:

Linux / macOS / Termux:

```bash
cp .env.example .env
```

Windows:

```powershell
copy .env.example .env
```

Откройте `.env` и вставьте токен Telegram-бота:

```env
BOT_TOKEN=ВАШ_ТОКЕН_ОТ_BOTFATHER
```

Запустите:

```bash
python -m app.main
```

## Запуск в Termux

```bash
pkg update
pkg install python
cd anime_photo_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python -m app.main
```

## Docker

Создайте `.env`, затем выполните:

```bash
docker compose up -d --build
```

Просмотр журнала:

```bash
docker compose logs -f
```

## Настройки `.env`

- `BOT_TOKEN` — обязательный токен от BotFather.
- `TRACE_MOE_API_KEY` — необязательный ключ trace.moe.
- `MIN_SIMILARITY` — минимальный процент уверенного совпадения.
- `MAX_RESULTS` — число результатов от 1 до 5.
- `REQUEST_TIMEOUT` — тайм-аут API в секундах.
- `MAX_IMAGE_SIZE_MB` — максимальный размер изображения.
- `DROP_PENDING_UPDATES` — удалять ли старые обновления при запуске.

## Советы для точного поиска

Используйте кадр непосредственно из серии. Уберите:

- чёрные рамки;
- субтитры;
- логотипы;
- кнопки видеоплеера;
- коллажи и обрезанные лица.

trace.moe лучше ищет кадры из выпущенных аниме-сериалов и фильмов.
Манга, арты, постеры, фан-арт и изображения персонажей могут не найтись.

## Безопасность

Никогда не публикуйте файл `.env` и токен Telegram-бота в GitHub.
Если токен попал в открытый доступ, отзовите его через BotFather и
создайте новый.
