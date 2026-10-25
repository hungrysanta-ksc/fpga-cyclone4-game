# NES302 — 재개 가능한 OBJ 계산과 공통 packet reader 검토

PR131의 후속 구현이다. 미채택301의 BG-DMA gate 위에 쌓지 않고 ARM296/RTL300에서 시작한다. production227/GBC164/saveSRAM을 유지한다.

## 실제 ARM 변경

OBJ의 rank/object 위치와 초기화 여부를 보존한다. 초기 OAM·448B scratch clear를 한 번만 실행한 뒤 반환하고, 이후 한 호출은 최대16개 후보 검사 또는 하나의 완전한 fragment 처리 후 반환한다. fragment 안의 palette epoch 처리, rank/evaluation 검사, resident slot, OAM 및 plan record는 한 단위로 끝낸다. 중간 결과 코드는3이며 기존 BG 완료1, 프레임 완료2와 구별한다. 따라서 매 OBJ yield마다 BG0x87을 다시 발행하거나 mixed batch 예약을 지우지 않는다. 초기화/STOP/cancel에서 continuation을 지운다.

완성된 plan record만 append하고 기존 batch sorting/reservation을 유지한다. 더 일찍 보내려고 불완전 batch를 flush하지 않는다. 그래서 slice가 끝났다고 즉시 새 E9가 생기는 것은 아니다. BG 완료 표식과 frame END의 의미도 유지한다.

대기 원인을 status 호출에서 명시한다. credit 대기는 응답 후 pending<4이면 계산 없이 복귀한다. drain은 pending==0이면 복귀하고, phase 대기는 요청한 bit가 준비되면 복귀한다. DMA-ready bit가 켜졌으면 다른 대기 중에도 OBJ 계산을 건너뛴다. 검사된 E2 progress를 먼저 반영한 뒤 계속 기다려야 하는 경우에만 한 slice를 실행한다. planner 안에서 재귀 SPI를 호출하지 않는다. 이는 협력적 재개이며 실행 중인 fragment 내부를 강제 중단하는 구현은 아니다.

raw patch·CGRAM·최종 resident prepare는 최종 단계에 남는다. OBJ slice의 최대 시간을 이 최종 단계 또는 전체 planner의 최대 지연이라고 부르지 않는다. foreground도 증분 step 사이에 실제 tile dispatch/refill을 수행하고 ARM 명령·추가 checkpoint 비용을 모두 일정에 포함한다. iteration bound는 기존32에서2048로 확대하지만 성공 판정은 유한 종료·바이트 동일성·최종 ACK로 한다.

## 공통 packet reader·descriptor·receipt 교체의 구체 경계

현재 queue 주소는 `NORMAL ? SNES address : exec_busy ? packet_at : parser_address`다. host의 HREAD/HCAP와 validator의 E_READ/E_CAP는 같은 registered RAM을 읽지만 수명은 다르다. 하나의 reader로 바꾸려면 다음 전이를 함께 교체해야 한다.

|단계|reader/저장 소유자|제거할 기존 상태|유지할 조건|
|---|---|---|---|
|head 획득|공통 reader|host HREAD/HCAP의 독립 read pipeline|head immutable,4credit,identity2..9 검사,CRC admission|
|header 해석|checked descriptor view|host opcode별 반복 start/end/length 해석과 header index mux|원본 header는 queue에 유지, overflow/domain/alignment, map batch의 범위별 정보|
|internal manifest|같은 reader의 continuation|별도 packet_at reader와 XBEGIN/XWAIT completion relay|encoded cursor·expanded cursor·RLE remaining·checked_byte는 서로 다른 상태이므로 유지|
|ordinary DMA|SNES가 read port 소유|공통 reader를 정지시키고 재개 위치만 유지|실제 읽힌 바이트 CRC tap,read_count,token,receipt,순서 검사|
|receipt/retire|독립 validator와 head owner|host의 중복 완료 relay|receipt commit 전 credit 반환 금지,STOP 최우선,최종 seal/12reads/ACK|

NORMAL 중 SNES 주소가 바뀌는 동안 공통 reader가 내부 바이트를 읽으면 read latency/tag가 오염된다. 다음 후보는 NORMAL 동안 reader를 완전히 정지시키고, 마지막 consume/receipt 후에만 소유권을 반환한다. pending read의 취소 또는 drain 한 cycle을 명시해야 한다. ACK를 먼저 반환하여 port를 얻는 방식은 제외한다.

header[0..20] 중 identity2..9는 이미 비교 후 저장하지 않는다. 따라서21B를 새로 제거할 수 있다고 계산하지 않는다. 일반 header는 opcode/section/start/length/expanded, typed는 token/batch count가 필요하다. checked record를 추가하면서 이 기존 값을 함께 남기면 비용이 늘 수 있다. 원본 packet bytes는 SNES와 독립 검사의 근거로 유지하고, 신규 record는 기존 실행 레지스터의 대체여야 한다. RAM cursor 공유만으로 crc_mask/receipt walk/manifest expanded 상태를 없앨 수 없다.

