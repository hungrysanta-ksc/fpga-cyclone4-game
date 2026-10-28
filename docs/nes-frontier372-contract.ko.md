# NES372 첫 블록 비용과 입력·표시 문맥을 포함한 공동 제어 교체

PR132 `e9005716f76f37244ec8272acbdcd41f497d7ec5` 이후 같은 브랜치다. 시간·RTL 기준은370이며371의 RX/양보 후보는 비교 근거로 보존한다. private 원본은 `probes/nes-frontier372`, 최종 근거는 `analysis/frontier372-verification.json`이다.

## 결과

370과 같은 ABI·hint packet·RTL에서 **915 캡처 승인**을 확인했다.914 local 저장은2.614195→2.299063ms로315.132us 빨라져915 기한에41.159us 여유가 생겼다.하지만 다음916이 거절됐으므로 연속60fps는미통과다.

최종 joint02는905~915의11프레임을 배출했다(초기화2/warm9).다음 캡처9회 중8회 승인,916 거절1회다.관찰 종료의 거절을 유지한 뒤배출했고coverage 오류1·경고0으로 보존했다. 넓은hint 후보joint01은915에서즉시실패했다.

|frame|370 ms|372 ms|변화 ms|
|---|---:|---:|---:|
|907|12.040741|11.879334|-0.161407|
|908|12.417419|12.104741|-0.312678|
|909|16.215692|15.933014|-0.282678|
|910|12.030379|11.865608|-0.164771|
|911|12.479010|12.206831|-0.272179|
|912|15.424883|15.237431|-0.187452|
|913|12.130105|11.940062|-0.190043|
|914|21.545718|21.500992|-0.044726|

위8쌍은source 시작 시각과ROMcycle가모두같다.앞선 일정은다르므로순수CPU만의독립실험이라고부르지않는다.914는44.726us 개선했지만21.500992ms로60Hz 예산보다4.834325ms 늦다.입력ACK는3.704796→3.310483ms다.첫hint 전송반환은1.750510→1.482701ms,첫BG는16.901206→16.857025ms로ROM대기는남았다.

ROM은기원기준요청/응답60477/60477,입력8846/8846,pending0이다.기존CAPTURE365의시각창counter8846/8845를동일요청기원의불일치로오인하지않으며새origin audit와모든응답값검사를사용한다.관측stack1288B,SysTick body41회/EXTI event243회다.

ARM text34234→35862B(+1628),data4/BSS48476B 동일이다.새회로절감은없다.371을제외해전체comb는17735→17698(-37),부족량은2327→2290이지만이는370 기준복구다.155여유포함2445순삭제가남았다.

## 실제 ARM 변경과 동등성

N5 MASK는64/66개 bit를 두 번 훑는 대신 mask byte 단위 popcount와 set-bit 순회를 사용한다. 유효 tail bit·변경 byte 수·남은 길이를 먼저 검사한 뒤 쓴다. geometry/ordinary의 쓰기와 raw의 값 범위/dirty 추적을 분리하여 geometry에서는 필요 없는 raw 비교를 하지 않는다. raw dirty bit는 같은8B group에서 실제 값 차이가 있을 때 한 번 OR한다. source CRC16과 N5 누적 CRC·seal 검사는 유지한다.

SHIFT의 고정64B 복사는 겹침 방향을 유지한 순서대로 펼쳤다. 왼쪽은 낮은 주소부터,오른쪽은 높은 주소부터 쓴다. byte 연산을 유지하므로 새로운 alignment 전제가 없으며 홀수 base도 대조했다. flash 증가를 받아들이고 반복 제어 비용을 줄인 선택이다.

hint packet은370과 같다. target bitmap 초기화를 묶고 target bank의 유효 resident bit만 순회한다. current geometry·직전 표시 이력·epoch/generation·cold/STOP 조건은 유지한다. 처음에는7tag의 넓은 선택도 비교했지만 strict joint01에서915를 놓쳤다. 그 build03 decoder도최종과달라hint 폭만바꾼A/B로보지않는다. 최종 build06/joint02는370과 hint까지 같은 좁은 정책이다. 넓은 후보의 미완료914 시간을 성공으로 계산하지 않는다.

