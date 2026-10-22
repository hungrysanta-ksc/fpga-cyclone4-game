# NES298 descriptor·manifest·receipt 공동 실행기

ARM296의 대기 중 OBJ plan 공급을 유지하면서, 실제 host/validator 사이의 descriptor receipt·manifest·certificate 완료 처리를 공통 host-clock 실행기로 교체했다. 기존 RTL295를 쓴297이 비교 기준이다. 기능 기준289·성능 기준287·production227/GBC164/saveSRAM은 바꾸지 않는다.

## 실제 교체 범위

`nes_joint298.apply`는 기존 `nes_validator278`에 전체 작업 실행과 queue reader를 통합하고, `nes_output260`은 패킷 admission·SNES view/관측·token·queue retire를 유지한다. 두 모듈을 이름만 바꾸거나 모든 state를 하나의 register로 합친 구현이 아니다. 변경한 경계는 실제로 공통 실행기가 queue/phase RAM 진행과 완료를 소유한다.

- **descriptor/receipt**: host가 계산한 original descriptor의 domain 변환을 전달하면, 공통 실행기가 기존 widened end/domain/중복 bit/실소비 CRC coverage를 독립 검사하고 receipt/persistent RAM 순회를 완료한다. host의 WAIT_RECEIPT와 OTILE/OSELECT→ORET 중계는 XWAIT 하나의 공통 완료로 대체한다. 원래 header/descriptor는 완료까지 immutable하다. 범위 산술과 independent check를 ARM으로 옮기지 않았다.
- **manifest**: encoded packet cursor와 RLE count/zero flag를 실행기로 이동했다. queue의 registered read→literal/RLE 해석→display 의미 또는 독립 manifest RAM 비교→다음 byte가 같은 FSM 안에서 진행한다. host의 ordinary_mode/opos/oend/rle 및 PREAD/PCAP의 ordinary branch, ORLE/OCHECKNEXT/ORET를 제거했다. expanded422B cursor와 checked_byte는 별도로 유지한다. packet 끝256과 RLE literal 부족·확장256 초과를 검사한다.
- **certificate/seal**: host OISSUE/OCERT/OFINISH를 제거하고 engine의 digest→certificate→seal continuation으로 연결했다. raw CRC RAM, H2 certificate CRC, all-consumed 검사를 유지하며, seal 이후12B 정확한 표시 읽기와 full token 최종 ACK는 기존 경로에 남긴다.

host에는 XBEGIN/XWAIT와 공통 완료 dispatch, queue address 선택이 추가된다. engine에는 encoded cursor/RLE 상태와 packet read/next/certificate/seal 상태가 추가된다. descriptor/CRC/범위 검사가 모두 사라지는 방식으로 회로를 계산하지 않는다. 기존 localparam 이름 중 사용하지 않는 값은 호환 정의로 남아 있지만, 해당 실행 case branch는 제거했음을 분석기가 확인한다.

## RAM·동시성·credit·STOP

phase RAM B는 기존 validator/공통 실행기 하나만 소유한다. NES source의 port A와 기존 lease/CDC는 유지한다. queue RAM과 phase RAM은 별도 포트이며, 새로운 queue address mux는 비용에 포함된다. ordinary SNES 읽기 중 동작하는 strobe/pattern/CRC tap은 원본과 바이트 단위로 동일하다. RAM mux/write gate, descriptor→receipt 범위 계산도 원본과 대조한다.

host는 공통 실행 동안 queue head를 유지한다. batch map의 중간 범위는 head/credit을 반환하지 않고 마지막 범위에서만 retire한다. 기존 단일 op12는 packet payload staging 이후 retire하는 정책과 aperture consume 수명이 다르므로 이를 바꾸지 않는다. ordinary는 정확한 read·ordered ACK·CRC tap drain 이후 receipt를 실행한다. 네 packet credit과 두 plan bank, E9/EA 공급은 그대로다.

exec busy/done은 reset/abort/fault에서 즉시 차단한다. 기존 RAM write inhibit, bank 무효화와 token/serial 소각을 유지한다. 최종 ACK는 공통 packet 완료와 구별하며, seal·certificate·12 exact reads·full token·empty queue/owner 이후에만 기존 mailbox를 보낸다.

## 검증

선택 test04/window04/guards02/board01/analysis01. 실제 ARM·IRQ·SPI·tile ROM의 정상/제한905–907에서 E1 명령 일치·최대4credit·metadata8570·receipt/CRC·최종 ACK와 finish267→commit285를 확인했다. 새 RTL 오류 주입42개(기존38+신규4)는 PASS다. 신규4는 encoded packet 주소 초과, expanded manifest 끝 초과, manifest 내부 STOP, seal 직전 STOP이다. 기존 ORET STOP 위치는 새 XWAIT 진행 구간으로 재연결했으며 이전과 같은 내부 cycle이라고 세지 않는다. guards01은 runner가 구형 patch를 바인딩해 elaboration에 실패한 기록으로 보존하고, guards02가 새 RTL hash와 일치한다.

ARM loaded PT_LOAD는296과 같고 서비스49,175 instructions(907)를 총 비용에 포함한다. ARM native71/1039명령73260B·fixture0, native6/wait8/H2 9/IRQ8cases33exceptions는 동일 loaded code의 기존 증거를 재사용한다. BG-close9도 동일 decoder hash로 재사용한다. 새 시험과 구별한다.

