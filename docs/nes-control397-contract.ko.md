# NES397: 남은 본체 삭제 경계·1,017comb 예산과 911 일정 재검토

## 판정과 이번 작업의 범위

**FIFO3584B·ordinary512B·ARM frontier33·907 복구를 유지한다. 다음 교체는 host/source/plan/queue/SPI의 본체와 EA hint 실행을 한 경계로 잡는다. 단,현재 증거로 새 제어가1,017comb에 들어가거나911을 통과한다고 승인할 수는 없다.**

397은 삭제 목록·포트/문맥 배치·실제 일정 계측을 확정한R0다. 새 실행RTL·새ARM 기계어·새Quartus MAP은 만들지 않았다.396의32개RTL/ELF를 그대로 실행하고 수동 관측만 추가했다. `joint-events.csv` 전체SHA256도396 live07과 정확히 같다. 고정907 복구와911 실패 시각316.648557725ms를 모두 보존했다. 단순한 관측 성공을 시간 개선으로 세지 않는다.

## 911 실패의 실제 경로

|908 사건|시각/상태|
|---|---:|
|EA hint의 실제SS 종료|282.727902ms|
|현재 ROM 허용창 종료|282.742976208ms|
|첫 hint ROM grant|282.728798ms|
|창 종료 직전 hint cursor|21/112|
|마지막 hint ROM grant|298.255402ms|
|hint 전체 완료|298.267927ms|
|마지막 실제BG tile|298.280452ms|
|마지막 source job 수신 완료|302.361337ms|
|12view·독립 최종 검사 완료|302.389514ms|
|실제CPU 후처리610master clocks 뒤 표시 gate|302.417916ms|
|목표VBlank17의 마지막 허용 gate|298.556721443ms|
|실제 표시 실행 시작/VBlank|313.799473ms/18|

EA 종료부터 ROM 창 종료까지 **15.074208µs**밖에 없다. ARM RPC 반환282.729868ms 기준으로는13.130340µs다. 실제 ROM grant는첫 tag의16byte를끝냈고,두번째 tag 도중 다음 창으로 밀렸다. 첫 tag의grant는282.728798..282.738297ms,두번째는282.739414..298.245345ms,세번째는298.246462..298.255402ms다. 총48grant는세개tag×16byte다. 허용창 안에서 시작조차 못한 것이 아니며,첫 byte부터 전체가 기다렸다고 해석하면 틀린다.

908의 실제 hint tag는 `0213,0218,0216,0213,0213,0213,0213` 이다. 유일한tag는3개지만 wire는고정7개/28B이고 실행기는112byte를 순회한다. 뒤의중복64byte는cache hit여도hint active를유지하며 실제plan 공급을막는다. **중복 실행만 생략해도 이미 두번째tag에서 놓친 ROM 창이 돌아오지는 않는다.**

현재908 gate는VBlank17의최종시각보다 **3.861194557ms 늦다**. 이후11.381557ms를 기다린다.908의host 비대기 상태를 IDLE/EXPOSE/WAITREAD/DONE을 제외하고 모두 합쳐도 **0.067390ms**다. 이 안에는 유지해야 할 최종 검사·12view도 들어 있다. 같은 ROM grant를 유지한 채 이 시간을 전부 없애도3.861ms를 메울 수 없다. 다만ROM 경계는불연속적이므로,이를 모든 공급 일정에대한 속도개선 불가능성으로 확대하지 않는다.

입력909는908 표시와겹쳐297.611929ms부터 시작하고298.243343ms에collector 내용을local source로넘겨collector를반환한다. 그러나 **source ring full이17.579431ms** 지속된다. ARM은908의최종표시를기다린뒤909의D4 수신을본격진행한다. 그동안capture910은수락되지만source909의문맥이남아capture910의다음handoff가늦어지고,316.648558ms의capture911이실패한다. 따라서source909의collector 반환과source 전송 완료를혼동하면안된다.

## 비교한 시간 후보

|후보|실제 비용/장점|판정|
|---|---|---|
|header/descriptor/FSM만 빠르게|908의비대기상태 전체도67.390µs|면적 삭제에는필요하나고정ROM grant에서3.861ms를복구하는해법은아님|
|중복hint 순회만생략,28B wire 유지|중복cache hit시간은줄지만두번째tag miss가먼저발생|단독선택하지않음|
|ARM이실제개수1..7을보내는EA+공통NES 실행|908은28→20B,wire만24.380952µs 감소|다음공동구현후보. 새M4/실행기 비용을포함한일정은아직미검증|
|한개씩여러EA로쪼개기|첫tag를먼저보낼수있으나EA마다14B공통비용·SS/ARM/IRQ추가|별도증분준비시각을입증하지않고이득으로세지않음|
|908 표시대기중909입력수신|11.382ms 대기와입력작업을겹칠여지는있음|capture911만구하고display908의33.580ms를남길수있다.60fps 성공조건으로대체하지않음|

