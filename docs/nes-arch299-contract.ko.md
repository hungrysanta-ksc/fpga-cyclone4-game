# NES299 — descriptor·manifest·주소 선택·ROM 일정의 구조 예산

PR130 merge `d7a96c5652d7c511d061ae5035277027c14ec597`가 origin/master에 포함됨을 fetch와 ancestor 검사로 확인했다. 이 master에서 `codex/nes-architecture-budget-299`를 생성했다. 기존 구현298·분리297·기능289·성능287을 비교 기준으로 보존한다. 이번 단계는 구조/예산 확정과 주소 모델 검사다. RTL 변경·새 ARM/65816 실행·Quartus 합성은 하지 않았다.

## 결론과 선택 범위

검토 대상으로 **원본 descriptor의 단일 admission record + 정렬된 phase RAM + 기존 압축 manifest의 단일 decode + OBJ 생산/공급의 선행 실행**을 선택한다. 제품 채택이나 목표 달성 판정은 아니다. 현재 FSM 통합298은 manifest decode를 이미 한 곳으로 옮겼다. 같은 작업을 다시 ‘중복 decoder 제거’로 계산하지 않는다.

현재 17683comb에서2275개를 더 줄여야 한다. 고정 출력 경계4837개를 모두 포함해2562개 이하로 만들어야 하므로 주소 정렬이나 parser 단독 개선만으로 충분하다는 근거는 없다. **구조와 통과 예산은 확정했지만 예상 합성값·새 프레임 시간은 미확정**이다. 이 둘을 임의로 채우지 않는다.

## 실제 코드의 중복과 유지해야 할 의미

|현재 경로/근거(test04 생성 RTL)|교체 대상|반드시 유지|
|---|---|---|
|host `bad_data278`, OSETUP, `descriptor_end287`, receipt_first/count (nes_mux260)|opcode/section/start/length 해석과 끝 주소 계산을 admission 한 번으로 모아 검증된 record 생산|원본 packet identity/length/overflow/domain/alignment 검사, 소비 중 descriptor 안정성|
|host map DCHECK→first/count, validator `range_end283`/domain_end283|검증된 first/end/domain record에서 DMA view와 receipt walk 파생. 독립 검사의 기준 입력은 원본 descriptor|map 순서·중복·cold coverage·raw CRC mask 검사. ARM이 제공한 first/end를 무검사 신뢰하지 않음|
|host OSETUP manifest phase/length, engine E_READ/CAP/NEXT/RLE|packet framing admission와 내용 해석의 책임 명확화. 공통 reader의 header→payload continuation 검토|compressed packet_at, expanded cursor, RLE remaining, checked_byte는 동시에 살아 있어 유지|
|validator V_CHECKTEST/PCHECKTEST|segment별 base/length를 한 번 설정하고 RAM 주소 순차 증가 검토|144B persistent subset,22B fresh/persistent 대조,256B map 일치/cold full-map,raw0 예외. 비교 자체는 중복이 아님|
|queue qaddr=NORMAL SNES / exec_busy / parser 선택|header·internal payload reader를 같은 queue cursor 소유자로 묶는 후보|SNES payload 읽기와 독립 CRC tap 동시성, head/4credit, registered RAM latency|
|phase RAM B v_addr 다중 base 산술|아래 정렬 layout와 region-local 주소 생성|source A/host B clock 분리, phase lease, STOP/fault write gate, read-before-write|
|service296 E2 응답에서 남은 OBJ step 실행|E2 조회를 기다리기 전 BG 완료 직후 실행 가능한 OBJ 생산을 진행하는 후보|기존 mixed batch 정렬/용량·2planbank credit·원본 명령 순서·STOP·최종 END 의미|

현재 host의 의미 해석과 validator의 독립 상태 검사는 같은 작업이 아니다. 공통 admission은 원본 descriptor를 FPGA가 검사하여 record를 만들고, 실행기는 이 record와 실제 receipt/CRC 상태를 대조한다. domain 검사 이동 시 유효하지 않은 원본 descriptor, 손상된 record/상태, 누락된 실소비가 각각 거부되는 검사를 유지해야 한다. 단순히 validator range check를 삭제하는 변경은 제외한다.

