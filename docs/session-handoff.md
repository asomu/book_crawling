# Session Handoff

## What Was Built

- script 기반 구현을 `legacy/`로 격리
- `app/` 아래 새 FastAPI + SQLite + Playwright 구조 생성
- Yes24 adapter, parser, worker, 이미지 파이프라인, 운영 UI 구현
- 상단 헤더를 단일 카드 구조로 정리하고 앱 이름을 `Book Crawling 후딱 v2`로 통일
- 이벤트 타임라인에 started / completed / job finish / error 라벨과 색상 구분 추가
- Yes24 중복 `infoset_chYes` DOM에서도 실제 상세 이미지를 선택하도록 파서 보정
- Yes24 ISBN 해석 흐름을 `홈페이지 워밍업 -> 검색 -> 메인 리다이렉트면 로그인 재시도 -> 상세 진입`으로 분리
- 설정 페이지에서 자격증명을 비우면 익명 모드로 되돌리고, 저장된 자격증명은 작업 실행 시 자동으로 적용
- 책 다운로드 ZIP에 이미지와 함께 `books.csv` 메타데이터 파일을 포함하고, 내부 폴더명은 ISBN 대신 책 제목을 사용
- Windows 패키징에서 Playwright 브라우저 번들 경로와 `winget` 설치형 Inno Setup 탐지를 보정
- Windows 설치본의 stale `.desktop.lock` PID 검사 오류를 WinAPI 기반 단일 실행 체크로 수정

## Runtime Facts

- 기본 DB: `data/book_crawling_v2.db`
- 기본 asset 저장: `data/assets/<isbn>/`
- 로그: `logs/app.log`
- browser storage state: `data/browser/yes24-state.json`
- 비성인 도서는 로그인 없이 익명 수집한다.
- Yes24 성인인증 페이지는 `adult_verification_required`로 실패 기록한다.
- job 상세와 도서 목록에서 생성 이미지 ZIP 다운로드를 지원하고, ZIP 루트에 `books.csv`를 함께 넣는다.
- ZIP 내부 폴더명은 책 제목 기준이며, 중복 제목은 `제목 (ISBN)`으로 구분하고 Windows 금지 문자는 `_`로 치환한다.
- 메타데이터는 SQLite에 저장하고, 이미지 파일은 `data/assets/<isbn>/`에 저장한다.
- 동일 ISBN 재수집 시 `books`는 upsert되고 `image_assets`는 기존 자산을 지운 뒤 최신 5종으로 교체한다.
- Windows 설치형 배포에서는 모든 쓰기 데이터가 `%LOCALAPPDATA%\BookCrawling` 아래에 저장된다.
- 저장된 Yes24 자격증명은 상태 점검과 작업 실행에서 자동 사용되며, 비밀번호는 UI에 다시 표시하지 않는다.
- Windows desktop launcher는 stale PID가 남아 있어도 `.desktop.lock`을 회복하고 정상 기동한다.

## If The Next Session Continues

1. 설치형 Windows 배포를 실제 새 PC/VM에 설치해서 WebView2 bootstrap, 다운로드, Yes24 로그인 흐름 확인
2. Yes24 실계정으로 healthcheck와 자동 로그인 재시도 흐름 확인
3. live HTML을 기반으로 ISBN 검색 리다이렉트 케이스를 더 수집해서 resolver fallback을 다듬기
4. 전체 `pytest`에서 남아 있는 Windows `KeyboardInterrupt` 종료 이슈를 정리
