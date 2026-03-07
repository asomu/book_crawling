# Session Handoff

## What Was Built

- script 기반 구현을 `legacy/`로 격리
- `app/` 아래 새 FastAPI + SQLite + Playwright 구조 생성
- Yes24 adapter, parser, worker, 이미지 파이프라인, 운영 UI 구현
- 상단 헤더를 단일 카드 구조로 정리하고 앱 이름을 `Book Crawling 후딱 v2`로 통일
- 이벤트 타임라인에 started / completed / job finish / error 라벨과 색상 구분 추가
- Yes24 중복 `infoset_chYes` DOM에서도 실제 상세 이미지를 선택하도록 파서 보정

## Runtime Facts

- 기본 DB: `data/book_crawling_v2.db`
- 기본 asset 저장: `data/assets/<isbn>/`
- 로그: `logs/app.log`
- browser storage state: `data/browser/yes24-state.json`
- 비성인 도서는 로그인 없이 익명 수집한다.
- Yes24 성인인증 페이지는 `adult_verification_required`로 실패 기록한다.
- job 상세와 도서 목록에서 생성 이미지 ZIP 다운로드를 지원한다.
- 메타데이터는 SQLite에 저장하고, 이미지 파일은 `data/assets/<isbn>/`에 저장한다.
- 동일 ISBN 재수집 시 `books`는 upsert되고 `image_assets`는 기존 자산을 지운 뒤 최신 5종으로 교체한다.

## If The Next Session Continues

1. 의존성을 설치하고 앱을 실제 부팅
2. Yes24 실계정으로 healthcheck 확인
3. live HTML을 기반으로 parser 선택자 검증
4. pytest 실행 후 실패하는 테스트나 누락 보강
