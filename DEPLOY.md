# Деплой EduMetric на VPS

Схема: интернет → Caddy (HTTPS и frontend) → Gunicorn/Django → PostgreSQL.
Наружу открываются только 80/443; база и Django не публикуют порты.
`docker-compose.yaml` остаётся конфигурацией разработки. Для сервера используется
**только `compose.production.yaml`**, без объединения с dev-файлом.

## 1. Подготовить сервер

- VPS с Ubuntu 24.04 LTS, ориентир: 2 CPU, 2–4 ГБ RAM, 20+ ГБ диска.
- Установить Git, Docker Engine и плагин Docker Compose по официальной инструкции:
  https://docs.docker.com/engine/install/ubuntu/
- Настроить вход по SSH-ключу, обновления ОС и firewall.
- Разрешить SSH **до** включения firewall, а также TCP 80 и 443.
  Не открывать 5432, 8000 или 5173. Проверить также firewall провайдера.
- Создать DNS A-запись домена (например, `exam.example.com`) на IPv4 сервера.
  AAAA добавлять только при настроенном IPv6. На время первого запуска отключить
  CDN-проксирование. Порты 80/443 должны быть свободны.

Далее команды выполняются из корня проекта. Заменить `<URL_РЕПОЗИТОРИЯ>` своим адресом:

```bash
git clone <URL_РЕПОЗИТОРИЯ> edumetric
cd edumetric
cp .env.production.example .env.production
chmod 600 .env.production
```

Изменения проекта должны быть предварительно отправлены в ваш репозиторий.
Не копировать локальный `.env` с тестовыми паролями на сервер.

## 2. Заполнить `.env.production`

```bash
nano .env.production
```

Заменить:
- `DOMAIN` — только домен, без `https://` и пути;
- `ALLOWED_HOSTS` — тот же домен, без протокола;
- `CSRF_TRUSTED_ORIGINS` и `CORS_ALLOWED_ORIGINS` — `https://ваш-домен`;
- `SECRET_KEY` — уникальный случайный секрет;
- `DB_PASSWORD` — отдельный случайный пароль базы.

Для генерации **каждого** секрета отдельно:

```bash
openssl rand -hex 48
```

`DEBUG=0` не менять. `.env.production` исключён из Git.
Обычный `.env` production-контейнерам не нужен.

## 3. Первый запуск

```bash
docker compose --env-file .env.production -f compose.production.yaml config --quiet
docker compose --env-file .env.production -f compose.production.yaml up -d --build
docker compose --env-file .env.production -f compose.production.yaml ps -a
docker compose --env-file .env.production -f compose.production.yaml logs --tail=100 release backend web
```

`release` должен завершиться с кодом **0**: он проверяет Django, применяет миграции
и собирает статику админки. Остальные сервисы должны работать. Caddy автоматически
получит сертификат. При сбое DNS/сертификата смотреть логи `web`.

`check --deploy` может предупреждать об отключённых HSTS includeSubDomains/preload:
это намеренно, чтобы не навязать HTTPS другим поддоменам. Остальные предупреждения,
особенно о секретном ключе и DEBUG, нужно устранить перед использованием.

Создать администратора и загрузить шаблоны ФИПИ:

```bash
docker compose --env-file .env.production -f compose.production.yaml exec backend python manage.py createsuperuser
docker compose --env-file .env.production -f compose.production.yaml exec backend python manage.py sedd_exam_templates
```

Команда `sedd_exam_templates` действительно пишется с `sedd`.
Проверить `https://ваш-домен/`, `/admin/`, регистрацию/вход, создание класса,
публикацию пробника и сохранение баллов учеником. Данные разработки автоматически
не переносятся. Для переноса нужна отдельная копия БД и согласованный план восстановления.

## 4. Резервная копия

Перед каждым обновлением и регулярно (например, ежедневно через cron):

```bash
mkdir -p backups
chmod 700 backups
docker compose --env-file .env.production -f compose.production.yaml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "backups/edumetric-$(date +%Y%m%d-%H%M%S).dump"
```

Проверять успешное завершение и ненулевой размер файла. Хранить копии **вне VPS**
в защищённом хранилище: дамп содержит персональные данные. Отдельно безопасно хранить
`.env.production`. Автоматического расписания/внешнего хранилища этот проект не создаёт.

Проверку восстановления сначала выполнять на отдельном тестовом сервере.
Следующая команда **перезаписывает данные целевой БД**. Только при осознанном восстановлении:

```bash
docker compose --env-file .env.production -f compose.production.yaml stop backend web
docker compose --env-file .env.production -f compose.production.yaml exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --exit-on-error' < backups/ИМЯ_КОПИИ.dump
docker compose --env-file .env.production -f compose.production.yaml start backend web
```

## 5. Обновление

Сначала сделать резервную копию по разделу 4. Для небольшого проекта используем
короткое окно обслуживания: старый backend не работает одновременно с миграциями.

```bash
git pull --ff-only
docker compose --env-file .env.production -f compose.production.yaml build
docker compose --env-file .env.production -f compose.production.yaml stop web backend
docker compose --env-file .env.production -f compose.production.yaml run --rm release
docker compose --env-file .env.production -f compose.production.yaml up -d --force-recreate
```

Последнюю команду выполнять **только если release завершился успешно**. Проверить
логи и основные сценарии. При смене пароля в env пароль уже созданной БД сам собой
не меняется: нужна отдельная согласованная смена пароля в PostgreSQL.

Не выполнять `docker compose down -v`: это удалит БД и сертификаты!
Восстановление старой версии после миграций требует совместимой схемы или резервной копии.

## Ограничения

- Это конфигурация одного VPS, не кластер и не безостановочный деплой.
- Почтовый ящик и SMTP не нужны. Caddy получает сертификаты без email.
  В production отправка писем отключена (dummy backend); проверка `mail.E001`
  отключена намеренно. Почтовые уведомления и восстановление пароля по email
  не будут отправляться.
- Настроить мониторинг доступности, диска, ошибок и успешности резервных копий.
- До публичного запуска проверить пользовательские сценарии на сервере и требования
  к обработке персональных данных. Production-сборка не заменяет аудит безопасности.
