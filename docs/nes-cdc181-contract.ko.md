# NES181 클록 전달 계약과 배선 제약

## 작업 목표

팔레트 후보의 배선 실패에서 관측한 과도한 클록 간 hold 지연을, 실제 전달 회로의 계약에 맞춰 줄이는 작업이다. NES181의 부분 행 출력 구현을 FPGA에 배치하기 위한 단계다. 게임 화면 정지 해결이나 60fps를 입증하는 단계는 아니다.

이번 후보는 팔레트 후보의 회로·핀·주파수·게임 데이터·메모리·ARM/SNES 프로그램을 그대로 사용한다. `board.sdc`에 정확한 CDC 경로 목록인 `cdc181.sdc`만 추가한다. 기존 같은 클록 CHECK·SPI 구현 예산도 유지한다. 별도 카트리지 SRAM은 사용하지 않는다.

## 클록과 전달 계약

`CLKIN`은 보드 8MHz이며 같은 PLL이 host 84MHz와 memory 168MHz를 만든다. 이 두 출력은 서로 관련된 클록으로 계속 검사한다. `SNES_SYSCLK`은 별도 입력이며 NES 로직의 기준이다. 기존 보수적 22MHz 제약(45.454ns)을 유지한다. 두 외부 입력의 일정한 위상 관계를 가정하지 않는다.

|경로|실제 전달 조건|이번 처리|
|---|---|---|
|native_records / native_prepared 데이터|송신 데이터와 request를 함께 등록, 수신 2단 동기화 뒤 추가 capture 에지, 수신 소비 후 ACK가 돌아올 때까지 원본 유지|실제 합성에 남은 87+17비트에 최대 지연, 해당 비트의 비동기 hold 관계만 제외|
|pad 데이터|host snapshot을 request/ACK로 고정, NES 2단 동기화 뒤 current_buttons로 수신|8비트 최대 지연과 hold 관계 처리|
|audio 데이터|새 sample은 ACK 완료 때만 기록, DAC 2단 동기화 뒤 수신|16비트 최대 지연과 hold 관계 처리|
|request/ACK, 상대 도메인 기동 확인, heartbeat, sticky ROM fault|2단 동기화, 첫 FF 출력은 두 번째 FF 한 곳에만 연결|정확한 source→첫 FF 17쌍만 setup/hold 제외; 다음 FF까지는 검사 유지|
|ROM 주소/응답 데이터, RUN·리셋·설정 경로|직접 소비·동시 취소·조합 논리 경유 등을 추가 검토해야 함|이번 변경에서 제외하지 않음|

SDC 최대 지연은 수신 주기 11.904ns 또는 45.454ns다. 이 도구의 최대 지연에는 클록 경로도 포함되므로, 배선 후 실제 `data_delay`는 별도로 **9.904ns / 43.454ns 미만**을 요구한다. 한 수신 주기보다 2ns 짧다. 수신이 가능한 가장 이른 에지는 pad/audio의 경우 요청 발생 뒤 두 수신 주기 이상, mailbox는 추가 capture까지 세 수신 주기 이상이다. ACK 전 원본을 바꾸지 않으므로 다음 값이 같은 capture 에지의 hold를 침범하지 않는다. 공통 리셋 시 데이터와 프로토콜을 격리하며, 한쪽만 독립적으로 리셋하는 운용은 여전히 지원하지 않는다.

일반 `set_false_path`는 최대 지연보다 우선하므로 데이터 버스를 통째로 제외하지 않는다. **데이터 버스에는 `set_false_path -hold`만 사용하고 setup 최대 지연이 실제로 남아 있는지 조회한다.** 첫 동기화 FF의 입력은 비동기이지만 두 번째 FF와 그 뒤 로직은 같은 클록 타이밍을 만족해야 한다. 전체 클록 그룹 제외나 전체 hold 최적화 OFF는 사용하지 않는다.

앞선 인계의 최소/최대 지연 쌍 검토에서 이 방식으로 구체화했다. Standard25.1에는 `set_max_delay -datapath_only`가 없고 `set_min_delay 0`도 클록 경로를 포함한다. 여기서 의미 없는 클록 위상의 hold 관계를 남기거나 큰 음수 최소값을 임의로 고르는 대신, 데이터 안정/ACK 계약으로 hold를 다루고 실제 데이터 지연 상한을 별도로 검사한다. 이 선택은 아래 RTL 및 적용 범위 검증에 한정되며 모든 CDC의 안전성을 뜻하지 않는다.

## 검증

