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
