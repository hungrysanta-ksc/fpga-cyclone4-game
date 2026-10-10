# NES 검증 재현 범위

134: run_nes_board134.ps1 / nes_board134_fit.py / nes_board134_timing.tcl / verify_nes_board134.py. 선택test02/fit02. 새ASCII 출력과 고정131 baseline 필요. [범위와 결과](../../analysis/BOARD134-RESULT.ko.md).

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

## CF86 MCU 세션094

[결과](../../analysis/SESSION094-RESULT.ko.md)와 [계약/명령](../../docs/nes-session094-contract.md)을 따른다. 공개 호스트63/대조4는 새 출력 경로로 실행한다. ARM과 동결 verifier는 비공개077/094 증거가 필요하며 공개 clone만의 재현으로 표현하지 않는다.

## CF86 전송 재생095

[095 조건/명령](../../docs/nes-replay095-contract.md)을 따른다. guard 반복 상태 논증과 정상-only 분리를 명시하며 실제 전체 감시 회로 실행/실기라고 부르지 않는다. 동결 verifier는 비공개 증거를 요구한다.

## 실제 native096

[096 계약/명령](../../docs/nes-native096-contract.md)에 따라 동결094 입력과 호스트 GCC를 사용한다.154경우/4대조, 동결 검증은 `verify_nes_native096.py`. 실제 구성 파일·main 메뉴·실기는 이 시험과 구분한다.

## 실제 구성·메뉴097

[097 계약/명령](../../docs/nes-config097-contract.md)에 따라 같은086 fit ASM/CPF와 실제 사용자 파일을 최종094 native/메뉴 함수에 연결한다.176호스트/5대조이며 전체main·실기 승인과 구분한다.

## 실제 메뉴 호출098

[098 계약](../../docs/nes-menu098-contract.md)은 실제main주소와전체load_rom의원본실패·수정26경우/4대조/동일ARM을확인한다. RTC/SPI등하위장치모델과실기를구분한다.

## RTC099

[099 계약](../../docs/nes-rtc099-contract.md): 고정098에서 RTC 한도와 오류 전달을 재현하고 실제 main/FatFS 및 동일 ARM을 확인한다. 레지스터/하위 IO 모델과 실기를 구분한다.

## 실제 하위 SPI100

[100 계약](../../docs/nes-lower100-contract.md): 고정099에서 SRAM/명령/SPI를 연결하고 칩 선택 및 공유 예산 보호를 검증한다. 바이트 모델과 물리 핀/이미 시작된 전송의 종료를 구분한다.

## SPI101 완료 순서

[101 계약](../../docs/nes-spi101-contract.md): 고정100에서 준비하고 위상336 및 기존100 통합34를 재실행한다. 새 GPIO/SPI 강제 중단 증거와 정상 완료 순서를 구별한다.

## 최종 정지102

[102 계약](../../docs/nes-quiesce102-contract.md): 고정101에서 준비해 실제 blocked/RESET/정리함수를 연결한다. 정지함수 진입 후 레지스터 상태와 최초오류부터의 지연을 구분한다.

## 공유 오류 관측103

[103 계약](../../docs/nes-observer103-contract.md): 고정102에서 실제 observer/printf/UART를 연결한다. 공유 fault와 recoverable report.error, 호스트 레지스터 접근과 실제 핀/MCU 시간을 구분한다.

## 타이머·IRQ104

[104 계약](../../docs/nes-timer104-contract.md): 실제 C 함수와 GPIO/TIM2/선점 모델을 구분한다. 카드 상태 대조는 DISK_OK에서 시작한다. 출력/상태 보존을 함께 검사하며 제품 budget을 늘려 통과시키지 않는다.

## 파일 조합105

[105 계약](../../docs/nes-pair105-contract.md):104/097/044 정확 조합과 역할 검사. 오프라인 통과는 설치 승인 또는 실기 성공이 아니다.

## 실기 조건106

[106 계약](../../docs/nes-trial106-contract.md):086원시경로 재계산과운영관측정책. 계산상양수/600초한도를물리승인·MCU완료보장으로쓰지않는다.

## CSS/NMI108

[108 계약](../../docs/nes-css108-contract.md)에 따라 고정104에서 준비하고 실제C·ARM벡터/종료경로를 검사한다. 전체native회귀/실기와구분한다.

## CSS 통합109

