# P0 인터페이스·클록·리셋 감사 — 2026-09-23

## 기준과 증거 범위

- 격리 사본: `ISOLATION-MANIFEST.json`의 `complete=true`, 31,256개, 4,090,209,408바이트. 원본 root `.git`만 제외하고 중첩 Git은 보존했다. 이 문서는 사본에서만 작성했다.
- 동결 물리 후보: `probes/full-core-link/results/fxpak-g13-prefill-endpoint-seed7-hold1-v1/` (이하 C). top `fxpak_gbc_top`, EP4CE15F17C8, seed 7, Quartus 25.1std.0 build 1129. C의 `verification.json`에 든 주요 소스·SDC 해시는 실제 파일과 대조했다. `pin.sta.rpt` SHA256 `104ccb42fa7dc87a37b1bda20d26ed306914ca8fd4c07995d5399a8c1606a648`, `pin.fit.rpt` `db6cc91fd382cb5dbbfca5b2a73c91ac19b6481f3698ed2ec175cfe354738f18`.
- upstream Gameboy_MiSTer HEAD `7a5ff50528cd9c1d13ffb675e7df8506bffaa078`, upstream sd2snes HEAD `cf7e21d7a5978fcd74981d71c3cfbf6e982a4dd1`. 둘 다 로컬 수정이 있으므로 HEAD만으로 후보를 재현할 수 없다. 이 감사의 최초 로컬 문서 기준은 `0ae1cff231546536865d1918c24fa8f77ca2ad11`이다. 공개 저장소의 후속 이력은 Git에서 확인한다.
- C `pin.qsf`에는 물리 위치 135개, 해당 IO standard 135개(모두 3.3-V LVTTL), current strength 135개(모두 4mA)가 있다. 이는 fit의 135 physical/0 virtual pins와 일치한다. 위치 배정 완전성과 실제 보드 회로·트랜시버 전압/타이밍 적합성은 다른 판정이다.
- 이 감사는 기존 결과와 소스의 정적 판독이다. 새 Quartus/Questa 실행, 보드 파형 측정, 비트스트림 생성은 없다. C의 `gbc_live_core.sv` 첫 주석은 오래된 resource-probe 설명이지만 C의 `full_core_link.sv`는 실제 core를 인스턴스화한다. 반대로 C의 G13 endpoint 시험은 실제 게임 CPU 대신 고정 RGB 입력을 사용했다. 두 검증 범위를 혼합하지 않는다.

## 클록과 리셋

| 도메인 | 생성/관계 | 리셋 및 미결 |
| --- | --- | --- |
| `board8` | `CLKIN` 8MHz, `pin.sdc` 125ns | 외부 기준 클록. 전원/콘솔 재구성 시 실제 안정 시간 미확인. |
| `core` | `gbc_pll0`: 8MHz ×151/36 ≈33.5556MHz; `sys` 29.8013245ns는 외부 PSRAM용 **가상** 클록 | `clock_reset_guard`가 두 PLL lock 상실에 비동기 assert, core 두 에지 뒤 release. core 게임 reset은 `gbc_host_start_guard`/MCU run 조건을 추가로 받음. PLL lock 재취득·부분 재구성 시험 미완료. |
| `bus` | `gbc_bus_pll0`: 8MHz ×21/2 =84MHz | FIFO/uploader/SNES frontend/SRAM writer가 공통 reset을 받아 각 도메인 release pipe 사용. 공통 assert 동안 WE/OE·소유권 유지 검증이 필요. |
| `mcu_spi_sck` | `SPI_SCK`에 20.833ns(약48MHz) 선언; `board8` 및 PLL과 비동기 프로토콜 | `gbc_spi`는 SSEL 상승에서 framing만 초기화하고 byte toggle/held byte는 core로 2단 전달. STM32 펌웨어 소스는 SPI1=PCLK/2=42MHz mode 0을 설정하지만 실제 구성/파형과 MISO setup/hold는 미확인. |
| SNES PHI2/제어 | `SNES_CPU_CLK_IN`은 데이터·slot용 비동기 입력, FPGA 생성 클록 아님 | 84MHz에서 첫 단계 동기화. raw `/RD`가 transceiver release에도 직접 쓰이므로 CDC 예외와 별도로 pad/OE/turnaround를 검증해야 함. |

## 인터페이스 계약 inventory

`unknown`은 승인된 무관 항목이 아니라 P0/P4 gate의 추적 대상이다. 주소는 RTL 기준이며 제품 메모리 맵 확정과 구별한다.

