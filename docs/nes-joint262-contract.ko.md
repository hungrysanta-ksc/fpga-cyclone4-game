# NES262: H2 선행 문맥과 기존 완료 통지 경로 공유

NES261의 ARM 출력은 H2를 SEAL 직전에 보냈지만 실제 core는 BEGIN 전에 문맥32B를 요구했다. NES262는 이 순서를 실제 패킷으로 연결한다. 전체 일반 출력 생산기와 전체60fps 검증을 완료한 단계는 아니다. production227/GBC164/saveSRAM은 유지한다.

## 확인 결과

ARM71계획은 H2→BEGIN 순서와 기존 인증서·일반명령·map 값이 일치했고 전체 SPI bytes/status 횟수/packet 수가 변하지 않았다. text2244→2320B(+76),bss312B 유지, 관측 stack144→136B다. 전체 serializer 명령 차이−380..+1587은 컴파일 및 polling 순서 차이를 포함한다. 최대 증가는84MHz/CPI1 가정18.893us이며 실제 MCU 시간이나 순수 prepass 비용이 아니다. 기존12오류와 새6선행검사,65530→41 counter wrap/4credit를 통과했다.

공유 구조는71프레임의32B H2 문맥2272B,124묶음/2069map범위/13406B와 source83240B를 검증했다. 기존6취소 외 BEGIN 선행,짧은 H2,중복 H2,잘못된 bank,문맥 CDC 중 STOP,최종 인증서 CRC 오류의6검사를 통과했다. 각 오류에서 최종 표시/lease 차단 및1024B RAM 동결을 확인했다. 별도 partial01은8B가 이미 RAM에 반영되고 다음 byte가 CDC에서 대기할 때 STOP을 넣어 BEGIN 미발행과 RAM 동결을 추가 확인했다.

| 동일 통합 경계 | LE | comb | FF | RAM bits |
|---|---:|---:|---:|---:|
|261: 문맥/BEGIN 외부 fixture|7141|5665|2788|90368|
|262: 별도9bit mailbox|7266|5773|2830|90368|
|262: 기존24bit mailbox 공유|7216|5755|2806|90368|

공유로50LE/18comb/24FF를 줄였다. 이는 같은 기능 경계의 합성 결과 차이이며 mailbox 인스턴스 자체만의 cell 수로 귀속하지 않는다. core RTL이 같아도 연결 조건에 따라 최적화가 달라졌다.261 대비 H2/BEGIN 실제 연결의 순증가는75LE/90comb/18FF다.

기존 제거 장부3336comb/2084FF/98560bits에 대해 새 core+output(lease/top 제외)은5555comb/2707FF/90368bits다. 장부상+2219comb/+623FF/−8192bits이며 서로 다른 합성 경계이므로 whole-LE 회수 계산은 아니다. 기존490LE/40LAB 부족은 미해결이다.493개 top I/O는 내부 진단 경계이며 실제 보드 pin 수가 아니다. async_reg 등 기존 경고를 보존했으며 새 FIT/STA/CDC 면제를 만들지 않았다.

같은900서비스에서 공유−별도 출력 시간 차이는 [0.0, 0.0]ms다. 각 프레임 결과는 비용표에 보존했다.

| frame | 261 fixture/500 | 262 실제 prelude/900 | 복합 변화 |
|---|---:|---:|---:|
|905|15.764629ms|16.063080ms|+0.298451ms|
|907|0.626674ms|1.036897ms|+0.410222ms|
|954|2.249746ms|3.368141ms|+1.118396ms|
|963|2.511015ms|3.834454ms|+1.323439ms|
|970|2.454016ms|3.740182ms|+1.286166ms|

별도 구조의 test03은 정상71프레임과11오류를 통과했지만 PRENEG6에서 시험 코드가 DMA 서비스까지 꺼 대기했다. 해당 simulator만 종료하고 로그를 보존했다. 최종 공유 test05는 수정한 서비스 조건으로12오류를 모두 통과했다. test01 선언 순서 오류와 첫12개 ARM guard 결과도 보존했다. map01은 test02, map02는 test04와 같은 RTL이며 최종 공유71시험의 합성 소스가 map02와 일치한다. 새 실제65816 실행을 했다고 주장하지 않으며261 CPU 증거를 서비스 민감도의 출처로 사용한다.

## 실제 연결 범위

ARM262는 호출자가 반환 시점까지 보존하는 plan/material을 사용한다. 길이·serial·generation과 마지막 SEAL을 먼저 확인한 뒤 기존 H2 패킷을 맨 앞으로 옮긴다. 인증서용 추가 버퍼나 패킷은 없다. N5 decoder/planner/RUN/IRQ를 새로 실행한 것이 아니라 기록된71개 C 계획을 Cortex-M4 명령으로 직렬화했다. 기존 epoch1 기록 범위이며 실제 RUN의 epoch 공급까지 승인하지 않는다.

