# NES335 실제 DMA 읽기·receipt 소유권 교체 검토

기준은 **332 RTL+334 ARM**이다. `probe_nes_receipt335.py`는 DUT와 ARM을 바꾸지 않고 descriptor, 실제 응답 바이트, read 종료, token ACK, receipt RAM 접근과 expected 저장 시각을 관측한다. 고정·제한 연속·정상 연속의905/906/907을 재실행하고 기존334의 모든 비계측 이벤트와 ARM 실행 결과가 같아야 통과한다. `analyze_nes_receipt335.py`는 실제 바이트 경계에서 별도로 coverage mask와 raw CRC를 계산해 RTL의 range·RAM write와 비교한다.

**이번 단계는 계측·구조 비교다. 새 receipt RTL이나 새 Quartus 합성 결과는 없다.** whole332 Lite 보고서와 실제 입력 hash를 다시 결합해 비용 기준으로 사용한다. 제외한334 공동 FSM을 복원하거나 그 비용을 새 후보 비용으로 사용하지 않는다. 시간과 회로를 함께 줄였다는 판정은 아직 없다.

## 계측 결과

총9개 일정에서642 chunk/56877개의 실제 aperture 응답 byte/13983 coverage units/1914 bitmap bytes/96 raw CRC를 대조했다. 모든 read offset·token·count·순서·ACK 뒤 receipt write와 persistent mask가 일치했다. 바뀌지 않은334 이벤트와 ARM 명령/전송 결과도 전부 같다. 기존325의536B 실제65816 bus trace를 재사용한 실행이며 새65816/실물 측정은 아니다. ARM은CPI1/84MHz 일정 모델이다.

|제한 연속 프레임|aperture bytes|coverage units|bitmap bytes|receipt RAM µs|ACK→마지막 RAM 합계 µs|ACK→소비 해제 합계 µs|
|---|---:|---:|---:|---:|---:|---:|
|905|9104|2316|311|8.713728|11.143360|12.451000|
|906|9040|2314|316|8.951808|11.576592|12.979000|
|907|815|31|11|0.357120|0.631944|1.001000|

RAM 상태 점유,ACK 후 RAM까지,ACK 후 소비 해제까지는 서로 포함되는 구간이다. 더하지 않는다. 마지막 열 전체를 없애도 warm 이득 상한은1.001µs이며 구현에서 필수 ACK 처리까지 없앨 수 있다는 뜻이 아니다. 따라서 이 경로는 현재662.113µs의 post-ROM 부족을 닫는 시간 후보가 아니다.

|warm907 일정|전체 ms|ROM 이후를0으로 둔60Hz 초과 ms|post-ROM3.180ms 상한만 적용한 전체 ms|
|---|---:|---:|---:|
|제한 연속|20.696615274|0.187835607|20.034502274|
|동일 시작·ROM cycle|25.059517464|4.551282797|24.397949464|
|정상 연속|13.435202412|-8.271699255|11.574967412|

이 표의0-cost/상한 열은 **시작과 ROM 수락을 고정한 산술**이며 새 실행 결과나 모든 위상의 불가능성 증명이 아니다. 제한 warm은 앞선 구간이 입력 완료보다0.940125082ms 먼저 닫혔다. 입력 완료→첫 요청은5.728363728ms이고, 앞선 닫힘 시각까지 요청을 당기려면 약6.668488810ms가 필요하다. 최후 유효 slot에는 추가 정렬 여유가 필요하다. 이전 프레임 시작 이동과 현재 처리량을 섞지 않는다.

실제 최소 aperture read 간격은369.000ns였다. 아래의8/4/6-cycle 보수 배정 모델에서 모든 job은 정확한 ACK 전에 끝났고 최대 backlog는2,최대 port 대기는71.424ns였다. 실측 mask 저장량은 chunk당 최대11B이며 ABI 전체의18B 상한을 대체하지 않는다. A의 추가 mask 읽기 배정만으로 warm 0.261888µs가 더 들 수 있다. 새 RTL 지연이나 합성 결과가 아니다.