| 경계/producer → consumer | 신호·소유권·흐름 | 시간/폭/리셋 계약과 증거 | 미결/gate |
| --- | --- | --- | --- |
| GBC CPU/PPU → `ppu_stream` → `frame_pipeline_ring3` | core 33.56MHz, `ppu_ce/lcd_clkena`, RGB555 15비트, `pixel_valid`, frame/LCD 상태. capture bank 3개에 epoch/소유권. | C `full_core_link.sv`, `frame_pipeline_ring3.sv`; G13 제한 장면 exact. reset/LCD off에서 불완전 frame 폐기·재시작 가드 존재. | 실제 게임의 double-speed/DMA, LCD 전환, 장기 frame ID 무누락은 미증명. 점멸 원인으로 단정 불가. |
| encoder/next-use → PSRAM background | `req_valid/write/addr[22:0]/data[15:0]`, `req_ready`, 별도 `rsp_valid/data`; capture와 audio가 `psram_bg_arbiter`를 공유. | C `full_core_link.sv`, `psram_bg_arbiter.sv`; one-request/one-response는 테스트 범위의 계약. | 최장 arbitration 지연/blackout, read-during-write·부품 tAA/tWP, 실제 ROM/save 경합 상한 unknown. |
| renderer metadata/pixels → 출력 FIFO → SRAM writer | source 33.56MHz → bus 84MHz, 4개 ×33비트 Gray-pointer FIFO. `ready`는 enqueue ACK이고 SRAM commit이 아님; `drained` 후 publish. | C `output_fifo_cdc.sv`, `board_output_ring3_link.sv`, `frame_output_pages.sv`; pointer 2단 동기화, slot은 read pointer 반환까지 불변. | Gray bit skew/MTBF 범위, 긴 blackout 중 overflow, reset 중 미완료 write와 publish 검증 미완료. |
| source page → uploader → SNES renderer | bus `upload_start/read_idle`로 새 frame read를 막고 기존 read를 drain; toggle request/ack가 source로 왕복, bus가 page/valid를 취득. | C `upload_boundary_cdc.sv`; busy 중 새 frame read는 프로토콜 오류. renderer는 poll 뒤 DMA/HDMA. | timeout 없음. 요청 중 reset, MCU/menu/reconfigure, 실제 반복 설치/refresh/HDMA 시퀀스 확인 필요. |
| SNES CPU/DMA → `snes_frontend` → 외부 8비트 SRAM | SNES 주소[23:0], `/RD,/WR,/ROMSEL`, PHI2는 비동기. 동기화된 slot이 비-SRAM 새 사이클에서만 writer grant. raw `/RD`는 OE 해제. `RAM_ADDR[18:0]`, `RAM_DATA[7:0]` 양방향. | `snes_sram_slots.sv`, 연결된 `sram_burst_writer.sv`: 다음 SRAM read strobe까지 **최소 270ns** 가정, byte/word writer 각각 8/14 bus clocks 예약; WE는 각 펄스에서 4 bus clocks low, 후속 data hold/tri-state. 시뮬레이션 모델 tAA45/tHZ20/tWP≥35ns 등. | 실제 SNES CPU/DMA/HDMA PHI2·주소·read strobe 상대 파형, 트랜시버 DIR/OE turn-around, contention, SRAM 부품/보드 지연 unknown. slot 위반 검출은 이미 시작한 write를 되돌리지 못함. 실기 진단 전 차단 gate. |
| MCU SPI/loader → ROM PSRAM 및 renderer SRAM | SCK↔core toggle+held byte; MCU command/주소[23:0]/data[7:0], `MCU_RDY` completion poll. renderer access는 `mcu_address[23:19]==10001`일 때 별도 loader가 core↔bus handshake. | C `fxpak_gbc_top.sv`, `gbc_spi.sv`, `gbc_sram_loader.sv`; `sgb_features[15]` 후 run. 아래 정적 call path 감사에서 GBC 구성 뒤 단일 바이트 pacing과 과거 G12-save ELF 포함을 확인했다. | 현재 G13 실기 펌웨어 바이너리/플래시 상태, 실제 byte 간격·MISO/MCU_RDY 파형, SS 중단·빠른 back-to-back, loader와 live SRAM ownership 전환은 미확인. 새 block callsite가 생기면 pacing 재검토 필요. |
| GBC ROM/cache/SaveRAM ↔ PSRAM | 16비트 `ROM_DATA`, byte lane `ROM_BHE/BLE`, 주소[21:0], OE/WE. Save 주소 17비트 생성, K141 8KiB 회귀 성공. | C `rom_bus_bridge_save.sv`,`psram_rw3_save.sv`, `full_core_link.sv`; G12S2 세 방향 save 교차 로드는 사용자 실기 성공. | 외부 PSRAM 실제 데이터/주소 setup/hold, OE/WE 및 양방향 turn-around, MCU 동시 접근·저장 중 reset 보호는 별도 gate. Save 재구현 대상 아님. |
| joypad → GBC | SNES register의 8비트 상태+toggle가 bus→core 2단 전달, bundled data hold. | C `joypad_cdc.sv`, `board_output_cdc.sdc`; 이전 G12 실기 조작 성공. | 빠른 연속 갱신/메뉴 복귀/reset edge 및 실제 입력 지연 범위 unknown. |
| GBC APU → audio PSRAM delay → DAC | source signed stereo16, CIC/64, 8192-sample 외부 PSRAM ring 후보, commit toggle가 bus 84MHz로 전달. `DAC_MCLK/LRCK/SDOUT` 출력. | C `gbc_dac_psram.sv`, `audio_psram_delay_client.sv`; 기존 제한 통합에서 overrun/serial mismatch 0. | DAC 부품 setup/hold, 지연 ring의 최악 backlog와 실제 표시 frame age, reset 시 오디오 연속성 unknown. |
| SNES reset/menu/reconfigure ↔ MCU/FPGA | `power_reset=0`인 top에서 PLL lock과 run bit가 내부 실행을 지배; SNES IRQ는 0, 일부 보드 입력은 미사용 tie-off. | C `fxpak_gbc_top.sv` 및 G12 실기 cold/warm 차이 관측. | 콘솔 reset이 FPGA 구성·MCU command·renderer 상태에 각각 미치는 효과를 원인별로 분리해야 함. ROM/save 재적재, epoch, OE 안전 기본값 확인 필요. |

