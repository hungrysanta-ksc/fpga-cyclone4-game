# NES255: query 선행 읽기와 receipt·바이트 소비 제어 공유

NES255는 별도 query FSM 없이 선행 읽기를 복원하고, receipt와 실제 바이트 수락 어댑터의 제어를 공유했다. 동일 어댑터 경계 MAP은 기준3414LE/1046FF에서 후보3362LE/985FF로 52LE·61FF 감소하며 RAM49152bits는 같다. warm 준비는11836..11854cycles, 출력 제어는 기준보다74..152cycles 감소했다. 두 구성 각각71프레임·28오류 검사와 후보의8개 부분 CRC 갱신을 통과했다. 실제 출력은 같은 클록의 valid/ready 수락까지이며 SPI packet parser·SNES 실행/표시 연결은 미완료다. 전체490LE/40LAB 부족과60fps는 미해결이며 P2 미선정이다.

## 같은 경계에서 바꾼 것

- query는 source cursor로 section/index를 계산한다. 마지막 lane을 FETCH에서 new_byte로 옮긴 직후 보관64bit를 비우고, FSTORE의 다음 cursor를 이용해 다음 응답을 미리 요청한다. 보관중/응답대기2bit만 추가하며 별도 query FSM·index·generation·offset 카운터는 복구하지 않는다. source가 입력측 SPI record 출력·CRC 작업으로 대기해도 한 응답을 미리 보관할 수 있다.
- receipt 초기화·manifest 검사에는 입력 단계에서 쓰던 cursor를 재사용한다. 범위 바이트 수락에는 입력 expanded 카운터를 재사용한다. source/출력 수명이 겹치지 않으며 인증서832..863과 영속 validity/CRC0..395는 그대로 유지한다.
- 출력 A 포트는 received/map receipt를 읽고, 빈 B 포트는 같은 사이클에 해당 bank의 validity를 읽는다. RWRITE에서 두 포트를 함께 갱신해 기존 VREAD/VWRITE를 제거한다. manifest의 metadata 검사도 두 포트로 읽어 CHECKVALIDREAD/TEST를 제거한다. 실제 M9K TDP 추론과 포트 충돌·주소 수명을 검사했다.
- 새 범위 어댑터는 descriptor의 map/first/count를 받고 byte valid/ready를 목적지 kind/unit/lane/data로 전달한다. BG16B·OBJ32B·map2B·CGRAM16B·rawCHR16B 단위를 사용한다. 모든 바이트가 sink에 수락된 뒤에만 receipt를 갱신한다. 범위당 map≤32/nonmap≤16, BG→OBJ 및 OBJ→metadata 경계 교차는 거절한다.
- 기준은254 core에 별도 descriptor·byte counter·4상태 어댑터를 붙인 구성이다. 후보는 descriptor 보관과 바이트 완료 상태를 receipt FSM에 흡수한다. 두 구성의 포트·기능·입력 바이트와 backpressure를 맞춰 비교했으며, 어댑터가 없던254의3239LE와 직접 비교해 절약이라고 하지 않는다.
- STOP·lease 상실·세대 변경에는 byte 수락과 ready를 즉시 막는다. 최종 표시 ACK는 별개이며, 부분 범위 완료·조기 finish·조기 display ACK는 봉인되지 않는다. 기준 어댑터의 lease gate 누락은 코드 검토 중 보완해 최종 기준 MAP에 반영했다.

## 실제로 실행한 소비 경계

