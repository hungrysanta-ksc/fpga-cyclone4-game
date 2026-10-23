# NES329 — ROM 허용창과 실제 제어 교체 예산

선택 기준은 **325 RTL + 327 ARM manifest 선행 발행**이며,328의 ARM-only 분리 검증 결과를 사용한다.328 공동 cursor RTL은 채택하지 않는다. 이번 단계는9개 기존 일정과325 전체 Quartus Lite MAP의 재분석이다. 새 RTL·ARM·65816·합성 실행이나 새 절감 실측은 없다. 재현 도구는 `tools/analyze_nes_budget329.py`, hash가 결합된 결과는 `analysis/budget329-verification.json`이다.

## ROM 요청을 앞당기는 것과 실제 공급 개선의 구분

제한907의 원시 이벤트는 다음 순서다. 시각은 동일 테스트의 절대 ms다.

|사건|시각 / cycle|
|---|---:|
|source 시작|261.524134 / 5,753,596|
|첫 BG plan 수락|269.957101|
|첫 BG ROM 요청|269.957147 / 5,939,125|
|map manifest 저장 완료|271.438327|
|첫 ROM 수락|274.905042|
|첫 ROM 응답|274.905269|
|첫 BG 출력 byte|274.905315|
|마지막 tile 실제 소비|276.523013|
|첫 map 실제 소비|277.730888|
|마지막 map 실제 소비|278.008609|
|마지막 ordinary 실제 소비|279.302716|
|최종 완료|279.655644|

ROM 요청 대기는4.947895ms이고 첫 수락→응답은0.227µs다. 응답 지연 자체보다 허용창과 이후 공급 순서가 중요하다. ARM 조기 manifest는이미 ROM 수락3.466715ms 전에 저장되므로 같은 조기발행을 다시 신규 이득으로 세지 않는다.

제한 테스트의 qualify 식은 `cycle % 357368 ∈ [330088,354640)`와12cycle당1회 조건이다. 코어 요청은120cycle당1회 우선한다.22MHz 모델의 실제 주기는45.454ns이며 창 주기는16.243807072ms, 창 폭은1.115985808ms다. 이는 테스트의 ROM 경쟁 모델이고 실제 보드 최악 위상 증명은 아니다. 이벤트 모니터가cycle을먼저증가시키므로 경계는±1cycle 오차로 다룬다.

이전 창 종료cycle5,715,160은 **source 시작보다1.747069944ms 이전**이다. 현재 BG 요청은 그 종료보다10.180105110ms 늦다. 현재 창의 명목 시작cycle6,047,976 후 약0.182µs에 이미 수락된다. 따라서 현재 프레임에서plan을더빨리만드는것이나 요청 후 polling을줄이는것으로 이전 창을잡을수없다. source 시작을늦춰duration만줄이는방법도채택하지않는다. 대화 중 임시계산1.293ms는잘못된차감이며 원시cycle로재계산한1.747069944ms가정정값이다.

반면 고정 시작907에서는 이전 창 종료가source 시작6.089654196ms 뒤이고 요청이그끝을2.345835486ms 놓친다. 여기서는준비앞당김으로이전창을잡을가능성이있지만,그성과를제한연속907의성과로바꿔쓸수없다. 정상연속은요청대기0이다. 세일정의요청대기/수락후완료는각각고정12.782528/4.750829ms,제한4.947895/4.750602ms,정상0/5.905588ms다.

## 시간 예산: 수락 후 경로를 우선 교체

현재 제한907은18.131464238ms이며16.666666667ms보다1.464797571ms 늦다. 마지막소비후0.352928ms를전부없애도1.111869571ms가남는다. 후반checker만으로닫히지않는다.

수락 시각과 그 이전 일정을 유지하면 수락→최종완료는 **4.750602→3.285804429ms 이하**여야 한다. 다음은 실측 절감 예측이 아니라 구현의 상한 예산이다. 서로 겹치지 않는 사건 구간으로 나눠 ARM·SPI·IRQ·DMA 시간을 중복 합산하지 않는다.

|구간|현재 ms|설계 상한 ms|교체 초점|
|---|---:|---:|---|
|첫 ROM 수락→마지막 tile 소비|1.617971|0.900|tile run 재해석·반복 status 교환과 E1 공급 연결|
|마지막 tile→첫 map 소비|1.207875|0.400|ROM 대기 중 map packet 준비, tile 종료 직후 발행|
|첫 map→마지막 map 소비|0.277721|0.280|기존 batch·실제 DMA 유지|
|마지막 map→마지막 ordinary 소비|1.294107|1.300|기존65816 실행시간 유지, 앞선 준비와 credit 연결|
|마지막 소비→최종완료|0.352928|0.300|expected/receipt 공동 실행과 종료 응답|
|합계|4.750602|3.180|신규 overhead도각구간안에포함|

