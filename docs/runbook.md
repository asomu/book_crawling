# Runbook

## 처음 실행

1. 가상환경 생성
2. `pip install -e ".[dev]"` 또는 `uv pip install -e ".[dev]"`
3. `playwright install chromium`
4. `uvicorn app.main:app --reload`
5. 필요하면 `/settings`에서 Yes24 자격증명 저장

### 개발 서버 스크립트

- 실행: `./scripts/dev.sh`
- 중지: `./scripts/stop.sh`
- 다른 포트 실행: `PORT=8001 ./scripts/dev.sh`
- `./scripts/dev.sh`는 포트 충돌 시 PID, 상태, 명령어를 바로 보여준다.

## 주요 경로

- `/` 대시보드
- `/books` 도서 목록
- `/settings` 자격증명 및 상태 점검

## 장애 대응

### `login_failed`

- 이 오류는 설정 화면의 로그인 상태 점검에서만 주로 확인한다.
- 수집 job 자체는 익명 브라우징으로 실행되므로 비성인 도서는 계속 수집 가능하다.
- 계정이 꼭 필요하면 자격증명을 다시 저장하고 `/settings`의 상태 점검을 실행한다.
- 반복 로그인 실패나 캡차가 발생하면 `data/browser/yes24-state.json`을 삭제하고 충분한 시간 후 다시 시도한다.

### `adult_verification_required`

- Yes24 성인인증 게이트가 감지된 경우다.
- 현재 v2는 익명 수집을 우선으로 하므로 이 항목은 정상적인 실패로 간주한다.
- 해당 책은 제외하거나, 별도 운영 절차로 로그인 상태를 확보한 뒤 후속 대응한다.

### `search_no_result`

- ISBN 입력값 확인
- Yes24 검색 결과 페이지에서 실제 노출 여부 확인

### `selector_changed`

- `data/snapshots/`에 저장된 HTML 확인
- `app/infrastructure/crawlers/yes24/parser.py` 수정

### 이미지 오류

- `resource/쿠팡_아이콘.png`, `resource/네이버_아이콘.png` 존재 여부 확인
- 대상 이미지 URL 접근 가능 여부 확인

## 다운로드

- 작업 상세 `/jobs/{id}`에서 성공한 항목은 ZIP으로 즉시 다운로드할 수 있다.
- 작업이 `success` 또는 `partial_success` 상태가 되면 브라우저에서 자동 다운로드를 한 번 시도한다.
- `/books` 목록에서는 체크한 도서만 묶어서 ZIP으로 다운로드할 수 있다.
