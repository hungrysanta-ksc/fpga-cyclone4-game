# NES327 — expected 직접 읽기와 ROM 대기 중 map manifest 발행

325의 단일 확장/native65816 소비/실제read CRC/tile ping-pong을 유지한 구현 실험이다.319는 역사적 비교 기준,325는 직전 실측 비교 기준이다. 결과는 `analysis/joint327-verification.json`에 소스·실행·전체MAP hash를 묶는다. production227/GBC164/saveSRAM을 바꾸지 않는다.

## 실제 교체와 유지 경계

op15/10/11의 압축 expected 저장은 기존 queue RAM0..445를 쓴다. terminal op3 이후에는 validator가 자신의 display index·독립 expected cursor로 이 RAM의 B포트 주소를 직접 지정한다. host의 op3 MREAD→MCAP→held→MISSUE→MWAIT 바이트 전달·manifest_byte 증가를 없애고 scan start/done 경계로 교체했다. host는 scan 완료 후 기존 hash·certificate·finish·seal 절차를 진행한다. RAM을 추가하거나 async read로 바꾸지 않았다.

validator의 E_READ327/E_CAPTURE327이 동기 expected read를 받아 기존 display 의미검사와 independent coverage 검사에 전달한다. expected는 ARM의 원래 bitmap에서 나오고 actual receipt/CRC는 실제 staging read와 token ACK에서 나온다. expected를 producer 결과로 다시 만들지 않는다. 최종 scan의0..445 정확한446회 순차 읽기를 시험벤치에서 검사한다. STOP과fault는scan 완료·RAMwrite·lease·seal을차단한다. 최종12display reads와token ACK/VBlank 경로는그대로다.

전부 하나의 FSM으로 합친 것은 아니다. ingress RLE→expected 저장, ordinary 단일 확장, receipt granule walk,hash/certificate,source/plan은 유지한다. 특히 manifest 저장에도 필요한 host counter와 MREAD/MCAP/MISSUE 상태 자체는 남는다. 제거한 것은 terminal 재생의 이중 진행과 byte handoff이며, 모든 manifest 상태·주소 계산을 삭제했다고 주장하지 않는다.

ARM은op15 발행 후같은209B metadata 버퍼를 재사용해map bitmap을최대16B씩RLE로준비한다. 한work 방문에서최대17단계를허용하되매단계DMA대기·plan 공급·GPIO/IRQ 진행을다시확인한다. serial/generation/target과planner준비완료는기존metadata_ready317 조건으로검사한다. payload가200B 예산을넘으면선행발행을포기하고원래late manifest 경로를쓴다. 추가200B buffer나wire 확대는없고진행상태7unsigned의ARM저장비용은실측ELF에포함한다.

완성된map manifest는2슬롯storagecredit이있을때만기존E1/CRC/응답검사로발행한다. DMA가아직소비되지않아도expected 저장은가능하지만receipt나최종seal을앞당기지는않는다. 성공적으로발행한경우만뒤의동일manifest 전송을생략한다. packet sequence/CRC는새순서에맞추고E9·opcode별원본payload 동일성은분석기로대조한다. cold/overflow는기존분할/전송으로돌아가며그준비실패비용도시간에포함한다.

## 보존한 중간 결과

fixed01은SystemVerilog 선언전참조 컴파일실패였다. validator 주소출력을기존rec_i/cursor 선언뒤로옮겼으며license 문제는없었다. fixed02는첫기능연결의3프레임PASS다. 그러나대기방문마다16B 한단계만처리해서warm 선행발행이완료되지않았다. 이일정과원본로그를보존하고,매단계우선권을재검사하는최대17단계의bounded loop를최종ARM안으로삼았다. 이는첫결과를선행발행성공으로세지않기위한구분이다.

## 전체 회로 비용

Quartus Lite 전체MAP은22,627LE/17,812comb/9,024FF/307,808RAM bits다.325 대비+10LE/+10comb/+3FF/0RAM,부족은2,394→2,404comb로늘었다. host 자체2,411→2,410(−1),validator1,015→1,040(+25),aperture205동일이다. 나머지전체mapping 변화를포함한합이+10이므로local 합을전체절감으로치환하지않는다. 기존cache_index141 이외의새latch/undriven 여부를분석기에서확인한다. FIT/STA는실행하지않는다.

따라서이교체안만으로시간과회로가함께줄었다고판정할수없다. terminal446B 전달을옮겨도ingress 저장제어와checker의새read/address 경계가남기때문이다. 회로해결을위해더필요한것은expected 저장·최종검사·receipt의포트/주소소유권을더넓게교체하는구조이며,검증된tile 선행생산을없애거나FSM/seed를반복조정하는방식으로이실패를숨기지않는다.

## 증거의 적용 범위

통합일정은실제Cortex-M4 명령/IRQ·SPI응답·2슬롯·tile ROM·staging경쟁과325에서실제실행한65816 bus trace replay를포함한다. ARM은CPI1/84MHz와관측IRQ경계모델이며물리MCU계측이아니다.65816 ROM 자체는이번에변경하지않았으며325 CPU/STOP/경계시험의같은ROM과trace를hash로결합한다. 새live full65816/fullpixels/71 ARM/fullRUN/실물60fps 증명으로확대하지않는다.