다음후보의시간gate는 **같은source시작/ROM위상에서908을VBlank17에표시하고,연속capture911도통과**하는것이다. count3 wire절감24.381µs는새실제완료시각이아니다. 먼저ARM이count를언제확정하는지,CRC/serializer/공통host 진입·NES tag 읽기·ROM 경쟁까지측정해야한다. 초기허용치는기존에비해추가critical work≤4µs로둔다. 이는측정한여유가아닌필터이며,새실제일정에서검증/폐기한다.14B E2 하나의wire만42.667µs이므로critical hint경로에추가poll을넣는안은이예산에맞지않는다.

cold905의마지막OBJ는66.302049ms로현재창종료까지128.741µs가남는다.907 복구보존을위해이경로의누적추가작업도기존395의잠정100µs gate를지킨다. source/plan을RAM으로옮기면서매plan마다미사용16row/8ALT를전부초기화하면이여유를소모할수있다. shortform의rows=0/ALTmask=0은mask로가리고,미사용RAM을읽거나clear하지않는방식이필요하다. 미사용RAM poison·full→short·STOP뒤늦은DONE을시험해야한다.

## 실제 삭제 경계

|현재396 self comb|삭제할본체|유지할물리/독립경계|
|---|---|---|
|host1750+descriptor checker300=2050|packet/header/record/manifests/receipt/FENCE/display 의미FSM,96bitfield bus mux,17bit 병렬/별도ALU microprogram|실제SNES read/token capture·CRC/coverage handshake·namespace burn|
|source388|record open/flush/seal·footer·D4/D5 해석/ACK/주소·head snapshot FSM|4packet RAM·Gray CDC·원래codec의block CRC datapath|
|plan356+walker20+endpoint96=472|E9/EA 완료·bank lifecycle·field decode·형식검사/retire FSM|2×512B plan RAM·seal전미공개·generation/epoch·drain|
|SPI700|184bitview·variable byte mux·별도request 필드/CRC snapshot·response lifecycle|동기화/SCK edge·RX/TX byte latch·wire수신·CRC검사|
|queue219|중복identity/header·length/completion/credit state|2×256B packet저장·독립expected RAM·저장/실제소비구분|
|EA hint155|112bit tag FF·가변tag mux·별도cursor/running/pending controller|causal hint의namespace검사·cache/ROM 요청·STOP drain|

중요한유지경계는codec1340+validator1011=2351comb,cache542·tile변환629·ROM arbiter41·FIFO538등이다. source query/core나tile datapath 전체를지웠다고세지않는다. 실제read마다공통program이문맥을fetch하도록바꾸지않는다. read_count/tap/token/주소검증·CRC ready는작은hot lane에서진행하고,program은fragment 시작/종료event만처리한다. 이hot lane과새header RAM response는아래150comb 포트예산에포함한다.

## 1,017개와 확장 경계의 예산

396 whole는 **18108=3872+2351+11885** 다. hint155를밖에그대로두면제어상한은1017이다. hint도공동실행기로교체하기위해양쪽경계를같이옮기면 **18108=4027+2351+11730**,새상한1172가된다. 이것은155개의새절감이나목표완화가아니다. 어느경계든순삭제 **2855** 가필요하고최종whole목표는15253/155여유다.

|교체영역|현재|새상한|순변화상한|
|---|---:|---:|---:|
|host+descriptor byte 실행기|2050|270|-1780|
|NES source/plan/endpoint+EA 실행기|1015|355|-660|
|SPI shift·serialCRC·IRQ|700|220|-480|
|queue credit·namespace|219|80|-139|
|tile mailbox bridge|43|43|0|
|새program/context/physical bus 포트|0|150|+150|
|예비|0|54|+54|
|합계|4027|1172|-2855|

상한은실측결과가아니다. host1750을남겨둔보조기,별도checker300,기존SPI700을그대로남기는구조는이대장과맞지않는다. SPI만그대로두어도목표보다480초과한다. body를삭제하고기능을공통program/고정포트로이전한최소경계가구현된뒤matching whole Lite로확인한다. FF도현재9033에서기준8985이하를목표로하고,RAM/ROM decode·새CDC·physical packing을함께지불한다.

## RAM·클록·소유권 계약

|물리RAM|포트A|포트B|
|---|---|---|
|source1024×8|NES record/CRC/footer write|host D4 read/footer load|
|plan1024×8|host E9 write|NES field read|
|queue1024×8|host SPI ingress/scratch R/W|host packet/독립expected R/W|
|tile metadata1024×8|host prefill/stamp/context/status/header response|NES mailbox write/source·plan context|
|payload4096×8|host tile prefill/ordinary write|SNES 실제read|
|공통control512×18 제안|host instruction/data 접근|NES instruction/data 접근|

한포트에두개의`always` 소유자를추가하지않는다. metadataA는payload copy의read→write쌍단위로yield하고,source header·SPI reply prefetch·문맥접근은tagged response를갖는다. queueA의ingress가우선이며scratch는byte사이빈clock에쓴다. metadataB의tile write와문맥접근도중재한다. source write와plan read가이번905..908에서동일NES edge에겹친관측은0이지만,이들은별도RAM포트를계속쓰며이결과를모든frame의무료공유로확대하지않는다. host ingress와packet read는cold905/906에서4/3 edge가겹쳤다.

