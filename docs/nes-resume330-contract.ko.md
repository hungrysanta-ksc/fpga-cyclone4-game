# NES330 — ARM tile 재개와 첫 map 준비 분리 검증

비교 기준은328에서분리검증한325 RTL +327 manifest 선행발행이다.329의ROM 허용창·제어삭제예산을유지한다.330은ARM 코드만바꾸고실제M4 명령·SPI·IRQ·2slot·ROM·staging·32565816 trace 일정에연결한다. 새RTL을추가하지않으며,모든RTL hash가325와같은지확인하여기존전체Quartus Lite MAP 비용과연결한다.

## 구현과 소유권

- `tiles290`은batch 끝/남은record 수를보존하고,검사완료한record마다cursor를갱신한다. 비최종호출은최대16record 후복귀하며최종호출은나머지tile과출력을완료한다. SPI 대기는기존동기호출안에서진행한다. 따라서기존함수가credit 대기때마다처음부터재실행됐다고주장하지않는다. 앞선bulk 성공후에만다음record를commit하고,전송실패는terminal fault로처리해재제출하지않는다.
- ARM `prepare_map330`은준비된planner snapshot과선행map manifest 발행후에만동작한다. 기존209B `metadata317` buffer를재사용하며첫native map packet을208B 이하로만든다. 16개scan 단위씩진행하며범위최대32word와기존순서를보존한다. 연속range가buffer를넘으면해당range 처음으로cursor를돌려나머지를기존생산경로에맡긴다. 준비가미완료면원래경로로fallback한다.
- 첫packet 이후map walk는빈bitmap byte를8word씩건너뛴다. 따라서map 변경의분리비교는 **선행준비+빈byte 순회개선**을묶은것이며cache만의절감이라고표시하지않는다. emitted E1 batch의순서·값·token과E9가같은지별도대조한다.
- metadata buffer 소유권은manifest 송신이끝난후에만넘긴다. 그전에는새준비가buffer를쓰지않는다. 실제expected bitmap은독립입력으로유지하고receipt에서생성하지않는다. 추가상태는tile8B+map20B=28B이며새payload buffer는0B다. 329의32B 상태예산안이다.
- `work302`의DMA pending·plan supply·IRQ 우선조건아래에서만준비한다. 완성되지않은map을queue head에넣지않으며,staging과tile 두chunk는바꾸지않는다. STOP/reset/begin에서새진행상태를초기화하고STOP후prepare는scratch를변경하지않는다.

## 실제로 줄인 것과 남은 회로 교체

이번변경은FPGA 거래나검사를삭제하지않는다. 325의header/descriptor admission,manifest ingress/최종중계,receipt RAM 진행,queue 완료계수,source/plan FSM이그대로남는다. immutable SPI snapshot·CRC8/CRC16·독립expected 검사·실제read CRC·token·STOP/drain·최종12display reads/ACK·VBlank도그대로다.

그러므로전체22,617LE/17,802comb/9,021FF/307,808RAM bits,조합논리부족2,394개에는**절감0**을계상한다. 새합성을실행한것이아니며같은RTL을재합성한결과로포장하지않는다. 부모inclusive 자원과own 자원을중복합산하지않는다.

329의제어영역6,632→4,110comb 상한은여전히설계예산이다. ARM의재개cursor를옮긴것으로host+validator1,326/queue+SPI373/source669/plan154개절감이실현됐다고세지않는다. 다음RTL 구현은host의manifest 중계와validator의별도RAM 진행완료를한host-clock job owner로대체하고,source/plan의중복field 진행은source drain 후NES-clock owner로인계하는범위가필요하다. 검사datapath와CDC·tile 진행은남겨야한다. 새로운공동FSM 옆에기존완료제어를보존하는접근은교체완료가아니다.

제한907의실제명령수는기준/330모두E1 15회,E2 24회,E9 4회,E0 4회,EA 1회다. ROM 수락후끝나는전송808B 중E2/E0 상태거래는370B다. 기존2.625MHz에서wire-only1.127619ms에해당하지만DMA·ARM·준비와겹치므로그대로전체절감에더할수없다. 이결과는다음교체에서**진행event와tile/map identity 확인을함께다뤄야한다**는근거다. 모든짧은status를12B씩늘리고E0 4회를없앤다는단순가정조차24×12−4×26=184B 순증가이므로응답확대를무조건개선으로세지않는다. 이는wire 산술예시이며새응답ABI 검증이아니다.

후속후보는공통record 완료event가storage-retired/actual-consumed와현재chunk identity를한번확정하고,변경된identity만ARM에전달해중복full snapshot 요구를줄이는구조다. 기존host/queue/validator의완료신호와SPI snapshot 생성owner를실제로교체해야한다. transaction 시작시점의snapshot은이번E1의수락을증명하지않으며generation/token/CRC 검사와freshness를유지해야한다. 이구조의면적·추가응답byte·IRQ 및cold 일정은아직미측정이다.

## 검증 범위

통합일정은기존325 CPU bus trace를재사용하며새65816 ROM 실행이아니다. ARM은실제Cortex-M4 명령실행과SPI/IRQ rendezvous이고시간환산은CPI1/84MHz 모델이다. 제한ROM 창을넓히거나코어우선권을빼지않는다. 고정source 시작/ROM cycle과제한·정상연속일정을각각비교한다.