위 상한을 모두 만족하고 앞부분이 같다는 가정에서16.560862238ms, 여유0.105804429ms다. **1.570602ms의 순절감이 필요하며 달성 여부는 미검증**이다. 경계가바뀌면최종전체duration으로다시판정한다. 정상일정은오히려수락후더길기때문에제한907한개에맞춘우회는선택하지않는다. cold905/906 시간도별도회귀검사하며warm60fps와혼동하지않는다.

실제 ARM 함수 계측에서907의 `tiles290`은31호출이다. ROM 수락후시작한2호출의포함명령수는122,331(CPI1/84MHz 환산1.456321429ms)이고수락경계를가로지르는호출도1개다. 이값에는하위serializer·검사·IRQ등이포함될수있으므로중복작업이나그대로제거할시간으로세지않는다. 반면수락후 `issue_map327`49호출은441포함명령이다. 이미끝난map manifest준비를더최적화하는것보다 `tiles290`의재시작지점과map/DMA발행준비를분리계측하는편이우선이다.

구현 후보는ARM의tile run 해석을재개가능하게하여검증한record 경계마다진행을보존하고,credit 부족시pending run만유지하는것이다. 현재함수는local `at/used/kind/first`로순회하고정상끝에서만영속cursor를저장하므로,반환경로별재해석과실제packet 제출을분리해야한다. 성공한bulk의token을재사용하거나중복제출하지않도록submit/accepted/consume 상태를별개로둔다. 이것이명령122,331개를모두제거한다는주장은아니다.

ROM 대기 중에는확정된BG/map의변경범위와첫packet 길이까지만증분준비한다.OBJ 계산이끝나야확정되는부분은기다린다. DMA pending·E9 plan credit·IRQ를매단위우선하고,미완성E1을두슬롯head에넣지않는다. 기존serializer buffer를tile E1과동시에덮어쓰지않으며buffer 추가가필요하면BSS·복사·SPI 비용을공개한다. 우선예산은큰새payload buffer0B,추가작업상태32B이하이고초과시재설계한다. 독립expected bitmap을실제receipt로채우는변경은금지한다.

이전프레임에서CHR을미리읽는후보는별도보류한다. ROM bank/tag·mapper epoch·lease·무효화·STOP과다음프레임query가확정되기전의유효성을증명해야하고RAM/cache 제어비용도추가된다. 현재1.747ms 경계를넘을권한이나미래CHR내용을가정해절감에넣지않는다.

## 회로 예산: 주소 레지스터가 아닌 실행 소유권 교체

전체325 MAP은22,617LE /17,802comb /9,021FF /307,808RAM bits다.15,408comb 목표보다2,394개 부족하다.328은16FF를줄였지만74comb를늘렸고host/validator FSM은이미추출되었다. FSM 추출이나cursor 공유를새해법으로반복하지않는다.

|동일 전체 MAP의 own 비용 경계|현재comb|교체 후 허용 상한|필요 감소|
|---|---:|---:|---:|
|host 자체 + validator|3,426|2,100|1,326|
|queue + 공통 SPI 자체|973|600|373|
|source encoder + transport subtree|1,769|1,100|669|
|plan 자체 + transport subtree + endpoint|464|310|154|
|교체 영역|6,632|4,110|2,522|
|그 밖 보드|11,170|11,170|0|
|전체|17,802|15,280|2,522|

128comb 여유를포함한설계할당이며합성예측이아니다.외부mapping이늘면그만큼4,110상한을줄여야한다. host+validator만으로해결하려면1,032이하가필요하다. source+plan2,233을가상으로전부지워도2,394에못미친다. plan cache/arbiter/tile datapath는각영역의부모inclusive값을더하지않고외부11,170에남겼다. RAM은307,808bits 이하를초기상한으로두되M9K 배치와포트성립은별도통과해야한다.

상한은상당히공격적이다. source transport subtree 전체가423comb이므로그전부를공짜로없애도encoder 자체에서246개이상을추가로줄여야한다. queue 자체276개를전부지워도SPI에서97개이상이더필요하고,plan endpoint91개를전부지워도plan 진행에서63개이상이더필요하다. 실제로는각검사·CDC가남으므로필요한재구성은더크다. 이산술은삭제실현근거가아니며,기존외부continuation을그대로둔작은공동FSM 추가만으로예산을충족했다고간주하지않는탈락기준이다.

실제삭제대상과유지기능은다음과같이묶는다. 아래삭제는**다음구현의검수목록**이며이번에삭제했다는뜻이아니다.