기록된 C247 출력의 실제 타일·map·CGRAM·rawCHR 36,646B, 2,302개 범위를 두 RTL에 각각 입력했다. 매 수락마다 데이터와 목적지 kind/unit/lane를 확인하고, 모델 목적지 RAM에 저장한 결과도 비교했다. 각 범위 마지막 바이트를256cycles 막아 receipt가 미리 갱신되지 않음을 검사했다. 수락 횟수·목적지·최종 receipt/CRC/H2·SPI 입력 bytes가 두 구성에서 동일하다.
이 sink는 같은 클록의 실제 RTL valid/ready 경계와 테스트벤치 목적지 메모리다. 모델 RAM의 bank는 frame harness가 지정하며 실제 consumer의 bank/token 소유권 연결은 남아 있다. 물리 SNES가 읽었다는 뜻이 아니며, 출력 SPI packet header/CRC/parser, 큐 head 중재/retire, SNES 버스/DMA/최종 표시 ACK는 연결하지 않았다. tail CRC·fresh scroll은 기존 실제 C 바이트 fixture 경로에 남고 OAM/H2 전송도 새 sink에 연결되지 않았다. 이 descriptor는 RTL 입력 인터페이스이며 새 wire 형식이 아니다. 실제 패킷을 이 범위 단위로 나누는 제어·프레이밍 비용도 남아 있다. 따라서 전체 출력 어댑터가 완성됐다고 부르지 않는다.
기존 SPI 큐의 D2/ACK나 bulk aperture consume을 단순 ready로 대체할 수 없다. typed consume과 final display ACK/capture lease retire를 분리한 채 기존 head 소유권을 실제로 대체해야 한다. 이 연결 비용은 아직0으로 계산할 수 없다.

## 회로 비용

| 구성 | LE | comb | FF | RAM bits |
|---|---:|---:|---:|---:|
|254, 소비 어댑터 없음|3239|2932|1006|49152|
|254+별도 소비 어댑터, 최종 기준|3414|3107|1046|49152|
|255 선행 읽기+receipt/소비 공유|3362|3055|985|49152|

동일 경계에서52LE·52comb·61FF가 감소한다. 이는 세 변경을 함께 적용한 결과이며 개별 효과로 분해하지 않는다. FSM은 최종 core에서 계속 추출된다. source base4096×8+512×8, phase1024×8 TDP, SPI512×8 RAM을 유지한다.
어댑터가 없던254보다 후보는123LE 크다. 기능 추가를 포함한 비교이므로 이 증가를 선행 읽기 단독 비용으로도 해석하지 않는다. 전체240의490LE/40LAB 부족에서 국소 MAP 차이를 빼지 않는다. fullFIT·배치·STA·mapper 여유는 새로 검증하지 않았다.

## 처리 시간

| warm69 항목 | 후보 cycles | 기준 대비 cycles |
|---|---:|---:|
|query/source/SPI/input ACK|75214..138081|-2138..+0|
|source 준비|11836..11854|-1868..-1866|
|출력 전체, 시험 대기 포함|5342..15460|-152..-74|
|입력+출력 전체 차이|—|-2264..-120|

22MHz 환산 source 준비는0.538000..0.538818ms다. warm 입력 평균 변화는-0.060074ms이며 빨라진 프레임64개, 느려진 프레임0개다. 실제 status polling까지 포함한 전체71프레임 wire 차이는-1040B다. 이를 wire 시간으로 다시 더하지 않는다.
출력 전체 시간에는 매 범위 마지막256cycle stall, 매 바이트1cycle 공급 공백, 11바이트마다2cycle 공급 pause가 들어 있다. 이는 처리기 성능 한계가 아니라 동일 조건의 스트레스 입력이다. 비교 차이에는 같은 바이트 수·같은 공급 지연이 상쇄된다. 출력의 절대 시간을 그대로 SNES 실행 시간으로 사용하지 않는다.
stream 단계만 제외한 후보 출력 제어·CRC·문맥·fixture dispatch는1974..2136cycles다. stream 점유는 descriptor별 n바이트에 대해2n+2ceil((n−1)/11)+256으로 계산하고, 최종 기준71프레임 및 후보 부분갱신4프레임의 RTL 상태 계수와 대조했다. 이 분리는 시간 회계를 위한 것이며 실제 packet parser가 구현됐다는 근거는 아니다.

## 전체 일정의 비용 회계

254의 조건부 일정에서 실제 source 시간과 출력 검증 항을 교체하되 두 회계 조건을 구분했다. transfer_covered_conditional은 기존 parser8cycles/byte·DMA 배정이 새 byte 수락 단계를 감당한다고 가정해 stream을 제외한다. 실제 연결로 입증되지 않은 조건이다. serialized_stress_reservation은 시험의 모든 byte 공급/256cycle stall을 추가로 예약하며, 기존 전송·DMA 배정과 일부러 중복 청구하는 보수적 민감도다. 두 수치 사이를 실제 성능 범위라고 주장하지 않는다.