## MCU SPI 실행 경로 정적 감사

격리 사본의 수정된 sd2snes 소스와 과거 `obj-mk3-stm32-g12-save` 링크 결과를 대조했다. `src/Makefile`은 `memory.c`, `fpga.c`, `fpga_spi.c`를 포함하고 `config-mk3-stm32`의 `CONFIG_ARCH=stm32f4xx`가 `stm32f4xx/variables.mk`의 `stm32f4xx/spi.c`를 선택한다. `memory.c`의 GBC 로드는 `fpga_pgm(FPGA_SGB)` 뒤 renderer SRAM과 게임 PSRAM을 `gbc_copy_verified`로 기록·재읽기한다. `fpga.c`는 구성 파일명이 `FPGA_SGB`일 때 `gbc_spi_pacing=1`을 **`fpga_postinit()` 전에** 설정한다.

`stm32f4xx/spi.c`의 SPI1 설정은 명목 PCLK/2=42MHz, mode 0이다. 단일 바이트 TX는 `BSY` 해제 후, RX/TXRX는 응답 수신 후 `gbc_spi_pacing` 조건에서 `delay_us(1)`을 호출한다. `timer.c`의 이 지연은 84MHz 설정의 TIM2 카운터를 사용한다. `fpga_spi.h`의 일반 SELECT/DESELECT는 `spi_tx_sync()`로 마지막 전송 완료를 기다린다. 메모리 복사 경로는 `FPGA_TX_BYTE`/`FPGA_RX_BYTE`와 `FPGA_WAIT_RDY`를 사용한다. `FPGA_TX_BLOCK`/`FPGA_RX_BLOCK`의 **실제 호출은 현재 `src`에서 없고 매크로 정의만 있다**. 이 block 함수 자체에는 GBC pacing이 없다.

과거 G12-save `sd2snes.map`의 할당된 코드에는 `spi_tx_byte`, `spi_rx_byte`, `delay_us`가 있고 `gbc_spi_pacing`도 BSS에 있다. `.text.spi_tx_block`, `.text.spi_rx_block`, `.text.spi_txrx_byte`는 주소 0의 discarded input section에 있으므로 이 ELF에서 호출되지 않았다. `stm32f4xx/spi.lst`에도 조건부 `delay_us` 호출이 나타난다. 이는 **해당 과거 ELF의 포함 여부**를 확인한 것이며 현재 G13 기기에 같은 바이너리가 올라갔다는 증거는 아니다. 재검토용 SHA-256: 수정 소스 `stm32f4xx/spi.c` `6e4f18bad103d204185853e63220e80fd7ca7d292d4bffa70a545921fd2fe3e1`, 과거 ELF `04a47fb515f02762d549950f28c0591ae5b616f492bf05ece064d472f02515e0`, map `ecd3cee37bd773bb294b1c1e9265eeb817c9bd20fa58a4dbc02a57f909957518`. 원본 바이너리·리스트·맵은 공개 저장소에 없다.