|기존 블록/제어|대체해서 삭제할 것|유지해야 할 기능|
|---|---|---|
|`nes_output260` + `nes_validator278`|host의MREAD/MCAP/MNEXT/MISSUE/MWAIT 연쇄와validator의별도expected/receipt RAM 진행owner를한host-clock job 실행기로대체. terminal446B를host가다시중계하는경로와중복완료handshake 제거. header→native목적지/receipt주소선택은admission 한번으로고정.|단일압축확장,범위/overflow/rawtail 검사,독립expected 원본,실제read-count/CRC/token에서만receipt 생성,H2certificate,12display reads,VBlank·최종ACK. 비교datapath 자체는공동제어안에남김.|
|`nes_queue260` + `nes_spi270`|queue 전용load/clear/finish 진행과endpoint별status 선택을공통admission/slot-event 전이로흡수.2slot record와통일완료event가SPI snapshot/IRQ를갱신하도록하여기존상태복사·응답mux 경계를교체.|물리SPI shifter,SS별immutable snapshot,CRC8/CRC16,원자적packet 승인,accepted/storage-retired/consumed 별도계수,serial/generation/token history. snapshot을live shift로바꾸지않음.|
|`nes_core257` + `nes_transport257`|source record 생성과block close/publish의서로대기하는완료제어를하나의NES-clock byte job 종료로연결.별도record-open/last/flush 재판정과주소선택경로삭제.|기존압축wire/CRC,query응답과source snapshot,2bank publish/POP CDC,COMMIT와DISPLAYED 구분. codec 계산을없어진것으로세지않음.|
|`nes_plan_batch206` + `nes_plan_spi200`|plan READ/CAPTURE/CHECK 진행을source 종료후동일NES-clock byte job에인계. 별도plan field 진행FSM/endpoint complete owner 삭제;기존wire bytes를동일RAM에서해석.|sealed batch CRC/exact length/shape/generation,immutable plan bank,READY/RUN 중tile field 고정,partial BG end와frame end 구분,STOP/drain.|

host-clock 실행기와NES-clock 실행기를하나의클록없는FSM으로합치지않는다. source→plan 인계는query/source/transport drain과display lease가확정된후다. source출력생산과plan소비가실제로겹쳐야하는반례가나오면공유실행기후보를철회하거나중단가능한context 비용을예산안에넣는다. tile producer/cache를그실행기에묶어source/SPI stall 동안멈추게해서도안된다.

## RAM 포트와 완료 순서

|RAM / 포트|소유권 및 다음 구현 규칙|
|---|---|
|phase1024B A, NES clock|source query/codec. output phase의source write 금지와drain 검증유지. plan RAM과물리적으로같은포트라고세지않음.|
|phase1024B B, host clock|receipt read→mask/CRC 검사→write는중간job 교체없는원자단위.그다음expected 비교/hash/context/display fetch. expected값과actual receipt의provenance는분리.|
|queue1024B A|두packet slot의ingress write. admitted length/CRC완료전slot 공개금지.|
|queue1024B B|공통reader가head header/payload를읽거나canonical expected0..445를저장/읽음.동시에두요청을발행하지않음. RAM read 대기1cycle과held byte를비용화.|
|plan1024B, source transport512B|각각기존서로다른clock 포트/불변bank CDC 유지.공동제어가RAM을자동으로합친다고주장하지않음.|
|staging4096B|325 tile 두chunk 선행생산과map 소유권 유지.실제SNES read와producer write의충돌방지.단일chunk로축소하지않음.|

우선순위는진행중인RAM read/write pair 완료→소비event/CRC/receipt 처리→필수head payload/plan 공급→expected 저장·최종scan이다. 실제소비event는ready/valid로보존하고DROP하지않는다. scan은op3+모든소비완료+expected complete가성립한후에만최종seal로이어진다. storage credit 반환은payload를staging/active record에안전하게옮긴후이고실제소비완료는별도다. STOP은새read/write/publish를차단하고진행중physical ROM을drain하며,token은burn하고세RAM의freeze를검증한다.

## 다음 단계의 순서와 판정

1. **일정 A/B:**325 RTL을유지하고ARM 재개가능run/첫map 준비만연결한다. `tiles290` 내부decode/packet-build/submit/credit-wait를구분계측하고원시instruction·SPI·IRQ를포함한다. 기존327 manifest 선행발행은유지. payload/E9·expected 내용동일성,2slot과cold fallback을검사한다.
2. **실제삭제 A/B:**host job과NES byte job을위삭제목록단위로교체한다.상태이름만바꾼경로/동일중복주소mux가남으면삭제완료로세지않는다. 독립expected 변조와actual CRC 변조가각각검출되어야한다. source/plan 공유는phase 불겹침이증명된범위만채택한다.
3. **전체 gate:**동일source 시작/cycle 고정A/B와제한·정상연속905/906/907,STOP·partialE1/E9·ROMpending·earlyconsume/finalACK·bank/token재사용·RAMfreeze를유지한다. 실제65816 경로를바꾸면325 trace 재사용만으로통과시키지않고새CPU 실행을한다.시간3.18ms 후반상한과최종≤16.666667ms,wholeLite≤15,280comb(하드목표15,408),RAM/port 상한을동시에평가한다. 하나만좋아지면기준선을교체하지않는다.

새회로·시간절감은아직null이다. 목표충족가능성이증명된구조로승격한것이아니라,328의실패를반영해측정대상과교체경계·상한·탈락조건을확정했다. FIT/STA·71프레임전체ARM·물리MCU주기·실물60fps는미검증이다. 생산227/GBC164/saveSRAM과325/327/328의기존증거는보존한다.
