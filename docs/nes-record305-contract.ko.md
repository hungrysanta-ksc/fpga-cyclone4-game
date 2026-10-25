# NES305 — active record와 page 주소 실행 교체

PR131 / `codex/nes-architecture-budget-299`. 기준 회로는 RTL300, 시간 비교는 ARM296/RTL298이며, ARM303을 유지한 동일 일정과도 별도로 비교한다. 생산227/GBC164/saveSRAM은 변경하지 않는다.

## 판정

header·typed descriptor 중복 저장을 실제로 대체했고 whole Lite는 **61comb / 126LE / 25FF 감소**했다. 정상·제한 ROM 905/906/907 전체 일정은 ARM303 경로와 정확히 같았다. **회로의 작은 순절감은 확인했지만 추가 시간 개선은 없으며, 60fps·board 적합성 후보로 승격하지 않는다.** ARM296/RTL300 기준은 보존하고 이 변경은 검증된 부분 교체로 보관한다.

제한907은 17.462790444ms, 60Hz 예산보다 **0.796123777ms 초과**한다. comb는 17,617로 기기 수량15,408보다 **2,209개 부족**하다. 304에서 요구한 전체 경계 교체는 아직 달성하지 못했다.

## 실제로 없앤 것과 남긴 것

- 쓰기 가능한 `header[0:20]` 배열과 별도 typed `length/first/count/token/remaining` 저장을 packed active record로 대체했다. 기존 이름의 header는 record의 조합 배선 별칭이며 별도 저장소가 아니다. identity2..9는 기존대로 입수 즉시 비교하고 저장하지 않는다.
- op·section·byte start·encoded length·span·token·batch remaining을 한 record에 둔다. typed first/count/length는 그 record의 배선 변환이다. op12의 word start는 admission에서 byte start로 한 번 정규화한다.
- 일반 명령의 end와 section별 receipt first/end를 admission에서 계산·보관한다. 실행과 CRC tap은 보관된 end를 사용한다. 원본 overflow/alignment/domain 검사는 admission에서 유지하고 validator는 독립 범위 검사를 수행한다. typed map의 범위는 정규화된 start/span에서 독립 map 검사로 전달한다.
- 내부 manifest 명령의 정적 OSETUP 검사를 CHECK로 옮겨 XBEGIN298에 직접 진입한다. tile 실제 소비/token 증명은 여전히 OSETUP 이후 조건이다. 원본 packet은 queue에 남아 독립 검증기가 직접 소비한다.
- validator의 fresh/persistent/map 주소는 page와 bit offset 연결로 만들고, manifest는 fresh166B 이후 map-local0..255로 전환한다. 기존 `cursor-166`과 bank/base 주소 덧셈을 대체한다. CRC hash와 persistent 검사 주소도 같은 물리 배치의 연결식이다.
- record 자체145bit, 별도 packet cursor9bit 포함 **154bit ≤ 160bit 상한**. 이전 논리 저장 상한189bit 대비35bit 감소이며, 실제 FF 감소25개와 구분한다. RAM 추가0; hot descriptor를 RAM에 저장하지 않는다.
- 기존 물리 RAM, host/source clock 소유권, CRC 포트 공유와 frame clear 영역은 유지한다. page 선택 mux 자체가 모두 사라졌다는 주장은 하지 않는다.
- queue/SPI/plan ingress, HREAD/HCAP, 내부 packet cursor, XWAIT/완료 relay는 남아 있다. 303의 rejected 공통 cursor/완료 RTL을 가져오지 않았다. `nes_joint303.native`만 사용해 ARM 공급 우선순위를 유지한다.

## whole Quartus Lite — parent/child 중복 합산 없음

|항목|RTL300|305|차이|
|---|---:|---:|---:|
|LE|22578|22452|−126|
|comb|17678|17617|−61|
|FF|9022|8997|−25|
|RAM bits|307808|307808|0|
|comb 부족|2270|2209|−61|

host own2103→2087(−16), validator1310→1250(−60), glue54→48(−6), queue129/SPI655 동일, plan576→577(+1). 고정 경계4827→4746(−81), 밖12851→12871(+20), whole 순감소61. 외부 RTL은 그대로여도 whole mapper 결과 변화까지 비용에 포함한다. record 감소를 전체 절감의 독립 원인으로 분해하지 않는다.

새 고정 경계 상한은15408−12871=2537이다. 기능 상한은128comb 정책 여유 포함2409이며, 현재4746에서2337comb 추가 절감이 필요하다(여유 없이2209). 기존304 caps는 예상치가 아닌 요구 배분이며 이번 결과에 맞춰 전체 합계 상한을 갱신해야 한다. host+validator3337을 그대로 두고 나머지만 모두 지워도 충분하지 않다. host를0으로 해도122comb가 부족하다.

## 실제 ARM·IRQ·ROM 일정

|조건/frame|기준298 ms|ARM303 ms|305 ms|
|---|---:|---:|---:|
|normal905|79.689998254|79.721134244|79.721134244|
|normal906|56.212189082|56.180144012|56.180144012|
|normal907|15.473814312|15.430951190|15.430951190|
|restricted905|104.876059654|104.883650472|104.883650472|
|restricted906|116.900688084|116.901188078|116.901188078|
|restricted907|17.468381286|17.462790444|17.462790444|

