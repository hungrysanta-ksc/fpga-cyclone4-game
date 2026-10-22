# NES306 — ingress·후반 DMA·manifest 공동 교체 계약

## 결론과 증거 범위

이번 단계는 **구조·예산 확정과 기존 실행 자료 재분석**이다. 새 RTL/ARM 실행이나 Quartus 합성을 하지 않았다. 구현 후보의 예상 면적·재배치 일정은 null이며, 305의 실측 부족 **0.796123777ms / 2209comb**는 아직 해소되지 않았다. 생산227/GBC164/saveSRAM과 ARM296/RTL300 기준을 보존한다.

채택할 다음 실험 범위는 **공통 ingress admission + 소비 기반 실행/retirement + 마지막 DMA 뒤 manifest 선행 큐잉**이다. requirements 압축은 이 경계 안에서 기존 map RLE 실행기를 재사용하는 보조 수단이다. 독립 검사를 생산자 승인bit로 바꾸지 않는다. 단독 queue/FSM/record 미세 최적화로 돌아가지 않는다.

분석기는305의396개 입력 SHA를 재검증하고, 실제 native71프레임 terminal op3에서166B requirements를 추출한다. ARM serializer가 이를 op15와 최종16B op3로 나누는 관계를 제한907 wire payload와 비교했다. 초기 분석01은 native 파일에 op15가 있다고 잘못 가정하여 assertion 실패했다. 수정 후 analysis02는71원본+18경계 codec roundtrip/5잘못된 stream 거부를 통과했다. 이는 Python 모델 검사이며 새 FPGA 검증 횟수가 아니다.

## 실제 삭제·유지·대체 경계

|305 기존 책임|306 대체 책임|반드시 유지할 것|
|---|---|---|
|queue admission, plan endpoint의 can_write/ended/retiring, 중복 SS 종료 길이·CRC 조건|host clock의 단일 transaction admission: destination/length/sequence/CRC 결과를 한번 commit|출력4credit과 plan2bank는 별도 자원. 미완성 packet은 비공개; STOP 중 commit 금지|
|SPI270 count와 request fields를 각 endpoint가 재해석|공통 byte event에서 목적지별 제한을 검증하고 commit event만 발행|270은 이미 bit/count를 공유한다. 이를 새 절감으로 세지 않음. source D계열·E1·E9·EA 각 CRC domain 유지|
|E1 payload CRC16 및 plan batch host CRC16의 별도 병렬 datapath|한 transaction 동안 선택된 CRC16 accumulator, 목적지별 시작·포함 범위 명시|같은 polynomial이어도 E1 command 포함과 E9 payload-only는 다름. CRC8 request/status와 교환 순서도 보존|
|host header/body reader와 validator 내부 packet cursor/완료 relay|305 active record를 받는 단일 실행 owner와 consume 완료 event. HEADER→BODY→WAIT_CONSUME→CHECK→RETIRE|서로 다른 clock의 FSM을 하나의 reg로 묶지 않음. validator의 수치 bounds·실제 소비 CRC·coverage 독립성 유지|
|plan_spi200 seal/retire relay와 transport206 host admission 중복|공통 admission에서 plan bank seal 발행; NES측 decoder/shape 검사·tile_done 소유권은 유지|generation, BG 부분완료와 frame 종료 구분, mailbox acknowledgement, alt tag/row 검사|
|op15 display+166raw 요구량, op10/11 map 검사 경로|24B display 독립 비교 유지;166B 요구량과256B map에 같은 bounded zero/literal decoder 사용|도메인166/256은 타입에서 결정, 외부 길이로 검사 범위를 축소 못 함. raw fallback 포함|
|모든 DMA retire 뒤 manifest 생산·전송 대기|마지막 DMA packet의 **accepted sequence 확정 뒤**, 다음 빈 output credit에 manifest enqueue|DMA 앞에 삽입하지 않음. 소비·coverage 검사는 queue head가 된 뒤 수행. 최종 ACK 앞당김 금지|

새 generic microcode ROM/추가 실행 엔진을 기존 FSM 옆에 더하지 않는다. 각 새 책임이 들어갈 때 표의 기존 상태·counter·port mux를 제거한 diff가 필요하다. 원래 source 기능이 공유 SPI 밖으로 이동하면 그 비용도 whole 결과에 포함한다.

### RAM·CDC 소유권