[109 계약](../../docs/nes-css109-contract.md)에 따라104/108고정입력으로 통합·고장·새파일조합을 검사한다. PA1/PB8 모델,호스트결과출력과제품UART억제를구분한다.
## 검토 후보110

`tools/stage_nes_trial110.py --pair <review109> --out <new>`로 검토용 후보만 생성한다. `tools/verify_nes_trial110.py --evidence <frozen110>`로 원본/ZIP/정책을 확인한다. 실행 지시가 아니며 [사용자 선택](../../docs/nes-trial110-review.ko.md)이 먼저다.

## 현재 실행 패키지111

사용자 선택 후 `tools/release_nes_trial111.py --pair <review109> --out <new>`로 생성한다. `tools/verify_nes_trial111.py --evidence <frozen111>`는 전달 무결성을 확인한다. [실기 안내](../../docs/nes-trial111-instructions.ko.md)가 현재 실행 절차이며, 위110 검토 지시는 선택 전 이력이다. 변경 없는 ARM/FPGA는 재빌드하지 않는다.

## 역사적 단계 로그 개선판112

`prepare_nes_checkpoint112.py --evidence108 <frozen108> --out <new>`로 준비하고 기존100 ARM builder/고정mini를 사용한다. `test_nes_checkpoint112.py --evidence109 <frozen109> --gcc <gcc> --out <new> --cases 0:0,0:303,0:201,50:0`는 실제C통합/고장/예산을 재현한다. `check_nes_checkpoint112_arm.py`가 실제ELF/host소스를 대조한다. `release_nes_checkpoint112.py --pair <pair109> --firmware <ARM112> --out <new>`로전달물을만들고`verify_nes_checkpoint112.py --evidence <frozen112>`로무결성을확인한다. [실기 안내](../../docs/nes-checkpoint112-instructions.ko.md).

## 역사적 진입 전용113

`prepare_nes_entry113.py --evidence112 <frozen112> --out <new>`로 소스를 준비하고 `build_nes_entry113_arm.ps1`에 기존 ARM/host GCC/Make/UnixBin/고정mini 인자를 전달한다.113은 begin을run에서 한 번만 실행하므로 옛100검사기의 중복 begin 요구를 그대로 적용하지 않는다.

`test_nes_entry113.py --baseline <frozen112/host03> --gcc <gcc> --out <new> --old --cases 61`은 기존 무로그 거절을 재현한다. `--old` 없이 기본10개 사례를 실행하면 수정·실제FatFS 로그 재열기와80KiB 회귀를 확인한다. 모형에 완료된 다중읽기 상태를 주입하며 실제 메뉴 전체/CMD18/전기파형을 실행한 것은 아니다.

`check_nes_entry113_arm.py --arm <arm113> --host <final-host113> --objdump <arm-objdump> --out <new>`는 실제ELF/벡터/새진입순서/C소스를 대조한다. `release_nes_entry113.py --pair <pair109> --firmware <ARM113> --out <new>`로 패키지를 만들고 `verify_nes_entry113.py --evidence <frozen113>`으로 검증한다. [실기 안내](../../docs/nes-entry113-instructions.ko.md).

## 현재 기본 FPGA 복구 전용116

`prepare_nes_base116.py --evidence113 <frozen113> --out <new>`로 준비하고, 기존 `build_nes_entry113_arm.ps1`에 ARM/hostGCC/Make/UnixBin/고정mini 인자를 전달한다. 새RTL/ASM은 필요 없다.

`test_nes_base116.py --evidence113 <frozen113> --gcc <gcc> --out <new>`는 짧은 정상 복구, DONE/BSY/TXE/토큰/SD/CSS 오류, 전체80KiB 회귀8개를 실행한다. 실제FatFS 로그 재열기2개도 포함한다. 핀·시간·카드·초기 상태는 모형이다.

`check_nes_base116_arm.py --arm <arm116> --host <final-host116> --objdump <arm-objdump> --out <new>`로 실제 ELF와 C를 대조한다. `release_nes_base116.py --pair <pair109> --firmware <ARM116> --out <new>`로 패키지를 만들고 `verify_nes_base116.py --evidence <frozen116>`으로 검증한다. [116 실기 안내](../../docs/nes-base116-instructions.ko.md).

## 현재 전체80KiB 통합복구118

동일116 ARM과기존host03 case70/ARM검사를재사용한다. `python tools/release_nes_full118.py --pair <pair109> --firmware <ARM116> --out <new>`는입력쌍해시/디코딩/fixture와ZIP12항목을검증한다. 새C/RTL/ARM빌드는없다. [118실기안내](../../docs/nes-full118-instructions.ko.md)를현재실행절차로사용한다.