| 회계 조건 | SNES setup | 검사 정책 | 최대 ms | 잔여 ms | 초과 frames |
|---|---:|---|---:|---:|---|
|transfer_covered_conditional|500|command_tail|15.995909|0.670758|없음|
|transfer_covered_conditional|500|only_bitmap_removed|16.376777|0.289890|없음|
|transfer_covered_conditional|1000|command_tail|16.857285|-0.190618|970|
|transfer_covered_conditional|1000|only_bitmap_removed|17.238153|-0.571486|954,962,970|
|serialized_stress_reservation|500|command_tail|16.548909|0.117758|없음|
|serialized_stress_reservation|500|only_bitmap_removed|16.929777|-0.263110|954,962,970|
|serialized_stress_reservation|1000|command_tail|17.410285|-0.743618|954,970|
|serialized_stress_reservation|1000|only_bitmap_removed|17.791153|-1.124486|952,954,962,970|

ARM32000cycles·H2 32B·parser 배정과 SNES validate181 제거는 계속 조건부다. 남은 시간은 실제 ARM N5 복원/계획/전송 fullRUN/IRQ, 출력 큐/parser, SNES DMA/명령 dispatch/poll/VBlank 및 캡처/표시 lease 중첩을 모두 감당해야 한다. 이 조건부 표로60fps를 승인하지 않는다.

## 검증·보존

- 후보 test03와 최종 기준 reference02: 각각 실제71프레임·451SPI블록·83,240payload B, receipt53,534B/CRC4,544B/H2문맥2,272B 및28개 오류 검사 PASS. 잘못된 query, 인증서/내용CRC/문맥, 부분 소비 STOP/조기 finish/lease 상실/display ACK/범위 초과/query 중 STOP·세대 변경을 포함한다.
- 후보 test04: 실제4프레임에서 양 bank granule2/7/12/15의8개 부분 갱신. 마지막9B granule 포함. 강화된818B RAM 조기 쓰기 검사와 stream 상태 점유 계수도 확인한다. test05는 같은 RTL에서 새 소비/취소 검사22..28을 강화된 sink 수락 금지 assertion으로 재검사한다.
- test01은 q_section과 TB frame의 선언 순서 컴파일 실패로 보존했다. test02/reference01은3프레임 초기 PASS. refmap01은 lease gate 보완 전 진단이며 최종 기준 수치로 쓰지 않는다. map01은 test02와 동일 후보 RTL이고 test03/04/05도 같다. refmap02는 reference02와 동일 RTL로 합성했다. seed/옵션 탐색이나 fullFIT 반복은 없다.
- 이전254 archive 전체와 공개8개 파일을 재해시해 보존한다. production227/unplaced240/rejected2412462472/GBC164/saveSRAM은 변경하지 않는다. 공개 변경은 생성기·검사기·집계·계획 문서다.
- 실제 기록71프레임은 raw2다. 새 raw0 통합 전환은 실행하지 않았으며 이전250 검사를 보존한다. CRC16은 인증이나 충돌 없는 내용 동등성 증명이 아니다.

NES255의 선행 읽기와 범위 receipt/소비 제어 공유는 P1 후보로 유지한다. 다음은 기존 출력 SPI 큐의 head/READ/ACK 소유권과 실제 typed parser·SNES 소비를 이 경계에 연결해 기존 제어를 대체하는 구조를 검토한다. tail CRC·fresh scroll·OAM·H2 전치도 실제 소비에 결합하고, 입력 COMMITTED/typed consume/final display ACK를 구분한다. ARM N5 복원·계획·전송 fullRUN/IRQ 및 실제 SNES setup/DMA/poll/VBlank 비용을 함께 계산해야 한다. 추가 기능만 누적하거나 작은 국소 차이를 전체 회수로 계산하지 않고, 근거 없는 FIT·seed·ROM/opcode 반복은 하지 않는다.

[계획](nes-joint255-plan.json) · [집계](../analysis/joint255-verification.json) · [프레임별 시간](../analysis/joint255-frames.csv) · [조건부 일정](../analysis/joint255-schedules.csv)
