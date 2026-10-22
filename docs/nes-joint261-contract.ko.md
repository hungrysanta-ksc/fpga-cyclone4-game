# NES261 — 실제 source·map receipt·표시 lease 통합

PR130의 NES260 묶음 경로를 실제 collector/query/source/공유 CRC·RAM core와 연결했다. packet CRC→범위 staging→SNES consume→core receipt→H2/manifest 검사→최종 표시 ACK→lease 해제를 한 통합 경계로 만든다. production227/GBC164/saveSRAM은 변경하지 않는다.

이 단계의 판정은 **map 경로의 기능 연결과 묶음 전송 이득은 유지되지만, 전체 회로 여유와60fps는 아직 확보되지 않았다**이다. 새 top은 실제 입력 source와 출력 경로를 함께 포함한다. ARM N5/planner/RUN/IRQ, 일반 출력 명령에서 core로 들어오는 non-map/H2/manifest 생산기, tile192/ROM 중재와 전체 board FIT/STA는 여전히 경계 밖이다.

## 연결과 검증 경계

`nes_joint261`은 source257와 output260을 같은 SPI 핀에 붙인다. D0..D3 source와 E0/E1 output의 실제 selected 신호로 MISO를 중재한다. 독립 진단 CRC나 무료 query 생산기를 쓰지 않는다. 실제201 collector의 관측 프레임을 query하고 N5 bytes를 내보내며, 입력 완료 후 collector를 해제하고 captured epoch/generation의 표시 lease를 유지한다.

output260의 가짜8cycle receipt 응답과 시험 코드의 sealed 상수는 제거했다. DMA token의 정상 소비를 host→NES mailbox로 넘겨 core의 V_STREAM→V_RREAD/V_RWRITE를 실행한다. core가 다시 ready가 된 뒤에만 다음 범위를 열고 마지막 범위 뒤 packet credit을 반환한다. 최종 ACK도 core의 실제 v_sealed를 전제로 하고, core IDLE 및 lease 해제까지 확인한다. STOP·flow/core/lease 오류가 서로의 가시성과 메모리 갱신을 취소한다.

ARM260이 앞 단계에서 실제 실행해 생성한 batch의 **모든 descriptor/value와 packet 분할**을 사용한다. 이번 시험에서 일반/tile 명령은 기존 fixture 경계이므로 packet sequence와 시작 token은 이 경계의 live namespace에 다시 결합한다. 따라서 전체 ARM 명령열을 새 core와 동시에 실행했다는 뜻은 아니다. 원본 packet hash, 바뀐 시험 header, 각 bank 복원 결과를 분리해 보존한다.

non-map range stream, H232B context·fresh scroll·raw-tail granule bytes 및422B manifest 공급은255 fixture다. core에서 CRC와 receipt/manifest 비교는 실제 실행하지만, 실제 일반 출력 packet에서 이 입력들을 생산하는 회로는 아직 없다. 현재 시험은 non-map fixture를 마친 뒤 map 구간을 실행한다. 실제 일반 packet 생산기와 map receipt가 동시에 core ready를 요청할 때의 중재도 추가로 구현해야 하며, 이를 무료로 처리했다고 계산하지 않는다. 특히 ARM260은 H2op13을 SEAL 직전에 보내지만 core는 V_IDLE에서 begin보다 먼저 context를 받는다. 이 순서 차이를 숨기지 않으며, ARM prelude/prepass 또는 검증기 context 시점 변경을 포함한 후속 설계가 필요하다.

## manifest 정합에서 찾은 문제

기존250/255 fixture는 gap16 map 정책이고 ARM260은 실제 sparse 범위를 사용한다. 첫 전체 시험의914프레임에서 기존 manifest가57word를 요구하지만 현재 ARM 전송은41word여서 core가 정확히 fault3으로 거절했다. 이는 새 입력의 생산 오류를 증명한 것이 아니라 서로 다른 두 계획의 접속 불일치다.

수정한 시험은 각 bank의 마지막 표시 이미지에 실제 ARM descriptor/value를 적용하고,4096B 전체가 해당 프레임의 기대 이미지와 동일한지 독립 확인한다. cold bank는2048word 전체를 요구하고 중복 범위도 거절한다. 그 뒤에만 실제 범위의256B map manifest와 기대 receipt RAM을 재구성한다. non-map166B 및 영속 validity·CRC 기대값은 그대로 유지한다. 단순히 core가 만든 receipt를 다시 기대값으로 읽는 검사가 아니다.

## 회로 비용과 실제 대체 대상

Quartus **Lite25.1std**에서 검증된 통합 top을 한 번 MAP했다. source/core를 출력 standalone 수치에 덧붙여 추정한 값이 아니다. 합성 경계의507개 I/O는 내부 접속점까지 외부 port로 드러낸 것이며 실제 board pin 배치가 아니다.