별도ARM 생산자검사는71프레임의전체canonical map 범위·값과나머지명령을기존oracle에대조한다. 이검사는dispatch를가로채며실제credit/ACK 시간검증과구분한다. 준비buffer 소유권검사에서는선행manifest 송신완료flag를명시적으로설정하는directed fixture를사용하고,그실제발행경로는통합실행으로검사한다. 포함명령수에fault test가들어갈수있으므로이생산자검사로성능을계산하지않는다.

추가3프레임검사는전체plan을먼저만들어tile 비최종호출이여러번필요하도록강제한다. cold905/906은남은record14/13/12/11/2를보존한뒤재개했고최종byte 결과가같다. map 준비중STOP,완성cache 후STOP,송신실패후재시도금지를검사한다. 실제RTL에서는partialE1 STOP,조기최종ACK,독립expected 변조,physical ROM pending STOP/drain,실제consumed CRC 변조,early expected 저장중STOP을새ARM 일정에서검사한다.

최종측정표와선택판정은아래에기록했다. source·TB·ELF·CPU trace·fault log와전체MAP hash는 `analysis/resume330-verification.json`에결합한다. 결과가없는새시간/회로절감은계상하지않는다. production227/GBC164/saveSRAM과325/327/328의증거를보존한다.

## 확정 측정과 판정

|warm907 일정|328 기준 ms|330 ms|차이 ms|
|---|---:|---:|---:|
|고정 시작/위상|25.968779280|25.726373098|-0.242406182|
|제한 연속|18.131464238|17.882967220|-0.248497018|
|정상 연속|14.338555208|14.130784974|-0.207770234|
|tile 재개만/제한|18.131464238|18.133282398|+0.001818160|

제한330 시작261.530180/ROM 수락274.905042/완료279.413192ms다. 기준대비시작+0.006046ms,절대완료−0.242452ms와duration−0.248497018ms를구분한다. 고정source-start/ROM cycle 비교에서도−0.242406182ms이므로warm 이득이시작위상만의효과는아니다. 반면cold 고정905/906은+6.454468/+6.045382µs,정상cold는+39.044986/+41.908588µs다. tile만바꾼제한warm은+1.818160µs여서속도개선으로채택할근거가없다.

full330과tile-only의제한warm 차이는−0.250315178ms지만서로시작도달라져map cache 단독의고정위상이득으로단정하지않는다. map 변경은선행준비와빈bitmap byte 순회개선을함께포함한다. 정상907은ROM 수락전에새준비호출이완료된건이0이므로모든이득을ROM 대기와의중첩이라고설명하지않는다.

제한330의수락후경로는4.508150ms다. 마지막tile 소비276.527120→첫map 소비277.485571은0.958451ms로기준1.207875ms보다0.249424ms짧아졌다. 마지막소비279.058041→완료는0.355151ms다. 329의수락후3.180ms 설계상한과최종60Hz는아직못맞추며전체초과는1.216300553ms다.

ARM text30,090B/BSS47,404B/data0,기준대비+696/+28/0B,관측stack1,304B동일이다. tile-only는text29,534/BSS47,384B다. 세full 일정의PT_LOAD가같다. 프로그램/stack은시험ELF 범위이며production SRAM 증명이아니다.

제한warm 명령725,031→719,450(−5,581),SPI1,123B동일이다. tiles290 포함명령219,642→213,984,새prepare_map330은64호출/10,685포함명령이며32호출이첫ROM수락전에끝났다. 하위SPI·IRQ가포함될수있으므로이수치들을별도시간으로더하거나122,331명령을중복decode로제거했다고주장하지않는다.

|일정|3프레임 SPI B|SysTick/EXTI|관측stack B|
|---|---:|---:|---:|
|window01|21819|27/71|1304|
|fixed01|21805|36/68|1304|
|normal01|21427|18/62|1304|
|tile-window01|21819|27/71|1304|

12통합일정의모든E1 opcode payload(순서번호/CRC 제외)와E9 byte가기준과같고FPGA 검증의실제순서/CRC/receipt/최종ACK는각실행에서통과했다. expected변조fault3,actual CRC변조fault7,STOP/조기ACK fault4를확인했으며phase1024B·queue1024B·staging4096B freeze와ROM drain/lease·seal·ACK 비노출을검사했다. 기존aperture tile pingpong/3418B/wrong-token/partial STOP도PASS다.

**판정:**330은warm ARM 시간개선후보로보존한다. cold 회귀와회로절감0때문에시간·회로동시목표달성으로선정하지않고325RTL+327earlyARM 기준선을유지한다. 다음작업은실제완료/identity 제어교체와cold 준비비용을함께검증하는것이며동일회로MAP 반복이나작은cursor 공유를절감으로세지않는다.

분석기첫partial 실행은wire가없는ARM checkpoint를byte0으로읽어실패했고,빈wire 관측을분리하여수정했다. 실패log와후속PASS를probes에보존하며이는RTL/ARM 기능실패가아니다. FIT/STA·71전체ARMIRQ·fullRUN·물리주기·실물60fps 승인은없다.
