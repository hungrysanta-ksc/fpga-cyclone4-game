# NES345 — MASK·SHIFT 유지 압축 입력과 host 실행기 삭제 예산

선택 기준은 **338 RTL·336 ARM 유지**다. 제한 ROM 연속 warm907의20.689660812ms, 60Hz 대비4.022994145ms 초과와 whole17274comb/1866개 부족은 바뀌지 않았다. 이번에는 기존 실제 실행 증거2204파일을 재해시하고71프레임의 단일 record 저장 모델을 검증했다. 새 ARM/RTL/MAP 실행이나 개선 실측은 없다. 증거는 `analysis/budget345-verification.json`, 재현은 `tools/analyze_nes_budget345.py`다.

## 압축을 유지하면서 삭제할 source 경로

340의 map MASK·SHIFT, nonmap literal/repeat8/raster repeat16 형식을 유지한다. 71프레임 성공 입력 wire는338의52113B에서340의32236B로 줄었고 기록된 프레임별 wire 회귀가 없다. warm907은564→206B다. 이 수치는 기존340의 실제 codec 결과이며 새 구현의 성능은 아니다. MASK를 없앤343 모델의11프레임 회귀, SHIFT까지 없앤342의21프레임 회귀를 다시 허용하지 않는다.

이번 저장 모델은340의 record와 CRC를 그대로 사용한다. 기존512B phase RAM 중 local256..383의128B를 최종 record 저장소로 예약하고, data를 최종 위치에 먼저 쓰고 prefix를 나중에 확정한 뒤 순차 출력한다.71프레임 전체 byte 동일성을 확인했고 최대 record는76B다. model prefix 쓰기는 MASK1/SHIFT4/nonmap4클록, 프레임 최대273클록(22MHz에서12.409µs)이다. H/GEO/END·CRC 작업, query·비교·mask 쓰기·RAM stall은 이 숫자 밖에 있으며 무료가 아니다. 이미 입력 중 쓴 데이터에 대한 추가 복사 루프를 만들지 않는다. 모델은 완성 record를 입력으로 받으므로 실제 스트리밍 생성·포트 충돌·STOP 안전성 증명을 대신하지 않는다.

|대상|실제 삭제할 경로|유지하거나 새로 지불할 비용|
|---|---|---|
|MASK|출력시 mask/value 구간 선택·주소 빼기|변경 비교, mask 누적·지연 쓰기, base history|
|SHIFT|출력시4B mux|좌우 비교·edge 보존, 최종4B 쓰기|
|nonmap|340 RUN 출력의 rec_i−4 주소, seed/seed_hi 출력 mux|region 경계,64B 제한, seed 비교, pending 입력 보존|
|공통 출력|형식별 emit/continue에 흩어진 record cursor 갱신|단일 base+cursor, length, record_ready/accept, CRC trailer2B 선택|
|query|가능한 region-local 주소와 경계 산출을 builder와 공유|source NES clk와 host clk 사이 mailbox/CDC, query 선행 읽기|

nonmap payload는 local260부터 쓰고 prefix256..259를 backfill한다. repeat seed도260/261에 실제로 저장해 출력 seed mux를 제거한다. MASK는257부터 mask와 compact values, SHIFT는256..259를 사용한다. 서로 다른 record를 동시에 소유하지 않는다. mask_pending이 남으면 prefix 쓰기를 기다리고, 미소비 record가 있으면 다음 record를 덮어쓰지 않는다. `stop_run340`에서 현재 query byte를 재사용하는 pending 동작은 반드시 남긴다. 출력 완료를 입력 소비 완료로 잘못 간주하면 변경 byte를 유실한다.

344의 실제 연속 저장 변경은 whole11comb만 줄였고340의 이중 경로는 whole328comb를 늘렸다. **둘을 합치면 절감된다는 근거는 없다.** 이 후보는 별도 RUN emitter를 추가하는 patch가 아니라 출력·주소·record 진행을 실제 삭제하는 교체여야 한다. CRC streaming 때문에 마지막 trailer가 늦게 확정되는 비용도 남긴다.

## host 공통 실행기의 삭제 계약

338 `nes_mux260.sv` 기준으로 단순 PREAD/PCAP 공유는 이미 충분하지 않았다. 아래 다섯 목적지 진행 상태를 하나의 ISSUE/WAIT/ADVANCE로 바꾸는 것이 최소 교체 경계다.

|기존 경로|교체 후 소유권/진행|
|---|---|
|PUT|literal 또는 H2의 byte를 목적지 adapter에 제시; 실제 accept에서만 출력 cursor 증가|
|EXPAND325|공통 seed_width/phase와 output_remaining으로 반복; encoded cursor는 증가하지 않음|
|MISSUE313|expected RAM 주소·범위 검사 후 쓰기 발행; 승인되지 않은 쓰기를 반복하지 않음|
|MWAIT313|RAM latency/port 소유권에 맞는 완료 이후 한 번만 진행|
|MNEXT313|zero/literal 공급과 run 종료 선택을 공통 supplier/ADVANCE로 이동|

MCAP313의 opcode/version/encoded length/RLE run-end/166·256 영역 검사, PCAP의 identity·token 해석은 필수 검사를 유지한 checked supplier로 옮긴다. 목적지 cursor는 `at`, `expanded325`, `manifest_byte313`의 상호 배타적인 **payload 진행 용도**를 대체한다. `at`의 header/token/final scan 용도까지 삭제했다고 세지 않는다. encoded cursor와 expanded cursor는 RLE에서 증가 조건이 달라 둘 다 필요하다. `run_left313`는 압축 run 잔량이며 destination span과 같은 값이 아니므로 무조건 합치지 않는다.