record는 bank/generation/token, section/kind, byte start/end, receipt first/end, CRC 영역/정렬 의미와 유효 상태를 담는 **기존 저장값의 대체**다. 새로운 폭·FF 수는 구현 설계에서 계상하며 기존 header/first/count와 새 record를 동시에 영구 유지하지 않는다. SNES가 원본 header/view를 필요로 하는 동안 그 바이트를 삭제할 수 없다. 데이터 bus CRC 관측기는 별도로 계속 동작한다.

## RAM 주소 후보: 1KiB 유지

|논리 영역|현재 주소|제안 주소|바이트|
|---|---|---|---:|
|persistent bank0|0..165|0..165|166|
|persistent bank1|166..331|256..421|166|
|두 bank raw CRC|332..395|448..511|64|
|fresh receipt|396..561|512..677|166|
|H2 32B + display offset4B|832..867|680..715|36|
|map receipt|562..817|768..1023|256|
|source scratch(input phase)|512..1023|512..1023|512, phase 겹침|

논리854B/주소 여유170B다. persistent bank 주소는 bank bit와8bit index, map은상위2bit `11`, receipt는상위bit `1`과 제한된 index로 선택 가능하다. CRC base도64B 정렬이다. host 주소 선택 전체가 사라지는 것은 아니며 manifest segment 전환, H2/display, clear/read/write 상태는 남는다.

source scratch와 persistent/CRC는 겹치지 않는다. scratch와 receipt/map/H2는 **입력 종료·source drain·출력 lease 전환 후에만** 겹쳐 쓴다. H2를 source 입력 중 해당 공간에 쓰는 조기 생산은 금지한다. 기존 BEGIN의 연속396..817 clear를512..1023 clear로 바꾸면 H2가 파괴된다. 새 clear는 receipt512..677와 map768..1023의 두 구간으로 한정해야 한다. raw0 무효화도148..165/404..421로 옮겨야 한다. 초기 reset clear는 source 시작 허가 이전에 끝나야 한다.

[주소 모델](../tools/analyze_nes_arch299.py)은854개 주소의 일대일 대응, 양 bank manifest 읽기888개,422B frame clear, persistent/source 비중첩, H2 보존을 전수 검사한다. 잘못된 연속 clear가 H2 36B를 훼손하는 반례도 확인한다. **이는 수학적 layout 검사이며 RTL latency/CDC/STOP 동작 검증을 대체하지 않는다.** 새 M9K를 추가하지 않는 설계 제약이며 합성 추론 결과는 아직 없다.

## 함께 바꿀 ROM 공급 일정

현재 restricted907은 17.468381286ms, 초과0.801714619ms다. parser0.026832+receipt0.000250=0.027082ms 전량 제거라는 불가능한 가정에서도0.774633ms가 남는다. OBJ service49175명령은CPI1/84MHz에서0.585417ms다. 그것까지 전량 삭제하고 두 구간을 더해 차감하는 낙관적 진단에서도 약0.189216ms가 남는다. 실제로는 service가 이미 일부 대기와 겹치며 제거할 수 없으므로 시간 이득으로 합산하지 않는다.

restricted907 첫OBJ plan275.212038ms→start275.212402ms, 둘째 plan275.223447ms→start275.352082ms다. 이전 tile receipt275.351207ms가 둘째 시작에 앞선다. 따라서 plan을 더 일찍 만드는 것만으로 두 번째 변환까지 즉시 시작한다고 가정하지 않는다. 실제 aperture 점유·tile 완료·ROM qualified slot과 core 우선권을 함께 본다.

후보 일정은 (1) source COMMITTED 이후 BG 계획 확정, (2) 기존 credit 범위의 BG batch 송신과 동시에 가능한 OBJ 생산, (3) 원래 mixed batch 정렬 경계와 남은 용량을 보존한 OBJ batch 송신, (4) aperture가 비면 변환·DMA·receipt, (5) 모든 범위 후 최종 manifest/seal/표시 ACK다. ARM CPU의 동시 실행을 가정하지 않고, 실제 SPI 대기/IRQ 서비스 사이의 실행 기회만 사용한다. 단순 조기 E9를 추가하는 방식은295 회귀 때문에 기본안에서 제외한다. BG 부분 완료와 최종 END는 구별한다.

