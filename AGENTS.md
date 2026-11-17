# AGENTS.md

Guidance for coding agents working in this repository.

## Project

EduMetric — a web app for teachers and tutoring centers to record mock exams (ЕГЭ/ОГЭ), enter
per-task scores, convert primary scores into secondary ones using FIPI scales, and analyze class
and student performance.

- Backend: Django 6.1 + DRF + SimpleJWT, PostgreSQL.
- Frontend: Vue 3 + Vite + TypeScript (still the starter scaffold).
- Domain language (model `help_text`, `choices` labels, UI copy) is Russian; identifiers are English.

## Structure

```text
edumetric/
├── backend/                    # Django service; run manage.py from here
│   ├── backend/                # project config: settings.py, urls.py, wsgi.py, asgi.py
│   ├── src/
│   │   ├── user/               # custom User (AUTH_USER_MODEL = "user.User"), JWT auth
│   │   ├── school/             # SchoolClass, Student, Subject enum (school/enum.py)
│   │   └── exams/              # ExamTemplate(+Task), ScoreConversion, Exam, ExamTask,
│   │                           # StudentResult, TaskResult; business logic in services.py
│   ├── templates/              # Django templates dir (console email backend configured)
│   ├── manage.py
│   ├── pyproject.toml          # uv deps, ruff, ty
│   └── uv.lock
├── frontend/                   # Vue 3 + Vite + TS
│   ├── src/                    # only App.vue and main.ts so far
│   └── package.json, vite.config.ts, tsconfig*.json
├── docs/                       # project documentation (empty)
├── docker-compose.yaml         # Postgres 16 only
├── .env / .env.example         # one shared env file for Django and compose
└── Readme.md                   # Russian product overview
```

Application code imports apps as top-level modules (`from school.models import Student`,
`from exams.models import Exam`) — never `src.`-prefixed. `backend/manage.py`, `wsgi.py` and
`asgi.py` add `backend/src` to `sys.path` for that; `INSTALLED_APPS` uses `user.apps.UserConfig`,
`school.apps.SchoolConfig`, `exams.apps.ExamsConfig`.

## Environment & services

- Env is read from the repo-root `.env` via `django-environ` (`BASE_DIR.parent / ".env"` in
  `backend/backend/settings.py`), never `backend/.env`. Copy `.env.example` and fill it in.
- No defaults for `SECRET_KEY`, `ALLOWED_HOSTS`, or `DB_*` — the app fails to start without them.
- `docker-compose.yaml` runs Postgres 16 only (`edumetric-db`, host port 5432) and reads
  `POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD` from the same `.env`. Start: `docker compose up -d db`.
- Settings basics: `LANGUAGE_CODE="ru-ru"`, `TIME_ZONE="UTC"`, `USE_TZ=True`,
  `django.contrib.postgres` installed, DRF defaults to JWT auth + `IsAuthenticated`.

## Backend (run from `backend/`)

- Python >= 3.12, dependencies via `uv` (`pyproject.toml` / `uv.lock`; a local `.venv` may exist).
- `uv run python manage.py migrate`, `runserver`, `makemigrations`, `createsuperuser`.
- Tests: Django runner, `uv run python manage.py test`; `src/<app>/tests.py` modules are empty stubs.
- FIPI data: `uv run python manage.py sedd_exam_templates` seeds `Subject` templates, tasks and
  conversion scales (the command name has a typo — "sedd", not "seed").
- Lint/format: `uv run ruff check .` and `uv run ruff format .` (line-length 100, target py312,
  rules E/F/I/B/UP/DJ, migrations excluded).
- Types: `uv run ty check`. `[tool.ty]` is read, but `[tool.ty.src]` is misspelled as `[toll.ty.src]`,
  so its `include`/`exclude` are ignored.
- Routers: everything is under `/api/v1/`; `user/` holds auth/registration, `school` and `exams`
  mount on the bare `/api/v1/` prefix (see `backend/backend/urls.py`).

## Frontend (run from `frontend/`)

- Node `^22.18.0 || >=24.12.0`. `npm run dev` (Vite), `npm run type-check` (`vue-tsc --build`),
  `npm run build` (`run-p` of type-check and `vite build`).
- Alias `@` -> `frontend/src`. Installed deps: Vue 3.5, Pinia, Vue Router, Axios, Vite 8, TS 6.
- The UI is still the Vite starter screen; `Readme.md` describes a richer planned frontend
  (views, stores, router) that does not exist in the repo yet.

## Conventions

- New models: UUID primary key (`uuid.uuid4`, `editable=False`), `related_name` on every FK,
  uniqueness via `Meta.constraints`, Russian `verbose`/`help_text` strings.
- Scores are `PositiveIntegerField`s bounded by `max_score`; secondary scores are 0–100.
- Keep views thin: query/aggregation logic goes to `services.py` or serializers.
- Run `uv run ruff format .` before committing; double quotes are enforced.

## Pitfalls

- Do not import an app through `src.` (`from src.user.models import User`): that loads a second copy
  of the module, so models get registered twice. Always use the top-level names.
- `exams` has models but no migrations yet; `migrate` will not create that schema until
  `makemigrations exams` runs.
- `manage.py` must be launched as a script (its `sys.path` fix-up lives there); a bare
  `django-admin` or an import from a different entry point will not find `user`/`school`/`exams`.
- `docker-compose.yaml` mounts `./postgres_data:/var/lib/postgres/data`, but the official image
  writes to `/var/lib/postgresql/data`, so database data is not actually persisted.
- `.env` must satisfy both consumers: `DB_*` for Django and `POSTGRES_*` for the Postgres container.
- `Readme.md` drifts from the code (paths like `~/Projs/...`, a non-existent `src/auth` app, a
  frontend that has not been built yet), so verify structure against the tree above.
