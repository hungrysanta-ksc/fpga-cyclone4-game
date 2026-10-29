# 코어 현황

프로젝트 목표와 최신 상태는 [루트 README](../README.md), 상세 판정은 [프로젝트 현황](../docs/PROJECT-STATUS.ko.md)에서 관리한다.

| 코어 | 현재 상태 | 진입점 |
|---|---|---|
| GB/GBC | **추가 성공·0.9.0 공개** | [G13C44 기준선·빌드·호환성](gbc/README.md) |
| NES | **개발 중**: 제한 NROM474 실기 평균23.59fps, 정상 구간 약24fps | [현황](nes/README.md) · [현재 인계](nes/HANDOFF.ko.md) |
| PC Engine | 조사 대기, 구현 미완료 | [조사 범위](pce/README.md) |

[등록부](registry.json)는 현재 선택과 근거 경로만 유지한다. 후보별 실험·과거 실기는 [PR 기록](../docs/progress/README.md)과 그 상세 근거에서 읽는다. 새 코어는 [제안서](CORE-PROPOSAL.ko.md)·[포팅 절차](../docs/PORTING-PLAYBOOK.ko.md)를 따른다. 현재 성능 개발은 사용자 요청으로 중지했다.