- 새 합성의 서로 다른 클록 간 setup/hold/recovery/removal 목록에서 6,980개 고유 경로·검사 조합을 비교했다. 지정한 162개만 제외되어 6,818개가 남았다. 예상하지 않은 제외는 0개이고 recovery/removal 및 같은 PLL 간 경로가 유지됐다.
- 데이터 128쌍의 최대 지연 관계와 첫 FF→두 번째 FF 17쌍의 setup/hold를 3개 조건에서 조회했다. 486행 모두 존재하고 각 첫 FF의 fanout이 다음 FF 한 곳뿐임을 확인했다. 합성 후 값은 적용 범위 확인용이며 배선 타이밍 통과로 사용하지 않는다.
- 실제 mailbox의 시뮬레이션 복사본에 데이터 경로 지연 9.904ns/43.454ns를 넣었다. 여섯 위상·방향 조합, 450회 전달, 공통 리셋 72회, 클록 정지 12경우를 통과했다. 59.520ns/227.270ns로 과도하게 늦춘 대조군은 잘못된 데이터로 실패했다. 실제 배포 RTL은 수정하지 않았다. 메타안정성, pad/audio 파형 전체, 실기 검증을 주장하지 않는다.
- 최초 목록은 실패한 이전 FIT DB의 post-map view였다. 새 합성에는 추가 record bit60이 남아 있어 범위 검사가 추가 경로 4개를 검출했다. 이 초안을 폐기하고 **새 합성 DB를 원래 SDC로 재열거한 inventory02**로 제약을 만들었다. map01에는 FIT를 실행하지 않았으며 map02에만 실행한다. 실패한 DB의 부분 최적화 목록을 새 합성의 완전한 목록으로 취급하지 않는다.
- 기존 181 공개 소스 핀 46개·보존 파일 14,122개, 배포180 MCU 1,413파일·FPGA 62파일·ZIP과 paired ARM fw105f819f(여유1,032바이트)를 해시로 재사용 확인했다. GBC 등록 내용도 유지한다.

## 아직 예외 처리하지 않은 경로

각 setup/hold 목록에 같은 PLL 등 관련 root 간 1,446쌍, ROM 응답 1,257쌍, 주소 21쌍, lifecycle 473쌍을 유지한다. 서로 다른 클록의 recovery/removal은 각148쌍을 유지한다. 이 수는 고유 source/destination 및 클록 조합이며 물리 wire 수와 다르다. ROM 응답은 단순 byte register 외에 CPU/PPU/fill의 조합 경로까지 이어지므로, 8비트라는 이유로 한 번에 제외하지 않는다.

RTL·SDC·source/destination 수가 달라지면 생성기와 검사기가 중단한다. 배선 단계에서 레지스터가 합쳐지거나 이름이 사라져도 자동으로 무시하지 않는다. 실제 배선 후 같은 클록과 같은 PLL 관계, 데이터 경로 상한, 리셋, PSRAM/SNES/SPI 조건부 지연을 통과해야 설치 후보가 된다. 메타안정성 MTBF·실측 전기 타이밍의 전체 승인은 별도다.

## 배치 결과

**단일 FIT map02는 15,072 LE / 963 LAB / 38 M9K로 배치·배선을 완료했다.** 하지만 실제 클록 setup이 실패하여 미채택이며 새 ARM 빌드·ASM·RBF·ZIP은 만들지 않았다. [기계 판독 검증](../analysis/cdc181-verification.json).

|검사|결과|
|---|---|
|전체 FIT|성공, LAB963/963|
|hold 보정 삽입 지연 합계|605.4 → 455.5ns; 여러 신호의 합이며 slack·처리 속도가 아님|
|실제 관련 클록쌍 전체 setup / hold|−3.379ns 실패 / +0.146ns 통과|
|동일 PLL memory→host setup|−0.740ns 실패|
|NES 자체 / host 자체 setup|+7.430ns / +0.335ns|
|영상 record / prepared 실제 데이터 지연|3.707ns / 3.075ns, 조건부 상한 통과|
|pad / audio 실제 데이터 지연|3.198ns / 2.014ns, 조건부 상한 통과|
|17개 동기화 체인의 setup/hold 최솟값|+0.189ns, 다음 단계 검사 유지|
|PSRAM70ns 조건부 여유|+2.082ns|
|SNES / SPI 조건부 응답 범위|74.630ns < 270ns / 164.264ns < 190.476ns|
|native 데이터·제어 음수 reset 경로|0; 원시 리셋·전체 MTBF 승인은 아님|

최악 경로는 memory 클록의 `control.shift[0] → control.offset[9]`다. 실제 지연9.254ns 중 배선8.526ns(92%), 논리 단계0개다. 같은 PLL의 `boot.check_failed → sink.endpoint.ack_work[31]`는6.990ns, 논리4단계·배선71%다. 앞 경로의 실패를 조합 논리 계산량 문제로 단정해서 로더 미세 최적화를 반복하지 않는다. 소스는 그대로이고 이전 실패 DB와 배치가 달라졌으므로, CDC 수정이 이 실패를 단독으로 만들었다거나 남은 ROM CDC만 고치면 반드시 통과한다고 주장하지 않는다.

기존 ROM 응답 쪽 hold 보정이 여전히 큰 비중을 차지한다. PLL memory→NES 합계398.0ns이며 개별 `data_hold → cpu_line_byte/ppu_byte`에는5ns대 보정이 남아 있다. 이는 다음 범위를 정하는 근거이지 blanket false path의 근거가 아니다.