따라서 현재 소스의 GBC 로더에 unpaced block 호출이 숨어 있다는 가설은 정적 검사에서 지지되지 않는다. 물리 SPI SCK/SS/MOSI/MISO/MCU_RDY의 최소·최대 간격, SSEL 중단 복구, 실제 펌웨어 버전은 계측/배포 기록으로 확인해야 한다. `pin.sdc`의 SPI SCK 20.833ns 선언과 펌웨어의 명목 42MHz 설정도 같은 실제 파형을 직접 입증하지 않는다.

## SNES SRAM 조건부 슬롯 재검증

연결 경로를 재확인한 결과 동결 후보의 `snes_frontend.sv`는 `sram_burst_writer.sv` (`fba9cee7…44c03826`)를 사용한다. 앞선 `snes-slot-actual-writer-v1`의 `sram_granted_writer.sv` 시험은 **후보에 존재하지만 해당 frontend에 연결되지 않은 byte writer**의 참고 결과로 정정한다.

실제로 연결된 `snes_sram_slots.sv`·`snes_cart_map.sv`·`sram_burst_writer.sv`를 동일 후보 해시로 고정해 Icarus에서 다시 실행했다. 합성 PHI2/ROMSEL/읽기 신호에서 비-SRAM cycle 다음 SRAM read까지 270ns를 주고 시작 위상 12개를 검사했다. 바이트 쓰기 6회와 워드 쓰기 6회, program/frame read 24회가 예상 데이터와 일치했고 모델의 tAA=45ns·WE pulse≥35ns·주소/데이터 setup 검사를 통과했다. 80ns 조기 읽기 반례에서는 `protocol_error`와 `slot_violation`이 올라왔지만 이미 진행된 쓰기를 되돌리지는 못한다. 비공개 재현 ID는 `snes-slot-burst-writer-v1`; testbench·연결된 frontend·RTL 해시와 로그는 격리 사본의 `verification.json`에 있다. 생산 RTL 수정이나 새 fit은 없었다.

실제 270ns 하한은 **아직 측정하지 않았다**. 다음 보드 관측에서는 CPU fetch, DMA, HDMA, refresh/idle 전환을 포함해 비-SRAM PHI2 상승→다음 SRAM read strobe의 최소 간격을 구분한다. 같은 캡처에서 주소/ROMSEL, `/RD`, SRAM `/OE`·`/WE`, transceiver DIR/OE의 전환 순서와 겹침을 확인하고, 신호별 지연·프로브 분해능을 기록한다. 짧은 간격 한 번이라도 발견되면 현재 슬롯 grant 계약은 실패다. H/V 시간이나 합성 DMA 설정 간격을 이 파형의 대체 자료로 쓰지 않는다.

현재는 로직 애널라이저가 없어 위 보드 파형을 얻을 수 없다. 따라서 270ns·핀 방향 전환·실제 SRAM 사양은 미확인 gate로 유지한다. 그동안에는 동결 RTL의 합성 버스 모델, 리셋 오류 주입, 정적 계약/제약 검사를 진행하고 결과의 적용 범위를 각각 명시한다.

### SRAM 쓰기 중 리셋 오류 주입

실제로 연결된 동결 `sram_burst_writer.sv` (`fba9cee7…44c03826`)에 `/WE` low 시작 후 1/10/25/40ns에 리셋을 넣었다. 바이트 쓰기 펄스와 워드 쓰기의 **두 번째** 펄스 모두 비동기 리셋 경로가 `/WE`와 `/OE`를 즉시 high로 올렸고, 관측된 `/WE` low 폭은 각각 1/10/25/40ns였다. 워드 쓰기의 첫 번째 펄스는 47.616ns였다. 1/10/25ns 자극 6개는 기존 디지털 SRAM 모델의 최소 35ns 쓰기 펄스 조건을 충족하지 못한다. Icarus 오류·경고 없이 8개 자극과 리셋 후 내부 상태 정리 검사를 완료했다. 비공개 재현 ID는 `sram-burst-reset-pulse-v1`이며, testbench/연결된 frontend/RTL 해시와 로그는 격리 사본에 있다. `clock_reset_guard`는 PLL lock 상실 때 이 경로의 리셋을 비동기 assert한다. **이는 현재 연결 경로가 기존 모델의 최소 쓰기 펄스 조건을 충족하지 못하는 반례**다. 실제 시스템 장애 여부는 중단된 페이지가 노출되는지와 물리 SRAM의 동작까지 함께 판정해야 한다. 실제 SRAM의 최소 펄스 폭이나 콘솔에서의 리셋 파형을 측정했다는 뜻은 아니다. 클록이 멈추는 PLL unlock에서도 최소 펄스 폭을 보장한다는 수정은 현재 회로만으로 주장할 수 없다. 다음에는 리셋 시 즉시 핀 비활성화와 미완료 페이지 폐기, 재시작 뒤 새 프레임 전체 재작성의 연결 계약을 검증해야 한다.

