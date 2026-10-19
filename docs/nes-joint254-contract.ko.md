# NES254: query/source 통합·인증서 RAM·FSM 추출 원인 검증

NES254는 query/source 제어 중복과 인증서 문맥 레지스터를 실제로 제거했다. 상태 대소 비교만 동등 비교로 바꾸면 core FSM이 추출되며 3404→3296LE가 된다. query 통합·인증서32B RAM까지 적용하면 3239LE/2932comb/1006FF/49152bits다. 253 대비165LE·94FF 감소지만 준비 시간 증가와 출력66cycles 추가가 발생한다. 71프레임·21오류 검사·별도8granule 갱신 PASS. 조건부500setup 최대16.028909ms/잔여0.637758ms. 전체490LE/40LAB 부족 해결이나60fps는 입증하지 못했으며 P2 미선정이다.

## FSM이 추출되지 않은 원인

`output_phase = state >= V_CLEARALL`의 숫자 순서 비교를 해당 출력 상태의 동등 비교 목록으로 바꿨다. 모듈 이름을 제외하면 이 표현 하나만 달라졌음을 생성된 RTL 전체 비교로 확인했다. 상태 폭·합성 속성·seed는 바꾸지 않았다.
같은 Quartus25.1/EP4CE15F17C8 standalone MAP에서 기존253은 reader만 FSM 표에 있었고, 수정 뒤에는 core와 reader가 모두 표에 나타났다. 따라서 이 설계·설정에서 상태 순서 비교가 core FSM 추출을 막았음은 분리 실험으로 확인했다. 최종 통합 후보에는 reader 자체가 없으며 core만 추출된다.
분리 진단은 실제3프레임의 입력/출력 사이클 CSV와 SPI 블록 바이트가253과 정확히 같다. 최종 후보는 전체71프레임을 별도로 실행했다. 불법 상태까지 포함한 형식 동등성 증명이나 다른 도구 버전의 일반 법칙을 주장하지 않는다.

## 실제로 없앤 중복과 RAM 문맥

- query의 별도 FSM·출력 offset·section/index/lane 카운터·generation·patch snapshot을 제거했다. source cursor에서 query section/index/첫 바이트를 계산하며, 동일 source 상태기가 요청·응답·보관·소비를 담당한다. 이미 필요한 generation·admitted raw와 오류/STOP 수명을 공유한다.
- collector의 가변 개수와64bit 응답 보관은 남긴다. inactive 항목은0으로 만들고, raster 투영·mode·raw 순서 의미검사는 유지한다. 실제 query 수와 모든4398B 투영 바이트 및 N5 출력은 이전253과 같다.
- 인증서 scroll length·table lengths·mask·display-base의75bit 보관 레지스터를 제거했다. 실제 C252가 만든 H2 인증서32B를 source 입력 COMMITTED 후 공유 RAM832..863에 순서대로 한 번 저장한다. source용 rec_i를 이 단계의 입력 위치로 재사용한다.
- 저장할 때 identity/길이/mask/raw/covered와 display-base<current serial을 검사한다. display-base 비교는 little-endian 바이트마다 갱신하는 비교 상태 하나로 수행한다. 내용 CRC는 최종 소비 후 계산하고 RAM22..23과 대조한다. certificate CRC는 RAM 첫30B를 다시 읽어 계산한 뒤30..31과 대조한다.
- fresh scroll 소비 전 RAM의 길이2B를 동기 읽기로 가져와 h_count를 남은 바이트 수로 사용한다. 인증서 재검사도 실제 동기 읽기 대기 상태를 포함한다. 인증서 입력 뒤 외부 context_data를A5로 바꿔도 결과가 같고 RAM32B가 끝까지 보존되는지 검사한다.
- 기존32B 인증서를 앞에서 저장하고 끝에서는 내부 RAM을 읽는다. 동일 인증서를 두 번 전송하지 않으며 추가 인증서 wire bytes는0이다. 다만 실제 packet framing·전치 전송·어댑터와 ARM 일정은 아직 구현되지 않아 그 비용을0으로 주장하지 않는다.
- source COMMITTED 전에는 문맥 RAM을 쓰지 않으며, 출력 시작은32B가 모두 저장된 뒤만 허용한다. 부분 문맥 STOP·조기 begin·잘못된 문맥은 봉인으로 이어지지 않는다. 입력 커밋과 최종 표시 ACK는 계속 별개다.

