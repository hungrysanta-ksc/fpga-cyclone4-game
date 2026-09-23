# P0 인터페이스·클록·리셋 감사 — 2026-09-23

## 기준과 증거 범위

- 격리 사본: `ISOLATION-MANIFEST.json`의 `complete=true`, 31,256개, 4,090,209,408바이트. 원본 root `.git`만 제외하고 중첩 Git은 보존했다. 이 문서는 사본에서만 작성했다.
- 동결 물리 후보: `probes/full-core-link/results/fxpak-g13-prefill-endpoint-seed7-hold1-v1/` (이하 C). top `fxpak_gbc_top`, EP4CE15F17C8, seed 7, Quartus 25.1std.0 build 1129. C의 `verification.json`에 든 주요 소스·SDC 해시는 실제 파일과 대조했다. `pin.sta.rpt` SHA256 `104ccb42fa7dc87a37b1bda20d26ed306914ca8fd4c07995d5399a8c1606a648`, `pin.fit.rpt` `db6cc91fd382cb5dbbfca5b2a73c91ac19b6481f3698ed2ec175cfe354738f18`.
- upstream Gameboy_MiSTer HEAD `7a5ff50528cd9c1d13ffb675e7df8506bffaa078`, upstream sd2snes HEAD `cf7e21d7a5978fcd74981d71c3cfbf6e982a4dd1`. 둘 다 로컬 수정이 있으므로 HEAD만으로 후보를 재현할 수 없다. 공개용 `repository/` HEAD `0ae1cff231546536865d1918c24fa8f77ca2ad11`, push 전이다.
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
| SNES CPU/DMA → `snes_frontend` → 외부 8비트 SRAM | SNES 주소[23:0], `/RD,/WR,/ROMSEL`, PHI2는 비동기. 동기화된 slot이 비-SRAM 새 사이클에서만 writer grant. raw `/RD`는 OE 해제. `RAM_ADDR[18:0]`, `RAM_DATA[7:0]` 양방향. | `snes_sram_slots.sv`, `sram_granted_writer.sv`: 다음 SRAM read strobe까지 **최소 270ns** 가정, writer 8 bus clocks 예약; WE 4 bus clocks low, 후속 data hold/tri-state. 시뮬레이션 모델 tAA45/tHZ20/tWP≥35ns 등. | 실제 SNES CPU/DMA/HDMA PHI2·주소·read strobe 상대 파형, 트랜시버 DIR/OE turn-around, contention, SRAM 부품/보드 지연 unknown. slot 위반 검출은 이미 시작한 write를 되돌리지 못함. 실기 진단 전 차단 gate. |
| MCU SPI/loader → ROM PSRAM 및 renderer SRAM | SCK↔core toggle+held byte; MCU command/주소[23:0]/data[7:0], `MCU_RDY` completion poll. renderer access는 `mcu_address[23:19]==10001`일 때 별도 loader가 core↔bus handshake. | C `fxpak_gbc_top.sv`, `gbc_spi.sv`, `gbc_sram_loader.sv`; `sgb_features[15]` 후 run. `upstream-sd2snes/src/stm32f4xx/spi.c`의 단일 바이트 TX/RX는 `gbc_spi_pacing`일 때 전송 뒤 `delay_us(1)`을 호출하고 `fpga.c`는 `FPGA_SGB` 구성 시 이 flag를 켠다. 정적 코드 근거다. | 실제 firmware build에 이 코드가 포함되는지, 1µs 최소 간격의 계측, SS 중단·빠른 back-to-back·MISO/MCU_RDY 타이밍, loader와 live SRAM ownership 전환 unknown. block TX/RX 함수 자체에는 pacing이 없어 GBC 경로에서 호출되지 않는지 callsite 회귀 필요. |
| GBC ROM/cache/SaveRAM ↔ PSRAM | 16비트 `ROM_DATA`, byte lane `ROM_BHE/BLE`, 주소[21:0], OE/WE. Save 주소 17비트 생성, K141 8KiB 회귀 성공. | C `rom_bus_bridge_save.sv`,`psram_rw3_save.sv`, `full_core_link.sv`; G12S2 세 방향 save 교차 로드는 사용자 실기 성공. | 외부 PSRAM 실제 데이터/주소 setup/hold, OE/WE 및 양방향 turn-around, MCU 동시 접근·저장 중 reset 보호는 별도 gate. Save 재구현 대상 아님. |
| joypad → GBC | SNES register의 8비트 상태+toggle가 bus→core 2단 전달, bundled data hold. | C `joypad_cdc.sv`, `board_output_cdc.sdc`; 이전 G12 실기 조작 성공. | 빠른 연속 갱신/메뉴 복귀/reset edge 및 실제 입력 지연 범위 unknown. |
| GBC APU → audio PSRAM delay → DAC | source signed stereo16, CIC/64, 8192-sample 외부 PSRAM ring 후보, commit toggle가 bus 84MHz로 전달. `DAC_MCLK/LRCK/SDOUT` 출력. | C `gbc_dac_psram.sv`, `audio_psram_delay_client.sv`; 기존 제한 통합에서 overrun/serial mismatch 0. | DAC 부품 setup/hold, 지연 ring의 최악 backlog와 실제 표시 frame age, reset 시 오디오 연속성 unknown. |
| SNES reset/menu/reconfigure ↔ MCU/FPGA | `power_reset=0`인 top에서 PLL lock과 run bit가 내부 실행을 지배; SNES IRQ는 0, 일부 보드 입력은 미사용 tie-off. | C `fxpak_gbc_top.sv` 및 G12 실기 cold/warm 차이 관측. | 콘솔 reset이 FPGA 구성·MCU command·renderer 상태에 각각 미치는 효과를 원인별로 분리해야 함. ROM/save 재적재, epoch, OE 안전 기본값 확인 필요. |

