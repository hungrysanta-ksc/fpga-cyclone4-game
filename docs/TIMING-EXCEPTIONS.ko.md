# P0 타이밍·예외 판정 — 2026-09-23

대상은 `probes/full-core-link/results/fxpak-g13-prefill-endpoint-seed7-hold1-v1/`의 **원래 STA 제약** `pin.sdc` + `board_output_cdc.sdc`다. `placement-target.sdc`는 fitter용 추가 min-delay와 ROM_OE 요구 변경을 담고 있으며 원래 STA 제약과 구별한다. 세 파일 및 성공/실패 결과를 수정하지 않았다. 새 제약이 필요하면 버전 이름·근거·diff·영향 경로를 먼저 적고 같은 소스 후보에 실행한다.

## 보고서가 입증하는 범위

| 항목 | 보고값 | 판정 |
| --- | --- | --- |
| STA 5종 최소 slack | setup +0.051ns, hold +0.134ns, recovery +8.036ns, removal +0.673ns, min pulse +5.649ns | **적용된 제약에 한해** 양수. C `pin.sta.summary`와 `verification.json`. 물리 I/O/CDC 승인 아님. |
| fit | LE 14,877/15,408; M9K 56/56; 135 physical pins; virtual 0 | C `pin.fit.summary`. 자원 확장 여유와 board timing은 별도. |
| clock status | board8, SPI SCK, 두 PLL generated 및 virtual sys 모두 constrained | C `pin.sta.rpt` Clock Status. clock transfer 구조/false path의 적절성은 별도. |
| unconstrained path summary | 입력 **36 ports/292 paths**, 출력 **29 ports/1030 paths**, setup과 hold 모두 동일 | C `pin.sta.rpt` Unconstrained Paths Summary. **출하 차단 미분류 잔여**. |
| 기본 상세 UCP 표 | 입력 `SPI_MOSI`, `SPI_SS` 2개 이름; 출력 `MCU_RDY`, `ROM_WE`, `SNES_DATABUS_DIR`, `SNES_DATABUS_OE`, `SPI_MISO` 5개 이름 | 요약 36/29와 다르다. 기본 표를 전체 목록으로 해석하면 안 된다. 비트 확장/보고 필터·setup/hold·포트/경로 집계 차이는 확장 `report_ucp`로 대조해야 한다. |
| metastability | 53 chains, 최단 2 registers, MTBF 미계산 비율 0.962 | 약 51/53 chain에 계산값 없음으로 추정되지만 원인/chain ID는 별도 보고 필요. `1e+09 years` headline은 전체 승인 불가. 0.962는 고장 확률이 아니다. |

## 포트·경계 분류

| 집합 | 현재 상태 | 필요한 계약/판정 |
| --- | --- | --- |
| SPI_MOSI/SS/SCK/MISO, MCU_RDY | SCK clock 20.833ns(약48MHz) 선언, MOSI/SS와 MISO/RDY 지연 미지정. STM32 소스는 SPI1 42MHz mode 0 및 GBC 단일 바이트 후 조건부 1µs pacing. SCK→PLL 계열 넓은 false path. | 실제 MCU 빌드/파형의 mode·최단 간격과 선언의 관계, MOSI/SS setup/hold, MISO 출력/tri-state, MCU_RDY sample 방식. protocol-asynchronous인 첫 단계와 timed I/O를 분리. **실제 쓰이는 포트**. |
| ROM_DATA/ADDR/CE/OE/BHE/BLE/WE | sys virtual 29.801ns, ROM_DATA max 87.6ns 및 3/2 multicycle, 출력 다수 17.201ns. `ROM_WE`는 상세 UCP에 남음. | 부품 tAA/tOE/tWP, lane setup/hold, FPGA/board delay·양방향 turnaround, multicycle의 안정 데이터 전제와 실제 read/write 파형. WE를 static으로 처리하지 않음. |
| RAM_DATA/ADDR/OE/WE | bus clock에 0ns I/O envelope; output max는 뒤의 -11.9047619ns가 대체. RAM_DATA 양방향. | 이 수치는 내부 routing 예산이며 8비트 SRAM tAA/tWP/setup/hold 및 board 지연을 포함하지 않음. OE/WE·FPGA/MCU/SNES transceiver contention 검증. |
| SNES_ADDR/DATA/PHI2/RD/WR/ROMSEL | 첫 sampling FF에 제한된 false path. 데이터의 다른 raw 사용, OE release 경로는 그대로. 0ns virtual input envelope. | 실제 CPU/DMA/HDMA 파형, min/max input arrival, raw `/RD`→OE release, address/data stability 및 270ns slot 계약. protocol-asynchronous라고 전체 경로를 자르지 않음. |
| SNES_DATABUS_DIR/OE | 상세 UCP에 존재; 실제 트랜시버 제어 | 방향 전환 dead time, FPGA/SNES data drive 중복 금지, 출력 delay 및 전압/핀 회로 확인. **출하 차단**. |
| DAC_MCLK/LRCK/SDOUT | 0ns bus 출력 제약 | DAC 부품 clock/data setup/hold, 보드 지연, serial phase. 기존 simulated serial exact만으로 전기적 합격 불가. |
| unused/static 보드 입력/출력 | top에서 SNES_CIC_CLK/REFRESH/PA/PARD/PAWR 등 일부 명시 미사용, IRQ=0, ROM_ZZ=1 | 합성 후 실제 pin list와 회로의 안전한 기본 레벨 대조. UCP 요약 전체 36/29를 이 집합으로 덮어쓰지 않음. |

