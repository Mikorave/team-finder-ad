# TeamFinder

Django-платформа для поиска команды на pet-проекты. Вариант 2: навыки пользователей и фильтрация участников по навыкам.

## Состояние

Выполнена первая из пяти частей: настройки, модели, миграции, админка и публичные страницы просмотра. Подробный план — [docs/План_реализации.md](docs/План_реализации.md).

Регистрация, вход через сайт, редактирование, участие, избранное и управление навыками пока не подключены. Ссылки и кнопки этих действий присутствуют в исходных шаблонах и будут подключены на следующих этапах. Сейчас данные можно создавать и редактировать через `/admin/`.

## Запуск в Windows PowerShell

Нужны Python 3.13 и Docker с Docker Compose.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env_example .env
```

Если `.env` уже заполнен, сохраните его значения. Установите `TASK_VERSION=2` и собственный `DJANGO_SECRET_KEY`. Параметры PostgreSQL в `.env` используются приложением и контейнером. `POSTGRES_PORT` задаёт внешний порт контейнера, по умолчанию 5436. При локальном запуске Django укажите `POSTGRES_HOST=localhost`.

```powershell
docker compose up -d --wait
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

При создании администратора укажите email, имя, фамилию и пароль.

- Главная: http://127.0.0.1:8000/
- Проекты: http://127.0.0.1:8000/projects/list/
- Участники: http://127.0.0.1:8000/users/list/
- Админка: http://127.0.0.1:8000/admin/

На главной отображаются открытые проекты, сначала новые. Закрытый проект доступен по прямой ссылке. Профиль использует постоянный адрес с ID.

## Проверки

На работающем PostgreSQL:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Пользователь PostgreSQL должен иметь право создавать тестовую базу. Пользователь из стандартного Docker-контейнера это право имеет.

Без PostgreSQL можно проверить код и миграции на временной SQLite:

```powershell
python manage.py test --settings=team_finder.test_settings
python manage.py makemigrations --check --dry-run --settings=team_finder.test_settings
```

Основные настройки всегда используют PostgreSQL. SQLite включается только явно указанными настройками тестов.

## Файлы и настройки

- `team_finder` — настройки и корневые маршруты.
- `user_app` — пользователи и их навыки.
- `project_app` — проекты и участники.
- `templates_var2` — используемые шаблоны.
- `static` — исходные стили, шрифт и JavaScript.
- `media` — загруженные и сгенерированные аватары; не хранится в Git.

Пароли проверяются стандартными валидаторами Django и при разработке. Секреты хранятся в `.env`, который исключён из Git. Для внешнего размещения настройте `DJANGO_ALLOWED_HOSTS`, отключите `DJANGO_DEBUG` и организуйте раздачу static/media веб-сервером.
