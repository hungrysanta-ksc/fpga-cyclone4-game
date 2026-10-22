# NES301 — BG 완료·DMA 공급 뒤의 OBJ 계산과 넓은 제어 교체 예산

PR131의 후속 실험이다. ARM300의 E9 직후 계산은 제거하고 ARM296에서 다시 시작했다. descriptor/RAM RTL300, 독립 검사와 압축 전송은 그대로 유지한다. production227/GBC164/saveSRAM은 변경하지 않는다.

## 실제 구현

`nes_supply301.py`는 두 조건을 추가한다. 정상 E9 전송을 마친 payload가 길이3/count1/0x87인 BG 완료 표식이면 `bg_published301`을 세운다. 일반 원본 op7/section0의 BG DMA 패킷을 전송하고 ARM sent/sequence를 갱신한 뒤 `bg_dma301`을 세운다. 두 조건 전에는 `service296`가 OBJ 계산을 하지 않는다. 두 조건 후에는 DMA 전송 직후 또는 기존 E2 대기 서비스에서 OBJ를 한 번 계산한다. 두 조건은 새 frame 시작과 STOP에서 지운다.

BG 완료 표식의 생성과 전송을 구별한다. 이전300은 첫 BG E9 뒤 내부6B(3B batch header+3B 표식)가 남아도 OBJ를 계산했다. 이번에는 실제 표식 E9 전송까지 마친다. DMA 조건도 plan 전송이나 tile-ready만으로 세우지 않는다. op7 E1 제출 후, **sent counter를 갱신한 다음** 계산한다. E1 응답은 command-start snapshot이므로 그 응답 자체가 현재 E1 admission/receipt를 증명한다고 해석하지 않는다. 기존 drain·독립 receipt·최종 ACK가 계속 성공해야 프레임이 완료된다.

실제 SPI 함수는 in/out buffer를 덮어쓰므로 op7/section0 여부는 호출 전에 지역 변수에 저장한다. OBJ 계산은 wire buffer를 다시 사용하지 않으며 후속 refill에서 새 plan을 공급한다. BG DMA가 없는 프레임은 이 gate로 계산을 당기지 않고 원래 증분 planner가 진행한다. 새 packet·planbank·FPGA RAM은 없다. ARM 상태8B와 실행 명령은 비용에 포함한다.

## 더 넓은 교체 범위 검토

현재 whole Lite17678comb 중 출력 경계4827, outside12851이다. 경계 목표는2557 이하, 128comb 정책 여유를 두면2429 이하다. 이 여유는 FIT 보장이 아니다.

|현재 own comb|실제로 대체할 수 있는 제어|남겨야 하거나 새로 필요한 비용|
|---|---|---|
|host2103|header HREAD/HCAP/CHECK, opcode별 NORMAL/OTILE/OSELECT와 internal continuation, queue 주소 선택을 단일 transaction reader로 대체|원본 SNES header view, 실제 DMA descriptor, 소비 바이트 CRC tap, token·read coverage·ACK owner|
|validator1310|공통 reader가 만든 immutable record에서 manifest/receipt 실행을 시작하고 host completion relay를 대체|원본 범위의 독립 domain 검사, persistent/fresh/map 비교, raw CRC, H2 seal와12 exact reads|
|queue129|E1 framing completion을 공통 ingress에서 발행하여 endpoint의 byte-count/admission 분기 대체|4개 immutable packet, accepted/retired 차이, packet length, parser_retire 후에만 credit 반환|
|plan576 = endpoint162 + transport414|E9 framing과 host seal/write 진행을 공통 ingress transaction으로 대체; plan decode를 host reader에 옮기는 후보|CRC16 seal, 두 bank 소유권, generation·shape 검사, tile_done까지 descriptor 유지, NES CDC와 retire handshake|
|SPI655|공통 ingress의 endpoint-specific request-field/CRC completion을 위 endpoint와 함께 재구성|이미 공유된 SPI shift/count/CRC8·status snapshot·IRQ, E1 CRC16, command-start counter 의미|
|glue54|서로 다른 owner의 completion 연결 정리|STOP/fault 우선권, source/display lease, 마지막 ACK CDC|

