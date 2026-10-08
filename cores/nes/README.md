# NES 개발 현황

현재106: CF86의 외부 지연 예산을 원시3168경로에서 재계산하고, 최소 조건이 CE 비활성 간격임을 확인했다. 실기 미결 조건을 외부 전기적 범위와 공통고장 처리 두 항목으로 좁히고 관측·종료 절차를 구체화했다.

**작업 의미:** 실기 디버깅 기반의 진입 조건 분석이다. 필요한 외부 근거의 수치와 관측 판정 기준이 명확해졌다. 새로운 코어 배선·게임 기능·실기 PASS를 추가한 작업은 아니다.

107은 반복 분석 대신 미결 E1/E2를 닫는 근거 확보 또는 설계 변경을 선택한다. 먼저 기존 보드 설계·핀/전원 자료에서 전기적 상한을 확보할 수 있는지 조사하고, 없으면 필요한 측정과 공통고장 대안을 구체적으로 보고한다. 조건이 열린 상태에서 또 패키지 준비 PR을 반복하지 않는다. 준비도4완료/7부분/1미완료, 설치 미승인.

## 작업 진입점

- [현재 인계](HANDOFF.ko.md) · [106 결과](../../analysis/TRIAL106-RESULT.ko.md) · [관측 초안](../../docs/nes-trial106-observation.ko.md)
- [105 파일조합](../../analysis/PAIR105-RESULT.ko.md) · [104 통합](../../analysis/TIMER104-RESULT.ko.md)

## 이전 단계별 근거

- [070 결과](../../analysis/CF68-SESSION-RESULT.ko.md) · [전체 CF68 계약·재현](../../docs/nes-cf68-session-contract.md). 검증후보070/MCU069/FPGA068,설치 불가.

- [069 결과](../../analysis/CF68-MCU-RESULT.ko.md) · [CF68 MCU 계약·재현](../../docs/nes-cf68-mcu-contract.md). MCU069/FPGA068, 설치 불가.

- [068 결과](../../analysis/DIAG-SAFETY-RESULT.ko.md) · [초기 대기/외부 예산 계약](../../docs/nes-diag-safety-contract.md). FPGA 후보CF68,설치 불가.

- [067 결과](../../analysis/DIAG-MEMORY-RESULT.ko.md) · [계약/재현](../../docs/nes-diag-memory-contract.md) · [다음 Sol 작업 상세 인계](../../docs/development/NES-067-SOL-HANDOFF.ko.md). 이전067 후보CF67, 설치 불가.

- [066 파일 쌍 결과](../../analysis/PAIR-PREFLIGHT-RESULT.ko.md) · [계약·재현·실기 시험표](../../docs/nes-pair-preflight-contract.md) — 오프라인 준비, 설치 승인 아님.

- [065 메뉴 복귀 결과](../../analysis/MENU-RETURN-RESULT.ko.md) · [계약·재현](../../docs/nes-menu-return-contract.md) — compile-only, 설치 후보 아님.

- [064 하위 종료·오류 결과](../../analysis/DIAG-RECOVERY-RESULT.ko.md) · [계약·재현](../../docs/nes-diag-recovery-contract.md) — compile-only, 설치 후보 아님.

- [063 전체 세션 결과](../../analysis/BOARD-SESSION-RESULT.ko.md) · [계약·재현](../../docs/nes-board-session-contract.md) — 디지털 검증, 설치 후보 아님.

- [062 메뉴 연결 결과](../../analysis/MENU-DIAGNOSTIC-RESULT.ko.md) · [계약·재현](../../docs/nes-menu-diagnostic-contract.md) — 설치 후보 아님.

- [실기 진입 전 공정 점검·진척도·모델 운영 가이드](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md) — 현재096 요약과 과거 항목별 점검표. 최초061 점검과 이후 결과를 구분한다.

- [061 결과](../../analysis/BOARD-DIAGNOSTIC-RESULT.ko.md) · [물리 진단 계약](../../docs/nes-board-diagnostic-contract.md)

- [060 결과](../../analysis/SD-READBACK-RESULT.ko.md) · [SD 읽기 비교 계약](../../docs/nes-sd-readback-contract.md)

- [059 결과](../../analysis/SPI-READBACK-RESULT.ko.md) · [SPI 읽기 확인 계약](../../docs/nes-spi-readback-contract.md)

- [058 결과](../../analysis/ROM-READBACK-PORT-RESULT.ko.md) · [공유 읽기 포트 계약](../../docs/nes-rom-readback-port-contract.md)

- [057 결과](../../analysis/ROM-GEOMETRY-RESULT.ko.md) · [형상 연결 계약](../../docs/nes-rom-geometry-contract.md) · [readback 후속 설계](../../docs/nes-rom-readback-plan.md)

- [056 결과](../../analysis/MCU-LOADER-RESULT.ko.md) · [STM32 적재 계약](../../docs/nes-mcu-loader-contract.md)
- [055 결과](../../analysis/SPI-LIVE-RESULT.ko.md) · [SPI 실제 코어 계약](../../docs/nes-spi-live-contract.md)
- [054 결과](../../analysis/SPI-BOOT-RESULT.ko.md) · [SPI 계약](../../docs/nes-spi-boot-contract.md)
- [현재 인계와 다음 작업](HANDOFF.ko.md)
- [공개 재현 시험과 로컬 의존성](REPRODUCING.ko.md)
- [단계별 진전](MILESTONES.ko.md)
- [실기 044 관측](../../analysis/H1-HARDWARE-044-RESULT.ko.md), [053 결과](../../analysis/ROM-BOOT-RESULT.ko.md), [053 계약](../../docs/nes-rom-boot-contract.md)
- [출처·고정 upstream·보류 파일](../../analysis/source-lock.json), [공개 구현 해시](publication-sources.json)
- [다른 코어에도 적용할 작업 방식](../../docs/development/MILESTONE-WORKFLOW.ko.md)

구현은 `src/nes`, 시험은 `tests/nes-functional`, 자체 SNES 진단 생성기는 `snes/video_probe`, 도구는 `tools/nes_*`·`tools/run_nes_*`에 있다. 기존 GBC 소스를 이동하거나 새 NES 작업에 맞춰 변경하지 않았다.

기존 문서에 반복 누적된 과거 상태는 [이전 README 이력](history/README-053.md)과 [이전 인계 이력](history/HANDOFF-053.ko.md)에 보존한다. 이력 속 ‘현재/다음’ 표현은 당시 기준이며, 현재 판단은 이 문서와 위 인계 문서를 따른다.