## 예외·경고 ledger

| ID | 실제 제약/로그 | 잠정 판정 | 다음 확인 |
| --- | --- | --- | --- |
| E1 | `pin.sdc`: `set_false_path -from mcu_spi_sck -to {*|pll|*}` | SPI toggle/held data CDC를 의도한 듯하나 대상이 넓음. SPI SCK-domain → core 첫 동기화·held bundle·MISO 조합 경로를 개별 분해하기 전 유효성 미확정. | `report_clock_transfers`, `report_exceptions`/path 상세과 RTL 대조; MCU 최소 간격과 bundle hold. |
| E2 | `pin.sdc`: renderer_loader의 request/ack/run 첫 sync FF false path, address/write/is_write→bus max10ns + hold false, result→read_data max15ns + hold false | handshake와 안정 데이터가 전제일 때만 합리적. clock/reset 후 재전송·실제 bus endpoint 매칭 확인 전 보류. | matched endpoint 수, toggle ownership와 stable window, 오류 주입. |
| E3 | `board_output_cdc.sdc`: writer Gray pointer와 uploader toggles 첫 FF false path + net max10ns; entry/held bundled data max10ns·hold false | 자료 구조상 근거가 있으나 Gray skew/hold 및 어떤 제약이 최적화 후 실제 적용됐는지 미완결. | 전체 chain별 endpoint·최대 skew, 이중 전환·reset 동시성, 보고서 생성. |
| E4 | guard release → 도메인 reset pipe false path; joypad/audio/diagnostic toggle·bundled data 예외 | async assert/sync release 의도. hold false 대상은 stable-data invariant가 필요. | reset injection, payload stability assertions 및 endpoint report. |
| E5 | SNES pad → **첫 sampling FF만** false path | 비동기 입력에 정당할 수 있음. raw `/RD`→OE 및 두 번째 FF는 제외되지 않아야 함. | `report_exceptions`와 실제 pad-to-OE 경로 확인, 외부 timing 모델. |
| W1 | STA `332174` 5건: `*uploader|brst*`, `*writer|bus_reset*`, `*writer|source_reset*`, `*host_frontend|bridge|wr_sync[0]`, `*host_frontend|bridge|addr_meta[*]` unmatched | 최적화/병합/현재 hierarchy 차이 가능. `required_regs`의 nonempty 전체 collection 검사로 개별 패턴 실패가 가려질 수 있음. 미적용 대상이 실제 필요한 경로라면 **제약 누락**. | 각 register의 post-map 이름/경로와 예외가 실제 의도대로 적용된 endpoint 수 대조. 임의 wildcard 확장 금지. |
| W2 | STA `332054` 29건: `board_output_cdc.sdc:44`가 RAM_DATA[0:7], RAM_ADDR[0:18], RAM_OE/WE output delay 대체 | 같은 `-max` 0ns 뒤 -11.9047619ns override가 의도적 routing budget일 수 있음. `-add_delay`를 경고 제거용으로 넣으면 **의미가 달라짐**. | post-SDC 실제 min/max 값을 포트별 출력하고 외부 SRAM timing 계약과 분리. |
| W3 | STA `114001` 5건: 29.8013245, 17.2013245, -11.9047619ns 등 반올림 | 수치 표현 경고. 작은 setup slack과 같은 자릿수라 영향 크기 비교 필요. | 적용된 시간값과 worst path에 대한 영향 기록; 무근거 period 완화 금지. |
| M1 | 53 chains 중 0.962 MTBF unavailable | 보고 범위 부족. 수동으로 모든 chain이 안전하다고 간주 불가. | `report_metastability -nchains 100`, source/dest clock, toggle rate, settling/chain 식별, missing reason 분류. |

## P0 다음 재현 명령과 안전 조건

C에는 `clock_checks.tcl`이 `check_timing`, `report_clock_transfers`, `report_ucp`를, `cdc_metastability.tcl`이 `report_metastability -nchains 100`을 요구한다. 스크립트 존재만 확인했으며 C에 해당 출력 `full-unconstrained.rpt`, `full-clock-transfers.rpt`, `cdc-metastability-*.rpt`는 보존되지 않았다. 현재 기본 `.sta.rpt`의 기본 UCP 목록 2/5로 36/29를 해소하지 않는다.

새 분석 실행 전 C의 `pin.qsf`가 상대 HDL/SDC 경로인 점을 확인했지만, 동결 결과 폴더에 STA netlist가 보존됐는지 확인하고 복사본에서만 실행한다. 원본 임시 경로가 기록된 JSON/로그는 증거로 유지한다. 분석 보고서는 별도 `p0-timing-audit-v1/`에 출력한다. 실제 DB가 없으면 새 full-fit을 무작정 시작하지 않고 **미결**로 기록한다. 새 SDC 예외나 slack 완화는 이 P0 단계에서 하지 않는다.
