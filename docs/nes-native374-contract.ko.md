# NES374: host native plan과 단일 word RAM 후보

## 구현 범위

NES373의 입력·표시 문맥,4packet source ring/512B shadow,공통 SPI/queue와372 ARM을 유지한다. 이번 후보는 plan wire의 압축/shortform ABI를 유지하면서 host가 기존 logical1KiB에 native32B record를 생성하도록 옮긴다. NES의 wire operand/shortform/packed alternate-tag decode FSM 본체를 실제로 제거했다. host descriptor·manifest·receipt 실행기 전체와 통합한 것은 아니다.

최종 기본 RTL은373으로 유지한다. native374는 기능·합성·시간을 검토하기 위한 별도 후보이며,회로 용량이나 지속60fps를 승인하는 변경이 아니다. production227/GBC164/saveSRAM과 기존 VBlank firmware는 변경하지 않는다.

## native record와 포트 소유권

|native byte|내용|
|---|---|
|0|kind와BG partial 표시|
|1..2|generation|
|3..4|slot|
|5..6|tag|
|7|mask|
|8..13|rows|
|14|alternate mask|
|15|형식 확인 byte1|
|16..31|8개 alternate tag의16bit 저장|

wire는 기존3/7/8B short 또는16+2×popcount(alt_mask)B full 그대로다. host는 고정 위치에 byte를 쓰며,short record의 rows/mask와미사용 lane은 record 시작 시8host clock의 word 초기화로 채운다. 실제2.625MHz SCK에서 다음 byte 전에 완료되는 비용을 포함한다. 초기화 중 너무 빠른 입력은 fault로 거절하며 조용히 유실하지 않는다. host가 wire 길이·record 수·완전한 record 경계·CRC/seal을 확인한 뒤 bank를 공개한다.

단일256×32 M9K의 A port는 host byte-enable 쓰기와초기화가 소유하고 B port는 NES word 읽기가 소유한다. 기존 두512B bank와최대16record를 유지한다. NES는1prime+8word capture 후generation·slot/tag high bits·kind별 shape·BG 부분 완료/프레임 END·tile_done·retire를 검사한다. decoded 필드는 tile_done까지 유지하고 마지막 record를 latch/검사한 뒤에만 mailbox credit을 반환한다.

실제 Intel altsyncram을 기능/보드 양쪽에서 사용한다. Questa에서도 altera_mf_ver 모델을 로드하며 별도 behavioral RAM 대체를 두지 않았다. 모델이 DONT_CARE mixed-port read를 OLD_DATA로 취급한다는 안내를 보존했다. 다른 bank 쓰기와이미 latch된 record의 유지를 검사하며,충돌한 미소비 q 값에 실행을 의존하지 않는다. CDC/STA 전체 증명은 아직 아니다.

## 같은 시작·ROM 위상과 실제 연속 일정

최종 joint02는실제Intel RAM model과기존372 ARM을연결해905~916의12프레임을배출했다.908~917 capture10/10 승인,오류0/계수경고0이며vendor의mixed-port 안내문은raw log에보존했다. 공통compiled module31개가전체보드와바이트일치하고,wire plan·source payload·causal hint는373과12쌍 모두 같다. ARM PT_LOAD·관측stack1,288B와SPI45,528B도같다.

|frame|373 처리 ms|374 처리 ms|기존/data word 읽기 예산 clock|
|---|---:|---:|---:|
|907|11.879698|11.879698|108/72|
|908|12.105105|12.105105|48/36|
|909|15.933377|15.933377|48/36|
|910|11.865926|11.865926|6/9|
|911|12.207195|12.207195|20/18|
|912|15.237795|15.237795|20/18|
|913|11.940425|11.940425|20/18|
|914|21.500992|21.500992|90/63|
|915|21.111314|21.111314|76/54|
|916|15.720925|15.720925|6/9|

907~916의10개warm은source 시작 시각·ROMcycle가같고표시처리시간도로그정밀도에서모두동일했다.914의data-read예산90→63clock은제어/CDC/END/stall을포함한전체이득이아니다. 실제914는21.500992ms,첫BG16.857025ms로같고최대warm표시완료간격25.804373ms도같다. word decode를빠르게해도ROM창·다른완료대기에가려진다.

초기화905/906은각각0.773/0.318µs 짧아졌지만906은이전완료가빨라져source시작위상도달랐으므로동일위상순수이득으로보지않는다. 다음915/916/917 capture여유1.738684/1.746003/1.772094ms를그대로유지했다.917은다음캡처승인까지만확인했다.

ROM은62,222요청/응답,pending0이며입력기원10,878쌍이다.373의10,877쌍과기원분류가1쌍달라졌지만총요청은같고양쪽모두요청-응답이일치한다.IRQ body41회/EXTI254회와실제sharedSPI·2출력credit·독립CRC/coverage·최종12read/token·실제retire를유지했다.58개새directedcase와바이트일치하는기존373 source/context14개guard의재사용범위를구분한다.

## RAM 추론 실패와 수정

첫 구현은 full-word 초기화와byte 쓰기의 주소 선택이 분리돼8,192bit가 FF로 풀렸다. MAP02의37,348LE/24,347comb/17,301FF/292,448bits는 실패 후보 비용으로 보존한다.

한 write address/mask로 정리한 MAP03은22,560LE/17,721comb/9,077FF/300,640bits였다. 그러나 네 개의byte RAM으로 나뉘어 기존 단일 primitive 유지가 확인되지 않았으므로36comb 절감을 최종 이득으로 세지 않는다.

