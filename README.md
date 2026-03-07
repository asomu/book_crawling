# Book Crawling 후딱 v2

Yes24 운영용 내부 웹앱입니다. ISBN 목록으로 크롤링 작업을 만들고, 작업 진행 상태와 실패 원인을 확인하고, 수집한 책 메타데이터와 생성 이미지를 관리합니다.

## Stack

- FastAPI
- Jinja2 + HTMX + Tailwind CDN
- SQLAlchemy + SQLite
- Playwright
- Pillow
- Alembic

## Quick Start

### 1. `uv` 사용

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
playwright install chromium
uv run uvicorn app.main:app --reload
```

### 2. 표준 `venv` 사용

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
playwright install chromium
uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`으로 접속합니다.

## Launch Modes

- 로컬 서버만 실행: `python launcher.py server --host 127.0.0.1 --port 8000`
- Windows 데스크톱 셸 실행: `python launcher.py desktop`

데스크톱 모드는 `pywebview` 기반 창을 띄우고 내부에서 FastAPI 서버를 랜덤 localhost 포트로 실행합니다.
설치형 Windows 배포에서는 모든 쓰기 데이터가 `%LOCALAPPDATA%\\BookCrawling` 아래에 저장됩니다.

## Shortcut Commands

```bash
./scripts/bootstrap.sh
./scripts/dev.sh
./scripts/stop.sh
./scripts/test.sh
./scripts/smoke.sh
```

또는:

```bash
make bootstrap
make dev
make stop
make test
make smoke
```

`./scripts/dev.sh`는 기본 포트 `8000`이 이미 사용 중이면 PID와 명령어를 보여주고 종료합니다. 다른 포트가 필요하면 `PORT=8001 ./scripts/dev.sh`처럼 실행할 수 있습니다.

## 운영 흐름

1. 필요하면 `/settings`에 Yes24 자격증명을 저장합니다. 저장하지 않아도 비성인 도서는 익명 수집이 가능합니다.
2. 대시보드에서 ISBN 목록으로 작업을 생성합니다.
3. worker가 pending job을 순차 처리합니다.
4. `/jobs/{id}`에서 항목별 성공/실패와 로그를 확인하고, 성공 결과는 ZIP으로 즉시 내려받을 수 있습니다.
5. `/books`에서 누적된 도서 데이터와 생성 이미지를 검색하고, 선택 항목만 묶어서 ZIP으로 내려받을 수 있습니다.

## Directory Guide

```text
app/
  config/            settings and runtime paths
  domain/            enums, errors, schemas, credential service
  infrastructure/
    crawlers/yes24/  Playwright adapter and parser
    db/              SQLAlchemy models and engine
    images/          image generation pipeline
    storage/         filesystem path rules
  web/               FastAPI routes, templates, static assets
  worker/            in-process background worker
docs/
  adr/               architecture decision records
legacy/              previous script-based implementation
```

## Tests

```bash
pytest
```

## Notes

- v1 범위는 Yes24만 운영 지원합니다.
- 성인인증이 필요한 도서는 익명 수집 대상에서 제외되며 `adult_verification_required`로 기록됩니다.
- 자동 배치, 다중 사이트 동시 운영, 자동 업데이트는 후속 단계입니다.
- 기존 스크립트 기반 구현은 `legacy/` 아래에 보관했습니다.

## Windows Packaging

Windows 패키징은 Windows PC/VM에서만 수행합니다.

```bash
pip install -e ".[dev,windows]"
python scripts/build_windows.py
```

빌드 결과:

- 앱 번들: `dist/BookCrawling/`
- 설치 프로그램: `dist/installer/BookCrawlingSetup.exe`

패키징 스크립트는 다음을 수행합니다.

1. Playwright Chromium을 앱 번들용으로 staging 합니다.
2. WebView2 Evergreen Bootstrapper를 다운로드합니다.
3. PyInstaller `onedir` 앱을 생성합니다.
4. Inno Setup 설치 파일을 생성합니다.