## 공유 RAM 수명

| 구간 | 용도 | 수명 |
|---|---|---|
|0..331|양 bank validity332B|프레임 간 영속|
|332..395|양 bank CRC64B|프레임 간 영속|
|396..561|received166B|출력|
|562..817|map receipt256B|출력|
|832..863|H2 문맥32B|입력 커밋 후부터 표시 ACK까지|
|512..1023|source scratch512B|source 입력|

같은1024×8 TDP를 유지하며 context는 출력 B 포트, receipt/hash는 A 포트를 쓴다. source와 출력의 겹치는 주소는 단계별로 배타 사용한다. 실제 포트 주소 범위·동시 충돌·오류 뒤1024B 불변을 검사했다. 추가 M9K는 없으며 논리 RAM bits는49,152로 같다. 이 값은 전체 배치 여유나 물리 RAM 사용 승인이 아니다.

## 같은 독립 경계의 합성 비용

| 구성 | LE | comb | FF | RAM bits |
|---|---:|---:|---:|---:|
|기존240 source/query/SPI|2646|2336|989|57344|
|253 +receipt/H2|3404|3078|1100|49152|
|254 상태 판별만 수정|3296|2970|1130|49152|
|254 query/context 통합|3239|2932|1006|49152|

상태 판별 수정만으로108LE/108comb 감소,30FF 증가다. 여기에 query와 인증서 문맥을 함께 바꾼 효과는57LE/38comb/124FF 감소다. 최종253 대비165LE/146comb/94FF 감소를 확인했지만, query와 인증서 RAM 각각의 독립 기여도로 나누어 계산하지 않았다.
최종 같은 계층은 core2418comb/563FF, SPI(mailbox 포함)465comb/439FF, top 자체49comb/4FF다. core는 query 기능을 흡수했으므로 이전 core만과 직접 빼서 overhead를 주장할 수 없다. 부모 전체와 자식 값을 중복 합산하지 않았다.
문맥 경계는 기존75bit 병렬 필드 입력에서 valid/data/ready의 바이트 스트림으로 바뀐다. 이 MAP에는 새 packet adapter가 없으므로 경계 밖 조립·전송 제어 비용까지 절약한 것으로 해석하지 않는다.
새 후보는 기존240 source 경계보다 여전히593LE 크며, 새 receipt/H2 기능까지 포함한다. 전체240의490LE/40LAB 부족은 그대로 미해결이다. 독립 MAP 차이를 이 부족에서 빼거나 LAB 여유로 바꾸지 않는다. FSM 추출만으로 충분한 회로 여유가 생겼다는 결론은 아니다. fullFIT/STA는 실행하지 않았다.

## 처리 시간의 대가

| Warm69 구간 | 실제 사이클 범위 | 22MHz 환산 |
|---|---:|---:|
|query/source/SPI/input ACK|76639..138793|3.483591..6.308773ms|
|source 준비|13702..13722|0.622818..0.623727ms|
|출력 문맥 저장/receipt/hash/H2|2015..2147|0.091591..0.097591ms|

253 대비 입력 전체 변화는+0..+2138cycles, 평균+0.060068ms다. 빨라진 warm 프레임0개, 느려진 프레임65개다. 준비는+1866..+1868cycles 늘었다. 독립 query의 선행 읽기가 사라져 query 대기가 source 진행에 들어온다.
N5 payload와 블록은 같지만 준비 시점 차이로 실제 SPI status polling 바이트가 전체71프레임에서+1040B 달라졌다. 이 변화는 측정된 입력 전체 시간에 포함되어 있으며 wire 시간을 다시 더하지 않는다.
출력은 모든 프레임에서66cycles, 즉0.003ms 늘었다. 문맥32B의 저장 handshake와 동기 RAM 재읽기를 포함한 실제 합계다. 이전 인증서32B를 한 번 더 wire에 더한 수치가 아니다. 입력은 실제 collector/SPI 핀을 실행했으나 MCU 서비스 간격은 fixture이며, 출력은 실제 C 결과 바이트/소비 이벤트/표시 ACK의 재생이다.