일반 setup까지 잘못 지우는 음성 대조 SDC를 넣자 검사기가 `audio setup` 부재로 실패했다. 최종 IO 보고기 첫 실행은 기존 `records_req` 일반 setup 조회가 새 예외 때문에 비어 중단됐다. 수정02는 그 두 첫 동기화 경로만 `-false_path`로 지연을 조회하며 데이터 경로의 최대 지연 검사는 그대로 유지한다. 공개 생성기가 수정02를 포함한 실제 실행 파일4개와 바이트 단위로 같음을 확인했다. 실패 원문은 보존했다.

STA는 원본 FIT DB의 별도 복사본에서 실행했다. 원본 FIT 파일은 보존됐으며 복사본에서는 타이밍·보고·IO 캐시 파일5개가 바뀌었다. 원본과 복사본 전체 DB가 모두 불변이라고 주장하지 않는다. 기존 `loader|state*` 예산 필터는 현재 `phase` 구현에 매칭되지 않는 경고가 남는다. 이를 숨기거나 현재 로더 전체에 그 예산이 적용됐다고 해석하지 않는다.

## 다음 작업

1. **채택 기준은 그대로 배포180**, 분석 기준은 이번 routed map02/route01이다. 새 후보의 ROM 주소21쌍·응답1,257쌍을 실제 reader→arbiter→ROM service→CPU/PPU/fill 수신 조건과 함께 검토한다. 데이터가 유효해지는 가장 이른 에지·ACK 뒤 변경·중단/리셋을 증명한 경계만 제한적으로 제약한다. 기존 reader/arbiter 검증을 재사용하고 새 지연 조건만 추가한다.
2. 위와 함께 memory→host의 RUN/STOP·ACK 갱신 경로를 검토한다. 같은 PLL 출력끼리는 계속 related timing을 검사한다. 최악 `shift→offset`의0단계·배선92% 근거를 유지하여 무의미한 로더 계산식 변경·시드 재배치로 돌아가지 않는다. 필요한 경우 이전 OAM165의 실패 시도와 소비 시점을 재사용해 저장/조회 배선 밀도를 검토한다.
3. 변경된 계약과 최소 경계 검사를 통과한 후에만 다음 FIT를 정당화한다. 전체 실제 클록·조건부 IO/리셋이 통과하면 이미 검증한 paired ARM/client로 SMB3 숫자1→A 시험판을 만든다. 영상 지속·60fps는 아직 실기로 확인하지 못했다.

## 재현과 인계

`tools/nes_cdc181_inventory.tcl`은 격리된 합성 DB에서 원래 제약의 경로를 열거한다. `tools/nes_cdc181.py`가 동결된 palette181 소스와 새 합성 목록으로 후보를 만든다. `tools/check_nes_cdc181.py`는 대상 존재·예외 우선순위·두 번째 FF 타이밍·목록 차이를 검사한다. 지연 시험은 기존 FLOAT wrapper 안에서 `tools/test_nes_cdc181.py`를 실행한다. 완료 archive/record/audit를 덮어쓰지 않는다.

최종 FIT가 성공한 경우에만 배선 후 검사를 진행한다. nominal 보고서를 만들 때도 새 CDC 제약을 보존한다. 이전 clocks-only 보고 도구로 새 제약을 지운 결과를 현재 후보의 승인에 사용하지 않는다. 같은 소스 재배치·seed 반복과 무관한 독립 테스트는 하지 않는다. paired ARM/client는 바뀌지 않았으므로 해시 확인으로 재사용한다. 실기 시험의 목표는 SMB3 숫자1 타일→A 이후 영상 지속 여부이며, raw 전송 약53ms와 최대7vblank+final·60fps 개선은 아직 남아 있다.

## 근거

실행한 설치 버전은 Quartus Standard25.1이다. `help -cmd set_max_delay`, `set_min_delay`, `set_false_path`, `get_timing_paths`, `report_exceptions` 원문을 private evidence에 보관한다. 온라인 문서는 원리와 우선순위를 대조하는 근거이며 Pro 전용 명령을 복사하지 않는다.

- [Standard Timing Analyzer — 예외 우선순위](https://docs.altera.com/r/docs/683068/18.1/quartus-prime-standard-edition-user-guide-timing-analyzer/timing-constraint-precedence?contentId=ExPR38JDZMQqFAgpuM5jJw): false path가 max/min delay보다 우선한다.
- [Standard Timing Analyzer — 최소/최대 지연](https://docs.altera.com/r/docs/683068/18.1/quartus-prime-standard-edition-user-guide-timing-analyzer/minimum-and-maximum-delays?contentId=Xq66G0mHTlnsUikrXW9lGw): 클록 경로를 포함하므로 물리 데이터 지연과 같다고 취급하지 않는다.
- [기존 mailbox 로컬 리셋·전달 검증](nes-boundary165-contract.ko.md), [직전 팔레트 후보의 배선 실패](nes-rank181-contract.ko.md).
