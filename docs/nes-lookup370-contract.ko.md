# NES370 group-local membership과 긴 연속 일정의 입력·ROM 기한

PR132의369 커밋 `451aec33ef3498bb7c39d259fb3e5825e3d47f48`을 기준으로 같은 브랜치에서 진행했다. private 원본은 `probes/nes-source370`, 최종 검증은 `analysis/lookup370-verification.json`이다.

## 판정

909의 모델 처리 시간은16.873457→16.215692ms로 줄어60Hz 예산에 들어왔다. 그러나 길게 실행하자 **915 캡처가 거절**됐다.914의 마지막 local 저장은 기한보다273.973us 늦었고,914 처리 시간은21.545718ms였다. 현재 표시 부족량은4.879051ms,입력 인계 부족량은0.273973ms다. 더 긴 검사에서 발견한 값이며369에서 측정하지 않은 후반 프레임을 단순 회귀로 부르지 않는다. **지속60fps·실기는 미승인**이다.

strict `joint01 --last915`는915 첫 거절에서 즉시 실패했다. 진단 `joint02 --last914 --observe-last`는915 거절을 유지한 채914만 배출한 뒤coverage 오류로 종료했다. 모든 CSV event가 첫 실패 시점까지 정확히 같다. 진단의905~914 완료10프레임에는 초기화2개와warm8개가 포함된다. 다음908~914 캡처7회 승인,915 거절1회이며 계획한905~915 정상 완료는 미달성이다.

## 실제 구현과 검사

909의 BG 조회792회 중 두 tag를 번갈아 확인하는 경우가 많았다. `step286`의 한 BG group 호출 안에서 **성공한 BG membership 두 개만 재사용**한다. miss는 원래 binary search와kind 검사를 그대로 수행하고 실패를 저장하지 않는다. checked tag는4B local array이며 매 호출0xffff로 초기화한다. 호출 지점의 tag는13bit이므로 sentinel과 같을 수 없다. input은 기존 계약대로 group 실행 중 불변이다. 다음group·입력·generation·cold·STOP에 유지되는 캐시/권한은 없다. OBJ lookup과 exact-key/slot 할당도 바꾸지 않았다.

41개 실제909 snapshot에서 반환값과96개 전역 객체가 기존과 일치했다. BG 실제 검색은792→189,OBJ8회는 그대로다.369 대비55253명령 절감(할당CPI1/84MHz에서0.657774ms)을 확인했지만 이를 실제 일정 이득에 추가하지 않는다. 기존320descriptor/5STOP 대조도 통과했다. 추가45case는tag 누락·kind·alternate·generation·STOP·이전 stack 내용이 남은 다음 호출·3/4/8tag 순환을 대조한다. 주소는ARM 헤더를 컴파일한layout370.o의offset과 대조했다.

미선택build01의 단순 binary-search 일치 조기 반환은41단계에서7452명령만 추가 절감했다. 이는 새 처리 시간 측정이 아니며 선택하지 않았다. 선택build02는기존 binary search를 유지하고 local 재사용만 추가한다.

## 실제 ARM·SPI·IRQ·ROM 일정

907 캡처 시작은 기존과 같은 사전5371247 NESclock,이후357368clock 주기다. readiness에 맞춰 기한을 미루지 않는다.907~909 및911은369와 source 시작·ROMcycle가 같고,910은선행backlog 변화로 달라 별도 구분한다.

|frame|369 ms|370 ms|변화 ms|동일 시작·ROM 위상|
|---|---:|---:|---:|---|
|907|12.037514|12.040741|0.003227|예|
|908|12.574099|12.417419|-0.156680|예|
|909|16.873457|16.215692|-0.657765|예|
|910|12.027151|12.030379|0.003228|아니오|
|911|12.570599|12.479010|-0.091589|예|

|후반frame|처리 ms|마지막 local 저장 ms|입력 ACK ms|
|---|---:|---:|---:|
|912|15.424883|1.719162|3.307165|
|913|12.130105|0.568721|2.165770|
|914|21.545718|2.614195|3.704796|

907/910의약3.23us 증가는 숨기지 않는다. 초기화905/906은85.318135/114.773782ms이며 warm 이득과 분리한다. 독립 read→unit→private write→publish,2credit,프레임별12exact display reads/token과 실제retire를 대조했다. ROM 요청/응답57623/57623,입력에서 시작한 요청/응답8908/8908,pending0이다. 모든 응답 값 검사는 유지한다. 진단은의도된coverage 오류1·경고0이며 통과로 바꾸지 않았다.

## 914의 두 병목

첫payload 완료1.164641ms에서hint wire 시작1.657177ms까지0.492536ms가 걸렸다. 같은 causal snapshot의실제hint 함수는8917명령,해당 전송까지pending 명령은41373이다. 나머지32456을 전부decoder 비용이라고 단정하지 않는다. hintpacket28B 전송은1.750510ms에끝났다. 다음payload는2.381617ms까지여서2.340222ms의 다음capture 기한을 이미 넘는다. 마지막 local 저장은2.614195ms,입력ACK는3.704796ms다.