기존 ROM fixture의 period357368, qualified [330088,354640), 12cycle slot 및120cycle core request 위상을 고정한다. 새 ARM 작업량·packet·E2/E9·IRQ/타이머를 모두 기록하고 정상·제한905/906/907을289·297·298과 비교한다. 이후 창 시작/끝을 걸치는 위상 검사를 추가해야 한다. 단일 창을 우연히 앞당긴 결과를 WCET로 주장하지 않는다.

## 면적·시간·메모리 예산

|비교 경계|현재 comb|밖의 회로 고정 시 최대 comb|128comb 정책 여유 포함|
|---|---:|---:|---:|
|host+validator|3427|1152|1024|
|host+validator+queue+plan+SPI+glue|4837|2562|2434|

둘째 경계의 outside는12846comb다. queue129+plan573+SPI657+glue51=1410을 그대로 두면 실행기 예산은1152뿐이다. 이는 제거 목표66.4%이며 주소 정렬로 달성할 수 있다고 추정하지 않는다. 독립 검사·queue/plan CDC·CRC tap·새 record/selector/continuation을 포함한 **전체 교체 비용**이 이 한도에 들어야 한다. 각 작은 블록의 LUT 절감량은 합성 전 미확정이며 parent/child 값을 중복 합산하지 않는다.128comb는 계획 여유이지 FIT 보장이 아니다.

시간은 `실제 critical-path 순절감 >= 0.801714619ms + 새로 추가된 비용 + 별도 여유`가 최소 조건이다. 같은 초과분은CPI1/84MHz 기준67344명령 상당이지만 ARM 명령만 줄여야 한다는 뜻은 아니다. SPI는2.625Mbps에서 추가1B당 약0.003048ms이고 transaction/setup 비용은 별도다. 기본 후보는 기존 압축 payload와 원본 명령 수를 유지한다. expanded manifest/raw 전송이나 별도 실행 프로그램은 wire·SRAM·독립 검사 비용을 포함한 이득이 입증되기 전 제외한다.

새 FPGA RAM 추가0, source512B/phase1KiB 유지, 기존4credit/2planbank 유지가 이번 구조 제약이다. ARM record/batch 버퍼·stack 증분은0으로 가정하지 않으며 실제 크기를 보고해야 한다. 예산 확정은0.802ms·2275comb만큼 실제 개선했다는 뜻이 아니다.

## 후보 비교와 다음 판정

|후보|판정|
|---|---|
|현재298의 상태/cursor 추가 공유|독립 실시간 상태와 선택기가 남고 목표 규모 근거 없음. 반복 MAP 대상 제외|
|압축 유지 + 단일 admission + 정렬 RAM + 선행 OBJ 공급|다음 구조 설계 대상으로 선택. 면적/시간 예상은null, 목표 충족 여부 미확정|
|ARM에서 manifest를 모두 확장하거나 범위검사를 제거|추가 wire/ARM 비용 또는 독립 검사 손실. 현 단계 제외|
|source clock과 host clock/RAM 포트를 직접 통합|CDC·동시성·source lease 변경으로 경계 확대. 현재안 제외, 필요시 전체 예산부터 다시 검토|

다음 산출물은 원본 descriptor→checked record→DMA/receipt의 전이표와 공유 주소 datapath, old/new 회로 제거 목록이다. RAM remap·record·일정 개선을 구분해 회귀 원인을 추적한다. 유지된 검사와 새 비용을 포함해 위 예산에 접근할 구조 근거가 없으면 전체 구현/MAP 반복 대신 역할·표현을 재검토한다. 유망한 후보만 minimal RTL/ARM live 및 한 번의 matching whole Lite로 검증하고, 이후 heavy7/71/fullRUN/full65816/FIT/STA/실물 게이트로 확장한다.

STOP은 신규 admission·RAM write·receipt/credit 완료를 차단하고 token/plan namespace 재사용과 bank 무효화 정책을 유지한다. 최종 ACK는 seal/certificate,12 exact reads,fulltoken,빈 queue/owner를 만족한 뒤 lease를 반환한다. 새 malformed descriptor·CRC 누락·manifest truncation/RLE overrun·clear/H2 충돌·STOP 중단·최종 ACK 조기 발행 반례가 검증 목록이다. production227/GBC164/saveSRAM은 변경하지 않으며 자동 merge하지 않는다.