제한 연속·고정 일정에서 expected보다 이른 coverage는 cold905/906 각각2048/2078단위이고 warm907은0이다. 정상 연속에서는905/906/907 모두 이르며 각각2316/2314/31단위다. 현재 순서 그대로 expected와 즉시 비교하는 안은 성립하지 않는다. CRC/table/단위 주소를 ARM에서 새로 전송하는 안의 추가 비용은 실행하지 않았으므로 미정으로 남긴다.

## 실제로 중복되는 것과 남겨야 하는 것

|경로|현재 책임|제거·결합 검토|계속 필요한 증거|
|---|---|---|---|
|aperture 응답|RAM data/address/token tag와 유효한 bus 응답|검증된 실제 read event를 host와 CRC가 공동 사용|정확한 aperture 주소·token·한 strobe당 한 번·실제 응답 유효성|
|host read_count·tap|상승 read 종료의 순서/count와 별도 tap_seen/주소/CRC 전달|한 read-event 소유자가 offset·마지막 byte·CRC 진행을 제공|누락/중복/잘못된 주소·짧은 DMA·유효하지 않은 read 거부|
|descriptor→receipt|decoded_first/limit, active receipt_first/end, endpos|영역별 granule 해석을 실제 읽기의 완료 경계와 결합|domain·정렬·길이·overflow 및 map 순서 admission|
|validator range RAM 순회|v_bit_at/v_end, first/last mask, received·persistent RMW|완료한 bitmap byte 작업으로 교체|중복 receipt 검출, raw CRC 완료, bank별 persistent validity|
|expected·최종 검사|독립 queue expected와 actual coverage/CRC 대조|이번 교체에서 유지|expected를 실제 읽기/receipt에서 만들지 않음; H2·digest·12 display reads·최종 ACK|

주소·read count·token은 모두 같은 정보가 아니다. aperture의 응답 유효성과 host의 순차 read 완료 검사는 서로 보완한다. 하나를 삭제하려면 새 event가 두 조건을 모두 포함해야 한다. raw read 신호나 단순 DMA 요청을 event로 쓰지 않는다. ARM이 준 주소를 검증 없이 신뢰하거나 `v_all_consumed=1`을 독립 소비 증거로 쓰지 않는다.

## 후보 비교

### A. ACK 뒤 확정, DMA 중 mask 준비

실제 read에서 granule 완료를 모아 byte별 mask를 임시 저장한다. 정확한 token ACK 뒤에만 기존 received/persistent RAM을 갱신한다. 현재의 물리 receipt-before-ACK 금지 규칙을 그대로 유지할 수 있다. 대신 **ACK 뒤 RAM 순회 자체는 남는다.** pending mask 읽기와 port 선택이 추가된다. 순회만 사라진다고 계산하면 안 된다.

실측 chunk 최대 mask 수와 ABI 전체 최대는 구분한다. map 최대32단위는 정렬에 따라5 mask bytes, BG 최대128단위는17, OBJ 최대64단위는9, CGRAM은4, HDMA tail+raw 전체144단위는18이다. 18B pending mask를 기존 phase RAM716..733에 놓는 안은 설계 후보일 뿐이다. H2 680..711, display offset712..715와 분리되지만 source 입력기 수명 종료, STOP, 같은 B 포트의 CRC 서비스 및 앞으로의 사용자를 실제 RTL에서 증명해야 한다. 새 RAM/M9K를 무료로 추가하지 않는다. mask 외 base·count·token/완료 상태도 비용에 포함한다.

### B. DMA 중 private RAM 기록, ACK에서 공개