실제 M4의905~914 입력51block에서 반환값과96개 전역 객체가370과 일치한다. 추가2573개 MASK byte 전수/tail bit/zero mask/raw>=64/양방향SHIFT/홀수base 대조와 기존28개 hint guard·9개 source 수신/CRC/token/generation/cancel/ACK guard를 통과했다. 별도8개 causal snapshot의 hint 출력도 일치한다.

914 첫 block은32421→10758명령(21663절감),hint는8917→8084명령(833절감)이다. source 전체는73062→39941명령이다. 이 수치를 실제 일정 개선에 다시 더하지 않는다. payload/CRC와 hint packet,논리 plan record는370과 동일하며908에는 빠른 재진입 때문에 빈 D4 header13B가 한 번 늘었다. 이 비용도 실제 일정에 포함한다.

기능 실행의 공통 compiled module30개와370/368의 전체 Lite 보드 RTL이 바이트 일치한다. guard ELF와 전체 실행의 PT_LOAD 주소·크기·바이트 및 함수/객체 symbol을 대조한다. 파일 메타데이터까지 같은 해시라고 주장하지 않는다. RTL 변경이 없어 새 MAP을 반복하지 않고 일치가 확인된 전체 Lite MAP을 상속한다.

## 입력을 더 빠르게 해도916을 놓친 이유

915는 승인됐지만 source 시작이916 기한보다2.832533ms 늦었고,materialized는그 기한보다4.408605ms 늦었다. 915 source 자체의 materialized 기간은1.576072ms다. 이전914 표시/retire를 기다린 backlog와 이번 입력 해석 시간을 구분한다.915의 자체 처리 시간17.269452ms도60Hz 예산을 넘는다. 370이915에서 먼저 실패해 측정하지 못했던916을 새 ARM의 단순 회귀로 부르지 않는다.

따라서 source·host·queue·plan을 공통 FSM으로 바꾸면서 기존 단일 phase/lease 장벽을 그대로 두면916 문제는 남는다. 필요한 교체 단위는 **입력915 문맥과 표시914 문맥의 분리**,동시 생존 RAM,실제 SPI/IRQ/ROM 중재까지다. 전역 STOP은 둘 다 취소하되 ACK14가 이미 시작한 input15를 reset하거나,input15가 display14의 generation/expected를 바꾸면 안 된다. 최종 ACK는 해당 표시의12 exact reads/token·독립 receipt/coverage와 기존 VBlank 조건 뒤에만 공개한다.

현재의 source scratch512..1023과 validator phase RAM은 겹친다. 동시 실행에서는 이를 수명 공유 RAM으로 계산할 수 없다. 또 ARM의 wire259는 output14 전송에 필요하므로 background source15 raw를 그 buffer에 저장하면 안 된다. raw prefetch만 먼저 수행하고 N5/history 갱신은 이전 planner가 history를 쓰지 않을 때 수행해야 한다. 구현하지 않은 overlap 시간은0이다.

## 실제 전체 회로 비용과 삭제 예산

|전체 Lite|370/372|371|372의 변화|
|---|---:|---:|---:|
|LE|22710|22747|-37|
|comb|17698|17735|-37|
|FF|9171|9172|-1|
|RAM bits|292448|292448|0|

이는371 후보를 제외해370으로 돌아온 비용이며 **370 대비 새 회로 절감은0**이다. 2290comb 부족,155개 여유 포함2445개 순삭제가 필요하다. 새 FIT/STA·Standard는 실행하지 않았다.

queue를 parent의 inclusive cost에 중복 가산하지 않고 **self224**만 별도로 포함했다. source core1352,transport378,SPI567,validator1040,host flow2058,NES plan349,plan endpoint96,queue224의 disjoint 합은6064다. 기존7모듈 예산에 queue를 추가한 범위 변경이며 새 절감이 아니다.