실제주소표는검증JSON에byte단위로둔다.

- metadata800..927 host128B: record/view12,lease12,DMA cursors16,seed4,queue counters8,source head8,status2×24,manifest/dispatch16,saved PCs4. record/view alias는모든source·stamps·독립검사가끝난뒤만허용한다.
- 928..959 NES source32B,960..1023 NES plan64B. plan은16row를byte로정규화하고8ALT tag를16bitword로둬wide variable mux를없앤다. shortform/ALTmask로미사용필드를가린다. hotrow/tag·재개문맥의cycle 상한은구현후검증대상이다.
- queue472..511의현재미사용40B에SPI request/CRC checkpoint/scratch를둔다. expected0..471과packet512..1023을침범하지않는다.
- 제안control RAM은0..503 instruction,504..511을7개EA tag용data word로분리한다. **host tag write는instruction fetch를한cycle빼앗고,NES tag read도자기fetch를한cycle빼앗는다.** 세번째포트가아니다. hardware에서code write·data영역실행을막고CRC/namespace/seal후만EA를실행한다. plan과hint를동시에보존할때문맥RAM에14B를무료로중복시키지않는다.

control64×24를512×18로대체하는RAM 산술은 **310112−1536+9216=317792bits** 다. 새program은아직작성/assemble하지않았고physical M9K packing도미검증이다.504word에안들어가면1024word등의확장을검토하되RAM·decode·포트latency를다시지불한다.512word/4KiB를절대제한으로삼지않는다.

## 공통 실행기와 응답의 필수 동작

host84MHz와NES 클록에각각PC/재개문맥을둔다. program은공유해도clock을직접섞지않는다. 8bit ALU로bounds/CRC/field 동작을직렬화하고큰17bit별도검사기를남기지않는다. SPI CRC8/16만공유직렬화하며별도clock의source block CRC나독립validator CRC까지무료로공유한다고세지않는다. allocation/last_serial32bit 두개는STOP에서초기화하지않는hot namespace로남기며queue/namespace80comb 예산에포함한다.

다음은초기시간상한이지새측정값이아니다: host SPI byte service≤128clocks(256clocks/byte 안),새논리상태·accepted/status publication≤128clocks,header RAM response≤8clocks,fragment event≤24clocks,실제DMA byte는program을거치지않음. NES cache/read의6clock local hot handshake를유지하고source footer는byte경계에서yield한다.6clock은ROM 허용창/메모리응답대기를포함한전체latency가아니다. 희소row/ALT를program에서매번순회하거나clear하지않는다.

status는두24B bank에완료된coherent version으로발행한다. command 시점의bank를SS끝까지고정하고,쓰는중인bank를노출하지않는다. 한transaction에서두bank가모두보호되면추가snapshot은dirty로묶어SS후재발행한다. 실제DMA진행과working context update를그때까지멈추는방식은아니다. accepted 카운터는다음command에반드시정확해야하며retired/consumed는미래진행을광고하면안된다. IRQ는미발행dirty 상태/발행version을구분하고,SS·EXTI·WFI 경주/epoch wrap을기존actualM4로검증한다. old49bit key를16bit version으로줄이는경우에는미관측publication<65536의유한queue 상한을별도로입증해야하며,현재예산의실측절감으로세지않는다.

variable EA는hint count1..7/정확한길이`14+2n`/CRC16과기존7B retire EA를SS완료에서구분한다. 입력generation·epoch·serial은causal prelease에일치해야한다. STOP은program실행을기다리지않는공통gate로write/publication을즉시차단하고ROM응답을drain한다. namespace burn·늦은DONE·부분fragment·최종fence·12view·PPU/VBlank ACK는그대로검증한다.

## 다음 구현과 승인 gate

1. 위삭제대장과RAM배치대로host/SPI/queue 및NES/source/plan/EA 본체를대체한다. 기존body+새adapter 형태는제외한다.
2. 변수EA와actualM4의count 확정·serializer·IRQ·credit을연결한다. wire절감24.381µs를전체시간절감으로확정하지않는다.
3. 396의19guard/STOP·선점·FIFO wrap·독립bitmap/CRC·actual65816 경로에새snapshot/포트/poison/variableEA 오류를추가한다. ABI가바뀌면CPU와native service도다시바인딩한다.
4. 동일ROM phase/source시각에서cold907복구,908 VBlank17,연속911을함께확인한다. capture만살리고33ms 표시를남긴결과는60fps gate를통과하지못한다.
5. 같은기능RTL/actualM4/nativeROM의whole Lite가15253comb와RAM·FF 상한을충족하는지본다. 미달이면opcode/seed/FIT 반복대신ROM 중재·역할·하드웨어용량을재비교한다.

현재실측whole는396의22872LE/18108comb/9033FF/310112bits다. 새면적·새시간개선은없고FIT/STA도없다. fullresident/audio/input/WCET·정상STOP복귀·71heavy7·다중ROM위상·MMC4/5·실기60fps는열려있다. production375RTL/377ARM/227/GBC164/saveSRAM과PR132 draft를보존한다.