현재 `canonical_write313`는 MISSUE313 상태·범위·fault 조건으로 활성화되며 `range_ready` 자체가 RAM write ACK는 아니다. 새 adapter는 실제 write enable/latency를 별도 정의해야 한다. staging은 put_ready, H2는 mready, expected RAM은 독점 grant와 완료가 각각 accept 조건이다. READ/CAPTURE와 WRITE를 동시에 요구하면 명시적으로 중재하고 held byte를 안정적으로 유지한다. expected RAM과 validator final scan 충돌 시 producer를 정지한다.

독립 validator의 실제 SNES read CRC·coverage·private job·최종 scan은 삭제하지 않는다. host가 쓴 expected와 실제 read 결과는 서로 다른 증거다. qretire는 packet 저장 재사용, receipt는 실제 소비, 최종 ACK는 검사·표시 완료로 구분한다. batch 마지막 range 조건, lease·token·generation, STOP 취소, VBlank 표시 조건을 공통 완료 플래그 하나로 합치지 않는다. source와 host 간 클록 경계도 유지한다.

## 시간: 입력 바이트 감소와 ROM 창 확보를 분리

|기존 실제 warm907 결과|338 기준|340 압축|344 보정된 BG 선행 공급|
|---|---:|---:|---:|
|제한 ROM 연속 ms|20.689660812|20.691024432|20.790295968|
|고정 시작·ROM 위상 ms|25.051199382|25.051199382|25.152879980|
|일반 ROM 연속 ms|13.410066350|11.992901538|13.572655308|

일반 ROM 연속의340 개선1.417165ms를 제한 ROM 개선으로 이식할 수 없다. 고정907의340 첫 ROM 요청은 시작 후6.972302ms, 이전 허용창 종료는6.089722ms로 **최소882.580µs를 앞당겨야 그 창에 닿는다**. 이것은 필요조건이며 창 내부 공급량·뒤따르는 요청·VBlank를 포함한 충분조건이 아니다. source 완료는2.692376782ms이고 완료부터 요청까지4.279925218ms가 더 걸렸다. 후자는 하나의 planner 함수 비용이 아니라 준비·전송·대기를 합친 구간이다.206B 성공 wire만0.627810ms여서 source 나머지 약2.064567ms에도 ARM/응답/query/대기가 포함된다. 이를 전부 codec 계산으로 부르지 않는다.

다음 검증의 첫 목표는 **동일 시작·ROM 위상에서 요청을6.089722ms보다 이르게** 만드는 것이다. source 입력 완료와 첫 E9/ROM 요청을 각각 계측한다. 336 ARM의 기존 전체 COMMIT 장벽과 batch 크기·발행 순서를 유지한 압축-only 비교를 먼저 하며344의 추가 E9/E2 총36B를 섞지 않는다. 그 후 필요한 경우에만 준비 일정 변경을 별도 비교한다. 입력만 줄여도 나머지4.280ms가 자동으로 줄어든다고 가정하지 않는다.

343의206B/1bank/46B prefix 조건에서 비전송0.900ms·post-ROM3.180ms는 여전히 공격적인 **채택 상한**이다. 첫 source scan0.350ms 할당은 기존 약0.446ms보다 작아 아직 근거가 없으며, 이번 모델273클록으로 충족됐다고 보지 않는다. 제한 연속의4.023ms 부족과 고정 위상의8.385ms 부족은 따로 보고한다. 콜드905/906, 순차905→906→907, 일반/제한 ROM, 동일 위상을 모두 비교하고 평균값으로 실패 프레임을 숨기지 않는다.

## 전체 회로 예산과 중단 기준

|동일 own 범위 comb|338|채택 상한|필요 감소|
|---|---:|---:|---:|
|host|2161|1146|1015|
|validator/aperture|1159|1160|−1|
|queue/SPI|798|600|198|
|source|1747|1100|647|
|plan|459|297|162|
|소계|6324|4303|2021|
|외부 유지|10950|10950|0|
|whole|17274|15253|2021|

이는 Quartus 결과 예측이 아니라15408comb 한도에서155개 여유를 남기려는 목표다. 현재는1866개 부족하며 여유까지 총2021개를 줄여야 한다. source transport/mailbox399 유지 시 encoder 상한701:338의1348 대비647,340의1668 대비967개를 줄여야 한다. 이 큰 감소가 단일 record 출력만으로 가능하다는 증거는 없다.

queue/SPI·plan을 그대로 두고 host/source와 validator 상한만 충족하면 **15613comb로205개 부족**하다. 따라서 host/source 최소 기능 실험은 진행할 수 있어도 이것만으로 전체 해결 구조가 확정되었다고 채택할 수 없다. queue 응답 snapshot·저장 credit과 plan decode 중 실제 삭제할360개에 대한 별도 근거 또는 host/source 추가 감소가 필요하다. 이미 제거한 reader·active record·snapshot을 다시 절감에 포함하지 않는다. 기존 whole307808RAMbits를 늘리지 않는 것이 초기 제약이며 실제 M9K packing·LAB·타이밍은 별도 확인한다.

다음 구현 게이트는 (1) 동일340 압축 bytes/CRC와338 독립 최종 결과, (2) 다섯 목적지 진행 상태와 형식별 출력 주소 mux의 실제 삭제, (3) query·RAM·staging stall 및 모든 STOP 경계,2슬롯 credit wrap/reuse, premature ACK·expected corruption·VBlank 검사, (4) 실제 M4/SPI/IRQ 일정과 동일 소스 whole Lite 비교다. 회로나 제한 일정 중 하나라도 개선되지 않으면338/336을 유지한다. 새71 fullpath, full firmware RUN, 실제65816 재실행, FIT/STA, 물리 지속60fps는 이번 검토에서 검증되지 않았다. 자동 merge는 하지 않는다.