후속 단위 시험 `sram-burst-clock-stop-reset-v1`은 같은 동결 writer 해시에서 바이트 펄스와 워드의 두 번째 펄스 시작 10ns 후 클록을 멈추고 리셋을 assert했다. 두 경우 모두 클록이 없는 100ns 동안 `/WE`·`/OE` high, 완료 신호 증가 없음, 클록 없이 리셋을 내려도 비활성 유지, 재시작 후 중단 거래 완료 없음, 새 바이트 쓰기 한 번 완료를 검사했다. Icarus 2건 통과했다. **10ns 펄스 자체는 여전히 남는다.** 이 단위 시험에는 실제 SRAM, 페이지 소유권, 양 PLL의 아날로그 lock, MCU/콘솔 reset 시퀀스가 없다. 전체 출력 경로의 reset 시 불완전 페이지 비공개 검증과 보드 계약은 계속 미결이다.

연결 시험 `sram-page-reset-integration-v1`은 동결된 출력 FIFO·페이지 관리·실제 연결된 burst writer를 묶고, SRAM 내용은 리셋 뒤에도 유지하는 모델을 사용했다. 워드의 첫 번째·두 번째 `/WE` 펄스마다 시작 1/10/25/40ns 뒤 공통 리셋을 넣어 8건을 검사했다. 기존 35ns 모델에서 1/10/25ns의 쓰기 6건은 미완료로 남았다. 각 재시작에서 새 합성 프레임의 사용 바이트 21,764개가 현재 세대로 다시 기록되었고, 완료/게시 각 1회였다. 리셋 직후 불완전 페이지는 공개되지 않았다. 이 결과는 **8개 리셋 위상·각 한 합성 프레임의 디지털 모델**이며 실제 게임 CPU, SNES 버스 서비스, 물리 SRAM, 클록 정지까지의 연결 동작을 검증하지 않는다. 짧은 `/WE` 펄스도 해결되지 않았다.

## 리셋 검증 표

모든 행에서 `WE/OE` 비활성, 소유권 한 명, FIFO/page valid·epoch 초기화와 SaveRAM 보존을 함께 검사한다. RAM 전체가 0일 필요는 없다. 현재 C에 대한 **시험 계획**이며 통과 기록이 아니다.

| 자극 | 기대 관측 | 현재 |
| --- | --- | --- |
| cold boot, PLL lock 지연/상실 | lock 전 WE/OE 안전, core/bus 개별 release 후 단일 첫 epoch | 미검증 |
| console warm reset, menu return, 같은 ROM 재실행 | MCU/renderer/run bit와 양 도메인 valid 재동기화, 이전 frame/data를 새 epoch로 오인하지 않음 | 실기 차이 관측, 원인 미확정 |
| 다른 ROM 후 K141 복귀 | ROM/cache/save mapping 재설정, 보존할 저장만 유지 | 미검증 |
| capture·PSRAM 응답·FIFO drain·SRAM write·DMA/publish 중 reset | 미완료 frame 비공개, ack/toggle 재기준화, pin contention 없음 | SRAM write 중 리셋에서 기존 ≥35ns 모델보다 짧은 `/WE` 펄스 재현; 나머지는 제한 단위 시험만 있음 |
| save 중 reset | 이미 완료된 SaveRAM 유지, 부분 write와 MCU flush/파일 저장 경계 판별 | 미검증; 기존 save 성공 자체는 유지 |
| LCD off/on, 첫 publish | capture invalidation 뒤 다음 완성 frame만 공개 | 제한 모델 시험만 있음 |

## 실행 경로 확인

C `pin.qsf`의 HDL/SDC 참조는 상대 경로다. 과거 `verification.json`의 원본 절대 경로는 증거로 보존한다. 현재 `probes/full-core-link/*.ps1`에는 고정 Python 런타임 경로가 있고 일부 오래된 분석 스크립트에는 Downloads 입력 경로가 있으므로 실행 전 선택한 runner의 **입력·출력·임시 경로**를 다시 확인해야 한다. 이후 빌드는 반드시 사본 내부의 새 결과 디렉터리와 사본에서 생성한 QSF를 사용한다. C의 저장된 `pin.qsf`를 새 후보의 빌드 인증으로 재사용하지 않는다.
