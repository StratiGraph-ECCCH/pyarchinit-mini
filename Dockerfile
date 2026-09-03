# pyarchinit-mini — the Flask web interface, in a container.
#
#   docker build --build-arg S3DGRAPHY_VERSION=<version> -t pyarchinit-mini .
#   docker run --rm -p 8080:8080 -v pyarchinit_data:/srv/pyarchinit-data pyarchinit-mini
#
# The build argument is REQUIRED — see the note on it below.
#
# ── WHICH APPLICATION THIS SERVES, so the next reader does not wire the other ─
#
# `wsgi.py` → `pyarchinit_mini.web_interface.app.create_app()` → the FLASK app.
# That is the callable this image runs, and it is the one that has ever been
# deployed.
#
# There is a SECOND application in this repository: `main.py` →
# `pyarchinit_mini/api/__init__.py`, a FastAPI service with OpenAPI and JWT. It
# is not deployed anywhere today, this image does not run it, and wiring it here
# because it looks more modern would ship a different program under the same
# name.
#
# ── WHICH START COMMAND, since the repository holds two that disagree ─────────
#
#   Procfile      gunicorn --worker-class eventlet -w 1 wsgi:app --bind …
#   railway.toml  gunicorn wsgi:app --bind … -w 1 --threads 4 --timeout 600 \
#                     --graceful-timeout 30
#
# Railway prefers `railway.toml` over the `Procfile`, so THE CONFIGURATION
# ACTUALLY IN SERVICE is the sync worker with threads — and this image mirrors
# it rather than choosing in silence.
#
# The eventlet line is not merely unused, it is wrong: eventlet requires
# `eventlet.monkey_patch()` before any stdlib import, and `wsgi.py` never calls
# it. Reproducing it here would have produced a worker whose green threads sit
# on top of unpatched blocking sockets.
#
# The two flags are `railway.toml`'s own, with its own reasons, kept verbatim:
#   --timeout 600         a legacy SQLite → Postgres migration takes minutes,
#                         and the default 120s killed the worker mid-migration
#   --threads 4           some concurrency for the sync worker without pulling
#                         eventlet or gevent in
#
# KNOWN LIMIT OF THIS IMAGE, declared rather than discovered: `SocketIO(app,
# cors_allowed_origins="*", ping_timeout=120, ping_interval=30)`
# (`pyarchinit_mini/web_interface/app.py:817`) does not declare `async_mode`, so
# under a sync worker it falls back to `threading` — which means long-polling,
# not a real WebSocket upgrade. Live features work and are slower. Fixing it is
# an application decision (an async worker class plus the monkey-patching that
# goes with it), not a Dockerfile one.
#
# ── PYTHON ────────────────────────────────────────────────────────────────────
#
# `pyproject.toml` says `requires-python = ">=3.8,<3.15"`, so several versions
# would do. This is 3.12-slim because `stratigraph-server/Dockerfile` is: two
# images in one ecosystem sharing a runtime is one interpreter to reason about
# instead of two.
FROM python:3.12-slim AS base

# PYTHONDONTWRITEBYTECODE: nothing in the image should be modified at runtime.
# PYTHONUNBUFFERED: logs reach the orchestrator as they happen — and this app
# prints its database decision at import time (`[FLASK] Using database: …`),
# which is exactly the line an operator needs to see before anything else.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ── THE VERSION OF THE SHARED LANGUAGE, from one place ───────────────────────
#
# `S3DGRAPHY_VERSION` has NO DEFAULT, and that is the point rather than an
# omission — the same rule `stratigraph-server/Dockerfile` states at length. A
# default here would be a second spelling of a number that must agree with
# `dev-stack/.env.dev`, and two spellings of one version are two versions the day
# somebody edits one.
#
# It matters more here than elsewhere, because this repository declares the floor
# TWICE and the two disagree:
#   pyproject.toml:61    s3dgraphy>=0.1.42
#   requirements.txt:56  s3dgraphy>=1.5.0
# Today both resolve to 1.5.4, so the disagreement is mute — until a resolver
# chooses differently. Neither file is touched here; the pin is applied as a pip
# CONSTRAINT, which means a pin that contradicts either floor makes the build
# FAIL instead of quietly resolving to something nobody chose.
ARG S3DGRAPHY_VERSION

WORKDIR /srv/pyarchinit-mini