현재source는block286의CRC+N5 의미검사와선택hint가끝난 뒤다음D4에서pop을보낸다. 저장credit과foreground 의미완료가 결합돼있다. 다음후보는raw CRC가확인된payload를별도RX buffer에보관하고저장반환과의미완료를분리하는방식이다. 기존259B wire를bank0으로재사용하고250B bank1+32B문맥(추가282B)을예비예산으로잡되,DMA·CRC·token순서·SPI중재·STOP drain·목표전체firmwareRAM/WCET는아직구현/검증하지않았다. 미실행중첩이득은0이다.

출력 경로에는 hint/ROM 소유권과 공급 대기가 있다. 실제 BG plan의 SPI 전송은8.926865ms에 끝났지만 zero 결과는16.897933ms, 첫 BG 결과는16.901206ms였다. RTL은 hint_active 동안 zero를 포함한 실제 plan 승인과 cache request/reply 경로를 hint에 독점시킨다. 이 간격 전체를 BG ROM miss로 단정하지 않는다. 실행 후 확인한6개 BG tag 중6136/6554/6555가 초기 hint에 없었지만, 이 미래 plan 정보를 hint 생산에 넣지 않는다. 다음 비교에는 input RX뿐 아니라 hint의 안전한 양보·drain·read/reply owner 전환을 포함한다. gate만 제거하면 진행 중 응답이 잘못된 소비자에게 갈 수 있다.

## 전체 비용과 포트 경계

ARM text34186→34234B(+48),data4/BSS48476B 및관측stack1288B 동일이다. 모든DUT RTL은369와바이트가같으며기존13canonical/30공통 compiled module에연결된다. 새Quartus MAP은실행하지않았다. 기존Lite22710LE/17698comb/9171FF/292448bits를상속하며이번회로절감0,2290comb부족/155여유포함2445순삭제가남았다. FIT/STA도실행하지않았다.

|실제RAM|크기|포트A|포트B|유지할소유권|
|---|---:|---|---|---|
|source immutable blocks|512B|NES 쓰기|host 읽기|D4 저장반환≠입력commit≠표시ACK|
|expected+출력queue|1024B|host E1쓰기|host packet읽기/expected읽기·쓰기|expected472B와256B슬롯2개|
|source/validator phase RAM|1024B|NES source|host validator|기존phase grant·CDC·STOP|
|plan payload|1024B|host쓰기|NES읽기|BG부분완료≠최종END≠retire|

queue1KiB를빈packet RAM으로계산하지않는다. source와출력queue는쓰기clock도달라단순clock mux/배열병합으로제어절감을인정하지않는다. 공통host record·주소·진행실행기는expected독립성,host읽기·쓰기중재,source/output lease,plan CDC와STOP drain을포함해야한다.

7개대상모듈의겹치지않는self comb합은5840이다. 현재codec1352+checker1040을보존하는시나리오에서는나머지3448제어를1003이하로교체해야2445순삭제가가능하다. 이는필요한설계예산일뿐구현이나FIT보장이아니다. 실제삭제승인은0이다.

## 한계와 다음 작업

실제M4 C/IRQ body를실행했지만CPI1/84MHz·exception·주변장치는할당모델이다. ROM은ready-gated stress이며live NES CPU가아니다. ordinary65816 trace는재생하지만map DMA·최종표시는bus model이다. 기존VBlank firmware·production227·GBC164·saveSRAM은변경하지않았다. 전체65816/VBlank·firmware WCET·heavy7/71·다중시작위상·token/session회복·FIT/STA·실기60fps는미완료다.

369의 exact-key와370의 group-local membership 개선을 유지한다. 다음은 ARM RX 두 buffer/DMA, raw CRC 뒤 저장 credit과 N5 의미 완료 분리, 미래 정보에 의존하지 않는 BG hint 공급을 함께 검증한다. hint_active 동안 zero를 포함한 plan 승인을 막는 구조는 gate만 삭제하지 말고 drained/request-owner와 reply routing 교체로 검증한다. SPI 중재·CRC·token/generation·STOP drain·선행 ROM 기한·RAM 비용을 같은 실제 일정에 연결하고 미실행 DMA/중첩 이득은0으로 둔다. 기존259B wire 재사용+250B RX bank+32B 문맥(추가282B)은 예비 예산이며 목표 전체firmware RAM/WCET 적합성은 미증명이다. 현재 관측 목표는914 입력 인계273.973us 선행 및 표시4.879051ms 단축이다. 공통 host record/주소/진행 실행기는 source/queue/expected/plan 포트와CDC를 포함해야 한다. codec/checker를 보존하는 시나리오에서3448comb 제어를1003comb 이내로 교체해야2445순삭제를 충족하며 실제 절감이나FIT 보장은 아니다.915 실패 조건을 유지하고 heavy7/71·다중ROM위상·전체65816/VBlank·firmware WCET·FITSTA·실기를 검증한다.
