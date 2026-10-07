# NES 개발 현황

063 기준: **수동 메뉴 C의 두 형상 전체 적재·읽기 비교·FINISH·STOP를 보드 핀 모형까지 연결해 통과**. 총180,224바이트를 쓰고 읽어 순서 ACK했고 50,464,224응답 비트가 일치했다. 044 실기/GBC 기준과 061 RTL·062 펌웨어를 보존했다. 새 설치 파일과 실제 STM32 실행은 아직 없다.

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
| 제품 | 미포함, 새 SD 이미지 없음 | SNES 런타임 소비자·프레임 마감·복구 및 실제 보드 통합 |

## 작업 진입점

- [063 전체 세션 결과](../../analysis/BOARD-SESSION-RESULT.ko.md) · [계약·재현](../../docs/nes-board-session-contract.md) — 디지털 검증, 설치 후보 아님.

- [062 메뉴 연결 결과](../../analysis/MENU-DIAGNOSTIC-RESULT.ko.md) · [계약·재현](../../docs/nes-menu-diagnostic-contract.md) — 설치 후보 아님.

- [실기 진입 전 공정 점검·진척도·모델 운영 가이드](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md) — 현재063까지의 항목 상태와 남은 실기 조건. 최초061 점검과 이후 결과를 구분한다.

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