# ── SYSTEM PACKAGES, each with the measurement that justifies it ──────────────
#
# WEASYPRINT — imported at `web_interface/app.py:6392` (`from weasyprint import
# HTML`) and in `services/pottery_pdf_service.py`. Without the native libraries
# it imports fine and then fails AT RENDERING, which is the worst way to fail: a
# PDF button that works until somebody presses it. Pango, HarfBuzz, Cairo,
# gdk-pixbuf, libffi and shared-mime-info are what it links against; a font is
# what it draws with, and a container with no font at all renders boxes.
#
# GRAPHVIZ (the binary) — `harris_matrix/matrix_generator.py:819` does `from
# graphviz import Digraph`, and the code itself runs `shutil.which` and prints
# «Linux (Debian/Ubuntu): sudo apt install graphviz» (line 836). The Python
# package is a wrapper around the `dot` executable: without it the Harris export
# degrades, and the application is the one that says so.
#
# WHAT IS DELIBERATELY ABSENT, so nobody puts it back:
#
#   libpq-dev, build-essential — NOT needed. `psycopg2-binary` is a wheel, and
#     `requirements.txt:4` asks for exactly that. A compiler in a runtime image
#     is a compiler an attacker can use.
#   libmagic1, ffmpeg — NOT needed, and as of 2026-09-13 neither is the Python
#     half. `python-magic` and `moviepy` USED to be declared in both
#     `requirements.txt` and `pyproject.toml` while being imported by nothing —
#     a grep for `import magic`, `from magic` and `moviepy` across the whole
#     repository (not only the package this image copies) returns zero. So the
#     two declarations went, and with them 57 MB of wheels: moviepy 2 MB,
#     imageio 3 MB, imageio-ffmpeg 49 MB, proglog 1 MB, tqdm 1 MB, magic 1 MB.
#     Kept here because this is where somebody will come looking the day an
#     `import magic` appears: it will need `libmagic1` in the apt list above AND
#     the requirement back.
#   pygraphviz's build deps — NOT needed, because pygraphviz is not installed:
#     `requirements.txt:36` has it COMMENTED OUT (`#pygraphviz>=1.11.0`) while
#     `harris_matrix/enhanced_visualizer.py:89` imports it and raises an explicit
#     ImportError when it is missing. So THIS IMAGE HAS THE ENHANCED VISUALIZER
#     DISABLED, by inheritance from the requirement file. Written here because a
#     capability that is off should be readable, not discovered.
RUN set -eu; \
    apt-get update; \
    apt-get install --no-install-recommends -y \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
        graphviz; \
    rm -rf /var/lib/apt/lists/*

# ── PYTHON DEPENDENCIES, in their own layer ──────────────────────────────────
#
# `requirements.txt` and not `pip install .`, and the reason is the pin above:
# installing the package would put `pyproject.toml`'s `s3dgraphy>=0.1.42` floor
# in charge, and this image is not allowed to edit that file. The two dependency
# lists are otherwise the same length (42 each) and agree everywhere else.
#
# The application therefore runs FROM THE SOURCE TREE, which is also what
# `railway.toml` and the `Procfile` do (`gunicorn wsgi:app` from the repository
# root). Nothing needs the package installed: the templates, the static files and
# the compiled translations (`pyarchinit_mini/translations/*/LC_MESSAGES/*.mo`)
# all live inside the package directory, and the migrations are Python
# (`database/manager.py:31` → `migrations.migrate_all_tables()`), not an external
# SQL directory.
COPY requirements.txt ./
RUN set -eu; \
    : "${S3DGRAPHY_VERSION:?required — dev-stack/.env.dev holds it, and this image refuses a version nobody chose}"; \
    printf 's3dgraphy==%s\n' "${S3DGRAPHY_VERSION}" > /tmp/s3dgraphy.constraint; \
    pip install --upgrade pip; \
    pip install -r requirements.txt -c /tmp/s3dgraphy.constraint; \
    rm -f /tmp/s3dgraphy.constraint

COPY wsgi.py ./
COPY pyarchinit_mini ./pyarchinit_mini

# ── ONE WRITABLE HOME, AND BOTH CONVENTIONS POINTED AT IT ────────────────────
#
# This image CANNOT be read-only: `create_app()` does real work at import time
# (`web_interface/app.py:569-594`) — `os.makedirs(UPLOAD_FOLDER)`,
# `os.makedirs(DATABASE_FOLDER)`, `DatabaseConnection.from_url(...)`,
# `create_tables()`, `run_migrations()`. So the writable path has to exist and
# the database has to be reachable AT BOOT, not at the first request.
#
# AND HERE IS THE MEASURED CATCH, which is why `PYARCHINIT_HOME` alone is not
# enough. Six places honour that variable:
#
#   media_manager/media_handler.py:24 · web_interface/app.py:7193
#   stratigraph/sync_queue.py:77 · stratigraph/sync_orchestrator.py:101
#   services/app_setting_service.py:17 · services/backup_service.py:18
#
# …but the places that decide WHERE THE DATABASE AND THE MEDIA ROOT GO ignore it
# and hardcode `Path.home() / '.pyarchinit_mini'`:
#
#   web_interface/app.py:540      ← the database, UPLOAD_FOLDER, DATABASE_FOLDER
#   web_interface/app.py:3296, 3310, 6314          ← the media root
#   database/database_creator.py:265 · config/connection_manager.py:43
#   services/extended_matrix_excel_parser.py:113
#
# So `ENV PYARCHINIT_HOME=/srv/pyarchinit-data` on its own would have put the
# queue, the Fernet key and the backups in the volume and left THE DATABASE in
# `$HOME/.pyarchinit_mini/data/` — inside the container's writable layer, gone
# with the container. Measured before writing this file, not after.
#
# The repair that lives entirely here, with no application change: make the
# runtime user's HOME be the volume, and point the variable at the same
# directory the hardcoded half computes. Then both conventions resolve to one
# place, and everything the application keeps is in the volume:
#
#   HOME=/srv/pyarchinit-data
#   Path.home() / '.pyarchinit_mini'  →  /srv/pyarchinit-data/.pyarchinit_mini
#   PYARCHINIT_HOME                   →  /srv/pyarchinit-data/.pyarchinit_mini
#
# Making the six env-var readers agree with the eight hardcoded ones is the whole
# of it. If those hardcoded lines are ever taught to read the variable, this
# nesting can flatten — and that change belongs upstream, offered as a patch,
# not made in a fork's Dockerfile.
#
# The directory is CREATED IN THE IMAGE with the right owner for the reason
# `stratigraph-server/Dockerfile` gives for `/srv/em-data`: a named volume
# mounted on a path the image does not have is created root-owned, and a
# non-root process cannot then write its first file.
ENV HOME=/srv/pyarchinit-data \
    PYARCHINIT_HOME=/srv/pyarchinit-data/.pyarchinit_mini

# `PYARCHINIT_SECRET_KEY` is deliberately NOT set here. It is the Fernet key the
# application reads from the environment; a default baked into an image is a
# secret published in a registry.

RUN useradd --home-dir /srv/pyarchinit-data --shell /usr/sbin/nologin pyarchinit && \
    mkdir -p /srv/pyarchinit-data/.pyarchinit_mini && \
    chown -R pyarchinit:pyarchinit /srv/pyarchinit-mini /srv/pyarchinit-data
USER pyarchinit

# ── THE PORT ─────────────────────────────────────────────────────────────────
#
# 8080, because 8000 is em-server's in the same stack and two services fighting
# over a port is a diagnosis nobody enjoys. `PORT` stays overridable — Railway
# sets it, and both start commands in this repository already read it.
ENV PORT=8080
EXPOSE 8080

# ── NO HEALTHCHECK, and this is why ──────────────────────────────────────────
#
# There is no dedicated health endpoint in this application, and adding one is a
# change to a `.py` file that this image is not allowed to make.
#
# MEASURED: of 148 routes in `web_interface/app.py`, 33 carry no
# `@login_required`, and there is no global `before_request` hook adding one
# (Flask-Login is configured with `login_manager.login_view = "auth.login"` in
# `auth_routes.py:121`, which redirects rather than refuses). Of those 33,
# `GET /docs` (`app.py:897`) is the only one that takes no parameters, writes
# nothing and touches no database — it renders `docs/index.html`.
#
# So a probe IS possible, and `/docs` is what a human would curl. It is not
# wired as a HEALTHCHECK here on purpose: `/docs` answering 200 says the WSGI
# worker is up and templates render, and says NOTHING about the database — which
# is the one dependency this application resolves at import time and the one an
# orchestrator most needs to know about. A green probe that cannot see the thing
# most likely to be broken is worse than no probe, because it is believed.
#
# The declared shape of the gap: when `/health` (or any route that touches the
# database and answers anonymously) exists upstream, this is the line to add:
#
#   HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
#       CMD python -c "import os,urllib.request,sys; \
#   sys.exit(0 if urllib.request.urlopen(f\"http://127.0.0.1:{os.environ['PORT']}/health\", timeout=2).status == 200 else 1)"
#
# `--start-period=60s` and not 10s, because this application runs migrations
# before it serves, and `railway.toml` raised the worker timeout to 600s for a
# migration that took minutes.

# ── THE COMMAND ──────────────────────────────────────────────────────────────
#
# `railway.toml`'s command, with `$PORT` defaulted. `sh -c` because the flags
# read an environment variable, and a JSON-array CMD does not expand one.
#
# One worker, as both existing commands say: replicas are the orchestrator's
# business, and a process count baked into an image is a decision taken in the
# wrong place. `--threads 4` and `--timeout 600` are `railway.toml`'s, verbatim
# and for its stated reasons.
#
# PYTHONPATH is set on the command rather than trusted: gunicorn does put its
# working directory on `sys.path`, but an image that depends on that behaviour
# without saying so is an image that breaks quietly when it changes.
#
# It PREPENDS whatever PYTHONPATH the container was given instead of replacing
# it, and that is not tidiness — it is the whole `--local-s3d` mechanism. The
# dev stack runs a service against the s3Dgraphy CHECKOUT by mounting it and
# setting `PYTHONPATH: /s3dgraphy-src` in the environment
# (`dev-stack/docker-compose.local-s3d.yml`). A CMD that assigns PYTHONPATH
# outright wipes that: the mount would sit there, unused, and the container
# would go on importing the wheel from PyPI while an edit to s3Dgraphy
# stubbornly failed to show up — a silent wrong answer, which is the expensive
# kind. `${PYTHONPATH:+$PYTHONPATH:}` keeps the inherited path FIRST (the local
# source must win over the installed one) and appends the application's own.
CMD ["sh", "-c", "PYTHONPATH=\"${PYTHONPATH:+$PYTHONPATH:}/srv/pyarchinit-mini\" exec gunicorn wsgi:app --bind 0.0.0.0:${PORT:-8080} -w 1 --threads 4 --timeout 600 --graceful-timeout 30"]
