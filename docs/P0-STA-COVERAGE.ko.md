# P0 확장 STA 경로 감사 — G13 seed 7

대상은 `fxpak-g13-prefill-endpoint-seed7-hold1-v1`의 **동일 소스·핀·seed**다. `tools/run_sta_coverage.py`는 개인 snapshot 안의 `p0-g13-sta-coverage-v1/`에만 새 Quartus DB와 보고서를 만들었다. 모든 후보 파일을 `verification.json`의 SHA256과 대조하고, fitter에는 기록된 `placement-target.sdc`를 사용한 뒤 STA 전에 원래 `board_output_cdc.sdc`로 복원했다. Quartus Prime Lite 25.1std.0 build 1129의 map/fit/STA, `clock_checks.tcl`, `cdc_metastability.tcl`이 모두 성공했다. bitstream은 생성하지 않았다.

새 `pin.sta.summary`는 동결 후보와 **줄 단위로 동일**하다. fit summary도 실행 시각을 제외하면 같다: LE 14,877/15,408, M9K 56/56, 적용 제약의 최저 setup +0.051ns/hold +0.134ns. 새 raw fit/STA 보고서의 바이트 해시는 경로·실행 시각 때문에 동결본과 다르므로, 이 수치 일치를 보드 signoff로 확대하지 않는다.

## 미제약 경로의 실제 구성

기본 `pin.sta.rpt`의 `SPI_MOSI`, `SPI_SS`와 5개 출력 이름은 **입출력 delay 또는 예외가 없는 포트 표**다. `report_ucp`의 경로 표는 setup/hold에서 각각 **36개 입력 포트의 292개 경로**, **29개 출력 포트의 1,030개 경로**를 확인했다. 따라서 2/5와 36/29는 다른 집계이며 보고서 누락 추정이 아니다. 같은 입출력 간 조합 경로는 입력·출력 경로 표에 모두 나타나므로 292+1,030을 서로 다른 결함 수로 더하지 않는다.

| 경로 표 | 분포 | 판정 |
| --- | --- | --- |
| 입력 경로 292 | `SNES_ADDR_IN[0:22]` 230, `SNES_READ_IN`/`ROMSEL_IN`/`WRITE_IN` 각 10, `RAM_DATA[0:7]` 8, `SPI_MOSI` 2, `SPI_SS` 22 | 이 중 **269개는 종단 clock 표기가 없는 입력→출력 조합 경로**다. 특히 SNES 주소·제어→`SNES_DATA`/DIR/OE와 SRAM data→SNES data는 외부 파형·트랜시버 계약이 필요하다. 나머지 23개는 SPI clock 도메인 register 등으로 간다. |
| 출력 경로 1,030 | `SNES_DATA[0:7]` 795, DIR 86, OE 86, `ROM_DATA[0:15]` 48, `SPI_MISO` 12, `ROM_WE` 2, `MCU_RDY` 1 | 269개 입력→출력 조합 경로가 이 표에도 들어간다. 나머지는 register/clock에서 출력까지의 외부 delay 계약을 확인해야 한다. 특히 DIR/OE와 ROM_WE를 static/unused로 분류하지 않는다. |

`report_clock_transfers`는 core→bus 290 RR, bus→core 23 RR 경로를 표기하고 SPI SCK→core를 `false path`로 표기한다. 이 숫자는 clock 간 전체 경로 집계이며 path별 예외를 감안한 실제 유효 경로 수가 더 적을 수 있다고 Quartus가 명시한다. CDC 적합성이나 SPI bundle hold를 이 표만으로 판정하지 않는다.

## MTBF 체인 분해

