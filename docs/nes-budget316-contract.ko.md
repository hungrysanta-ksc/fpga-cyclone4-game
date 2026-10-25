# NES316 주소·완료 제어 및 BG 공급 일정 재예산

이번 단계는 NES315의 실제 ARM/RTL 실행 기록과 전체 Quartus Lite MAP을 재분석한 구조 검토다. 새 RTL·ARM 후보, 새 simulation/MAP 결과는 없다. 남은 0.239676ms/2462comb를 해결했다고 주장하지 않는다. `analysis/budget316-verification.json`과 `tools/analyze_nes_budget316.py`에 입력 hash·계산·한계를 기록한다.

## 확인한 임계 구간

|제한 ROM 907 경계|절대 ms|구간 ms|
|---|---:|---:|
|프레임 시작|263.660336|—|
|첫 BG tile 수락|274.905315|11.244979|
|마지막 실제 consume|280.050776|5.145461|
|마지막 internal packet 반환|280.364315|0.313539|
|최종 frame_done|280.566679|0.202364|

첫 BG tile 수락은 ROM grant 자체와 같지 않으며, 그 전 11.244979ms 전체가 유휴 ROM 대기인 것도 아니다. source·planner·ARM·SPI 작업이 포함돼 있다. 프레임 소요16.906343ms, 마지막 consume 뒤0.515903ms가 남는다. 0.239676ms를 consume→internal 반환 구간만으로 회수하려면 그 구간의76.44%를 앞당겨야 한다. 이는 필요한 개선량이며 가능한 절감량의 측정값이 아니다.

907의 metadata op15/op11/op3는 총125B다. op15 전송 완료280.041265ms는 마지막 consume보다 이미9.511us 앞선다. 따라서125B를 모두 후반 직렬 비용으로 더하거나 전부 앞당길 수 있다고 계산하면 중복이다. 해당 전송 checkpoint의11172 ARM 명령은 이전 checkpoint 이후 작업을 포함하므로 순수 encoding 비용도 아니다.

BG 전에는 E1 2회82B, E2 4회56B, E9 2회57B가 완료됐다. BG 이후 E1 13회502B, E0 4회104B, E2 23회322B, E9 2회35B, EA 1회7B가 완료됐다. 전송 완료 시각으로 나눈 분류이므로 정확한 SPI 점유 구간과 같지는 않다. metadata-ready 시각은 기존315 로그에 직접 계측되지 않아 **BG 대기 중 이동 가능 시간은 아직 미확정**이다.

정상907도 마지막 consume 이후0.515099ms가 남는다. 제한905/906에서는 각각1.425406/1.425946ms이며 metadata416B를 사용한다. 907만 앞당기고905/906 공급을 늦추면 이전315처럼 시작 위상만 바뀔 수 있으므로 세 프레임 합계·절대 완료 시각·첫 BG 이후 tail을 함께 비교한다.

## 현재 ARM에서 단순 재배치가 불가능한 이유

`prepare289()`는 resident/dirty prepared, video valid, committed source와 generation 일치를 요구한다. `seal289`의 requirements는 resident used/dirty stale에서 만들어지고 map manifest는 `mapstale247`에서 만들어진다. map 변경은 `map_change289()`가 두 bank의 stale bitmap에 반영하며 표시 완료 전에는 commit하지 않는다.

`nes_output264.c`는 첫 map manifest에서 requirements를 보내고, `requirements264`가 설정된 뒤에는 map manifest 외 일반 명령을 거절한다. 따라서 op15를 앞당기려면 다음을 함께 바꿔야 한다.

1. 최종 used/stale/map bitmap의 불변 시점과 준비 완료를 별도 상태로 기록한다. BG 완료만으로 OBJ와 모든 requirements가 확정됐다고 가정하지 않는다.
2. requirements 발행과 일반 DMA 금지 상태를 분리한다. 기대값 저장은 허용하되 수신한 metadata를 receipt 완료로 인정하지 않는다.
3. DMA-ready와 plan credit/IRQ 서비스를 최우선으로 유지한다. 남은 저장 credit이 있고 확정된 metadata가 있을 때만 작은 준비·전송 단위를 실행한다. 대기 중인 tile 명령 뒤의 metadata가 head를 막는 경우도 별도 측정한다.
4. terminal op3는 모든 명령 발행 뒤에 둔다. queue 저장 반환, 실제 consume, 독립 coverage, 표시 lease, VBlank와 최종 ACK는 각각 유지한다.

early manifest fixture 통과는 위 ARM의 준비·분할·응답 비용을 증명하지 않는다. 최종0.202364ms 전체도 삭제 가능 비용으로 잡지 않는다. 그 안의 E2/EA/IRQ·최종 완료 증거가 먼저 식별돼야 한다.

## 실제 삭제할 제어와 유지할 소유권

host와 validator는 현재 둘 다 host_clk에서 동작한다. 그러나 queue RAM과 validator phase RAM은 서로 다른 저장소이고 source 쪽 포트/수명은 별도다. 같은 clock이라는 이유만으로 RAM과 검사 상태를 하나로 합칠 수 없다.