whole Lite 기준17678comb,고정 출력 경계4827,밖12851,경계 한도2557이다. host+validator3413만 바꾸고 queue/plan/SPI/glue1414를 유지하면1143 이하가 필요하다. 즉 reader의 read/capture 두 쌍이나8/9bit cursor 하나를 합치는 것만으로2270comb 순절감을 주장할 수 없다. **공통 reader 구조는 이번에는 설계 검토만 했으며 새 RTL·합성 절감값은 없다.** 제거 후보와 유지 상태를 위처럼 확정했지만 전체 executor/control 교체의 합성 예산을 만족할 근거는 미확정이다. 같은 RTL의 MAP 반복이나 독립 검사의 삭제로 부족분을 없애지 않는다.

다음 RTL 후보는 ingress/header admission→공통 reader continuation→DMA port handoff→독립 receipt commit을 하나의 소유권 표로 구현해야 한다. 동시에 source/NES plan과host/SNES read가 공유하는 포트 비용, 정지된 reader의 descriptor 안정성,STOP pending read 폐기,최종 ACK를 검사한다. 기존 압축 packet과4credit/2planbank를 유지한 전체 교체 비용이2557 이하인지 확인하기 전에는 예상 시간·LUT를 숫자로 채우지 않는다.

## 검증과 증거의 구분

actual ARM의 정상/제한905..907, native71, 각 OBJ yield에서 STOP, 실제 IRQ 재개, H2 및 IRQ guards를 실행한다. 새 live 원본 E1/E9 byte/order, metadata·receipt·CRC,credit≤4,finish/final ACK/commit을 기준298과 비교한다. slice 때문에 checkpoint 수가 늘 수 있으므로 실제 foreground step 수+1과 비교하고 고정31을 강요하지 않는다.

RTL300은 변경하지 않는다. 기존 whole Quartus Lite300과44RTL guards의 소스를 새 live 소스 해시에 연결한다. 새 MAP/FIT/STA 또는 새 RTL negative 실행으로 세지 않는다. 시간 모델은 source replay,CPI1/84MHz,실제 M4 IRQ body+entry/exit24cycle,실제 SPI/tile ROM arbiter,ordinary65816 trace 및 map/tile/display bus 모델이다. physical MCU WCET/fullRUN/전체 live65816/최종71일정/실물60fps가 아니다.

test01은 initialization scope의 미사용 evaluation 포인터 때문에-Werror 컴파일 실패했다. 지역 변수 선언만 수정했다. test02는 DMA-ready 우선 버전이고, 이후 credit/drain/phase 사유까지 구분한 window01/test03과 분리하여 보존한다. 정상과 제한은 최종 실행 이미지의 PT_LOAD 주소·크기·바이트가 동일한 경우에만 같은 후보로 비교한다.


### WFI 전 대기 활용 보완(302b)

한 E2마다 slice 하나만 실행하는302는 다음 WFI에서 나머지 계산을 멈춰 두었다. 제한907 첫 OBJ plan이275.212038→276.230390ms로1.018352ms 늦어졌고, tile 시작은291.149302ms까지 지연되어 전체31.843436ms가 됐다. BG tile 완료 시각은 기준과 같아 이 경우 source/BG 변환 지연으로 설명하지 않는다.

302b는 같은 bounded slice를 반복하되 각 경계에서 실제 PB8 progress GPIO를 읽는다. pin이 올라오거나 pending planner가 끝나면 즉시 반환하여 기존 SPI/credit 처리를 계속한다. 최대2048회 방어 한도를 둔다. 무조건 polling packet을 반복하거나 CPU 두 개가 동시에 실행된다고 가정하지 않는다. planner가 생성한 batch의 전송은 기존 refill 소유자가 맡는다.

실행 harness는 실제 progress302 함수 진입에서 지금까지의 ARM 명령/IRQ 비용을 RTL clock에 반영하는 non-SPI checkpoint를 추가한다. 그 후 GPIO를 갱신하고 컴파일된 MMIO read/분기를 실행한다. 이를 하지 않으면 계산 중 FPGA가 정지해 pin이 영원히 옛 상태로 보이는 잘못된 시뮬레이션이 된다. checkpoint는 새 전송 바이트가 아니며 모든 경과 명령과 IRQ 진입/복귀 비용은 기존 ledger에 포함한다. 실제 하드웨어의 연속 실행을 instruction-boundary로 근사하므로 실물 WCET 주장에는 사용하지 않는다.


### 실제 sleep 이전으로 연결(302c)

302b는 반복 slice의 정상 동작을 확인했으나 WFI 앞의 실행 기회를 모두 사용하지 못했다. 302c는 E2 진입에서 기존 refill/WFI보다 먼저 bounded work를 수행한다. 응답 후에도 같은 helper를 사용한다. 새 plan이 생성되면 이어지는 기존 E9 refill loop가 먼저 공급한다.

