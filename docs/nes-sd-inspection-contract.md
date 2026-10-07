# SDINFO072 수집 계약과 재현

목표는 외부 실기의 원본 SD 정보를 사용자 실행→TXT 반환 방식으로 확보하는 것이다. `SDINFO072-BASE069`는 별도 수집 펌웨어이며, `NES-CF68-MCU-069`/FPGA068/쌍071을 교체한 새 NES 후보가 아니다. 실행은 [수집 안내](SDINFO072-RUN.ko.md), 다음 개발은 [인계](../cores/nes/HANDOFF.ko.md)를 따른다.

## 경계

실행 clone의069 실제 C275개는 동결069 manifest와 대조했다. main/Makefile/VERSION을 바꾸고 수집 C3개/header1개를 추가했다. 기존 embedded-mini SHA `9ae79c3028391063338d42ae16b19acf48d0d80858939b015ef6481f55cbefe9`는 HWINFO002 입력이다. main의 ARM 마지막 호출은 `sdinv_run`, 이후 메뉴/cfg/autoboot 경로는 실행되지 않는다. ELF에 기존 load_rom/fpga_pgm/verified_start 함수가 남아 있다는 사실과 실제 main의 호출 경계를 구분한다.

초기 file_init/하드웨어 bring-up/mini 화면 준비는 기존 경로다. 그 다음 RESET/USB 보호와 offload 차단을 시작하고069 하위 SD/SPI/TIM2/FatFS 예산을 쓴다. 수집 시작부터 마지막 상태 화면 출력까지 보호를 유지하고, 공유 오류는 RESET/USB를 유지한 채 멈춘다. 정상 완료/논리 파일 오류는 마지막 오류 확인 뒤 diag_leave/RESET 해제하고 NOP 루프다. 전체 부팅이나 실제 카드의 시간 상한을 입증하지 않았다.

입력4개는 원본 firmware 사본·현재 firmware·fpga_base.bi3·m3nu.bin이다. 실제 메뉴 헤더 위치6개(0xffb0/0x101b0/0x7fb0/0x81b0/0x40ffb0/0x4101b0)와 reset byte를 기록한다. 크기 상한은 firmware262656, 압축 FPGA1048576, 메뉴0x400200, 복원 FPGA2097152바이트다. 256바이트 단위 읽기, EOF/크기·STM3 길이/본문CRC·RLE token/count/복원 상한을 점검한다. `format_ok`는 실제 menu smc_id/sgb_id/mapper/carttype 분류 승인이 아니다.

TXT는 루트 HW003000–HW003999 중 CREATE_NEW만 쓴다. write/sync/close/reopen/크기·모든 바이트/close 검사를 한다. shared fault 뒤 close조차 포함한 추가 SD 접근을 금지한다. 논리적 오류와 하위 fault를 구분한다. SysTick100Hz 6000tick/100만poll 예산은 실제69 runtime의 복귀 IO 예산이며, 호출 전 legacy startup 대기는 범위 밖이다. TXT CRC는 인증·독립 백업·실행 출처 증명이 아니다.

## 공개 시험

```powershell
python -B tools/run_nes_sd_inventory_tests.py --gcc <host-gcc.exe> --out <새-호스트-출력>
python -B tools/check_nes_sd_inventory.py <HW003nnn.TXT>
```

collector52/writer23/platform6/report29를 실제 새 C 본문에 mock FatFS/peripheral로 실행한다. 실제 STM32/SD/메뉴 관측은 아니다. 원본/실행 펌웨어 혼동, 짧은 read/write, STM3 CRC, RLE65535/잘린 token/초과, 헤더/reset 경계, 모든바이트 readback, native fault 이후 추가 IO 금지, 마지막 화면 전 조기 diag_leave를 검사한다. readback 비교 제거·조기 diag_leave의 오류 대조2개는 각각 인과 assertion에서 실패했다. 첫 TXT 테스트의 repaired framing 기대 오류는 수정하고 원시 로그를 보존했다.

## ARM 재현과 수집 패키지

public clone만으로 ARM/동결 audit를 재현할 수 없다. 동결069의965파일 manifest `b5d50d8a5f7590a43f33b8ebe4d5166ff2f2ae0ba9bbebf953984959d6d026ae`, 정확한069 materialized MCU 트리, pinned mini, ARM13.3.rel1/Make3.81/GCC7.4/awk가 필요하다. 제공 대응 소스 zip은 실행 입력과 원래 고지를 보존한다. config/VERSION 등069 archive 밖의 입력은 이번072에서 새로 해시 고정하며, 전부069에서 고정됐다고 쓰지 않는다.

```powershell
python -B tools/nes_sd_inventory_prepare.py --mcu-root <069-materialized-root> --mcu-evidence <069-evidence-complete> --out <새-source>
./tools/build_nes_sd_inventory_arm.ps1 -SourceRoot <새-source> -ArmBin <ARM-bin> -HostGcc <gcc.exe> -Make <make.exe> -UnixBin <awk-bin> -MiniImage <pinned-mini.bi3>
python -B tools/package_nes_sd_inventory.py --firmware <동결072-firmware.stm> --source-zip <FXPAK-SDINFO072-SOURCE.zip> --out <새-kit>
python -B tools/verify_nes_sd_inventory.py --evidence <072-evidence>
```

builder는 사용 중이지 않은 W:/V:를 일시 매핑하고 끝나면 해제하며 PATH를 복원한다. 원본069/동결자료를 out으로 쓰지 않는다. 빌드 timestamp 때문에 재빌드 firmware는 고정 전달본과 SHA가 달라질 수 있다. 임의 header 정규화를 금지하고, 새 빌드는 새 입력/본문CRC/ELF 호출로 검증한다. 패키지 도구는 이번 고정 해시만 받는다. 공개 Git에는 바이너리/ROM/실물TXT/raw로그/라이선스/사적 경로를 넣지 않는다.

## 다음 완료 조건

이번 범위는 수집기 구현·시험·전달본 준비까지다. 사용자 실행의 새 TXT, 교체 전 원본의 독립 backup/readback, 복원 뒤 메뉴/GBC 관측은 미수행이다. TXT를 받은 다음 실제 분류 C에 bounded 입력을 제공해 smc_id/sgb_id·plain mapper0/1/carttype0–2·offset/payload≤4MiB·특수 FPGA/SGB/EGBC 없음 조건을 확인한다. 파일의 parseable RLE/작은 크기만으로 호환성을 가정하지 않는다. 전압/PCB/비동기SPI/SNES 및 lockedHIGH CE>8µs 반례는 계속 별도 미해결이다. 준비도5완료/6부분/1미완료와071 installable=false를 유지한다.
