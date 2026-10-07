# NES 검증 재현 범위

공개 저장소에는 자체 작성한 연결 RTL·진단 생성기·시험과 결과 요약을 보관한다. 전체 NES 게임 실행 파일이나 실기용 053 이미지는 없다.

## 공개 파일만으로 실행하는 메모리 회귀

Python 3와 SystemVerilog를 지원하는 설치된 Questa가 필요하다. 유효한 라이선스 실행 환경에서 아래를 실행한다. 이 명령은 라이선스를 설치하거나 변경하지 않는다.

```powershell
python -B tools/run_nes_public_units.py --questa-bin $QUESTA --out $FRESH_OUTPUT
```

`$QUESTA`는 Questa 실행 파일 디렉터리, `$FRESH_OUTPUT`은 존재하지 않는 ASCII 경로다. 이 프로젝트의 Windows 개발 호스트에서는 사용자 지침의 기존 FLOAT wrapper를 `-RunOnly -AfterSmokeScript <위 명령을 실행하는 절대 경로 작업 파일>`로 실행한다. 라이선스 파일·서버 로그는 공개하지 않는다. 서버가 작업 사이에 꺼지는 것은 정상이며 새 유료 라이선스가 필요하다는 뜻이 아니다.

| 시험 | 공개 입력 | 통과 조건 |
| --- | --- | --- |
| 049 로컬 RAM | 자체 생성 패턴 | 153604 검사, 12 KiB, 완료 초기화 3회·중단 1회 |
| 051 조기 ROM 서비스 | 자체 생성 주소·응답 | 4168 검사, 525 요청, 오류 6종 |
| 053 핀 적재·부팅 | 자체 생성 바이트, 초기값 없는 RAM 핀 모델 | 360505 검사, 180226 읽기, 이미지 2종, 오류 시나리오 8종 |

원시 compile/simulation 로그와 실행 소스 해시는 출력 폴더에 남긴다. 종료 코드 0뿐 아니라 정확한 PASS 표식과 Fatal/Error 부재를 요구한다. 이 시험은 실제 NES CPU/PPU 실행·물리 배치·실기 시험을 대신하지 않는다.

## 별도 도구 또는 로컬 자료가 필요한 경로

| 경로 | 필요한 자료 | 공개 자료의 의미 |
| --- | --- | --- |
| 초기 CPU/PPU 진단 | [고정 upstream](../../analysis/source-lock.json), Questa, 자체 진단 생성기 | 코드 채택 보류가 남아 upstream HDL은 vendoring하지 않음 |
| 047–053 실제 코어 통합·공동 fit | 해시로 고정된 014/018 생성 코어, 앞 단계 진단/메모리·전송 산출물, Quartus | 현재 `analysis/local-*` 의존. 깨끗한 clone만으로 전체 재현을 보장하지 않음 |
| `verify_nes_*.py`의 과거 증거 감사 | 해당 후보의 원시 로그·상태 스냅샷·manifest 대상 파일 | 공개 JSON은 과거 실행의 요약·색인. 대상 원본 부재를 통과로 처리하지 않음 |
| 참조 에뮬레이터 | 해당 에뮬레이터·런타임 및 자체 진단 생성물 | 일부 과거 스크립트의 `C:/works/dotnet` 설치 가정은 환경별 조정 필요 |
| 044 하드웨어 | 후보에 맞는 MCU/FPGA 쌍, 보드·SD·복구 백업 | [실기 관측](../../analysis/H1-HARDWARE-044-RESULT.ko.md)은 사용자 보고와 로그 해석 |

전체 코어 재현 절차를 공개 upstream에서 다시 구성하는 일은 별도 남은 작업이다. 보류 파일 4개(`regs_savestates.sv`, `bus_savestates.vhd`, `dpram.vhd`, `mappers/MMC3.sv`)의 채택 판단을 건너뛰지 않는다.

## 소스 출처와 버전

`src/nes`의 25개 파일은 자체 작성한 연결/진단 코드이며 기존 MIT 헤더를 보존했다. 실제 NES CPU/PPU upstream을 포함하지 않는다. `src/nes/nes_h1_board_bus.sv`와 MCU 파일은 과거 기반 소스다. **044는 `tools/nes_h1_sampling.py` 등의 고정 변환 경로로 생성**하며 오래된 원본 조합을 최신 보드 이미지로 빌드하지 않는다.

공개 정리 중 제품 RTL·C 코드·기존 시험/생성기의 바이트를 바꾸지 않았다. [공개 파일 해시](publication-sources.json)는 가져온 구현 파일을 고정한다. 과거 상태 설명은 `history/`에 링크 위치·라이선스 식별자만 정리해 보관하며 현재 진입점의 상태를 우선한다. 기존 artifact manifest는 원래 로컬 체크포인트용이며 공개 정리된 문서의 새 manifest가 아니다.

