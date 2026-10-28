# NES407: 227 loader 기반 NROM 프로파일 부분 연결

PR133 후속이다. **실제 227 loader 함수 전체·FPGA·ARM·SNES를 한 실행에서 검증하지 못했고 실제 base 복구도 아직 확인하지 못했다.** 현재는 고정 NROM16/수평/CHR-ROM8/PRG-RAM 없음 profile의 생성 소스, 실제 코드 블록의 모델 검증, FPGA status/STOP 단위 실행 및 Lite 전체 MAP이다. 60fps 후보 A/B의 새 실제 일정과 MMC4/5 실제 ROM 경쟁 비용은 미측정이다.

## 227에서 생성한 후보

`build_nes_nrom407.py`는 보존된 227의 `nes_h1_stm32.c`, `nes_rom_verify.c`, `nes_run136.inc`, 실제 FPGA SPI RTL과 406 cart를 바탕으로 별도 후보를 만든다. 첫 pass에서 header·정확한 NROM 파일 크기·고정 프로파일을 검사하고 CRC를 구한다. 둘째 pass는 원본 PRG/CHR bytes만 CRC에 넣으면서 기존 384KiB 물리 loader 형식의 나머지를 0으로 전송한다. 셋째 pass는 실제 227 readback의 `sd_source`에서 그 배치를 독립 관측값과 대조한다. 파일 오프셋, 크기, CRC, close 실패는 END/FINISH/START 전에 거부한다. 이 CRC는 세 pass 사이 변화 감지이며 파일 신뢰성·인증을 의미하지 않는다.

FPGA SPI 응답은 기존 227의 `74`와 구별되는 고정 profile ID `78`을 내며 후보 `sd_query`와 `nes_rom_verify`는 `78`만 받는다. 기존 관찰 명령 `0x74`는 별도 명령이므로 바꾸지 않는다. 보드 이미지를 프로파일별로 정적으로 빌드해야 하며 현재 단 하나의 `16KiB/수평` 후보만 227 loader에 연결했다. PRG32·수직 파일은 이 후보의 START 이전에 거절한다. 406의 4-profile cart 단위 PASS가 4개의 완성된 ARM/FPGA package를 뜻하지 않는다.

## 실제 코드로 확인한 범위

* `transfer01`은 **생성된 실제 227 파일 검증과 SPI DATA/END 코드 블록**을 추출해 파일·SPI peer 모델에서 실행한다. 정상 393,216B physical layout, padding, 수평 외 profile·크기 거부, pass 사이 파일 변경, DATA 실패, close 실패에서 END 차단을 검사한다. 실제 FatFS 카드, bit-level MCU SPI와 FPGA loader를 동시에 실행하지 않는다.
* `source04`는 생성된 실제 227 `sd_source`·CRC 및 `nes_rom_verify`를 합성 파일/독립 메모리 peer에 연결했다. PRG·padding·CHR·마지막 byte 손상, CRC/close·파일 위치/순서 및 이전 `74` ID 거부를 시험했다. CRC는 마지막 byte까지 승인·close 전에 확인된다.
* `cleanup01`은 생성된 **실제 227 cleanup 코드 블록**을 추출해 모델에서 실행한다. 성공 STOP과 base 설정/토큰 확인, STOP 실패·입력 변경·base 설정/토큰 실패의 fail-closed를 확인했다. 이 결과는 전체 `nes_menu_sd_probe` 실행이나 실제 SPI/RESET/base 장치 복구 증명이 아니다.
* `spi02`는 실제 변경된 FPGA `nes_rom_spi_check`에 직렬 상태조회와 idle STOP을 보내 ID `78`과 STOP pulse를 확인했다. 오류·경고 0. RUN 중 STOP, loader·PSRAM·SNES·late DONE 동시 취소는 별도이다.
* `arm01`은 기존과 생성된 전체 `nes_h1_stm32.c` 및 새 layout/readback 파일을 Cortex-M4로 각각 컴파일했다. loader object text **9,124→9,196B**, 별도 layout object **206B**, loader object BSS 772B 동일이다. `nes_menu_sd_probe` 개별 static stack **1,008→1,032B**, `sd_source` 32→40B다. 객체 합산은 링크 후 증분/전체 resident stack이나 IRQ worst-case가 아니다. Makefile에는 새 C 파일을 추가했으나 **전체 firmware 링크·배포본은 아직 없다.**

