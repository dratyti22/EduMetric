# AGENTS.md

Guidance for coding agents working in this repository.

## Project

EduMetric — a web app for teachers and tutoring centers to record mock exams (ЕГЭ/ОГЭ), enter
per-task scores, convert primary scores into secondary ones using FIPI scales, and analyze class
and student performance.

- Backend: Django 6.1 + DRF + SimpleJWT, PostgreSQL.
- Frontend: Vue 3 + Vite + TypeScript SPA (Vue Router + Pinia).
- Domain language (model `help_text`, `choices` labels, UI copy) is Russian; identifiers are English.
- Naming note: the backend app is `exams`, but the frontend calls the same domain "mock tests"
  (`stores/mockTests.ts`, `views/MockTestsView.vue`). It is one and the same feature.

## Structure

```text
edumetric/
├── backend/                    # Django service; run manage.py from here
│   ├── backend/                # project config: settings.py, urls.py, wsgi.py, asgi.py
│   ├── src/
│   │   ├── user/               # custom User (AUTH_USER_MODEL = "user.User"), JWT auth/registration
│   │   ├── school/             # SchoolClass, Student, ClassJoinRequest; Subject enum (school/enum.py),
│   │   │                       # join codes (codes.py), permissions.py; logic in services.py
│   │   └── exams/              # ExamTemplate(+ExamTemplateTask), ScoreConversion, Exam(+ExamTask),
│   │                           # StudentResult, TaskResult; business logic in services.py
│   ├── templates/              # Django templates dir (console email backend configured)
│   ├── manage.py
│   ├── openapi.yaml            # hand-maintained OpenAPI 3.0.3 spec for the API
│   ├── Dockerfile, entrypoint.sh  # container image: install deps + migrate + runserver (port 8000)
│   └── pyproject.toml          # deps, ruff, ty
├── frontend/                   # Vue 3 + Vite + TS
│   ├── src/
│   │   ├── views/              # page components (Login, Dashboard, Classes, MockTests, ...)
│   │   ├── stores/             # Pinia stores: auth, classes, mockTests, results
│   │   ├── router/             # Vue Router routes
│   │   ├── components/         # Modal.vue, Navbar.vue
│   │   ├── types/              # shared TS types
│   │   └── utils/              # scales.ts, storage.ts
│   └── package.json, vite.config.ts, tsconfig*.json
├── docker-compose.yaml         # services: db (Postgres 16), backend (port 8000), frontend (port 5173)
├── .env / .env.example         # one shared env file for Django, compose and containers
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
- `docker-compose.yaml` runs three services, all reading the same `.env`:
  - `db` — Postgres 16 (`edumetric-db`, host port 5432, healthcheck);
  - `backend` — Django on port 8000 (`entrypoint.sh` runs `uv sync` + `migrate` + `runserver`);
  - `frontend` — Vite dev server on port 5173.
- Start: `docker compose up -d` (all three) or `docker compose up -d db` (only the database).
- Settings basics: `LANGUAGE_CODE="ru-ru"`, `TIME_ZONE="UTC"`, `USE_TZ=True`,
  `django.contrib.postgres` installed, DRF defaults to JWT auth + `IsAuthenticated`.

## Backend (run from `backend/`)

- Python >= 3.12. Dependencies are declared in `pyproject.toml`; use the local `backend/.venv`
  (activate it, or call `backend/.venv/bin/python` directly).
- `python manage.py migrate`, `runserver`, `makemigrations`, `createsuperuser`.
- Tests: Django runner, `python manage.py test`; `src/<app>/tests.py` modules are empty stubs.
- FIPI data: `python manage.py sedd_exam_templates` seeds `Subject` templates, tasks and
  conversion scales (the command name has a typo — "sedd", not "seed").
- Lint/format: `ruff check .` and `ruff format .` (line-length 100, target py312,
  rules E/F/I/B/UP/DJ, migrations excluded; some rules are ignored — see `pyproject.toml`).
- Types: `ty check`.
- Routers: everything is under `/api/v1/`; `user/` holds auth/registration, `school` and `exams`
  mount on the bare `/api/v1/` prefix (see `backend/backend/urls.py`).

## API contract

- `backend/openapi.yaml` is the hand-maintained OpenAPI 3.0.3 description of the HTTP API.
  Its `servers` entry is `/api/v1`, so paths inside the file are written without that prefix
  (`/classes/` means `/api/v1/classes/`).
- Any change to the API surface must be reflected in that file in the same change:
  - added, renamed or removed routes and HTTP methods;
  - request/response fields, types, required flags and examples;
  - status codes and error responses;
  - authentication or permission requirements.
- Keep it in sync with the code (`backend/backend/urls.py`, `src/<app>/urls.py`, views and
  serializers) — the code is the source of truth, the spec must match it. Bump `info.version`
  when the published contract changes.
- Unfinished modules stay out of the spec: the `exams` endpoints are currently hidden on purpose,
  so add them only once the module is stable.

## Frontend (run from `frontend/`)

- Node `^22.18.0 || >=24.12.0`. `npm run dev` (Vite), `npm run type-check` (`vue-tsc --build`),
  `npm run build` (`run-p` of type-check and vite build).
- Alias `@` -> `frontend/src`. Installed deps: Vue 3.5, Pinia, Vue Router, Axios, lucide icons,
  Vite 8, TS 6, vue-tsc.
- The UI is a full SPA: Vue Router routes in `src/router/`, state in Pinia stores (`src/stores/`),
  pages in `src/views/`. API access goes through Axios (see the stores).
- `Readme.md` (Russian) describes the frontend architecture — it matches the code.

## Conventions

- New models: UUID primary key (`uuid.uuid4`, `editable=False`), `related_name` on every FK,
  uniqueness via `Meta.constraints`, Russian `verbose`/`help_text` strings.
- Scores are `PositiveIntegerField`s bounded by `max_score`; secondary scores are 0–100.
- Keep views thin: query/aggregation logic goes to `services.py` or serializers.
- Run `ruff format .` before committing; double quotes are enforced.

## Pitfalls

- Do not import an app through `src.` (`from src.user.models import User`): that loads a second copy
  of the module, so models get registered twice. Always use the top-level names.
- `manage.py` must be launched as a script (its `sys.path` fix-up lives there); a bare
  `django-admin` or an import from a different entry point will not find `user`/`school`/`exams`.
- `.env` must satisfy both consumers: `DB_*` for Django and `POSTGRES_*` for the Postgres container.
- Backend domain is `exams`, frontend domain is "mock tests" — don't treat them as different
  features when tracing code across the stack.
