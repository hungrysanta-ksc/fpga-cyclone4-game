# NES 개발 현황

059 기준: **044 H1 진단의 제한된 실기 성공, 059 SPI 전체 읽기 확인·실행 gate와 실제 코어 회귀 검증 완료**. NES는 아직 제품에 포함되지 않았으며 일반 게임 실행을 실기에서 검증한 상태가 아니다.

| 구분 | 현재 근거 | 남은 경계 |
| --- | --- | --- |
| 실기 기준 044 | 사용자 확인: LINK SCREEN 1→2→3→1, 자동 종료 없음, GBC 정상 플레이. 로그: protocol44/status03, RESET 복귀 성공 | 재진입·장시간 반복·SD 읽기 해시·전기 타이밍 |
| 실제 코어 통합 047–059 | 진단 2종, 8프레임, 491520픽셀. 96/80KiB SPI 적재·전체 CHECK 승인 후 실행 | 제한된 BG·팔레트·불변 CHR 진단 범위. 일반 게임·소리·입력 미완료 |
| STM32 적재 056 | 호스트26경우/18입력 거부, GPIO→RTL29024비트 일치, ARM 전체 링크 | 메뉴/START 미연결. 실제 STM32/SD 실행·물리 무결성 |
| SPI 경계 054 | 80KiB 직렬 적재·163894 검사, C 응답7784비트 일치 | 물리 무결성 확인·실기 호출 |
| ROM 부팅 053 | 360505 검사·180226 읽기, 오류 8개 시나리오. 쓰기/읽기 핀 소유권 분리 | 물리 무결성 확인, 실제 보드 클록 |
| 공유 읽기 058 | 핀 모델 CHECK180238회·RUN1024회,052 reader와4096요청 차등 | 059에서 SPI/MCU 확인 연결. 실제 보드 타이밍 미검증 |
| SPI 읽기 확인 059 |149제어 검사,MCU180224바이트 모형,5656C GPIO 응답 비트,전체 코어 회귀 | SD callback·메뉴 미연결,ARM 미호출 함수 링크만 |
| 공동 자원 059 |14180 LE,959/963 LAB,26 M9K,LAB4개 여유 |288가상핀/22미배치/PLL0. 완성 보드 fit/STA 아님 |
| 제품 | 미포함, 새 SD 이미지 없음 | SNES 런타임 소비자·프레임 마감·복구 및 실제 보드 통합 |

## 작업 진입점

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