한 read-event 경로가 coverage byte mask와 CRC 작업을 생성하고, DMA 사이에 received/persistent RAM RMW를 수행한다. 기존 descriptor range 요청→끝주소→RAM walk의 실행 제어를 제거할 가능성이 있다. 한 개의 active chunk와 coalescer/port owner를 두며, 기존2슬롯은 저장 queue 역할을 유지한다. 두 번째 chunk나 다음 queue head가 첫 작업의 context를 덮어쓰면 안 된다.

하지만 이 안은 현재의 **물리 RAM receipt-before-ACK 금지 조건을 그대로 만족하지 않는다.** 새 기록은 token 검증과 모든 RAM/CRC job drain 전까지 private이며, final checker와 bank reuse가 이를 committed로 보지 못해야 한다. 단순히 기존 assertion을 삭제하는 변경은 금지한다. 다음 조건을 실제로 검증해야 한다.

- 실제 마지막 응답 byte, 정확한 read count·순서,4 token bytes/마지막 consume 값,bank·generation·lease와 pending job0을 확인한 뒤 한 번만 공개한다.
- 잘못된 token·중복/누락 read·CRC 오류·STOP이면 공개하지 않고 모든 후속 write/ACK를 막는다. 이미 수정한 persistent bits는 원래 값으로 복구된 것으로 간주하지 않는다. 재사용은 기존 fault/reset→cold 초기화가 끝난 뒤만 허용하며 양쪽 bank의 유효성 누출을 검사한다.
- metadata 저장 credit과 소비 완료를 합치지 않는다. early manifest가 저장돼도 pending chunk를 건너뛰어 SEAL/final scan을 시작할 수 없다.
- 독립 expected와 실제 CRC/receipt는 분리한다. VBlank·표시 lease·12개의 정확한 display read·최종 token ACK는 유지한다.

이것은 **다음 구현 비교 후보**다. 새 공개 규칙·port arbiter·context 상태의 면적까지 포함한 whole Lite와 취소 검증을 통과하기 전에는332를 대체하지 않는다. 물리 RAM의 기존 ACK 경계를 반드시 그대로 유지하는 구현이라면 B를 제외하고 A를 사용해야 한다.

### C. expected를 DMA 중 직접 비교해 receipt 저장 제거

현재 cold 일정에서 map/requirements expected가 실제 소비 뒤에 저장되는 사례가 있다. warm만 보고 이 안을 선택할 수 없다. 기존334의 manifest 선행 발행도 이미 기준에 포함돼 있다. 더 앞당기려면 material/geometry 확정·map planner·queue 저장 credit·IRQ·DMA 우선 공급을 실제 ARM에서 재배치해야 한다. 독립 expected를 actual read에서 대신 만드는 것은 대안이 아니다. 따라서 C는 현 전송 순서에서 제외한다.

### D. ARM이 FPGA 물리 주소·receipt 명령을 직접 전송

descriptor 범위 계산 일부를 ARM으로 옮길 수 있지만, FPGA의 domain/overflow/actual-read 검증을 전부 없앨 수는 없다. 기존 압축 payload와 source/plan 준비 비용에 command bytes·serializer·cold 분할·2슬롯 응답을 더해야 한다. 이번에는 새 ABI·ARM 전송을 실행하지 않았으므로 절감 수치와 wire 비용을0으로 확정하지 않는다. 과거 단위 좌표/별도 참조 프로그램 실패를 이름만 바꿔 반복하지 않는다.

## RAM 포트 예산의 의미

모델은 기록된 실제 read 종료 시각에 작업을 넣는다. CRC byte당8 host cycles(길이/hash RAM 및 중재 여유 포함), map mask당4 cycles, 기타 mask당6 cycles를 예약한다. 이것은 **새 RTL 실측값이 아니라 구현 상한 배정**이다. 실제84MHz host clock의11.904ns를 사용한다. CRC와 bitmap 작업은 같은 B 포트에서 직렬 서비스하고, source용 A 포트를 빌리지 않는다. queue expected RAM은 별도 기존 포트를 그대로 사용하며, final scan은 모든 pending 작업 뒤에 실행한다.