## 현재 정상속도메모리120

기존FLOAT wrapper로 `run_nes_core_memory120.ps1`을실행한다. Baseline은공개052 artifact로검증되는이전live디렉터리이며새ASCII Out만사용한다. 핀단위는같은FLOAT RunOnly 세션에서 `nes_memory120_unit.py --out <new> --questa-bin <bin>`;근거검증은 `verify_nes_core120.py --evidence <frozen120>`.120은실제코어제한prefix/16위상핀시험이며전체8프레임은다음단계다.

## 121 전체 프레임 회귀

`run_nes_core_frames121.ps1`을 기존 FLOAT RunOnly 경로와핀된052live Baseline/새ASCII Out으로실행한다. `verify_nes_frames121.py --evidence <frozen121>`은6사례/24프레임을보존된기준과재비교한다. 테스트벤치consumer이며실제SNES소프트웨어나보드PLL시험은아니다.

## 122 등록형 reader 회귀

`run_nes_safe_reader122.ps1`(6사례 전체프레임)과 `run_nes_safe122_unit.ps1`(16위상·110ns/HOLD제거 거부)을 기존 FLOAT RunOnly·핀된052live Baseline·새 ASCII Out으로 직렬 실행한다. `verify_nes_safe122.py --evidence <frozen122>`은 동결 failed01/unit01/full02/unit02와 공개 소스·기준 프레임을 재검증한다.168MHz 제어는 디지털 후보이며 보드 타이밍 근거가 아니다.

## 123 실제 클록/핀 가능성 검사

`nes_clock_fit123.py`는핀된059fit 입력에서읽기전용코어/PLL후보를생성하고map/fit/STA를수행한다. `nes_clock_audit123.tcl`을동일작업폴더에복사해quartus_sta -t로60개클록쌍최악경로를보고한다. `verify_nes_clock123.py --evidence <frozen123>`은46핀·클록·긍정및부정타이밍증거를보존했는지검증한다. 설치용이미지가아니며동결DB는수정하지않는다.

## 124 도메인별 reset 구현

`nes_reset124.py`는과거소스를유지하고새작업폴더의진단RTL만변형한다. `nes_reset124_fit.py`는고정059fit입력에서map/fit/STA를수행하며,동일폴더에서`nes_reset124_audit.tcl`로72클록쌍과1272init_done경로를보존한다. `run_nes_reset124_unit.ps1`, `run_nes_reset124_core.ps1`, `run_nes_reset124_transport.ps1`은기존FLOATwrapper/Questa/Python/새ASCII출력을받으며1seat직렬실행한다. core는고정052baseline을쓴다. `verify_nes_reset124.py --evidence <frozen124>`은기준프레임·해시·실제reset종착점을재검사한다. 전체CDC/실물타이밍통과나설치이미지는아니다.

## 125 묶음 데이터 CDC

`nes_cdc125_sta.py --evidence124 <frozen124-final> --out <newASCII> --quartus-bin <bin64>`가 같은 배치의 정확한372쌍을 검증한다. `run_nes_cdc125_protocol.ps1`에는 Python/FloatWrapper/QuestaBin/Out/Baseline(124-final)을 지정한다. 기존1seat FLOAT로 reader2/bridge3위상과조기캡처부정대조2개를 실행한다. `verify_nes_cdc125.py --evidence <frozen125>`는 재실행없이 원시 경로·소스·DB·로그를 검사한다. 모든CDC/실물MTBF/IO통과나설치이미지가 아니다.

## 126 제어 동기화 배치

`nes_control126.py --baseline124 <frozen124-final> --baseline125 <frozen125> --out <newASCII> --quartus-bin <bin64>`로같은매핑/정확8QSF/새fit·STA를수행한다. `review_nes_control126.py --out <same> --quartus-bin <bin64>`로새내부타이밍·reset보고를검사한다. `verify_nes_control126.py --evidence <frozen126>`는전체해시·실제체인·데이터제약을재검사한다. 동기화속성변경에는Fitter재실행이필요하며,종료성공만으로적용성공을판단하지않는다.실제UserSpecified인식과Ignoredassignment부재를검사한다.

## 127 로더·소유권·클록 감시 통합