최종은 byte-enable4를 가진256×32 단일 M9K를 명시했다. 선언 순서와simulation library 연결 문제를 수정한 기록도 보존했다. 최종 기능 실행·guard·MAP의 canonical file SHA를 대조한다. 이 과정은 RAM 연결/추론 오류의 수정이며 seed/opcode/FIT 반복이 아니다.

## 전체 회로 비용

|항목|373 기준|374 단일 M9K 최종|변화|
|---|---:|---:|---:|
|LE|22,601|22,596|-5|
|comb|17,757|17,757|0|
|FF|9,091|9,077|-14|
|RAM bits|300,640|300,640|0|

전체comb 부족은2,349,155여유 포함2,504순삭제로 동일하다. plan transport의 self comb 감소를 전체 절감에 다시 더하지 않는다. host에 옮긴 해석·초기화·byte 주소 선택·NES word capture·단일 RAM 연결과clock/enable 제어를 모두 포함하면 순comb 절감은0이다. 새 host decoder가 host 출력 실행기와 독립적으로 남아 있기 때문이다.

이는 NES operand decode를 지우지 못했다는 뜻이 아니라,클록 경계를 옮긴 것만으로 회로가 줄지 않는다는 실제 결과다. 이번 후보를 단독 기본 회로로 승격하지 않는다.

## 검증과 한계

최종 실제 ARM·SPI·IRQ·ROM 및동일 시작/연속 일정의 수치는 analysis/native374-verification.json과nes-native374-plan.json에 기록한다. wire plan/causal hint/source payload·ARM PT_LOAD를373과 대조한다. 독립 read CRC/coverage·2출력credit·STOP·12exact display read/token·실제 retire와VBlank firmware를 유지한다.

기존373 decoder와36개 mixed 정상/8개 malformed/8개 STOP,최대512B/16record 경계를 비교한다. 별도6case는 두 bank 동시 수명/이미 latch된 record 불변/BG partial과프레임 END/retire 허가 대기/다음 generation bank 재사용,읽기·RUN 중STOP,조기retire,credit 위반,lease generation 변경을 검사한다. 완료 clock은 각 회로별로 추적하며같은 decoded field를 확인한다.

compiled M4는 CPI1/84MHz·IRQ/peripheral 할당모델이다. ROM은입력/출력 기원별 ready-gated stress이며ordinary65816 trace·map DMA/최종표시 bus model이다. 전체65816/VBlank·liveNES·firmware WCET·heavy7/71·다중 시작 위상·session reset·FIT/STA·실기60fps는 남아 있다.

## 다음 교체 경계

373을 기본으로 보존하고374 native record를 공통 host 실행기에 포함할 때의 실제 추가 비용으로 사용한다. plan FSM만 host로 옮겨 생긴 independent decoder를 그대로 더하지 않는다. host의 HLOAD/HCHECK·descriptor/manifest/receipt 진행,queue ingress/credit와plan record 생성이공통 address/byte execution을 사용하면서 기존 상태·주소 mux·중복 저장을 삭제해야 한다.

SPI byte 수신과SNES read/private expected 갱신은 동시에 발생할 수 있다. 공통 counter 하나로 덮어쓰지 않고필요한 pending context·RAM 포트 중재·우선순위까지 새 예산에 포함한다. queue expected0..471과output2슬롯을 유지하며남은40B에들어가는 context 범위만 인정한다. source/plan NES clock을host clock으로 mux해 공유하지 않는다.

914의ROM 허용 구간은word decode의µs 단축과구분한다. 실제 첫plan 준비가다음 ROM 창으로밀리는ms 대기를 줄이려면현재 CRC 확인 geometry로만계산하는선행 planner/공급 일정과host 출력 실행을 함께 바꿔야 한다. 실행 뒤 알게 된 tag를hint에 넣지 않는다. raw6packet/heavy7/71과다중위상·전체CPU/VBlank·WCET 및전체 용량 확보 뒤FIT/STA·실기로 진행한다.

## 후속 문맥 RAM의 실제 경계 검토

373에서source scratch가512B별도RAM으로옮겨져validator1KiB에는현재host read/write port만남아있다. 후속후보는이RAM에host-clock 문맥port를추가하는것이다. 포트추가와중재회로는아직구현하지않았고기존한M9K유지/FIT도보장하지않는다.

현재validator의accepted unit/cursor 범위에따른주소감사에서정상초기화후사용구간은0..165,256..421,448..677,680..715,768..1023이다. 연속**716..767의52B**를문맥후보로잡을수있다. V_CLEARALL은초기에이구간도지우므로init278 전에는새포트를막아야한다. 프레임별clear는677→768로건너뛰어이구간을보존한다. 이는제약된RTL 주소감사이며모든불법상태/모든프레임의새형식증명은아니다.

|일부 문맥 예산|byte|
|---|---:|
|active record|16|
|flow byte 진행|9|
|flow flags|2|
|plan wire 진행|6|
|SPI request/입력CRC|9|
|합계/남는공간|42/10|

42B는모든제어정보가아니다. response snapshot/CRC8,queue accepted/retired/consumed와token/serial burn이력,동기화기·실제read capture·fault상태등은별도유지비용이다.이번검토의실제FF/comb 삭제량과시간이득은0이다.

최종trace에서는E1전송중12,105개,E2중3,398개의SNESdata read가있었고E9중에는이표본의동시read가없었다. 이것을일반프로토콜의배타성으로쓰지않는다. 같은token 내최소관측read주기는369ns(약31host clock)였다.42B문맥을매read마다순차fetch하면이주기를넘으므로read-critical cache와pending capture를남기고최악중재기한을검증해야한다. source/host·queue/plan의단순counter합치기나전체RAM문맥의무료화는승인하지않는다.
