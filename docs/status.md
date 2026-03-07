# Status

## Current Scope

- Yes24 익명 우선 수집 흐름
- ISBN 기반 job 생성
- in-process worker
- 책 메타데이터 upsert
- 이미지 5종 생성
- 작업/이벤트/실패 이력 UI
- 통합 헤더 카드 UI와 상단 내비게이션
- started, completed, job finish, error를 구분하는 라벨형 이벤트 타임라인
- 자격증명 저장과 healthcheck
- 성인인증 도서 예외 처리
- job 결과 ZIP 자동 다운로드
- 도서 목록 선택 ZIP 다운로드
- live DOM 기준 상세 이미지 선택 보정

## Known Gaps

- 브라우저 기반 live integration test는 아직 포함하지 않음
- Alembic migration은 초기 스키마만 제공
- asset versioning은 아직 latest-only 방식
- multi-site adapter factory는 아직 구현하지 않음

## Next Recommended Work

1. Yes24 실계정 smoke test 자동화
2. selector drift 감지용 snapshot fixture 확대
3. asset versioning 또는 export archive
4. 예약 실행과 job cancel 지원

## Session Closeout

- 런타임 산출물 `.codex/`는 커밋 제외 대상으로 `.gitignore`에 반영했다.
- 현재 저장 구조는 `SQLite + data/assets 파일 저장`이며, 동일 ISBN 재수집 시 `books`는 갱신되고 `image_assets`는 latest-only로 교체된다.
