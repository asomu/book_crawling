# Status

## Current Scope

- Yes24 익명 우선 수집 흐름
- ISBN 기반 job 생성
- in-process worker
- 책 메타데이터 upsert
- 이미지 5종 생성
- 생성 이미지 파일명을 `책제목_variant.jpg` 규칙으로 저장
- 작업/이벤트/실패 이력 UI
- 통합 헤더 카드 UI와 상단 내비게이션
- started, completed, job finish, error를 구분하는 라벨형 이벤트 타임라인
- 자격증명 저장과 healthcheck
- 성인인증 도서 예외 처리
- job 결과 ZIP 자동 다운로드
- 도서 목록 선택 ZIP 다운로드
- 도서 목록 선택 삭제
- 도서 목록 컬럼 정렬
- Windows PowerShell 개발 실행 시 Playwright Chromium 자동 점검 및 설치
- live DOM 기준 상세 이미지 선택 보정

## Known Gaps

- 브라우저 기반 live integration test는 아직 포함하지 않음
- Alembic migration은 초기 스키마만 제공
- asset versioning은 아직 latest-only 방식
- multi-site adapter factory는 아직 구현하지 않음
- Windows 개발 환경에서 `scripts/test.sh`, `scripts/smoke.sh`를 직접 실행하려면 bash 호환 셸이 필요함

## Next Recommended Work

1. Yes24 실계정 smoke test 자동화
2. selector drift 감지용 snapshot fixture 확대
3. asset versioning 또는 export archive
4. Windows용 `test` / `smoke` PowerShell 래퍼 추가
5. 예약 실행과 job cancel 지원

## Session Closeout

- 런타임 산출물 `.codex/`는 커밋 제외 대상으로 `.gitignore`에 반영했다.
- 현재 저장 구조는 `SQLite + data/assets 파일 저장`이며, 동일 ISBN 재수집 시 `books`는 갱신되고 `image_assets`는 latest-only로 교체된다.
- 새 Windows 개발 실행 흐름은 `scripts/dev.ps1`에서 Playwright 브라우저 유무를 먼저 확인한 뒤 부족하면 현재 `.venv` 기준으로 자동 설치한다.
- `/books` 화면은 선택 ZIP 다운로드 외에 선택 삭제와 컬럼별 오름차순/내림차순 정렬을 지원한다.
- 새로 생성되는 이미지 파일은 `data/assets/<isbn>/<정리된 책제목>_<variant>.jpg` 형식으로 저장된다.
