# NES 개발 현황

2026-10-08 검토: [완료·미완료·P1–P6 작업 계획](../../docs/development/NES-077-PROCESS-REVIEW.ko.md)을 현재 우선순위로 사용한다. 준비도4완료/7부분/1미완료이며 최신 전체 통합 미검증을 반영한 집계다. 아래 단계별 표의 당시 미완료 항목은 후속 단계에서 해소됐을 수 있으므로 현재 잔여 작업은 위 계획을 따른다.

079에서 단계2–8의 문구 쓰기·전 바이트 비교/500ms 화면 기회/RESET 재유지와 실제 보고서 저장을 연결했다. 통합185·실제 타이머5·인과대조3·ARM 호출 검사 통과. SDREPORT079는 compile-only이며 부팅/file_init·가독성·복원 패키지는 남는다. P1 부분/준비도4완료7부분1미완료 유지. [079 결과](../../analysis/REPORT-CHECKPOINT079-RESULT.ko.md).

| 구분 | 현재 근거 | 남은 경계 |
| --- | --- | --- |
| 실기 기준 044 | 사용자 확인: LINK SCREEN 1→2→3→1, 자동 종료 없음, GBC 정상 플레이. 로그: protocol44/status03, RESET 복귀 성공 | 재진입·장시간 반복·SD 읽기 해시·전기 타이밍 |
| 실제 코어 통합 047–059 | 진단 2종, 8프레임, 491520픽셀. 96/80KiB SPI 적재·전체 CHECK 승인 후 실행 | 제한된 BG·팔레트·불변 CHR 진단 범위. 일반 게임·소리·입력 미완료 |
| STM32 적재 056 | 호스트26경우/18입력 거부, GPIO→RTL29024비트 일치, ARM 전체 링크 | 메뉴/START 미연결. 실제 STM32/SD 실행·물리 무결성 |
| SPI 경계 054 | 80KiB 직렬 적재·163894 검사, C 응답7784비트 일치 | 물리 무결성 확인·실기 호출 |
| ROM 부팅 053 | 360505 검사·180226 읽기, 오류 8개 시나리오. 쓰기/읽기 핀 소유권 분리 | 물리 무결성 확인, 실제 보드 클록 |
| 공유 읽기 058 | 핀 모델 CHECK180238회·RUN1024회,052 reader와4096요청 차등 | 059에서 SPI/MCU 확인 연결. 실제 보드 타이밍 미검증 |
| SPI 읽기 확인 059 |149제어 검사,MCU180224바이트 모형,5656C GPIO 응답 비트,전체 코어 회귀 | SD callback은060에서 연결.메뉴·실기 보드는 미연결 |
| SD 연결 060 |41실행·복구/18입력 거부,2개 검사 제거 대조,C GPIO72312응답 비트,ARM 링크 |실제 STM32/SD 미실행,메뉴·실기 보드 이미지 미연결 |
| 공동 자원 059 (060 재사용) |14180 LE,959/963 LAB,26 M9K,LAB4개 여유 |288가상핀/22미배치/PLL0. 완성 보드 fit/STA 아님 |
| 물리 적재 진단 061 |135핀/PLL1,2386LE/186LAB/44M9K,내부 STA 최소0.131ns,C GPIO72312비트·3개 실패 대조 |외부 IO·정확한 부품·설치 이미지 미완료. 메뉴 호출은062에서 연결 |
| 메뉴 연결 062 |41SD/18입력 거부/16메뉴 세션·검사 제거2대조,72320C GPIO 응답 비트,최종ARM3호출 |전체C→보드 성공은063에서 연결. 진행/종료·쌍이미지·실기 미완료 |
| 전체 보드 세션 063 | 80/96KiB 전체 C GPIO,8MHz SPI/PSRAM,50,464,224응답 비트; 마지막 ACK/FINISH/STOP | 미사용84MHz 영역의 테스트 변경 명시. 외부 IO·실기·설치 쌍 미완료 |
| 하위 종료·관측 064 |FPGA22/SD24/LED16/UART5/FatFS6·native 오류 보호2·ARM 실제 호출,두 전체 SPI trace063 동일 |메뉴 offload/늦은 로그·물리 시간/가시성·설치 쌍 미완료 |
| 메뉴 복귀 065 |93 하위/복귀 검사·4개 인과 대조·16메뉴·ARM 호출,전체 SPI063 동일 |외부 IO·쌍이미지·물리 가시성/시간/재진입 미완료 |
| 파일 쌍 사전 점검 066 |061 Standard ASM/CPF·510856바이트 정확한 C 복원·18개 안전 검사,065 ARM 쌍 |실제 SD/base/menu·복원 실행·외부 IO·물리 설치 미완료 |
| 진단 메모리 067 | 정상4/실패대조4·bounded C72312비트·2372LE/184LAB/44M9K·내부30summary 통과 | 외부 min/max·전원/클록 정지·전체SPI·새ARM/쌍·실기 미완료 |
| 진단 안전 068 | 초기 대기 정상2/실패2·핀 정상4/실패4·C72312비트·routed3168경로 | 실제전압/PCB·클록정지차단·CF68 MCU/전체SPI/새쌍·실기 미완료 |
| CF68 MCU069 | READY/구형 ID 거부·하위95/상위 회귀·대조7·bounded C72320비트·ARM 호출 | 전체 물리 SPI80/96KiB·새 쌍·외부 조건/실기 미완료 |
| 전체 CF68 세션070 |180224byte 실제 핀 쓰기/읽기/ACK·901152프레임·50464224응답비트·초기READY·대조1 | 새ASM/ARM 쌍·실제SD복원·외부전기/실기 미완료 |
| SD 원본 수집072 | read-only 입력4·헤더6/reset·새TXT/allbyte readback·별도ARM | 실제 SD 실행/TXT·메뉴분류·독립백업/복원·CF68 실기 미완료 |
| 제품 | 미포함, 새 SD 이미지 없음 | SNES 런타임 소비자·프레임 마감·복구 및 실제 보드 통합 |