H2는 실제 SPI E1/CRC→4credit queue→기존 header reader→PREAD/PCAP/PUT의 held byte→CDC→core context RAM832..863으로 전달된다. RAM 쓰기 준비와 CDC 확인을 받은 후에만 H2 head를 retire한다. 별도 인증서32B register array는 추가하지 않는다. BEGIN은 기존 일반 packet aperture에서 SNES 소비자가 읽고 ACK한다. ACK가 성공하면 core BEGIN 이벤트를 보낸 뒤 다음 head를 허용한다. BEGIN보다 앞선 H2, 중복 H2 금지, frame별 재입장, STOP 시 공통 취소를 유지한다.

이번 BEGIN 소비자는 정확한28B 기록 패킷을 읽어 비교하고 실제 ACK register를 쓰는 버스 서비스 모델이다. 일반 BEGIN 의미검사 전체와 실제65816 명령 실행은 이 시험의 범위가 아니다. H2/BEGIN의 실제 ARM 생성 bytes를 replay하며 map의 sequence/token은 생략된 일반/tile 명령 때문에 현재 시험의 실제 namespace에 다시 맞춘다. full ARM→SPI 동시 실행으로 표현하지 않는다.

그 뒤 map packet→staging→SNES bus DMA→범위별 core receipt→검사→최종 ACK→lease retire는261의 실제 경로를 유지한다. freshscroll/rawtail digest 입력,383개 non-map 범위의 stream,422B manifest 생산은 아직 fixture다. CRC는 무결성 검사이며 인증·충돌 없음의 증명이 아니다.

## 비교할 두 회로

첫 구조는 H2/BEGIN용9bit mailbox를 추가한다. 둘째는 기존24bit map 완료 mailbox를 공유해 그 추가 인스턴스를 제거한다. map first는0..2047이며 parser가 상위 bit11을0으로 생성하므로 메시지 bit23이 항상0이다. bit23=1을 제어 메시지로 쓰고 bit22로 H2 byte/BEGIN을 구분한다. 이 값은 외부 패킷의 임의 tag를 그대로 신뢰한 것이 아니라 검증된 parser 상태에서 생성한다.

H2/BEGIN 단계에는 map receipt FSM을 진행시키지 않는다. map 단계에서는 기존 범위 admission→DMA done→receipt handshake를 유지한다. 두 생산자는 동일한 parser 상태에서 서로 배타적이다. 이 변경은 CDC synchronizer를 생략하거나 두 clock을 같다고 가정하지 않는다. 별도/공유 구조의 실제 합성과 같은 서비스 조건 시뮬레이션을 비교한다. 최종 수치와 선택 실행은 [검증 JSON](../analysis/joint262-verification.json)과 [비용표](../analysis/joint262-costs.csv)에 기록한다.

## 시간 계산의 범위

261 실제 cold CPU에서 ready→consume은1412..1460master clocks였고 nominal64B DMA512를 제외하면900..948이었다. 이번 버스 서비스의 setup 배정을500→900으로 바꾸어 RTL 일정 안에서 중첩을 다시 관찰한다. 900은 cold 측정에서 얻은 민감도이며 warm WCET가 아니다. 별도 token bus write와400ns/byte 서비스도 그대로 비용에 들어간다. 따라서 이 수치를 실제 CPU 처리시간이나 상한으로 쓸 수 없다.

별도/공유262 비교는 같은900 배정과 같은 생산자 조건이다. 261 비교는 context/BEGIN의 실제 wire 연결과 setup 변경이 함께 반영된 차이다. 그 차이를 모두 H2 추가 비용이라고 부르지 않는다. 260 전체 ARM 일정에는 H2/BEGIN wire가 이미 있었으므로262 출력 경계의 증가분을260 전체 시간에 통째로 다시 더하면 중복 계산이다. 전체 시간·whole-board LE 여유는 null로 남긴다.

## 다음 판정

공유가 국소 비용을 줄여도 기존 source+queue+bulk+control 제거 장부와 비교한 전체 논리 부족이 해소되는지는 별개다. 다음은 일반 명령/manifest 생산과 기존 header·ACK·receipt 제어의 실제 대체를 같은 경계로 연결한다. 동시에 SNES가 묶음의 bank/generation/tokenbase를 한 번 받아 범위마다 재사용하는 소비 경계를 검토해,900 배정의 실제 dispatch/token 비용을 줄일 수 있는지 실제65816에서 비교한다. 기존 token·전체 byte 소비·범위별 receipt·최종 표시 ACK 보장은 유지해야 한다. full ARM/ROM 경쟁·whole FIT/STA/CDC/IO 게이트 전에 제품 구현이나 실기60fps를 승인하지 않는다.

Quartus Lite만 사용하며 별도/공유 구조별 MAP 한 번씩 비교한다. whole FIT 반복, ROM opcode/seed 조정, production227 재시험은 이 단계에 포함하지 않는다.
