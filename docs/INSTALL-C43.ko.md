> Historical C43 preparation record. Current: [C44 release](RELEASE-C44.ko.md), [user guide](USER-GUIDE.ko.md), [build](BUILD-C44.ko.md).

# C43 설치와 사용

## 대상과 복사 파일

FXPAK Pro / Mk.III의 STM32·Cyclone IV 보드용 업데이트입니다. 정상 동작하는 공식 sd2snes 1.11.2 계열 설치 위에 사용합니다. 빈 SD를 완성하는 전체 펌웨어 패키지가 아닙니다. Mk.II, 다른 MCU 보드, ludufre 2.16.4와의 혼합 설치는 검증하지 않았습니다.

1. 전원을 끄고 기존 `sd2snes` 폴더와 세이브를 별도로 백업합니다.
2. ZIP의 `sd2snes` 폴더에서 아래 4개 파일을 같은 경로로 복사합니다.
3. FXPAK 날짜·시각을 확인합니다. 한국 현지 시각이면 동봉된 `gbc-utc-offset.txt`의 `+540`을 사용합니다. UTC로 설정한 기기는 `0`, 다른 지역은 UTC와의 차이를 분 단위로 적습니다. 기존 설정이 있으면 현재 지역에 맞춰 유지합니다.
4. 소유한 게임 파일의 **복사본** 확장자를 `.egbc`로 변경하고 실행합니다. 원본 ROM·세이브는 유지합니다.

| 파일 | 역할 |
| --- | --- |
| firmware.stm | 새 코어 로더·메뉴·저장·RTC |
| fpga_egbc.bi3 | GBC FPGA 코어 |
| gbc_snes.bin | 자체 SNES 화면·메뉴 출력 프로그램 |
| gbc-utc-offset.txt | 기기 현지 시각의 UTC 시차 |

`.egbc`에는 별도 SGB BIOS가 필요하지 않습니다. `.gb/.gbc`를 기존 SGB 코어로 실행하려면 기존 SGB 코어·BIOS 설치가 필요합니다. 이 ZIP에는 `fpga_sgb.*`, `sgb2_boot.bin`, `sgb2_snes.bin`이 없습니다. 기존 SD의 파일은 지우지 않습니다.

참고한 [ludufre 배포](https://github.com/ludufre/sd2snes/releases/tag/v1.11.2-br-v2.16.4)는 FPGA SGB 코어와 안내를 포함하고 BIOS 두 파일은 별도로 준비하도록 합니다. 우리 업데이트는 SGB 코어 파일도 제외합니다. 참고 ZIP의 실행 파일은 재사용하지 않았습니다.

## 조작과 저장

- **L+R+Start**: 코어 메뉴. **B / RESUME GAME**: 게임으로 복귀.
- **WRITE SRAM**: 현재 게임의 배터리 저장 RAM을 SD에 기록합니다. 게임 안에서 저장한 뒤 사용합니다.
- **AUTO WRITE SRAM**: 배터리 RAM 자동 기록. WRITE SRAM은 강제 저장과 다릅니다.
- **STATE SLOT 1~4 / SAVE STATE / LOAD STATE**: 실행 중 상태 저장·복원. 다른 ROM이나 다른 상태 스키마 파일과 섞지 않습니다.
- **SOUND / RESET GAME**: 음소거·동일 게임 재시작. 리셋 직전 SRAM 기록 실패 시 리셋을 진행하지 않습니다.
- **R 유지**: 약 3배 빨리감기. 메뉴 조합은 메뉴 호출을 우선합니다.

배터리 파일은 `sd2snes/saves/<게임 이름>.srm`입니다. 일반 SRAM은 원래 크기의 raw 파일이며, RTC 게임은 SRAM 뒤에 48바이트 메타데이터를 기록합니다. 한국판 금의 예는 32,816바이트입니다. 기존 44/48바이트 RTC footer도 읽습니다.

RTC는 메뉴·빨리감기 중에도 실제 시간에 맞춰 흐릅니다. 강제 복원은 현재 배터리 시계를 되감지 않습니다. 초 미만 위상은 전원 종료 파일에 저장하지 않습니다.

## 복구와 보고

문제가 발생하면 백업해 둔 이전 `firmware.stm`, `fpga_egbc.bi3`, `gbc_snes.bin`을 전원이 꺼진 상태에서 복원합니다. 이번 ZIP에는 이전 바이너리나 개인 세이브를 넣지 않았습니다.

보고에는 코어 버전, 게임 지역/버전, 멈춘 단계, 화면·소리·입력 상태를 적습니다. 게임 ROM이나 개인 저장 내용 전체를 공개 이슈에 올리지 않습니다. 패키지의 SHA256SUMS로 복사 파일을 대조할 수 있습니다.
