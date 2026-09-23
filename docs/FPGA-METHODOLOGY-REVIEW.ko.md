# FPGA 개발 방법론 재검토 — 2026-09-23

## 결론

포팅만 무작정 한 것은 아니다. 독립 영상 oracle, byte/RGB exact 비교, 오류 주입, lifecycle 시험, 동일 소스 해시, 실제 FPGA 배치까지 쌓은 검증은 유지할 가치가 있다. 다만 **기능 검증을 확장하는 속도에 비해 보드 인터페이스 계약·제약 완전성·자원/대역폭 예산·요구사항별 완료 판정이 뒤처졌다.** 특히 기존 `timing_pass=true`는 보드 전체 검증 완료로 읽으면 안 된다. 이를 보완한 뒤 최적화를 재개한다.

공식 Altera Quartus Standard 지침을 우선 사용했다. 문서 버전은 18.1 계열 설계 원칙이며 실제 설치 25.1std에서 명령·옵션 지원을 확인해야 한다. 최신 고급 FPGA의 기능을 Cyclone IV에 있다고 가정하지 않는다. 규제 인증/UVM 도입 자체를 목표로 하지 않는다.

## 일반 원칙과 현재 프로젝트 대조

| 원칙 | 이미 수행 | 보완 |
| --- | --- | --- |
| 요구→인터페이스/자원 예산→검증 계획→구현 | 무열화 비전, 독립 모델, 실제 게임 샘플 | 요구별 evidence/gate, 시스템 예산과 버스 계약을 구현보다 앞에 둔다 |
| 단위→통합→물리 구현→실기 | 단위/부정 시험과 출력 endpoint/full-fit | 실제 CPU·MCU·renderer·보드 경계를 합성 host와 구별한다 |
| 클록·리셋 경계를 명시 | 2단 동기화, Gray FIFO, 시작 guard, reset 시험 | 모든 경계의 종류/소유권/초기화/예외를 한 표로 추적한다 |
| STA는 제약의 정확성이 전제 | setup/hold 등 5종 슬랙 검사 | 미제약 I/O, 무효 예외, 보드 지연, MTBF 보고 범위를 별도 gate로 추가한다 |
| 물리 자원과 대역폭을 함께 설계 | fit 자원·cycle·FIFO peak 계측 | M9K 실제 블록 수, 최장 blackout, 누적 backlog/표시 나이, 메모리 충돌 계약 |
| 재현 가능한 실패/성공 | 소스 hash·동결 결과·실패 보존 | 경로 독립 실행, tool/version/seed/SDC/ROM 식별, Git allowlist와 clean rebuild |

