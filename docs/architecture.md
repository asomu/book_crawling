# Architecture Overview

## Goal

`book_crawling v2`는 Yes24 운영팀이 로컬 브라우저 기반 UI로 책 데이터를 수집하고, 실패를 재시도하고, 산출 이미지를 관리할 수 있게 만드는 내부 도구다.

## Runtime Topology

- `FastAPI` 웹 서버
- `SQLite` 데이터베이스
- `CrawlWorker` 백그라운드 스레드 1개
- `Playwright Chromium` 브라우저 세션
- 파일 저장소: `data/assets`, `data/browser`, `data/snapshots`

## Core Flow

1. 사용자가 대시보드에서 ISBN 목록으로 job 생성
2. `crawl_jobs`, `crawl_job_items`, `crawl_events`에 초기 레코드 저장
3. worker가 pending job을 가져와 익명 브라우저 세션으로 Yes24를 탐색
4. ISBN별 검색 결과 후보를 탐색하고 상세 페이지에서 ISBN13를 검증한다.
5. 성인인증 게이트가 감지되면 해당 item만 `adult_verification_required`로 실패 처리한다.
6. 메타데이터 upsert, 이미지 5종 생성, 이벤트 기록
7. 부분 실패 시 job status는 `partial_success`
8. 실패 항목 재시도 시 해당 item만 `pending`으로 되돌리고, 성공 결과는 ZIP 다운로드할 수 있다.

## Module Boundaries

- `app/domain`
  - 상태 enum, 고정 오류 코드, Pydantic payload, 자격증명 암호화
- `app/infrastructure/crawlers/yes24`
  - Yes24 전용 브라우저 로직과 HTML 파싱
- `app/infrastructure/images`
  - cover, y1000, coupang, naver, detail 이미지 생성
- `app/infrastructure/db`
  - SQLAlchemy 모델과 session factory
- `app/infrastructure/storage`
  - 파일 경로 규칙, snapshot 저장
- `app/worker`
  - job execution orchestration
- `app/web`
  - 라우트, 템플릿, HTMX polling UI

## Failure Model

고정 오류 코드는 다음만 사용한다.

- `login_failed`
- `adult_verification_required`
- `search_no_result`
- `detail_page_not_found`
- `selector_changed`
- `image_download_failed`
- `image_transform_failed`
- `storage_failed`

## Data Ownership

- 책 메타데이터의 진실 원천: `books`
- 실행 이력의 진실 원천: `crawl_jobs`, `crawl_job_items`, `crawl_events`
- 최신 이미지 산출물의 진실 원천: `image_assets`
- 브라우저 로그인 세션: `data/browser/yes24-state.json`
- 다운로드 아카이브는 요청 시점에 `image_assets`와 `data/assets`를 기준으로 즉시 생성한다.

## Extension Strategy

- 새 사이트 추가 시 `CrawlerAdapter` 계약을 만족하는 어댑터를 추가
- parser selector 변경은 `app/infrastructure/crawlers/yes24` 내부에서만 수정
- worker는 site별 adapter factory로 확장 가능