| 통합261 inclusive 계층 | comb | FF | memory bits |
|---|---:|---:|---:|
| 전체:7141 LE |5665|2788|90368|
| source/query/CRC/receipt core |3139|986|49152|
| output queue/parser/tile producer/aperture |2326|1703|41216|
| 표시 lease |167|99|0|
| 상위 접속 논리, exclusive |33|0|0|

부모·자식은 중복 합산하지 않는다. 아래240 수치는 이전 전체 MAP 계층의 제거 후보를 식별하기 위한 장부이며 새 통합 MAP과의 차이를 whole-FIT 여유로 해석하지 않는다.

| 기존240 기능 | comb / FF / memory bits |261 교체 또는 유지|
|---|---:|---|
| native_source240 전체 |2092 /974 /57344|core257로 교체; encoder/query235/transport235를 중복으로 남기지 않음|
| sink queue endpoint |679 /424 /8192|단일 일반/typed head·ACK·credit queue260으로 교체|
| direct bulk |465 /512 /33024|tile producer+공유 aperture로 교체; 이전 두 저장소를 함께 남기지 않음|
| direct bulk control |100 /174 /0|통합 token/consume/최종 ACK 제어로 교체|
| capture lease |기존 실제 회로 유지·재접속|새 통합 MAP의167comb/99FF에 포함; 무료 회수로 계산하지 않음|
| SNES bus/ROM |66 /149 /32768|유지; 새 control aperture와 bus 선택부 접속 필요|
| tile192/cache/ROM reader/arbiter 및 direct 나머지 |기존 회로 유지|제거 후보 아님; 실제 경쟁 시간도 아직 미확인|

위 source+queue+bulk+control의 중복 없는 기존 subtotal은3336comb/2084FF/98560bits다. 새 lease·상위 접속을 제외한 core+output은5465comb/2689FF/90368bits로 **계층 장부상 +2129comb/+605FF/-8192bits**다. 합성 경계가 다르므로 LE 차감/FIT 절약은 아니다. 그럼에도 기존 제어를 제거하면 자동으로 논리 여유가 생긴다는 근거는 없고, 미구현 일반 명령 생산기까지 추가 비용이 남는다. 기존240의490LE/40LAB 부족은 해소 승인하지 않는다. whole-FIT 반복은 실행하지 않았다.

## 시간 회계

71프레임 source+map+실제 core 검증의 이벤트와 기존260 실제 ARM 일정은 출처를 구분한다. 새 시험은 NES half-period22.727ns와 host half-period5.952ns(약22/84MHz)를 사용한다. 이전260 출력 단독 시험의100MHz host와 같지 않으므로 이전 전체 일정에 새 구간을 더한 값은 민감도 계산으로만 제시한다. 새 시험의 SNES bus 모델은200ns active+200ns release, 범위 setup500master-clock=23.28us다. non-map stream의 마지막 byte256cycle stall은 의도한 검증 지연이므로 실제 실행 비용으로 취급하지 않는다. source 캡처 stimulus를 재생하는 시간도 프레임 처리 예산에 합산하지 않는다.

실제65816/Mesen 연결은 cold map4096B의64 DMA와22묶음, 실제 VRAM·BG1SC/unblank/VBlank·최종 ACK를 검사한다. 파일RPC는 불변 DMA chunk 한 개의 실제 RTL 순차 read를 한 요청으로 실행하고, 실제65816은 각각의 byte를 읽은 뒤에만 consume을 쓴다. RTL read4096개와 CPU read4096개를 주소/값별로 대조한다. 파일RPC가 host bus를 늘리므로65816 master-clock와RTL 시간은 서로 독립된 측정이며 물리 총시간으로 합산하지 않는다. 일반 metadata/OAM/HDMA 설정 전체와 실제 완성된 SMB3 화면을 검증한 것은 아니다.

CPU는 다음 chunk의 준비 상태 또는 sealed를 기다린다. 범위 사이6051 receipt 표시는 짧을 수 있으므로 이를 지속적인 CPU polling 응답으로 가정하지 않는다. 다음 staging 자체가 이전 core receipt 완료를 전제로 한다.

같은4credit 공급·같은 실제 core·같은 bus 서비스로 비교한 출력 구간은 다음과 같다. non-map fixture와 의도한 stall을 포함하므로 전체 실제 출력 시간으로 해석하지 않는다.

| frame | 단일 범위op12 ms | 묶음op14 ms | 같은 경계 절약 ms |
|---|---:|---:|---:|
|905 cold|18.392279|15.764629|2.627650|
|906 cold|18.468687|15.840992|2.627696|
|907 warm|0.857717|0.626674|0.231043|