모든 기록이 ACK보다 먼저 끝나는지, 순간 backlog가 얼마인지 실제 cold/warm read 간격으로 계산한다. 이 결과는 B의 서비스 용량 가능성을 보여줄 뿐이다. 새 CDC/STA나 실제 SNES bus 타이밍, arbitrary stall/STOP·raw0의 새 RTL 검증을 대신하지 않는다. A는 mask 읽기를 위해 byte당2 cycles를 더 배정하므로 ACK 후 시간이 오히려 늘어날 수 있다.

## whole Lite 회로 기준과 합격 예산

기준 whole은22539LE/17649comb/9097FF/307808bits이고 comb 부족은2241이다. host2348+validator1053+aperture206의 own 합계는3607이다. **validator와 aperture를 통째로 없앤다는 불가능한 상한에서도982comb이 부족하다.** 이 세 경로의 작은 중복을 없애는 것만으로2241개를 회수할 수 있다고 가정하지 않는다. 신호별 FF 수나 상태 수는 LUT 절감량이 아니다.

|서로 겹치지 않는 범위|기준 comb|설계 상한|필요 순감소|
|---|---:|---:|---:|
|host+validator+aperture|3607|2306|1301|
|queue+SPI|851|600|251|
|source|1771|1100|671|
|plan|460|310|150|
|교체 범위 합계|6689|4316|2373|
|범위 밖|10960|10960|0|
|whole|17649|15276|2373|

333 예산에 aperture를 명시적으로 포함시켰으며 절감 목표를 새 실측치로 바꾸지 않았다. arithmetic capacity까지는 범위4448 이하,132comb 여유 목표는4316 이하가 필요하다. B의 event qualifier·coalescer·private/committed 상태·RAM arbitration과 유지할 독립 검사를 모두 이 안에 넣어야 한다. 별도 sidecar를 더한 뒤 기존 decoder/walker를 남기는 안은 교체가 아니다. 추가 RAM0, FF≤9097을 비교 예산으로 유지한다. 현재 어느 후보도 새 whole MAP으로 이 상한을 입증하지 않았다. MAP 수치도 FIT/LAB/STA 통과를 뜻하지 않는다.

## 다음 구현 경계

332 RTL과334 ARM을 유지한다. B를 구현하려면 먼저 공개 경계와 취소 후 cold 재초기화를 검증하고, aperture/host/tap의 검증된 read event 하나가 descriptor의 actual coverage·CRC·RAM 작업을 소유하도록 기존 경로를 실제 삭제한다. physical receipt-before-ACK를 유지해야 한다면 A와 비교한다. 동일 시작·ROM 위상과 연속 일정 모두에서 실제 ARM/SPI/IRQ/2슬롯 재실행 후 whole Lite를 한 번 비교한다. 기능 통과와 작은 FSM 절감만으로 채택하지 않는다.

시간은 receipt 이후 몇 cycle보다 source 입력 완료·첫 ROM 요청 및 tile/ordinary 공급이 우선이다. ROM 허용 구간, input-COMMITTED, VBlank를 완화해서 이득을 만들지 않는다. 새 후보의 시간·면적 순이득은 미측정이며, fullRUN71/FIT/STA/실물60fps는 여전히 미완료다. production227/GBC164/saveSRAM은 변경하지 않았다.

초기 window01은 계측 문자열의 줄바꿈과 format 인자 수 오류로 중단했다. DUT 실패나 라이선스 실패가 아니며 원시 로그를 보존한다. window02 이후에는0 compile warnings이며, 포맷·기존 이벤트 동일성 검사와 별도 coverage/CRC 계산으로 결과를 검증한다. 기존334의 오류 주입은 같은 RTL/실행 이미지의 배경 증거이고 B의 새 공개 규칙을 검증한 것으로 재사용하지 않는다.