## 작업 진입점

- [070 결과](../../analysis/CF68-SESSION-RESULT.ko.md) · [전체 CF68 계약·재현](../../docs/nes-cf68-session-contract.md). 검증후보070/MCU069/FPGA068,설치 불가.

- [069 결과](../../analysis/CF68-MCU-RESULT.ko.md) · [CF68 MCU 계약·재현](../../docs/nes-cf68-mcu-contract.md). MCU069/FPGA068, 설치 불가.

- [068 결과](../../analysis/DIAG-SAFETY-RESULT.ko.md) · [초기 대기/외부 예산 계약](../../docs/nes-diag-safety-contract.md). FPGA 후보CF68,설치 불가.

- [067 결과](../../analysis/DIAG-MEMORY-RESULT.ko.md) · [계약/재현](../../docs/nes-diag-memory-contract.md) · [다음 Sol 작업 상세 인계](../../docs/development/NES-067-SOL-HANDOFF.ko.md). 이전067 후보CF67, 설치 불가.

- [066 파일 쌍 결과](../../analysis/PAIR-PREFLIGHT-RESULT.ko.md) · [계약·재현·실기 시험표](../../docs/nes-pair-preflight-contract.md) — 오프라인 준비, 설치 승인 아님.

- [065 메뉴 복귀 결과](../../analysis/MENU-RETURN-RESULT.ko.md) · [계약·재현](../../docs/nes-menu-return-contract.md) — compile-only, 설치 후보 아님.

- [064 하위 종료·오류 결과](../../analysis/DIAG-RECOVERY-RESULT.ko.md) · [계약·재현](../../docs/nes-diag-recovery-contract.md) — compile-only, 설치 후보 아님.

- [063 전체 세션 결과](../../analysis/BOARD-SESSION-RESULT.ko.md) · [계약·재현](../../docs/nes-board-session-contract.md) — 디지털 검증, 설치 후보 아님.

- [062 메뉴 연결 결과](../../analysis/MENU-DIAGNOSTIC-RESULT.ko.md) · [계약·재현](../../docs/nes-menu-diagnostic-contract.md) — 설치 후보 아님.

- [실기 진입 전 공정 점검·진척도·모델 운영 가이드](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md) — 현재069까지의 항목 상태와 남은 실기 조건. 최초061 점검과 이후 결과를 구분한다.

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