905/906은 cold로 frame 예산을 크게 초과하며 숨기지 않는다. 기준298 대비907의5.591µs 이득을 active record의 시간 이득으로 세지 않는다. 동일 ARM303 경로 대비 이번 추가 이득은0이다. 실제 M4 명령과 SPI·GPIO IRQ·credit·tile ROM arbiter를 실행했지만 source replay/CPI1·84MHz/IRQ24cycle/ordinary65816 trace와 map·tile·display bus 모델을 사용한다. full ARM RUN·live65816·전체71 일정·heavy7·FIT/STA·실물60fps는 미검증이다.

ARM text27918B/BSS47120B/관측stack1288B. 제한907703224명령, SPI1236B, E2 26회, timer fallback1회. 겹치는 ARM 실행·ROM 대기·SPI·DMA 시간은 더하지 않는다.

## BG ROM 원인과 공급 일정

제한907 첫 BG plan cycle5,991,825, `cycle % 357368 = 273937`; 허용 window는330088..354639이고 세부 slot은전역 `cycle % 12 == 3`이다. window가 열릴 때까지56,151cycle(2.552286554ms)이 남는다. 첫 tile은 cycle6,047,986, plan 이후2.552742ms에 나온다. 첫 OBJ plan은 phase336854로 이미 window 안이며 첫 tile까지0.000545ms다.

window02 passive replay에서 BG 최초 요청272.352618ms는 cache hit0/pending0/ready0/qualified0이었다. 실제 miss 승인은274.905042ms(qualified1/core request0), 요청→승인2.552424ms이며 승인→첫tile0.000273ms다. OBJ도 첫 요청은 miss지만 허용 window 안이어서 요청→승인0.000228ms, 승인→첫tile0.000272ms다. 따라서 BG 첫 지연의 대부분은 허용window까지의 대기이고, 이 최초 승인에서 core 우선 차단은 없었다. 프레임 전체의core priority 차단13회와 별도로 구분한다. 사이클 counter phase는 posedge 관측의1cycle 해상도로 해석하며 qualify 실제 관측을 함께 기록한다. window와 core 우선권은 변경하지 않는다. 첫 plan을 수십µs 앞당겨도 같은 허용 window를 기다리는 한 최초 ROM 가능 시점은 변하지 않는다. 반대로 이전 window를 잡는 데 필요한 공급 당김은 별도 계산해야 하며, window 정책 자체를 임의로 완화해 시간 이득으로 세지 않는다.

## 검증·보존

최종 선택 결과와 모든 입력 SHA는 `analysis/record305-verification.json`에 기록한다. 원본 E1/E9 bytes/order, metadata8570B·receipt754B·CRC64B, bank 재사용, 4credit, 최종 표시12read/ACK를 비교한다. ARM native71/STOP35/IRQ재개11/credit11/supply20/actualwait7/H2 9/IRQ8 검증은 새 ELF로 실행한다.

- test01: 전체 compile 통과 후 display byte1 비교 실패. expected observer가 제거된 내부 OSETUP을 기다려 기대값이 미정이었다.
- test02: 실제값0x18/RAM699=0x18, 기대값xx를 진단해 관측기 문제를 확인했다. RTL의 독립 검사 완화 없이 XBEGIN에서 원본 queue를 읽도록 관측기를 옮겼다.
- board01: Quartus의 구조체 선언 전 참조 오류. 선언 순서만 수정했다.
- test03: 수정 후 정상3프레임 최종 ACK PASS.
- board02: fresh whole Lite MAP PASS, undriven0. functional RTL 변경은 host와 validator 두 파일. FIT/STA는 실행하지 않았다.
- window01: 제한3프레임 최종 ACK PASS. guards01의44개 retained 오류/STOP 검사도 모두 PASS했다. GNEG26의 이전 내부 OSETUP 대기는 새 XBEGIN에 연결했다. IRQ 포트 미연결3경고는 별도 RTL guard 경계의 기존 경고이고, 실제IRQ는 live/ARM검사에서 확인한다. window02는cache 요청/승인 계측을 추가한3프레임 replay이며 functional RTL과전체 완료시간이window01과동일함을분석에서검증한다.

## 다음 구조 판단

첫 BG 출력274.905315ms 이후 최종 완료281.339760ms까지6.434445ms가 남는다. 제한907 후반에는 일반DMA와209B op15 manifest 전송도 있으며, 이 시간이 모두 직렬로 절감 가능하다는 뜻은 아니다.

부분 저장/주소 교체로 목표를 달성했다는 결론은 내릴 수 없다. 다음 설계는 남은 host·validator3337comb와 queue/SPI/plan1360comb를 함께 줄일 실제 삭제 목록, old state/field/port 선택의 대체 관계, 독립 검사 유지 비용을 먼저 제시해야 한다. 목표는 새 경계4746→2537 이하(정책 여유 포함2409), 제한907에서최소0.796124ms 추가 개선(0.25ms 여유 포함1.046124ms)이다.

시간 쪽은 최초 BG miss의 실제 공급 가능 window와 DMA deadline을 바꾸는 근거가 필요하다. 더 이른 plan이 같은 window를 기다리는 경우와 이전 window에 들어가는 경우를 구분한다. source 중 speculative ROM fetch를 고려한다면 input COMMITTED 전 표시 금지, epoch/STOP/cache 무효화, RAM 포트와 core 우선권을 별도로 입증해야 하며 아직 구현·승인된 후보로 세지 않는다. FSM/seed/record 비트 미세 반복이나 생산자 승인bit로 독립 검사를 지우는 방법은 진행하지 않는다.