`build01` 생성 assert 오류, `source01` 상대 경로 compile 실패를 보존한다. 선택 증거는 `build04`(실제 시험한 build03의 RTL/C 바이트 동일, Makefile 추가), `transfer01`, `source04`, `cleanup01`, `spi02`, `arm01`, `map01`이다. `analysis/nrom407-verification.json`은 source hashes를 대조한다. raw logs는 workspace `probes/nes-nrom407`에 있다.

## 실제 비용과 남은 시간

동일한 227 board의 90개 Quartus Lite MAP 입력 중 `cart_nrom.sv`와 `nes_rom_spi.sv`만 바꾸었다. 기존 MMC3 **18,850LE/13,951C/8,353FF/256,608 RAM bits**, 후보 **18,178LE/13,557C/8,029FF/185,824 bits**다. 후보는 406과 같으며 −672LE/−394C/−324FF/−70,784bits다. 이 감소에는 미지원 PRG-RAM 65,536bits 제거와 고정 CHR에 따른 compact 합성 변화가 포함된다. 전체 게임 기능·loader 결합·FIT/STA 또는 MMC4/5 여유가 아니다.

기존 2.625MHz SPI에서 384KiB padding DATA 각각에 8B DATA와 8B STATUS가 사용되면 이 둘의 wire만 **19.174초 이상**이다. 384KiB payload 비트만 계산해도 1.198초다. 파일·CRC·IRQ·PSRAM·기타 명령은 제외한 계산이다. 이는 **시작 시 ROM 적재**에 드는 최소 전송량의 조건부 계산이며 gameplay 한 프레임 처리 시간이나 실제 ARM 실측이 아니다. 기존 안전한 3회 원본 CRC/독립 readback/STOP을 임의로 생략해 줄인 수치로 바꾸지 않는다.

402의 공동 실행기 후보 A와 ARM 최종 DMA job 후보 B는 둘 다 동일한 새 전체 구현·실제 ARM/IRQ/SPI/ROM 일정이 없다. 402의 전체 MAP/914·915 VBlank 결과는 [405](nes-hardware405-contract.ko.md)의 기존 비교를 유지한다. MMC4 mapper10 및 MMC5 mapper5 실제 PPU/core·ROM 경쟁, 추가 회로·시간도 null이다. 고정 NROM MAP 절감을 그들에게 적용하지 않는다.

## 남은 연결과 판정

1. 생성 소스를 실제 전체 227 firmware build에 넣어 link·flash/RAM/최대 stack/IRQ budget을 검사하고, fixed header→올바른 `78` FPGA image의 경로가 실제 menu에서 선택되도록 결합한다. 기존 game227 package와 GBC/save는 그대로 둔다.
2. 원본 227 loader 함수 전체를 실제 227 FatFS/MCU·FPGA loader/SPI/PSRAM 모델에 연결해 validation→write→readback→START→STOP→base/token/menu 복구를 한 번에 시험한다. header mismatch·wrong ID·원본 변경·CRC·SPI loss·late DONE·STOP 중단·복구 불가 등은 안전 상태에서 재실행한다. 별도의 발췌 함수 PASS는 이 관문을 대체하지 않는다.
3. NES core의 NROM 실행·PPU/CHR·SNES 표시, 입력/음성 해당 여부와 실제 ARM/IRQ/ROM 경쟁을 붙이고 같은 RTL Lite 전체 MAP/FIT/STA·CDC/IO 및 matched package를 확인한다. 지속 60fps와 MMC4/5는 실제 mapper workload·capture/표시 기한·회로 증분을 별도로 측정한다. 실기·60fps·MMC4/5를 승인하지 않는다.
