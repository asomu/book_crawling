# ADR 001: FastAPI + SQLite + Playwright

## Status

Accepted

## Context

운영자는 5명 이하이고, 대규모 분산 인프라보다 유지보수성과 빠른 수정이 중요하다. 기존 스크립트 구조는 UI, 실행 이력, 데이터 관리가 약했다.

## Decision

- 웹 서버는 `FastAPI`
- UI는 `Jinja2 + HTMX`
- 데이터 저장은 `SQLite`
- 크롤링 엔진은 `Playwright`
- 이미지 가공은 `Pillow`

## Consequences

- 장점: 단일 저장소, 낮은 운영 비용, Python 자산 일원화, 빠른 장애 수정
- 단점: 고동시성 작업이나 대규모 멀티유저 환경에는 적합하지 않음