첫 test01은 생성 코드 공백 누락으로 compile 실패했고 test02는 삭제한 ordinary_mode를 참조하던 관측 assertion 때문에 elaboration 실패했다. 두 실패를 보존했다. test03/window03은 기능 PASS지만 이전 WAIT_RECEIPT를 보던 receipt 시간 집계가 비어 있는 것을 확인했다. 최종 선택 쌍은 실제 host-clock exec_done으로 receipt를 관측하고 queue-head 보존을 검사한다. 관측 변경은 target ARM instructions나 RTL 구동을 추가하지 않는다. 과거 NES-clock 완료 샘플과 새 host-clock 관측의 세부 receipt 시간은 clock 양자화가 달라 직접 동일 정의로 빼지 않는다.

## 전체 시간

| 조건 | 297 ms | 298 ms | 변화 ms |
|---|---:|---:|---:|
|정상905|79.689998|79.689998|+0.000000000|
|정상906|56.212189|56.212189|+0.000000000|
|정상907|15.473814|15.473814|+0.000000000|
|제한905|104.876060|104.876060|+0.000000000|
|제한906|116.900688|116.900688|+0.000000000|
|제한907|17.468381|17.468381|+0.000000000|


제한907의60Hz 초과0.801715ms는 남는다. 정상907 parser 관측 구간은297의0.019332ms에서0.026831ms로 변했다. queue read와 RAM 검사를 단일 순서로 실행하여 바이트별 중첩이 달라졌으며, 이 내부 구간을 단순히 전체 시간에서 차감하지 않는다. 제한907의 SPI1236B/E226/E94/timer fallback1회,ARM699344instructions를 함께 집계했다.

source replay + 같은 프레임의 compiled M4/IRQ/shared SPI/ROM arbiter/출력 RTL 일정이다. 실제 ARM 명령 수는 Unicorn 실행이며 CPI1/84MHz와 IRQ exception 할당을 사용한다. 기존 ordinary65816 trace와 map/tile/display bus 모델이 남는다. 전체 live65816 CPU/fullRUN/WCET/실물60fps 또는 full71/heavy7 일정 증명이 아니다.905/906 초기 상태와 warm907을 구별한다.

정상/제한의905–907 모두 ARM SPI transfer record(tx/rx·명령·IRQ·checkpoint·RTL 시각)가297과 정확히 같다. 내부 parser 순회의 변화가 현재 SPI/polling 일정의 전체 완료 시간을 바꾸지 못했음을 확인했다.

## 전체 Quartus Lite 비용

| 항목 | 297 | 298 | 변화 |
|---|---:|---:|---:|
|LE|22603|22583|-20|
|comb|17703|17683|-20|
|FF|9029|9022|-7|
|RAM_bits|307808|307808|+0|


host2352→2100,validator1088→1327comb다. 고정 경계4847→4837,밖12856→12846이며 총17683와 일치한다. 한도15408 대비2275개 부족이다. 현재 밖 비용을 고정한 경계 예산은2562이며 새 실행기를 포함한 실제 비용은4837다. 손익은 실제 own 합계 기준으로만 계산하며 parent/child를 중복 합산하지 않는다.

whole board MAP 한 번을 실행했다. validator 공통 실행기와 host state는 모두 FSM으로 추출됐으며, 이번 작은 절감을 FSM 추출 실패로 설명하지 않는다. live와 board의 mux(기존 board-only 관측 포트 정규화), validator·plan·tile RTL을 대조하고 전체 입력 hash와 계층 own 합계를 검산했다. 변경 파일은 mux/validator/공통 연결wrapper 두 개이며 나머지 board 입력은295와 같다. MAP는 배치/FIT/STA나 전력/주파수 보장이 아니다. Standard 평가판이나 seed/FIT 반복은 사용하지 않았다.

## 판단과 다음 경계

공통 실행기를 구현하고 독립 검사와 STOP/최종 ACK를 보존했지만, 회로 절감은20개(기존2295개 부족의0.87%)뿐이다. 제한 ROM 초과0.801715ms와 회로 부족2275개를 함께 해소하지 못했다. ARM 시간 개선은 유지됐지만60fps/보드 수용 목표의 해결안으로는 채택하지 않는다. P2/FIT/production 승격은 하지 않는다.

이번 통합은 host에서 없앤 해석·진행 제어의 대부분이 engine 쪽에 필요하다는 것을 실제 합성으로 보여준다. 중계 상태의 수나 제거된 FF를2295개 회수 근거로 바꿀 수 없다. descriptor의 독립 bounds/coverage와 동시 CRC tap을 유지하는 한, host+validator만으로 무여유 목표를 맞추려면 약1145comb가 필요했던 구조적 간극은 남는다.

다음에는 같은 packet/descriptor를 여러 번 해석하는 데이터 표현과 주소 선택 구조까지 함께 검토해야 한다. original packet bytes를 두 번 전송하거나 ARM 계산값으로 독립 검사를 대체하지 않는 조건으로, 공통 descriptor의 입력/검사/실소비 소유권과 ROM plan 공급 시점을 함께 재설계한다. control state만 더 합치는 MAP 반복은 하지 않는다. 시간·전체 회로의 실질적 개선 근거가 있는 후보에만 full71/heavy7와 matching FIT/STA를 확대한다. 자동 merge하지 않는다.