검증 계획·시험 명세·결과 보고를 구분하고 요구에서 결과까지 추적하는 방식은 일반 검증 관리에도 유용하다. 인증 대상 프로젝트라는 뜻은 아니다. [Siemens: verification의 범위와 계획/명세/보고](https://blogs.sw.siemens.com/eda-consulting-services/2021/06/09/confused-by-scope-of-verification-in-iso-26262/).

## 발견 1 — 적용된 제약 통과 ≠ 전체 타이밍 signoff

대상: `probes/full-core-link/results/fxpak-g13-prefill-endpoint-seed7-hold1-v1/`의 `pin.sta.summary`, `pin.sta.rpt`, `verification.json`.

- 최소 setup **+0.051ns**, hold **+0.134ns**. recovery/removal/min-pulse도 기존 집계에서 양수다. 이것은 유효한 부분 성과다.
- 같은 `.sta.rpt`의 요약은 **미제약 입력 포트 36, 출력 포트 29**, 입력 경로 292, 출력 경로 1030을 보고한다.
- 상세 목록에서 SPI_MOSI/SPI_SS 및 MCU_RDY/ROM_WE/SNES_DATABUS_DIR/SNES_DATABUS_OE/SPI_MISO가 보인다. 요약 수와 이 목록의 수가 다르므로 확장 `report_ucp`로 대상/분석 범위를 대조해야 한다. 모든 항목이 버그라는 뜻도, 나머지가 안전하다는 뜻도 아니다.
- `fit_g13_word_endpoint.py`의 timing_pass는 summary의 5종 슬랙을 모아 판정한다. 미제약 경로·무효 제약·CDC 구조를 승인하는 검사가 아니다.
- SPI_SCK clock은 있으나 SPI 입출력 지연은 불완전하다. `mcu_spi_sck`→PLL 계열의 넓은 false path는 실제 동기화 구조와 안정 데이터 계약별 근거가 필요하다.
- `board_output_cdc.sdc`의 RAM 입출력 0ns 및 출력 -11.9047619ns 등은 주석대로 내부 routing 예산 성격이다. 외부 SRAM tAA/tWP/setup/hold, 보드 지연까지 검증됐다는 뜻이 아니다. DAC 경계도 동일하게 구별한다.
- unmatched reset/uploader/writer/bridge 패턴(332174), RAM output delay 대체(332054), 수치 반올림(114001) 등을 각각 판정한다. 병합/최적화나 의도적 override일 수 있다. warning을 모두 없애려고 `-add_delay`나 false path를 일괄 추가하지 않는다.
- `clock_checks.tcl`, `cdc_reports.tcl`이 사본에 있다는 것과 그 후보에서 실행되어 보고가 남았다는 것은 다르다.

Altera는 FPGA 내부만의 제약이 아니라 외부 시스템과 연결한 I/O 제약과 완전한 클록 관계를 요구한다. 잘못된 관계는 CDC 식별에도 영향을 준다. [공식 system-centric timing 지침](https://docs.altera.com/r/docs/683323/18.1/intel-quartus-prime-standard-edition-user-guide-design-recommendations/apply-complete-system-centric-timing-constraints-for-the-timing-analyzer?contentId=ziiyWBJXKjJ3J9OmPEBK2Q).

조치: 원래 SDC/성공 결과는 동결. 수정이 필요하면 별도 제약 버전으로 근거·diff·영향 경로를 기록하고 동일 후보에 재실행한다. ‘원래 제약을 영원히 고정’도, 통과하려고 완화하는 것도 맞지 않다.

## 발견 2 — CDC/리셋 검증 범위

같은 `.sta.rpt`는 53개 동기화 chain, 최단 2레지스터, **MTBF 계산 불가 비율 0.962**를 보고한다. `1e+09 years` 헤드라인만으로 전체 안정성을 주장할 수 없다. 96.2%는 계산/분석 범위의 문제이며 96.2% 고장 확률이 아니다. 관련 클록의 잘못된 분류, chain 강제 식별, toggle rate, 제약·settling 조건을 chain별로 검토한다. [Altera metastability reports](https://docs.altera.com/r/docs/683323/18.1/intel-quartus-prime-standard-edition-user-guide-design-recommendations/metastability-reports?contentId=p3cTBAjmz_hHYkinTNGWKg).

CDC는 ‘2단 플롭이 있다’만으로 끝나지 않는다. pulse 손실, toggle 두 번 합쳐짐, 다비트 원자성, FIFO Gray 경로 skew, 안정 데이터 hold 시간, reset 중 요청/응답 유실과 재시작 epoch를 확인한다. SPI의 byte spacing 주석도 MCU 실제 전송 코드와 대조한다. 비동기 reset은 도메인별 해제 동기화와 PLL lock 전후 상태를 검토한다. [Altera synchronized asynchronous reset](https://docs.altera.com/r/docs/683323/18.1/intel-quartus-prime-standard-edition-user-guide-design-recommendations/use-synchronized-asynchronous-reset?contentId=uO1NM_ceyYJJ7uTAQwfMMA).

실기 warm-reset 관찰은 중요한 단서이나 원인 확정이 아니다. 영상 경로만의 초기 RAM 패턴 시험으로 실제 게임 CPU/PPU·MCU·SNES 재시작을 배제할 수 없다. 첫 오류 시점의 고정된 context와 reset 이후 덤프를 구별해야 한다.

## 발견 3 — 메모리 ‘남은 비트’와 ‘추가 버퍼 가능량’은 다르다

동일 후보 `pin.fit.summary` / `pin.fit.rpt`:

| 자원 | 사용량 | 의미 |
| --- | --- | --- |
| LE | 14,877 / 15,408 | 531 LE 남음, 약 96.55%; 추가 제어/계측과 배선 여유 주의 |
| 메모리 비트 | 431,104 / 516,096 | 비트 집계 약84% |
| M9K 블록 | **56 / 56** | 새 블록은 없음; 재배치/폭·깊이 packing/기존 기능 절감 없이 단순 버퍼 증설 불가 |
| PLL | 2 / 4 | 잔여 PLL이 영상 대역폭을 늘려주는 것은 아님 |
| 핀 | 135 사용, virtual 0 | 오래된 virtual-pin fit 단계보다 진전됨; 외부 전기적 타이밍 승인과는 별개 |

높은 점유율만으로 구현 불가를 확정하거나 임의의 ‘70% 이하’ 기준을 만들지 않는다. 실제 critical path·메모리 배치·버스 처리량이 기준이다. 파이프라인 추가도 레지스터와 메모리 재배치 비용을 함께 계산한다. [Altera FPGA resource planning](https://docs.altera.com/r/docs/683323/18.1/intel-quartus-prime-standard-edition-user-guide-design-recommendations/planning-fpga-resources?contentId=LD7mHCW52COemjGZe8_7zQ).

SignalTap 같은 내부 로직 분석기는 공짜가 아니다. 현재는 적은 자원의 sticky fault/counter/기존 dump 확장부터 비교하고, JTAG 접근 가능 여부·디버그 코어 비용·계측으로 달라진 배치/타이밍을 확인한 경우에만 선택한다. 하드웨어 구매나 납땜은 이 계획에 포함하지 않는다.

## 발견 4 — 시간 초과와 무열화 요구의 연결을 명문화

최신 prefill은 nominal 10화면에서 최대535928클록으로 기존 561792 기준을 통과하지만 dense 두 조건에는 최악854748/852474클록, 각각2회 초과가 남는다. 첫 DMA gap 허용은 첫 화면만7103클록 개선했고 후속854748/702729와2회 초과는 남았다. 모두 제한된 시험에서 RGB/SRAM exact였지만 실기나 무한 연속 처리 증명은 아니다.

561792 단일 처리 지연 gate는 유지한다. 다만 원래 허용된 표시 반복과 원본 프레임 손실은 다르므로, 이 gate가 제품 요구를 충분히/필요하게 대변하는지 별도 검증해야 한다. 장기 source/capture/commit/display epoch 순서, 누락·중복, 최대 backlog·frame age, 서비스율과 최장 blackout을 측정한다. 기준 변경은 실패 숨기기가 아니라 증명과 명시적 결정이 있어야 한다.

현재 SNES native 첫 설치 계측은 실제 FPGA bus trace가 아니다. 반복 설치와 refresh/HDMA·CPU address·PHI2·read strobe를 포함한 증거가 필요하다. 270ns 쓰기 slot 계약은 아직 별도 검증 항목이다. 물리 파형 확보 수단이 없으면 모델만으로 승인하지 않고 부족한 관측을 명시한다.

## 발견 5 — 형상·진행 관리

root Git HEAD가 없고 소스/문서/결과가 대부분 untracked다. 기존 해시 증거는 보존하지만, 현재 상태에서 빈 worktree는 재개 자료를 잃는다. 분리된 전체 로컬 사본과 hash manifest를 먼저 만든다. 다음으로 소스·스크립트·제약·문서 allowlist를 정해 버전 관리한다. ROM/save/license/tool cache/results를 일괄 커밋하거나 외부로 push하지 않는다.

누적 상태 문서의 과거 ‘최신’/save-first/라이선스 대기/virtual pins 지시는 현재와 충돌한다. START-HERE와 EXECUTION-PLAN으로 현재 지시를 단일화하고 과거 기록은 증거로만 남긴다. 진행률 % 대신 요구별 구현/모델/RTL/fit/실기 상태를 보고한다.

## 이번 검토의 한계

보고서·소스·공식 방법론을 대조한 감사다. 새로운 full-fit/시뮬레이션/실기 측정은 하지 않았다. 제약 누락과 자원 압박은 확인했으나 이것이 사용자 점멸의 원인이라고 입증한 것은 아니다. 최종 무열화 가능성도 아직 확정할 수 없다.
