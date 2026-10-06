# H1 039: FPGA 최초 오류 분리

038 사용자 로그는 exit_reason=F2_STATUS, last_status_hex=07, polls=30,
start_result=0, stop_result=0, epoch=1, base_restored=1이었다.
MCU의 종료 판단은 RESET 감지가 아닌 FPGA 오류 응답이었다.07의 RUN/LOCK bit는1이고
통합 오류 bit도1이다. 실제 내부 오류 종류는038에 없으므로 아직 확정하지 않는다.
43개의10ms tick(430ms)은 FPGA 설정 시간을 포함하며30polls를 정확한 실행시간으로 바꾸지 않는다.

[039 설치 안내](../docs/nes-h1-fault-test.ko.md), 실기 ZIP (로컬 비공개 자료: `local-h1-fault-039/NES-H1-FAULT-039.zip`).
이번 후보는 원인 수집용이다. 화면 순환 실패를 고쳤다는 주장이 아니다.
기존 오류 판정과 MCU의 STOP/메뉴 복귀는 유지한다. FPGA/MCU를 쌍으로 업데이트한다.
프로토콜은39, 기존 실행 표식은 NES H1 037.nh1, 화면 프로그램 제목은 NES H1 034다.

## 최초 오류 관측

FPGA는 기존 통합 오류를 처음 관측한84MHz edge에서 스냅샷을 잡고 STOP/리셋까지 유지한다.
아래 F5…FF와 F0/F1/F2를 MCU가 CPU RESET을 잡은 뒤 STOP 전에 읽는다.
기본 FPGA 검증 후 /sd2snes/nes-h1-last-039.txt에 기록한다. SD 쓰기 실패로 복귀를 막지 않는다.

|SPI 명령|스냅샷 내용|
|---|---|
|F5|bit7 valid,6 producer_fault,5 stage_fault,4 exhausted,3 busy,2 ready,1 read_n,0 write_n|
|F6|상위4bit frontend_error mask,하위4bit bus_error code|
|F7|bit4 ROMSEL_n,하위4bit producer_error code|
|F8…FA|관측 주소24bit,낮은 바이트 먼저|
|FB…FE|ARM 후 동작 클록 카운터32bit,낮은 바이트 먼저|
|FF|published의 하위8bit|

오류 레지스터가 갱신된 다음 관측 edge의 주소이므로 원래 실패 버스 사이클의 주소로 단정하지 않는다.
시간 카운터는 nominal84MHz 기준이고 외부 전기 계측이 아니다. detail_hex는 F0/F1/F2와 F5…FF를
이 순서대로 붙인14바이트다. 식별A5/프로토콜39가 맞지 않으면 스냅샷을 신뢰하지 않는다.
[해석기](../tools/decode_nes_h1_fault.py)는038의 실제 로그와039의 합성5조건으로 확인했다.

## 실행 검증

- 전체 ARM 빌드,컴파일 경고0. 기존038에서 세션 프로토콜 및 스냅샷 읽기/기록만 파생 변경.
- 호스트15조건:기존 수명주기/실패 복구,서로 다른 응답 코드/비영 스냅샷 전체 텍스트 정확성,
  로그 open/write/short-write/close 실패에서도 메뉴 복구 유지.
- 실제 Questa MCU 파형448읽기/유효200비트/1880행. 실제039 C의 GPIO/지연을 재생했다.
  호스트 GPIO mock이며 명령 타이밍까지 재현한 ARM 시뮬레이터는 아니다.
- 보드9조건:ROM65536/payload8192바이트 exact,전송 후 상태/소비량/error register 읽기,
  패킷 사이 SPI 상태 폴링과 총15ms 대기,기존STOP/PLL loss 회귀.
  불완전 소비 COMMIT(bus5),읽기 중 주소 변경(frontend1),강제 queue 응답 오류(producer4)를
  의도적으로 주입해 각 스냅샷을 확인했다. 후속 bus8에서도 최초bus5가 유지됨을 검증했다.
  이는 실제 사용자의 오류를 재현했다는 뜻이 아니다.
- 같은 소스 full map/fit/STA/ASM:1453LE108LAB44M9K,135physical/0virtual/PLL1.
  최소 내부 slack은 setup3.028,hold0.125,recovery5.507,removal1.670,MPW5.604ns다.
- RBF215453바이트를 실제 MCU rle_file_getc()로 끝까지 비교하고 EOF까지 확인했다.
  압축기의 검증된 말미 FF1바이트 중복만 기존036 방식으로 제거했고 원본도 보존했다.
- 설치/복원8조건:실제038/039 MCU와036/039 FPGA,두 파일 사이 중단→원복,
  원본/세이브/로그 보존,변경·손상 거부. 실제 SD에는 쓰지 않았다.

외부38입력/11출력 미제약은 남고 각각831/895경로다. 동일 핀/SDC를 유지했다.
신규 Slow1200mV85C 경로 목록은 raw SNES→출력22.765ns,입력→register10.673ns,
register→SNES18.742ns다. 이 목록을 실제 보드 setup/hold/turnaround 통과라고 부르지 않는다.
ROM/패턴·기존GBC·전송부/프런트엔드/생산기 구현은 그대로다. 새 Mesen 실행은 하지 않았다.

최초 추가 오류 시험은 ARM 직후 패킷 준비 전에 acquire를 한번만 하고 기다려 watchdog에 걸렸다.
실제 ROM의 acquire 재시도와 다른 시험 fixture였으므로 오류 주입 전에 published 준비를 기다리도록
수정했다. watchdog을 늘리거나 오류를 무시하지 않았다. 첫 driver/로그를 보존했다.
파형 행 수의 최초 예상1866도 실제1880에 맞춰 바로잡았다. 최종 모든 검사가 통과했다.

다음은039 조합으로 한 번 재현하고 새 로그의 최초 오류 mask/code를 확인하는 것이다.
038 실기는 실패,039 실기는 아직 미실행 상태다. H0의 제한된 육안 통과와 구분한다.