## 리셋 검증 표

모든 행에서 `WE/OE` 비활성, 소유권 한 명, FIFO/page valid·epoch 초기화와 SaveRAM 보존을 함께 검사한다. RAM 전체가 0일 필요는 없다. 현재 C에 대한 **시험 계획**이며 통과 기록이 아니다.

| 자극 | 기대 관측 | 현재 |
| --- | --- | --- |
| cold boot, PLL lock 지연/상실 | lock 전 WE/OE 안전, core/bus 개별 release 후 단일 첫 epoch | 미검증 |
| console warm reset, menu return, 같은 ROM 재실행 | MCU/renderer/run bit와 양 도메인 valid 재동기화, 이전 frame/data를 새 epoch로 오인하지 않음 | 실기 차이 관측, 원인 미확정 |
| 다른 ROM 후 K141 복귀 | ROM/cache/save mapping 재설정, 보존할 저장만 유지 | 미검증 |
| capture·PSRAM 응답·FIFO drain·SRAM write·DMA/publish 중 reset | 미완료 frame 비공개, ack/toggle 재기준화, pin contention 없음 | 제한 단위 시험만 있음 |
| save 중 reset | 이미 완료된 SaveRAM 유지, 부분 write와 MCU flush/파일 저장 경계 판별 | 미검증; 기존 save 성공 자체는 유지 |
| LCD off/on, 첫 publish | capture invalidation 뒤 다음 완성 frame만 공개 | 제한 모델 시험만 있음 |

## 실행 경로 확인

C `pin.qsf`의 HDL/SDC 참조는 상대 경로다. 과거 `verification.json`의 원본 절대 경로는 증거로 보존한다. 현재 `probes/full-core-link/*.ps1`에는 고정 Python 런타임 경로가 있고 일부 오래된 분석 스크립트에는 Downloads 입력 경로가 있으므로 실행 전 선택한 runner의 **입력·출력·임시 경로**를 다시 확인해야 한다. 이후 빌드는 반드시 사본 내부의 새 결과 디렉터리와 사본에서 생성한 QSF를 사용한다. C의 저장된 `pin.qsf`를 새 후보의 빌드 인증으로 재사용하지 않는다.