**queue+plan+SPI 전체1360개를 공짜로 없앤다는 불가능한 상한에서도910개가 부족**하다. glue54까지 모두 없애도856개가 부족하다. 따라서 framing/endpoint만 묶는 후보는 목표 해결안이 아니다. 반대로 host+validator만 바꾸고 나머지를 유지하면3413→1143, 즉2270개 순감소가 필요하다. 각 계층 수치는 own comb만 더하며 inclusive parent를 중복 합산하지 않는다. 위 표의 비용은 현재 측정값이고 새 구현 예상값은 미확정이다.

다음에 구현할 만한 넓은 후보는 **공통 ingress + head transaction reader + 원본 descriptor view + manifest/receipt executor**의 동시 교체다. 공통 ingress는 E1/E9 종류·길이·CRC completion을 내되 두 credit 수명은 분리한다. E1의 retire는 실제 parser/DMA receipt, E9의 bank 반환은 NES plan 인수/실행 프로토콜이며 같은 완료 사건이 아니다. opcode별 continuation을 공통 reader가 소유하고 header와 새 record를 영구 중복 저장하지 않는 설계가 필요하다. 단순히 모듈 이름을 합치거나 기존 FSM 위에 공통 FSM을 하나 더 얹는 변경은 제외한다.

### RAM 포트와 일정의 제약

현재 packet RAM은 host write+host read, plan RAM은 host write+NES read다. SPI 쓰기를 공유해도 host packet read와 NES plan read는 동시에 존재한다. 두 RAM을 한 dual-port RAM으로 합치면 쓰기와 두 읽기의 **세 접근**이 충돌한다. 두 clock을 직접 mux하거나 plan 읽기를 공짜로 가정할 수 없다. 새 arbiter/holding register/CDC 또는 plan decode의 host 이전 비용을 포함해야 한다.

우선 후보는 두 RAM과4packet/2planbank 용량을 유지하고 제어를 함께 대체하는 것이다. plan decode를 host로 이전할 때는 현재 short/full/alternate-tag·generation 검사와 NES descriptor 유지 레지스터가 사라지는지, 단순 이동인지 구별한다. host reader가 manifest를 처리하는 동안 다음 plan을 굶기면 ROM 창을 놓칠 수 있다. BG 표식과 DMA 공급을 먼저 보장하고, plan·packet 간 최대 지연을 실제 ROM 창/IRQ 일정으로 검증해야 한다. 새 arbitration 비용은0으로 계산하지 않는다.

상태 전이는 `ingress reserve → CRC/length seal → immutable head → header/identity check → payload execution → DMA consume → receipt commit → packet retire`다. E9는 별도의 `sealed bank → NES acquire → tile_done/partial close → bank reuse → final END/EA` 수명을 유지한다. STOP은 모든 단계에서 새 write/commit을 막고, final ACK는 기존 seal/coverage/token/12read/빈 owner 조건을 모두 거친다.

이번에는 이 넓은 후보의 RTL을 구현하지 않았다. 목표 규모의 절감을 입증할 제거 목록이 완성되지 않았으므로 동일 RTL의 MAP 반복으로 성과를 만들지 않는다. 후보 예상 LUT·시간은 null이며 목표 달성 주장도 하지 않는다.

## 검증 범위

새 ARM ELF의 정상·제한 ROM905/906/907 여섯 일정을 실행한다. 실제 M4 명령·IRQ·SPI·tile ROM arbiter와 기존 ordinary65816 trace를 사용하며 source timing replay, CPI1/84MHz, IRQ 진입/복귀24cycle 및 map/tile/display bus 모델은 유지한다. 실물 MCU WCET/fullRUN/전체 live65816/71최종 일정/physical60fps가 아니다.

새 gate 검사는00/10/01에서 계산 없음,11에서 한 번만 계산, IRQ 중 prefix 보존, STOP 후 gate 초기화와 append/commit 거부, DMA dispatch 실패를 확인한다. native71 및 H2·IRQ 검사도 새 ELF로 실행한다. 변경하지 않은 RTL의44개 negative guards와 whole Lite MAP은300 결과를 재사용하고 입력 해시로 연결한다. 새 RTL guards나 새 MAP 실행으로 세지 않는다. 최종 시간과 수치는 아래와 machine-readable 검증 파일에 기록한다.

## 결과와 판정