|영역|교체 후보|반드시 유지할 것|
|ingress/queue|header/payload 주소의 operand 선택을 공통 주소 경로로 이동; 발행/retire 이벤트의 한 소유자|수신 중 CRC·identity·length, 2slot full/empty, SS 중단, 16bit counter 고갈·wrap|
|host|parser_address/cursor의 범위 진행 중복, canonical 주소 분기, 분산 qretire·packet_seq 갱신을 공통 transaction 완료로 교체|packet 저장 반환과 consume 분리, range token, staging owner, batch 마지막 범위 규칙|
|host+validator|MREAD/MCAP/MISSUE/MWAIT와 validator의 check-read/test 완료 왕복을 동일 요청/응답 계약의 실행 단계로 교체|기대 manifest와 실제 receipt의 독립 데이터, coverage·CRC·range 경계, 오류 우선·STOP freeze|
|validator|context/receipt/hash 주소 선택을 수명별 base+offset 경로로 통합; 공통 실행기가 발행하고 validator가 검사 결과 반환|persistent validity, raw CRC, H2/certificate 의미 검사, display 12read/token/finalACK|

validator의 receipt cursor를 producer의 완료 카운터로 대신하면 독립 검사가 사라진다. 공유 가능한 것은 주소 연산/실행 단계이며, 기대값과 실제 소비 증거까지 하나로 합치는 것이 아니다. 두 RAM 포트의 읽기 지연, 동일 주소 쓰기, STOP 직전/직후 request와 stale completion을 검증해야 한다.

## 회로 예산: 주소 mux만으로는 부족

315 전체 MAP은22664LE/17870comb/9040FF/307808bits다. 다음은 동일 report의 **own** 값이며 inclusive 자원을 합산하지 않는다.

|영역|comb|FF|
|---|---:|---:|
|queue|277|91|
|SPI front|695|292|
|host flow|2493|718|
|validator|1009|199|
|합계|4474|1300|

queue+SPI 전체972comb를 비용0으로 없앤다는 비현실적인 산술 가정에서도1490개가 부족하다. host+validator3502comb의42.55%를 추가로 줄여야 하는 규모다. 실제로는 ingress와 독립 검사 비용이 남으므로 이보다 어려워진다. 이는 합성 예측/물리 하한이 아니라 작은 교체 범위가 충분하지 않음을 보여주는 고정 경계 진단이다.

나머지 own 로직13396comb가 같다고 가정하면 위4474comb 영역의 새 예산은 **2012comb 이하**다. 128개 여유까지 원하면1884comb 이하가 필요하다. 새 control mux·CRC·port arbitration·CDC·오류 제어를 모두 포함한 예산이며 목표치이지 달성 예상치가 아니다. 전체 MAP 변화가 최종 판단이고 기존 parent 자원과 새 자원을 별도로 더하지 않는다.

|후보|시간 관점|회로 관점|판정|
|주소 선택/분산 retire만 통합|후반 metadata/응답 임계 경로 대부분 유지|972개 전체 삭제 가정조차 부족|독립된 최종 후보로 부적합|
|metadata 준비·발행만 선행|0.313539ms 구간에 유효 후보가 있음; 확정 시각 미계측|2462개 부족 해결 근거 없음|일정 분리 실험에만 적합|
|공통 transaction 실행+metadata 준비/발행 분리|DMA/plan 우선으로 후반 비용 앞당기기; terminal 검사 유지|host·validator까지 포함해4474→2012 이하 필요|다음 통합 검증 후보; 시간/면적 delta 미확정|

## 다음 검증의 통과 기준

첫 계측은 기존315 RTL에서 ARM metadata 확정·준비 진입/종료·ready DMA·queue credit·plan credit·IRQ를 동일 timeline에 기록한다. 준비 완료 전 발행 금지, 준비 도중 DMA/plan이 준비되면 양보, STOP/새 generation에서 준비 상태 폐기를 확인한다. 그다음 공통 transaction 후보와 결합해 다음을 판정한다.

- 제한907 소요16.666667ms 이하, 정상907 비회귀. 목표 순이득 최소0.239676ms; 소규모 여유를 포함하면0.300ms를 목표로 둔다. 세 프레임 합계/절대 완료/tail도 개선되어야 한다.
- 전체 comb15408 이하, RAM307808bits 이하. 이 범위 내 불가능하면 source/plan까지 역할과 저장소를 재설계하며 작은 mux/FSM/seed/FIT 반복으로 해결됐다고 하지 않는다.
- 저장과 소비 완료 분리, exact receipt/CRC/coverage, 2credit, 중간 취소·재사용·잘못된 완료, 최종ACK·표시 순서 유지. 315의12오류/queue14/SPI15/응답41 및 실제 ordinary CPU trace 결합을 동일 소스로 재검증한다.

이번 검토에서 새 time/area delta는 null이다. 현재 부족분은0.239676ms/2462comb 그대로다. baseline은 actual M4 instruction/CPI1·IRQ·ROM·2slot 응답을 포함하지만 physical WCET가 아니다. tile/map/VBlank 일부는 모델이며 whole71/fullRUN/FITSTA/실물60fps는 미검증이다. production227/GBC164/saveSRAM과315 증거를 유지한다.