2026-10-06 공개 체크아웃 재실행: 위 3종 총 **518277 검사 PASS**, Questa Starter 2025.2. [결과와 실제 실행 소스 해시](public-unit-result.json).

## 054 SPI 경계

[계약과 재현 인자](../../docs/nes-spi-boot-contract.md)의 `run_nes_spi_boot.ps1`은 공개 원본만으로 unit/wave 시험을 실행한다. [결과](../../analysis/SPI-BOOT-RESULT.ko.md)는 새 C callback 파형·80KiB 직렬 적재/읽기와 공동 자원을 구분한다. 공동 fit는 별도 private053 해시 고정 입력이 필요하다. `verify_nes_spi_boot.py --evidence <private054>`는 원시 근거 감사이며 새 시험 실행이 아니다.

## 055 SPI에서 실제 코어까지

[계약](../../docs/nes-spi-live-contract.md)의 `run_nes_spi_live.ps1`은 해시 고정 private053 실제 코어 export를 입력으로 받아 새 폴더에서 SPI 적재·코어 실행을 수행한다.96/80KiB 진단2종8프레임을 새로 실행했다. `verify_nes_spi_live.py`는 원시055/053/054fit 입력을 감사하며 새 시뮬레이션이 아니다. 공개 clone만으로 전체 코어를 재현할 수 있다고 주장하지 않는다. [결과](../../analysis/SPI-LIVE-RESULT.ko.md).

## 056 STM32 적재·복구

[계약](../../docs/nes-mcu-loader-contract.md)의 호스트/파형 시험은 공개 소스로 자체 진단을 생성하며 private053 코어 export가 필요 없다. ARM 전체 링크는 고정 sd2snes upstream·툴체인·검증한 mini FPGA 입력이 필요하다. 미호출 함수도 ELF에 남겨 링크를 검사하지만 메뉴 연결·설치용 후보는 아니다. `verify_nes_mcu_loader.py`는 보관한 원시 근거를 감사한다. [결과](../../analysis/MCU-LOADER-RESULT.ko.md).

## 057 승인 형상 연결

[계약](../../docs/nes-rom-geometry-contract.md)의 unit와 잘못된 인자 latch mutation은 공개 소스만 사용한다. live는055,fit는054의 고정 private export가 필요하다. 같은 승인 레지스터가 core mask를 구동한8프레임을055와 시각까지 비교하며 새 공동 fit를 실행했다. [결과](../../analysis/ROM-GEOMETRY-RESULT.ko.md). 물리 readback/보드 통과와 구분한다.

## 058 실행 전 공유 읽기 포트

[포트 계약](../../docs/nes-rom-readback-port-contract.md)의 unit/diff/mutation은 공개 자체 패턴만 사용한다. 공동 fit는 private057 export가 필요하다.058은 전체 코어 재실행·SPI/MCU readback·실기 시험을 포함하지 않는다. 원시 근거 감사는 `verify_nes_rom_readback.py`로 구분한다. [결과](../../analysis/ROM-READBACK-PORT-RESULT.ko.md).

## 059 SPI 읽기 확인과 실행 gate

[계약](../../docs/nes-spi-readback-contract.md)의 unit/host/mutation/wave는 공개 자체 소스·패턴으로 실행한다. 실제 C 파형은32바이트 확인 뒤 입력 오류 복구를 검사하며 전체 C 길이 시험은 별도 모형이다. 전체 코어/공동 fit는 private057,ARM 전체 링크는 private056 준비 트리가 필요하다. `verify_nes_spi_readback.py`는 원시 archive 감사이며 공개 clone 단독 재현이나 실제 STM32 실행이 아니다. [결과](../../analysis/SPI-READBACK-RESULT.ko.md).

## 060 SD 적재·읽기 비교 연결

[계약](../../docs/nes-sd-readback-contract.md)의 host/mutation/GPIO 재생은 공개 원본과자체 fixture를 사용한다. ARM은private059 준비 트리가 필요하며 메뉴 미호출이다. 전체 코어/fit는059 근거를 재사용한다. `verify_nes_sd_readback.py`는 private raw archive 감사다. [결과](../../analysis/SD-READBACK-RESULT.ko.md).

## 061 물리 적재 진단

[계약](../../docs/nes-board-diagnostic-contract.md)의 host060→board GPIO와3개 mutation,Quartus map/fit/STA는 공개 소스만으로 재현한다. 자체 fixture 외 사용자 ROM/실제 NES core export는 필요 없다. 실제 부품/아날로그 PLL/외부 IO 타이밍/실기 검증은 포함하지 않는다. `verify_nes_board_diagnostic.py --evidence <private061>`는동결 원시 근거 감사다.