|교체 범위|현재 self comb 상한|2445 순삭제 후 새 구현 상한|
|---|---:|---:|
|host SPI·flow·plan endpoint·queue|2945|500|
|위 범위+mixed-clock transport 전체|3323|878|
|codec/checker를 보존한 나머지8모듈 제어|3672|1227|
|8모듈 전체,codec/checker 내부 제어도 재구성|6064|3619|

transport378에는NES bank 생산과 host 수신이 섞여 있어 host-only 가용 비용으로 모두 승인할 수 없다. codec1352/checker1040을 보존하는 경우에는 새 제어 전체가1227 이하이어야 한다. 전체3619 상한은 독립 검사를 삭제해도 된다는 뜻이 아니다. 필요한 CRC/coverage/datapath·bridge·RAM arbitration을 모두 새 구현 비용에 포함해야 한다. 현재 새 제어의 합성 비용은null,삭제 인정량은0이다.

## 검토한 구체적인 교체 경계

1. **두 active context와 host 공통 진행 실행기.** SPI shift/synchronizer·직접 SNES read capture·token/serial burn 이력은 유지한다. source/queue의 header·주소·길이·CRC 진행,host descriptor/manifest/receipt 진행과 plan 수신을 같은 host-clock 실행 단계로 교체한다. source의별도header CRC8진행을공통response CRC로옮기고,E1의ingress length를기존request length문맥에통합하며,header는[0..3]/[10..20]두범위를읽도록해field338 재배열과별도loader진행을대체하는범위다. accepted/retired/consumed는서로다른사건이므로합치지않는다. 기존FSM을 남긴 wrapper는 교체로 세지 않는다. SPI 수신과 실제 read-event는 동시에 올 수 있으므로 별도 pending/owner 문맥을 보관하고 read-event를 우선한다. header 이후 한꺼번에 처리하는 평균 byte율만으로 응답 기한을 승인하지 않는다.
2. **queue footer의 상태 저장은 제한적 후보.** 0..471은 독립 expected,512..1023은256B packet 슬롯2개다. 472..511의40B에 SPI12B/active record16B/execution8B를 넣는36B 배치를 검토했다. expected의 실제 소비 주소가472 이상에 들어오지 않도록 증명하고 port A에 새 read/owner arbitration이 필요하다. source/checker의 모든 state,queue의accepted/retired/consumed/ingress sequence·admission identity나token 이력까지이36B에포함한것이아니며별도로유지하는비용을계상해야한다.
3. **plan의 host decode와 고정 native32B,word port.** wire E9의 압축/짧은 표현은 유지하고 host가 CRC/seal 전에 speculative native record를 만든다. 최대16×32B는 기존512B bank에 들어간다. NES는 lease/generation/정확한 count·BG partial/END·tile_done/retire를 검사하고 고정 record를 공급한다. 기존 NES operand decode 본체를 제거하는 범위다.8bit port를그대로두면914의7개 record data read는90clock→pipelined224 또는2cycle448clock으로늘어6.091/16.273us가추가된다. 그래서 **256×32bit word RAM에record당8word**를쓰고NES도word로읽는대안을함께검토한다.914의data read예산은56clock(-1.545us) 또는2cycle112clock(+1.000us)이다. host의word 조립·전부쓰기·CRC후publish 비용과logical1KiB가실제primitive에서어떻게배치되는지검증해야한다. 이수치는control·END·CDC·실제stall을포함한새측정이나시간이득이아니다.
4. **source의4packet ring·footer descriptor.** 512B를1024B(4×256B)로 확장하고 길이/generation/CRC/final 정보를 bank footer에 둔다. 기존 두 bank의 descriptor·publish/sent/busy와 host snapshot 제어를 ring ownership과 공통 reader로 대체하는 범위다. logical RAM은+4096bits이며8bit×1024 source RAM은 M9K 한 블록 형식 범위지만 새 합성/배치 보장은 없다. 완전한 read·token/gen·footer 확정 뒤에만 pop하고 final은producer의 END와 FIFO drain까지 확인해야 한다.
5. **source와 plan을 host clock으로 모을 경우 NES local row/query front를 유지.** 외부clock의RAM을 clock mux로 합치지 않는다. native capture/ROM lease·행 완료·query reply·STOP drain은 NES에 남고,in-order row 공급을 host executor로 넘긴다. source와 validator의 동시 scratch가 필요하면 기존 phase 공유를 폐지하고 shadow를 별도 배정해야 한다.