status259는 새 E2 송신 전0으로 지워지는 in/out buffer이므로 이전 phase 판단에 그대로 사용하면 안 된다. CRC·counter 검사가 통과한 progress282의 phase를 phase_ready302에 별도로 보존한다. reset과새 E1 제출 후에는 지우고 새 유효 응답에서 갱신한다. credit은 현재 sent/retired 차이로 판단한다. E1 응답 snapshot을 현재 E1의 완료로 취급하지 않는다. DMA-ready/진행 pin이 있으면 계산보다 응답 처리를 우선한다.

별도 사전 build01은 필요한 baseline C 준비 없이 build_rom을 호출하여 실패했다. build02는 제한 환경의 compiler DLL 실행 오류,build03은 다른 baseline builder를 사용한 transformer anchor 불일치로 실패했다. 모두 보존하고 측정에 사용하지 않았다. 최종 test05/window03은 원래 live harness의 동일한 준비·빌드 순서를 사용한다.

## 최종302c 결과

|조건/frame|298 ms|302c ms|차이 ms|
|---|---:|---:|---:|
|normal/905|79.689998254|79.720816066|+0.030817812|
|normal/906|56.212189082|56.253234044|+0.041044962|
|normal/907|15.473814312|15.429905748|-0.043908564|
|restricted/905|104.876059654|104.883650472|+0.007590818|
|restricted/906|116.900688084|116.901188078|+0.000499994|
|restricted/907|17.468381286|17.462790444|-0.005590842|

정상907은43.909µs,제한907은5.591µs 개선이다. 제한907 초과는0.796123777ms이며 기존0.801714619ms의 약0.70%만 회복했다. 제한907 source 관측도1host cycle(45.454ns) 차이가 나므로 전체5.591µs를 모두 ARM 계산 절감이라고 부르지 않는다. 정상905/906 및제한905/906은 회귀한다. **302c는 공동 목표 해결안으로 미채택**하고 ARM296 기준을 보존한다.

정상 세 프레임과 제한907의 첫 유효 service는 BG prefix 송신 후였다. 제한905는594B 중428B,906은594B 중536B에서 시작하여 각각166/58B가 남았다. 이 사실만으로 bank가 writable이었다고 단정하지 않는다. 그러나 queue credit/phase/IRQ만 보는 현재 helper에는 `미송신 BG + planbank writable이면 E9 우선`을 명시하는 gate가 없으므로, 모든 경우의 BG 공급 우선순위를 입증했다고 주장할 수 없다. 다음 교체에서는 이 조건을 실제 plan credit과 함께 모델링해야 한다. 이 관측을 숨기고907 결과만 채택하지 않는다.

OBJ yield 최대4556명령(약54.238µs)은905..907의 관측값이다. wrapper service에서는4580명령이 관측되며, 마지막 palette/raw/resident 단계는최대31275명령(약0.372321ms)이 별도로 남는다. 전체 처리의 최대 지연이54µs라는 주장은 하지 않는다. ARM text27858B는296대비+400,BSS47120B는+20,live observed stack1288B는 동일하다. native-only observed stack은 별도 수치다.

최종6live에서 E1/E9 bytes/order,metadata8570B·receipt754B·CRC64B,4credit,map receipt64/64/7,최종ACK/commit PASS. fresh native71/1039commands/73260B/fixture0,producer6negative,35개 OBJ yield STOP,11개 IRQ 재개,credit/wrap/phase11,H2 9,IRQ8/33exceptions PASS. 이외 중간test02/test03/window01/test04/window02도 각각 보존하며 최종6live와 혼합하지 않는다.

whole Quartus Lite는 변경하지 않은300 소스22578LE/17678comb/9022FF/307808bits,부족2270comb 그대로다. 새 합성 절감0이며 새 MAP을 실행하지 않았다. 기존44RTL guards,whole source,새live 소스를459개 입력 SHA와script hash로 연결했다. FPGA 구조 검토는 실제 새 RTL 구현/절감과 구분한다.

선택 증거는test05/window03/native04/guards04/credit03/h2guard03/irqguard03/analysis03다. 분석에는단일slice302와post-WFI302b 결과도 따로 들어 있다. source replay,CPI·IRQ allocation,bus model의 한계와미실행fullRUN/full65816/FIT/STA/실물 게이트는 유지한다.

## 다음 목표

같은 단위 크기·WFI 위치의 미세 반복은 중단한다. 남은 기준0.802ms·2270comb에 비해 이번 이득은 작다. 다음은 `미송신 BG/완료표식 및 OBJ batch + plan credit + 실제 DMA-ready + queue credit`를 한 공급 우선순위 표로 표현하고, 마지막0.372ms 정리가 왜 한 단계로 남아야 하는지 함께 재검토한다. 동시에 위 packet reader/descriptor/receipt의 포트 소유권·독립검사·완료 상태를 실제 대체하는 구조 근거를 확보한다. 새 record를 추가만 하거나독립 검사를 없애는 방식은 제외한다. 현재 확인된 시간 이득을 회로 절감과 합쳐 목표 달성으로 계산하지 않는다.