|조건/frame|298 ms|300 ms|301 ms|301−298 ms|
|---|---:|---:|---:|---:|
|normal/905|79.689998254|80.268082226|79.694134568|+0.004136314|
|normal/906|56.212189082|56.551957732|56.216825390|+0.004636308|
|normal/907|15.473814312|15.532449972|15.475223386|+0.001409074|
|restricted/905|104.876059654|104.876059654|104.878786894|+0.002727240|
|restricted/906|116.900688084|116.900733538|117.233456818|+0.332768734|
|restricted/907|17.468381286|17.468335832|17.611334116|+0.142952830|

정상907의300 회귀57.227µs는 회복했지만298보다1.409µs 느리다. 제한907은17.611334116ms로298보다142.953µs 느리고, 초과0.944667449ms다. **301은 성능 후보로 미채택**한다. 기준 ARM296/RTL300의 기존 분리 검증 결과를 유지하며 남은 기준 부족은 약0.802ms·2270comb다. 미채택301의0.945ms를 기존 기준의 개선으로 섞지 않는다.

원인은 전송량 증가가 아니다. 제한907은 ARM699344→698226명령, SPI1236→1200B, slot-wait57322→49957cycle로 줄었다. 그러나 첫 OBJ plan은275.212038→275.832713ms로620.675µs 늦게 도착했다. 앞선 BG plan/tile 시각은 두 실행에서 일치한다. 이전296이 DMA 제출 전 대기 중 수행하던49175명령의 OBJ 작업을,301은 DMA 제출 뒤49181명령으로 수행하여 기존 겹침을 잃었다. 제한906에서도 마지막 OBJ tile 시작이210.287317→210.619177ms로331.860µs 늦어졌다. ROM 창·aperture·DMA 순서가 결합된 일정이므로 SPI나 ROM wait 감소를 전체 시간 감소로 환산할 수 없다. 이 시각은 연속905..907 fixture의 timestamp이며 독립 프레임 WCET가 아니다.

모든6 실행에서 원본 E1/E9 payload와 순서가298과 정확히 일치하고4credit, map receipt64/64/7, metadata8570B·receipt754B·CRC64B와 최종ACK/commit이 통과했다. service 완료6건 모두 BG 표식 prefix 전송 완료와 BG DMA 제출 조건을 확인했다. fresh native71(1039commands/73260B/fixture0),producer6negative, 공급/STOP9,H2 9,IRQ 8 검사가 통과했다. native의 dispatch는 intercepted sink이므로 live6와 구분한다.

ARM text27586B는296대비+128,300대비+96이다. BSS47108B는+8, live observed stack1288B는 동일하다. whole Lite는 **기존300 결과**22578LE/17678comb/9022FF/307808bits 그대로이며 새 RTL/MAP은 없다. 소스 해시와 기존44RTL guards, whole 입력 및 새 live 소스를 연결했다. 검사·합성의 기존 출처를 새 실행으로 세지 않는다.

analysis01은 서로 다른 빌드 경로의 ELF 전체 파일 해시가 동일하다고 잘못 가정해 실패했다. analysis02에서 로드되는 PT_LOAD 주소·크기·바이트를 비교하여 동일 실행 이미지를 확인했다. 두 ELF 파일 해시는 각각 보존하며 조건을 생략한 것이 아니다. 원본 실패 로그도 보존했다.

## 다음 구조 선택

원자적인 OBJ 한 단계 전체를 E9 직후나 DMA 뒤로 이동하는 두 방식 모두 공동 목표를 해결하지 못한다. 다음은 **OBJ 계산을 중단 가능한 작은 단위로 나누고**, BG 완료 표식 송신과 DMA-ready/credit 처리를 먼저 수행하며 실제 대기 구간만 사용하는 후보를 설계해야 한다. 단위 크기와 IRQ 재진입/예약 상태·worst gap 비용은 측정 전 미확정이다. 계산을 잠시 중단하는 것과 planner 상태를 처음부터 재실행하는 것을 구별하고, append-only plan prefix·mixed batch 예약·STOP 불변식을 유지해야 한다.

회로는 위 공통 ingress/head reader/descriptor view/manifest·receipt 실행기를 함께 대체하는 old/new 저장·포트·전이표를 먼저 확정한다. 임의의 목표 배분만으로2557comb에 들어간다고 추정하지 않는다. 실제로 제거할 중복과 새 arbiter·CDC·독립검사를 포함한 근거가 나오기 전 동일 또는 소규모 FSM MAP/FIT 반복은 하지 않는다. fullRUN/full65816/FIT/STA/실물60fps는 계속 미검증이다.