`report_metastability -nchains 100`은 세 operating condition에서 각각 **53개 체인**을 출력한다. slow 85°C 표에서 **51개 Automatic 체인은 MTBF가 계산되지 않았고**, **2개 User Specified 체인(#37 DAC toggle, #52 joypad toggle)**만 `Greater than 1 Billion Years`로 계산·집계됐다. 미계산 51개에는 SNES 주소/데이터 첫 동기화 FF, 출력 FIFO Gray pointer, SPI byte toggle, loader, reset/진단 체인이 들어간다. 보고서의 `0.962`는 51/53의 미계산 비율이지 고장 확률이 아니다.

일부 체인은 source clock을 `Unknown`으로 표기하지만, 그것만으로 51개 전체의 미계산 이유를 설명할 수 없다. 예를 들어 SNES 주소 체인은 소스/동기화 clock 항목에 bus clock이 나타나도 `Not Calculated`다. `Automatic`과 `User Specified`의 차이는 관측된 상관관계이며 원인 확정이나 미계산 체인의 안전 판정이 아니다. 체인별 false path·toggle rate·첫 FF와 후속 FF의 matched endpoint를 RTL/SDC와 대조해야 한다.

## 미적용 register 이름 5개

`tools/sta_endpoint_audit.tcl`로 재생성된 netlist에서 경고 `332174`의 이름을 조회하고, 같은 실행의 `pin.map.rpt` 중복 register 병합 표와 대조했다.

| 원래 SDC 패턴 | netlist 조회와 합성 기록 | 남은 판단 |
| --- | --- | --- |
| `*uploader|brst*`, `*writer|bus_reset*` | 둘 다 0개. `brst[0]`/`bus_reset[0]`는 SNES frontend `reset_pipe[0]` 쪽으로 연쇄 병합됐고 `[1]`도 `reset_pipe[1]`로 병합됐다. frontend reset pipe 2개는 실제 존재. | reset release 예외의 실제 source/target과 recovery/removal 영향 확인 필요. |
| `*writer|source_reset*` | 0개. `[0]`은 uploader `srst[0]`를 거쳐 PSRAM `pin_reset`에 병합; uploader `srst[1]`은 실제 존재. | 동일 논리 병합은 확인됐지만 모든 의도 경로가 예외 처리됐다는 증거는 아니다. |
| `*host_frontend|bridge|wr_sync[0]`, `*host_frontend|bridge|addr_meta[*]` | 둘 다 0개. 각각 slots `wr_sync[0]` 1개와 slots `addr_meta[0:22]` 23개로 병합된 사실을 map 보고서가 명시한다. slots 패턴은 실제 register에 매칭된다. | slots 경로에 설정된 첫 FF 예외가 병합된 bridge 사용까지 적절한지 path별 확인 필요. |

따라서 다섯 경고는 이 후보에서 **원래 이름의 register가 없기 때문에** 발생했다. 경고가 무해하다고 일반화하거나 wildcard를 넓혀 없애지 않는다. 다른 fit/seed에서 병합 대상이 바뀔 수 있으므로 후보마다 조회를 반복한다.

## 다음 gate

1. **보드 계약:** 실제 FXPAK Pro 개정판·SRAM/PSRAM/DAC·트랜시버 부품과 회로의 지연/전압/방향을 확인하고, SNES `/RD` 해제·DIR/OE의 최소/최대 파형과 MCU SPI 입력/출력 지연을 잡는다. 270ns slot은 현재 시뮬레이션 가정이다.
2. **예외 적용:** `332174` 다섯 이름의 병합 대상은 찾았다. 실제 false path와 endpoint 적용 범위 및 `332054` output delay 대체 29개의 실제 적용값을 개별 대조한다. 단지 경고를 지우는 SDC 변경을 하지 않는다.
3. **CDC:** 51개 미계산 체인의 용도/clock/false path·bundle hold를 분류하고 필요한 작은 reset·연속 toggle 시험을 연결한다. 현재 계산된 2개만으로 전체 MTBF를 승인하지 않는다.

raw 보고서·Quartus DB·boot image는 공개 저장소에 없다. 개인 감사 폴더에서 `full-unconstrained.rpt` SHA256 `681904d96c61588329e2df5eb9082382f9eec3e6b3555d8caf93c9bcf9c950ef`, `full-clock-transfers.rpt` `93a28dc5cfe73f3a2a61301efb6926535be158c98611abf100839a7557530c2c`, slow 85°C MTBF 보고서 `3488b3fa56ab5818aa8522402caf1063c5f14aad464daa1632590648ea5d1969`를 보존한다. `tools/summarize_sta_coverage.py`로 위 집계를 재생성할 수 있다.