## 062 수동 메뉴와 후보 확인

[계약](../../docs/nes-menu-diagnostic-contract.md)의 host/검사 제거 mutation/C GPIO는공개 소스와자체진단으로 실행한다. ARM은해시고정private060준비트리와툴체인이필요하며최종ELF에서3메뉴호출을검사한다. 설치용쌍이나실제STM32시험은아니다. `verify_nes_menu_diagnostic.py`는309파일동결원시근거를감사한다. 061생산RTL은같아fit를재사용하며전체C→보드성공은아직미검증이다.

## 063 전체 C→보드 세션

[계약](../../docs/nes-board-session-contract.md)의 host capture와 보드 replay를 두 형상에서 실행한다. 원본 fixture는 공개 생성기로 만들며 RAM을 미리 채우지 않는다. 최종 두 시험은8MHz/2µs를 유지하고 미사용 legacy/H1 domain만 테스트에서 멈춘다. 원래 클록 대조는64프레임, legacy를 계속 구동한 대조는8,192프레임으로 범위를 구분한다. `verify_nes_board_session.py --evidence PATH`는 로컬 동결 증거 감사이며 공개 clone만으로 새 시험을 수행한 결과가 아니다. 생산061SV/062C가 같아 기존 fit/STA/ARM을 재사용했다. 실제 STM32/SD/PLL/외부 IO/설치 쌍은 검증하지 않았다.

## 064 진단 하위 종료·관측

[계약·실행 명령](../../docs/nes-diag-recovery-contract.md)과 [결과](../../analysis/DIAG-RECOVERY-RESULT.ko.md)를 사용한다. 상위 host와 실제 하위 함수/ARM 검증을 구분한다. 고정 private062 플랫폼/동결063 trace와064 archive가 필요한 검사는 공개 clone 단독 재현으로 취급하지 않는다. 설치 후보가 아니다.

## 065 메뉴 복귀 하위 종료

[계약·실행 명령](../../docs/nes-menu-return-contract.md)과 [결과](../../analysis/MENU-RETURN-RESULT.ko.md)를 사용한다.93 helper/복귀 검사·4개 mutation·전체 C SPI 동일 기록과 ARM 호출을 구별한다. 고정 private062 플랫폼/동결063 trace/065 archive를 요구하는 감사는 공개 clone 단독 재현이 아니다. 새 SD 설치 이미지가 아니다.

## 066 오프라인 파일 쌍·읽기 전용 사전 점검

[066 계약](../../docs/nes-pair-preflight-contract.md)의 명령은 명시적으로 제공한 private061 Standard fit·065 ARM을 필요로 한다. 공개 clone은 DB/바이너리를 제공하지 않는다.18개 SD 시험은 로컬 파일 모형이고 backup/rollback-plan은 사용자 SD를 수정하지 않는다. 정확한 부품·실제 menu/base·설치/복원은 남는다.

## 067 진단 메모리

[067계약](../../docs/nes-diag-memory-contract.md)의 명령을 사용한다.공개 단위시험은새loader/CHECK핀모형, bounded C replay는private060host입력이필요하다.동결067verifier는private원시근거검사다.외부IO/전체SPI/ARM/설치승인은포함하지않는다.

## 068 초기 대기·읽기 활성·외부 예산

[068 계약](../../docs/nes-diag-safety-contract.md)의 명령을 쓴다. 초기 guard·전체 pin 검사·fit는 공개 소스와 로컬 도구로 실행하고, bounded C replay는 private060 host가 필요하다. 동결 verifier는 private068 evidence-final을 요구한다. IO 추출은 원본 DB를 수정하지 않는 분석이며 생산 외부 승인이 아니다.

## 069 CF68 MCU

[069 계약](../../docs/nes-cf68-mcu-contract.md)의 host/helper/capture 명령을 사용한다. prepare/ARM은 pinned private062 플랫폼, bounded wave는 새069 host, frozen audit는069 evidence-complete와068 evidence-final이 필요하다. 실제 전체 보드 SPI 재생이나 설치 승인은 포함하지 않는다.

## 070 전체 CF68 세션

[070 계약](../../docs/nes-cf68-session-contract.md)의 새 실행기는동결069 session과068 evidence-final을 요구한다. 기존063 실행기는CF61에고정되어그대로호출하지않는다. `LimitFrames`는prefix만,전체완료는두geometry의마지막ACK/FINISH/STOP까지확인한다. 동결070감사는private증거가필요하며 설치승인이아니다.