초기1packet 공급 시험에서는 cold가 단일18.452733ms/묶음19.152679ms로0.699946ms 역전됐다. 묶음 전체 receipt를 기다리며 다음 SPI 전송을 막은 시험 정책 때문이었다. 네 credit 이내에서 다음 packet을 선행 공급하고 future token을 예약하도록 고친 뒤의 결과가 위 표다. 이전 시험도 보존한다. 실제 ARM260의 status polling/명령 비용은 이번 fixture 공급기에 포함되지 않는다.

실제 cold65816의 준비 상태 확인→consume64회는 **1412..1460 master clocks**였다. 명목64B DMA512클록을 제외한900..948클록에는 CPU setup·token 처리·refresh/정렬이 포함된다. 따라서 이전500클록 setup 모델을 실제 CPU 비용으로 확정할 수 없다. 이는 cold64B 명령 경계 측정이며 warm 작은 범위나 전체 command loop의 WCET가 아니다.

| 이전260 공유SPI 조건 | 이전 ms | 실제 tail + setup500→900 직렬 민감도 ms |16.667ms 대비 잔여 ms|
|---|---:|---:|---:|
|954/CPI1|14.381105|15.286926|1.379740|
|963/CPI1|12.931113|14.041803|2.624863|
|970/CPI1|14.447141|15.520582|1.146085|
|954/CPI2|16.549534|17.455355|-0.788688|

각 map 범위에400master clocks를 직렬 가산한 민감도다. 실제 중첩을 다시 스케줄한 결과가 아니며 이전 모델의 token bus write와 일부 중복한다. **상한·하한·실제60fps 실패/성공 판정으로 쓰지 않는다.** 다만 CPI2의 이전0.117ms 잔여를 확보된 여유로 취급하는 것은 부적절하다. 전체 비용의 미확인 항목은 JSON/CSV에서 null로 유지한다.

warm heavy7에서 마지막 map 완료 이후 실제 core 검사와 최종 bus ACK까지는 약0.067727ms다. cold는 약0.094ms다. 이 구간을 이전260 전체 일정에 통째로 더하는 보수적인 민감도는 별도 비용표로 제공하며, 이미 포함된 ACK와의 일부 중복·다른 host 클록 때문에 새로운 정확한 전체 시간이나 상한은 아니다. context 선행 전달/422byte manifest 생산·일반 출력 중재/실제 tile ROM/IRQ/VBlank는 여전히 별도 미확인이다.

최종 수치와 선택 실행은 plan/analysis 파일을 참조한다. 전체60fps를 승인하려면 미확인 항목을0으로 둘 수 없으며, 기존260 CPI2 공유SPI16.549534ms의0.117133ms 잔여 역시 확보된 여유가 아니다.

## 다음 판정

묶음 형식은 시간 이득을 보존하는 후보로 유지한다. 회로는 단순 병렬 연결로는 충분하지 않다. 다음 변경은 일반 출력 packet→core context/stream/manifest의 실제 생산 경계와 H2 선행 문맥 문제를 먼저 고정하고, source+output의 중복 제어를 정말 제거할 구조를 전체 비용표에서 선택해야 한다. 남겨 둔op12 분기 하나를 없애는 것만으로2129comb 장부 증가나 기존490LE/40LAB 부족이 해소된다고 가정하지 않는다. full ARM/실제65816 전체명령/tile ROM 경쟁의 비용이 닫히기 전 P2 및 whole-FIT/STA/실기60fps 승인은 보류한다.

## 선택 증거와 재현

선택은test05(71frames+6취소),single02(905..907 같은4credit op12),cpu02(64DMA/4096B 실제VRAM),map01(Lite 한 번, test02와동일 RTL),analysis01이다. map01과 최종 시험의 모든 합성 source hash가 같다. 입력 source83240B는249 기준 byte oracle과 일치하며255의 source 준비/query/전송 작업은 같고 CDC 대기 총시간 차이는-1..+1NEScycle다. non-map383ranges의 생산기는 여전히 fixture다. CPU ROM body181B는 이 map 진단 실행부의 크기이며 전체 SNES 프로그램 크기가 아니다.

첫test01 선언 순서 컴파일 오류, test03 정책 불일치, test04/single01의1packet 일정, cpu01 request291 파일 공유 오류와 로그를 보존했다. 최종 RPC는 파일 읽기의 일시적 공유 오류를 재시도하고 chunk read를 한 요청으로 묶는다. 라이선스 오류가 아니며 기존FLOAT 방식과 Lite만 사용했다. Python/JSON·근거hash·CPU/RTL read 대조 및git diff 검사를 수행한다.

[계획](nes-joint261-plan.json) · [검증](../analysis/joint261-verification.json) · [비용표](../analysis/joint261-costs.csv)
