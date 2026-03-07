# ADR 002: Yes24 Only for v1

## Status

Accepted

## Context

기존 코드상 다중 사이트 지원 흔적은 있었지만 실제 안정성은 사이트별로 크게 달랐다. v1의 목표는 운영 가능한 완성도다.

## Decision

v1은 `Yes24`만 공식 지원한다.

## Consequences

- 장점: 테스트 범위 축소, selector 변경 대응 집중, UI/worker/저장 구조 완성도 상승
- 단점: 교보문고/알라딘은 후속 단계까지 지원되지 않음