- 기존 output queue와 plan RAM은 각각 유지한다. plan 대기를 output FIFO head에 넣으면 뒤의 DMA와 서로 기다릴 수 있으므로 단일 FIFO로 합치지 않는다. shared ingress는 SPI 한 transaction의 쓰기 대상만 선택한다.
- 출력 queue write port: SPI admission만 소유. read port: head의 실행 owner 하나만 사용. ordinary SNES 읽기와 validator 읽기는 동시 요청하지 않도록 명시적으로 인계하며, 인계 전에 기존 pending read를 마친다.
- plan host write port: 비공개 writer bank만 쓰고 exact length/CRC 검사 뒤 seal. NES read port는 sealed reader bank만 읽고 tile_done까지 decoded plan을 유지한다. 이 clock-crossing ownership을 무료로 제거하지 않는다.
- validator phase RAM의 receipt/hash/coverage 쓰기와 display 읽기 순서는 기존대로 유지한다. expected manifest를 별도 RAM에 미리 풀어두지 않고 기존 queue에 압축 packet 상태로 보관한다. 추가 RAM 요구0은 설계 제약이며 새 합성 결과가 아니다.
- 전송 accepted는 DMA 완료가 아니다. packet slot은 마지막 실제 consume와 독립 검사 완료 후 반환한다. 부분 batch 중에는 token/credit을 재사용하지 않는다.

STOP은 ingress commit·RAM write·DMA 후속발행을 차단하고 모든 in-flight owner를 취소한다. sticky first fault를 cancellation reset으로 지우지 않는다. 재개 시 bank/generation/token 규칙 및 quiesce를 유지한다. SEAL은 모든 receipt/coverage/H2를 확인한 뒤 허용하고, 최종 ACK는 기존12회 정확한 display read와 표시 완료 조건 이후에만 허용한다. EARLY_MANIFEST는 전송만 앞당기며 SEAL/ACK의 의미를 바꾸지 않는다.

## Quartus Lite 전체 비용과 요구 예산

305의 whole MAP은22452LE/17617comb/8997FF/307808bits다. 아래 값은 inclusive parent/child 합산이 아닌 own 비용이다.

|경계|305 실제comb|306 기능 상한 — 예상치 아님|
|---|---:|---:|
|queue+SPI|784|425|
|plan endpoint+transport|577|300|
|host 실행·receipt|2087|750|
|독립 validator|1250|886|
|glue|48|48|
|기능 합계|4746|2409|
|정책 여유|0|128|
|기능+여유 상한|4746|2537|

밖12871+상한2537=15408. 여유 없이2209comb,128여유 포함2337comb(경계 약49.2%)을 더 줄여야 한다. queue+SPI+plan은 **1361**comb다(305 문서 마지막 문단의1360은 합계 오기). 이 영역을0으로 만들어도848comb 부족하다. 그대로 두면 host+validator 허용량은1128인데 현재3337이다. 따라서 ingress만 바꾸거나 validator를 그대로 두는 작은 변경의 면적 낙관치는 사용하지 않는다. host 목표750 역시 현재보다1337 감소를 요구하는 공격적인 상한이지 합성 예측이 아니다.

외부12871도 다음 whole mapper에서 달라질 수 있다. 기능2409 달성만으로 FIT를 선언하지 않고 **전체≤15408−128=15280comb** 여부를 다시 확인한다. LE/FF/RAM/clock/FIT/STA는 별도 gate다. 새로운 실제 구조가 없으므로 이번에는 같은 RTL을 다시 MAP/FIT하지 않았다.

## BG ROM 허용 구간을 포함한 일정

제한907의 plan cycle5991825,phase273937이며 ROM period357368,window330088≤phase<354640,세부slot은전역cycle%12==3이다. 최초 miss 요청272.352618ms→승인274.905042ms→첫tile274.905315ms. core 우선권과 window는 유지한다.

이전 window의 마지막 세부slot은 cycle5715159다. 그것만 잡으려 해도 plan을 최소276666cycle,**12.575576ms** 앞당겨야 한다. 그 마지막slot이 BG5개 전체를 공급할 수 있다는 뜻도 아니다. source COMMITTED 이전 speculative fetch는 별도 lease/cache/STOP 증명이 필요하므로 이번 후보에서 시간 이득으로 계산하지 않는다. 수십µs 조기 계산은 현재 첫 BG miss의 허용 시점을 바꾸지 못한다.

|제한907 관측 시점|절대ms|변경의 제약|
|---|---:|---|
|BG 첫 plan|272.352573|ROM window 대기 유지|
|BG 첫 tile|274.905315|이후 최종까지6.434445ms|
|마지막 map consume|277.960659|실제 receipt를 생략하지 않음|
|마지막 일반 DMA packet 전송 끝|279.213503|이 뒤 빈4credit 안에서 manifest 발행 후보|
|tail range receipt|280.051192|기존 timer fallback과 실제 소비를 구분|
|manifest 직전 ARM 응답 끝|280.097084|현행 drain barrier 지점|
|209B manifest 전송 끝|280.889583|전 구간0.792499ms에는 ARM과wire 포함|
|42B map manifest /19B SEAL 끝|281.070678 /281.178131|같은 ordered stream 뒤에 유지|
|최종 완료|281.339760|source+output17.462790444ms|