## 조건부 전체 일정

253의 실측 입력·출력 항을254 실측으로 교체하고 나머지 조건을 유지했다. ARM32000cycles, 인증서32B, parser8cycles/byte, 기존 SNES setup 배정과 validate181 제거 조건은 변하지 않았다. 이번 변경으로 새 미측정 비용이 사라졌다고 가정하지 않는다.

| setup | 남은 SNES 검사 정책 | 최대 ms | 잔여 ms | 초과 프레임 |
|---:|---|---:|---:|---|
|500|command_tail|16.028909|0.637758|없음|
|500|only_bitmap_removed|16.409777|0.256890|없음|
|1000|command_tail|16.890285|-0.223618|970|
|1000|only_bitmap_removed|17.271153|-0.604486|954,962,970|

잔여 시간은 실제 ARM·새 소비 어댑터·SNES DMA/dispatch/poll/VBlank가 함께 사용할 미확정 예산이다. capture 준비 전 NES 프레임 실행과 실제 lease 중첩도 계측 밖이다.60fps나 전체 회로 여유를 승인하는 수치가 아니다.

## 검증 범위와 보존

- 최종 test03: 실제71프레임/451SPI블록/83,240payload B 일치, receipt53,534B와CRC4,544B 및 H2 문맥2,272B 검사. 동일 query 수·payload 바이트·블록을253과 비교했다. status polling 증가분은 별도 계측했다.
- 기존14오류 검사에 부분 문맥 STOP, 문맥 완료 전 begin, 길이0, table길이0, display-base=current serial, covered 변조, mask 오류를 추가하여21검사 PASS. 각각 오류 뒤1024B RAM 불변과 ready/sealed 차단을 확인했다.
- test04: 실제4프레임에서 양 bank granule2/7/12/15, 총8개 부분 갱신. 실제 C 인증서를 재생성하며 마지막9B granule도 포함한다.
- fsm01/fsmmap01은 표현 하나의 분리 진단이다. test01은 context 배선의 선언 순서 컴파일 실패로 보존했고 test02는 수정된3프레임 PASS다. map01은 test02의 RTL 해시와 연결되며 최종 test03/test04도 같은 RTL이다. 새 fullFIT이나 seed 반복은 없다.
- 이전253 증거와 공개 구현, production227/unplaced240/rejected2412462472/GBC164/saveSRAM을 보존한다. ROM/PPU fixture/실행 로그/합성 결과는 private archive에 두고 공개에는 생성기·집계·계획만 추가한다.
- 실제 ARM N5 복원/계획/H2 전치/출력 전송·fullRUN/IRQ, SNES 소비/은행별 표시 이력/최종 ACK 연결, MCU 시간, mapper/CDC/IO STA는 미완료다. display-base<serial 검사는 실제 표시 이력 검증이 아니다.71프레임은 raw2이므로 새 raw0 통합 전환도 미실행이며 이전250 검사는 보존한다.
- CRC16은 오류 검출이며 인증이나 충돌 없는 증명이 아니다. source와 SPI host/mailbox의 다른 클록 수명은 합치지 않았다.

## 판단과 다음 단계

FSM 추출 수정의 효과는 보존하되 현재 query 통합을 제품 구현으로 채택하지 않는다. 다음 후보는 query 선행 읽기의 시간 이득과 cursor 기반 주소 해독 비용, receipt의 범위·manifest 제어 및 실제 출력 소비 어댑터를 같은 경계에서 함께 설계해야 한다. 별도 query FSM을 단순 복원하거나 레지스터만 줄였다고 전체 이득으로 계산하지 않는다. ARM N5 복원·계획·H2 전치·출력 전송·fullRUN/IRQ, 실제 SNES 소비/표시 이력·DMA/poll/VBlank 및 캡처 lease 중첩 비용을 포함해야 한다. 근거 없는 fullFIT/ROM/opcode/seed 반복은 하지 않는다.

[현재 계획](nes-joint254-plan.json) · [집계](../analysis/joint254-verification.json) · [프레임별 시간](../analysis/joint254-frames.csv) · [조건부 일정](../analysis/joint254-schedules.csv)