ROM accept와backend response는별도event로추가했다. 첫BG tile output을ROM grant로부르지않는다. 고정source시작/ROM cycle A/B와제한·정상연속일정을모두기록하고,이전cold완료에따른다음frame시작변화와실제절대완료변화를분리한다. 최종시간과오류검사결과는아래실측표에기록한다.

## 실제 시간과 ARM 비용

|907 비교|325|327|차이|
|---|---:|---:|---:|
|동일시작/ROM 위상 duration ms|26.186594848|25.963779340|−0.222815508|
|제한연속 duration ms|18.314098410|18.131464238|−0.182634172|
|제한연속60Hz 초과 ms|1.647431743|1.464797571|−0.182634172|
|정상연속 duration ms|14.370236646|14.328964414|−0.041272232|
|ARM text B|28,986|29,394|+408|
|시험ELF BSS B|47,348|47,376|+28|
|관측stack B|1,304|1,304|0|

시험ELF의BSS는전체시험환경을포함하므로production SRAM예산증명이아니다. 고정비교는160ms 간격의별도시작일정이므로그duration을제한연속의60Hz 판정값과직접비교하지않는다. 고정905/906/907은source시작과ROM cycle이정확히같고완료가각0.036954/0.040136/0.222816ms 빨랐다. 실제추가ARM명령은각26,368/55,414/27,226개다. 이를CPI 시간으로따로더하거나대기와겹친준비를무료로빼지않는다.

제한907은시작261.559270→261.519134ms(−0.040136),첫BG출력274.905315ms 동일,완료279.873414→279.650644ms(−0.222770)다. duration 단축0.182634ms와절대완료단축0.222770ms를구분한다. 새map manifest는271.433315ms에release되어첫BG보다3.472ms앞서며,마지막consume279.302716ms 뒤남은구간은0.347928ms다. 이전tail0.570531ms보다줄었지만목표까지1.464798ms가남는다.

고정907의map manifest는344.822261ms에release되어첫BG356.124704ms보다11.302ms앞선다. 마지막consume360.522375ms는325의360.522542ms와거의같으므로주된개선이그뒤일정에서발생했음을확인한다. op3 parser 점유는33.998→28.701µs,그안의직접scan은27.070µs다. 두값을가산하지않으며이5.297µs만으로전체222.816µs를설명하지않는다.

정상907은map manifest release189.192067ms가첫BG183.593456ms보다늦고마지막consume188.676743ms 뒤다. 이경우late 경로가남으며단축은41.272µs다. 절대완료−117.862µs에는앞선cold 개선76.590µs가포함되므로warm 이득으로세지않는다.

|3프레임 실제비용|고정위상|제한연속|정상연속|
|---|---:|---:|---:|
|SPI bytes|21,819|21,819|21,441|
|SysTick / EXTI|36 /68|27 /71|18 /62|
|warm ARM 명령증가|27,226|22,426|5,164|
|max storage credit|2|2|2|

9개일정의opcode별E1 payload는sequence/CRC를제외하면325와정확히같고E9는byte 단위로같다. SPI 합계변화는polling/응답이포함된결과이며새압축wire 절감이아니다. 매단계우선권확인과cold 선행준비포기비용,실제IRQ/ROM/staging경쟁을모두포함한다. ROMaccept→response→tile 첫byte도별도관측했다. 제한907 BG는274.905042→274.905269→274.905315ms이며이세경계를혼동하지않는다.


## 판정과 다음 교체 경계

선택증거는fixed03/window01/normal01/board01/guards01이다. 실제9일정과11fault가모두통과했다. source/plan/부분E1/E9/ROMpending/확장중/최종scan중 STOP,조기소비ACK·최종ACK는fault4,독립expected 변조는fault3,실제consumed-byte CRC 변조는fault7로거부됐다. 각fault 뒤8+256host clocks 동안phase1024B/queue1024B/staging4096B RAMfreeze와lease/seal/finalACK 비노출을확인했다. ROMpending STOP에서는drain도확인했다.

같은aperture RTL의tile 두chunk 보존·3418B 실제쓰기/읽기·잘못된token·부분확장STOP도통과했다. 정상통합일정의9회scan은각446B 순차읽기를확인했다. 실제65816 ROM과CPU trace는325와같고이번에CPU를다시실행한것은아니다. board/simulation의host·validator·source wrapper·aperture는기존tile_closed267 관측alias를정규화한뒤같은소스임을검사했다. 전체MAP입력hash,실행ELF,opcode별payload/E9,guard RTL/ELF/log hash를분석기로대조했다. `analysis01-run.log`와`analysis/joint327-verification.json`은PASS이며`git diff --check`도통과했다.

이번 구현은시간을줄였지만회로부족을10개늘려동시개선조건을충족하지못했다.327은시간개선증거로보존하되공동회로교체안은채택하지않는다.325의17,802comb/2,394부족을유지한기준과327의17,812comb/2,404부족을섞지않는다.

다음에는327 ARM 선행map 발행을325 RTL에연결한분리검증으로시간이득이유지되는지먼저확인해야한다. 이후expected ingress 저장·receipt·최종검사의주소/진행소유권까지실제로삭제할범위와포트일정을재설계한다. 현host counter가ingress에필요해남는다는측정결과를반영하며,terminal 재생만옮겨큰회로회수를가정하지않는다. 새로운회로절감예측값이나전체목표달성선언은없다.
