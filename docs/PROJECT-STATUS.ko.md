# 현재 개발 상태
기준일: 2026-10-04

## 공개 기준선

**sd2snesHST 0.9.0을 공개했습니다.** [릴리스](https://github.com/hungrysanta-ksc/sd2snesHST/releases/tag/v0.9.0)의 공개 시각은 2026-10-04 13:40:26 UTC입니다. 제품과 내부 GBC C44의 대응은 개발 저장소에서만 설명합니다.

- 실행 구현 커밋: `35ef4aef14fc6abef6495a980b7f00f257e5174f`.
- 대응 소스 묶음 커밋: `a2b1fb59390a96f70bbc8588a63e465831e7e247`.
- 배포 저장소 머지 커밋: `5bf51452505c5b2f461dc2320b0527328472aa01`.
- 최종 파일명·서버 SHA256·순서: [제품 매핑](../release/product-version-map.json).
- 실기 성공 범위: [호환성 기록](COMPATIBILITY.ko.md). C44는 load/cap/state 파일 로그를 끄되 저장·설정·통신을 유지했고 사용자가 최종 점검을 통과했습니다.
- 게임 실행은 Gameboy_MiSTer 기반 FPGA 이식, CGB 부트는 SameBoy 유래입니다.

## 다음 작업: NES

사용자가 NES 구현 착수를 요청했습니다. [NES 인계 계획](../cores/nes/HANDOFF.ko.md)과 [GBC 이식 회고](development/GBC-PORTING-LESSONS.ko.md)를 기준으로 후보 선정 → 독립 합성·예산 → 최소 화면/입력/음향 통합 → 실기 후보 → 매퍼/저장 확장을 진행합니다. 아직 NES 합성·구동·실기 성공은 확인하지 않았고 편입 버전·일정도 정하지 않았습니다. PCE는 조사 대기입니다.

0.9.0 바이너리·소스·기존 저장을 보존하고 NES는 별도 FPGA 이미지/작업 브랜치로 진행합니다. 공통 MCU나 화면 경로가 바뀌면 기존 GBC와 코어 전환 회귀를 수행합니다. 문서 인계 자체는 실행 코드를 바꾸지 않습니다.

## 저장소와 근거

개발 저장소는 구현·재현·검증·실패 원인을 관리하고 [배포 저장소](https://github.com/hungrysanta-ksc/sd2snesHST)는 사용자 안내와 제품 릴리스를 관리합니다. distribution/ 사본과 C43/C44 준비 문서의 공개 전 문구는 역사적 기록입니다. 사용자 문서의 최신 확정본을 과거 사본으로 덮어쓰지 않습니다.

[소유자 승인 라이선스](../LICENSE.md), [대응 소스](SOURCE-BUNDLE.ko.md), [최종 준비 검증](FINAL-0.9.0.ko.md), [개발 문서 안내](README.md)를 참조합니다. 2026-09-24 및 C10 시점 기록의 미완료 상태를 현재 상태로 해석하지 않습니다. 실기 표본과 양수 constrained slack은 전체 보드 timing/CDC signoff가 아닙니다.