실제 마지막 DMA enqueue부터 현행 manifest 발행 전까지0.883581ms의 후보 구간이 있다. **빈 credit이 그 전체 구간 동안 존재함을 현재 로그는 증명하지 않는다.** 새 ARM이 manifest를 생산할 수 있는 시점, IRQ 응답 latency, serial SPI 점유와4credit별 accepted/retired 시점을 실행 계측해야 한다. 먼저 DMA를 전부 제출하고, 빈 credit 발생 시 manifest를 뒤에 붙여 consumer와 겹친다. 마지막 DMA보다 먼저 manifest를 head에 놓는 재정렬은 금지한다. E9/OBJ가 남은 cold 프레임에서는 DMA/plan 공급 우선권을 유지하고 prequeue를 연기한다.

후반 일반65816 service6개의 합은2.088183883ms이나 ARM/SPI와 겹친다. 이를 그대로 절감 예산에 더하지 않는다. 첫BG→마지막ACK 구간도 모두 제거 가능한 직렬 비용이 아니다.

## 시간 후보 비교 — 실측과 감도 계산 구분

166B requirements를 기존 map과 같은 zero/literal run 형식으로 재구성했다. run은1..128,tag bit7=zero,나머지+1=count.24B display·16B header·E1·CRC16은 유지하고 codec byte1을 **추가로** 계산했다. 새 numeric opcode/version은 실제 ARM/RTL 호환 변경 시 확정한다. raw fallback은166+codec1이며, 압축이 항상 유리하다고 가정하지 않는다.

71개 실제 입력은 새64..87B/총9708B 절감 모델이다. 제한907은requirements166→20B,packet SPI209→64B로145B 감소한다. 원본 semantic bytes는 모두 같으며 decoded166/256 exact count, truncated literal, overrun, trailing run은 거부한다. map manifest42B와최종SEAL19B는 이 수치에 포함하지 않는다.

|후보/감도|확인한 값|목표에 대한 판단|
|---|---|---|
|305 유지|17.462790444ms/17617comb 실제|0.796123777ms/2209comb 부족|
|requirements 압축만|145B×3.047619µs=0.441905ms wire 감도|다른 시간 고정 시0.354219ms 남음. ARM codec 비용·IRQ·ROM phase 변화 미측정|
|manifest 발행 구간 전체 무료|0.792499ms 낙관 가정|그래도0.003625ms 부족;0.25ms 여유까지는0.253625ms 부족|
|공통 ingress+선행 큐잉+공통 manifest 실행|0.883581ms 후보 overlap 구간, 면적기능2409 요구|실행 가능 credit와 생산시점 검증 필요. 예상ms/comb=null|
|이전 BG ROM window 이용|최소12.575576ms 조기 공급 필요|현재 국소변경 후보에서 제외|

압축으로 줄인wire는 manifest 발행 구간 안에 포함되어 있다. **0.441905+0.792499를 더해 해결로 선언하지 않는다.** 새 구조는 최소0.796124ms, 정책여유 포함1.046124ms의 실제 net gain이 필요하다. SEAL·map manifest의 반복 transaction/ARM 상태 진행을 함께 줄이는 것은 다음 실행 대상이며 최종ACK 조건 제거로 대체하지 않는다.

## 다음 구현·검증 gate

1. ARM에서 마지막 DMA accepted 뒤 manifest를4credit에 선행 발행하고, accepted/retired/ready/IRQ/SPI 시각과 immutable producer snapshot 시각을 로그로 남긴다.305 RTL 기준으로 재배치 효과를 먼저 분리하고 cold905/906 회귀를 숨기지 않는다.
2. 위 공통 ingress·CRC domain·실행 owner·bounded manifest decoder를 실제로 교체한다. CRC 오류/partial SS/길이overflow/zero-run 경계/STOP 각phase/token wrap/재사용/BG부분종료/최종12read에 대한 기존44검사와 새경계 검사, native71 바이트 동등성을 수행한다. Python89+5는 이를 대체하지 않는다.
3. 같은 소스의 정상·제한905/906/907 실제 ARM/IRQ/ROM 일정과 fresh whole Lite MAP을 함께 비교한다. 전체comb와시간 양쪽 gain이 없으면 후보 승격을 중단한다. full71/heavy7/fullRUN/live65816/FIT/STA/실물60fps는 후속 gate로 남는다.