## 크기·SPI의 하한과 다음 후보

71개의 기록된 입력 크기는 새71프레임 실행이 아니다. 이 corpus의 warm 최대는6packet이다. 현재2packet 저장으로954를 materialize하려면 최소4packet을 ARM으로 옮기고 반환해야 한다. payload·D4 header/CRC·마지막 pop prefix만970B이며,현재 SCK 모델에서 **2.956190ms** 하한이다. 같은2.340222ms 창을 가정하면 CPU/producer 준비를0으로 둬도 넘는다.4packet source 저장이면2packet/501B,wire 하한1.526857ms로 줄지만 준비·CRC·경쟁 비용을 더 검증해야 한다.

중첩 후보는 source ring1KiB와 source shadow1KiB로 **+12288bits,총304736bits**를 예산으로 잡는다. 이는 논리 bit 예산이며 physical block/FIT 보장이 아니다. 입력·표시 문맥을 분리하면 현재915의3packet은4packet ring에 보관해 ARM이14를 실행하는 동안 materialize할 가능성을 검증할 수 있다. corpus 최대6packet에는 별도 raw RX2개×250B(500B)와 metadata가 필요하다. output wire를 재사용하지 않으며,actual SPI/IRQ/ROM 경쟁을 포함한 새 처리 시간/추가 logic은미측정이다. SNAPSHOT RAM을 무료로 공유하지 않는다.

또 실제370 packet을 record 단위로 복원한 뒤 BG/nonmap 경계에서 먼저 seal하면914는 **[220,187,246,30]→[190,217,246,30]B**로 재배치된다. concatenated source bytes와4packet 수는 같아 추가 header/CRC byte는0이며 첫payload30B가 줄어든다. source가현재 capture의 BG 경계를 알게 되는 시각·CRC pending·bank credit/STOP을 연결한 RTL은아직 없다. 이 조기seal과7tag hint를 함께 검증해야 하며 앞당김을 새 일정 이득으로 계산하지 않는다.

다음 R0/R1은 이중 문맥·shadow/RX 소유권·4packet ring/조기seal·host 진행/plan decode의 **실제 삭제 목록**을 한 경계로 구현해 동시 입력/표시를 검증하는 것이다. 같은 시작/ROM 위상뿐 아니라 input15와 display14의 동시 ROM request origin을 구분하고,producer가 빨라져 ROM 허용 구간이 바뀐 효과를 공짜로 더하지 않는다. 새 전체 Lite MAP에서3619/1227 상한과추가RAM/bridge를 함께 대조한다. 현재회로 절감이나60fps성공은미승인이다.

## 검증 한계

실제 compiled M4 C/IRQ와 SPI 신호를 실행했지만CPI1/84MHz·exception/주변장치는할당모델이다. ROM은ready-gated stress이며 live NES CPU가아니다. source 시작/ROMcycle가같다는것과모든core-request timestamp가같다는것을구분한다. ordinary65816 trace와map DMA/최종표시bus model이며전체CPU/VBlank·firmwareWCET·heavy7/71·다중시작위상·ABI/session회복·FIT/STA·실기60fps는미완료다. 독립read CRC/coverage·STOP·최종12read/token ACK와기존VBlank firmware·production227/GBC164/saveSRAM을유지한다.