기존 FLOAT 경로의 `run_nes_loader127.ps1`/`run_nes_loader127_decoder.ps1`에 `-Baseline <probes>`, 새 ASCII `-Out`과 기존 Python/Questa/wrapper 경로를 전달한다. `nes_loader127_fit.py --baseline <probes> --out <newASCII> --quartus-bin <bin64>`는 실제126코어+086래퍼를 생성하여 MAP/FIT/STA를 수행한다. `review_nes_loader127.py --out <same> --quartus-bin <bin64>`는 새 같은클록 setup실패까지 보고한다. `verify_nes_loader127.py --evidence <frozen127>`의 PASS는 기록 무결성과 시험범위 확인이며, timing/설치승인 PASS가 아니다.

## 128 명령·로더 타이밍 개선

기존 FLOAT 경로의 `run_nes_command128.ps1`/`run_nes_command128_boot.ps1`/`run_nes_command128_diff.ps1`에 `-Baseline <probes>`와 새 ASCII 출력/Python/Questa/wrapper 경로를 지정한다. `nes_command128_fit.py` 후 phase 완료를 확인하고 `review_nes_command128.py`를 실행한다. `verify_nes_command128.py --evidence <frozen128>`로 해시·실패를 포함한 결과를 확인한다. 최종 test06/boot05/diff02/fit07의 범위는 [128 결과](../../analysis/COMMAND128-RESULT.ko.md)를 따른다. fit 성공은 timing/설치승인이 아니다.

## 129 reader 소유권 등록

기존 FLOAT 경로의 `run_nes_reader129.ps1`에 `-Baseline <probes>`와 새ASCII 출력/Python/Questa/wrapper를 지정한다. `nes_reader129_fit.py`의 MAP/FIT/STA 완료 후 `review_nes_reader129.py`를 실행한다. 최종은test01/fit01이며 후속fit02–05는 미채택이다. `verify_nes_reader129.py --evidence <frozen129>`는 채택·미채택 증거를 구별해 검사한다. [129 결과](../../analysis/READER129-RESULT.ko.md)의 모델 범위와 남은 타이밍 실패를 유지한다.

## 130 로더 상태 합성 설정

`nes_enable130_fit.py`에 `--baseline <probes> --out <fresh ASCII path> --quartus-bin <bin>`을 지정해 MAP/FIT/STA를 수행한다. 완료 후 `review_nes_enable130.py`로 같은 출력과 Quartus 경로를 전달한다. 최종fit01은 상태만 변경하며 fit02의 카운터 설정은 미채택이다. `verify_nes_enable130.py --evidence <frozen130>`은 인접129증거와 함께 입력 재생성·동작 코드 동일성·실제 포트·타이밍을 검사한다. 새 기능 시뮬레이션은 없으며 [130 결과](../../analysis/ENABLE130-RESULT.ko.md)의 미통과 범위를 유지한다.

## 131 카운터 사전 설정

기존FLOAT 경로의 `run_nes_counter131_diff.ps1`와 `run_nes_counter131.ps1`을 직렬 실행한다. `nes_counter131_fit.py`의 새MAP/FIT/STA 완료 후 `review_nes_counter131.py`로 실제제어입력/clock별setup·hold를 확인한다. `verify_nes_counter131.py --evidence <frozen131>`은 인접130동결자료도 필요하다. [131 결과](../../analysis/COUNTER131-RESULT.ko.md)의 선택 후보와 모델 범위·미완료 조건을 유지한다.

## 132 현재 CDC 재검증

`nes_cdc132_inventory.py`로131fit05를별도복사하고 `nes_cdc132_sta.py`로현재경로를분류한다. 새MAP/FIT없음. `run_nes_cdc132_protocol.ps1`은기존FLOAT경로로actual131reader를시험하며125의고정fixture를사용한다. `verify_nes_cdc132.py --evidence <frozen132>`는인접125/131증거도필요하다. 124manifest불일치입력을재사용하거나과거archive를수정하지않는다. [132 결과](../../analysis/CDC132-RESULT.ko.md).

## 133 실제 RUN 계약

`run_nes_run133.ps1`으로 기존FLOAT 경로를 사용한다. 고정131fit05 입력, 이상적PLL/70nsRAM 모델, 초기값으로 넣은 이미지·적재·CHECK 완료 범위를 유지한다. 실제SPI 명령과CPU reset vector/명령 읽기, STOP/오류/클록 정지를 검사한다. `verify_nes_run133.py --evidence <frozen133>`은 인접131증거도 필요하다. [133 결과](../../analysis/RUN133-RESULT.ko.md).
