# Packet 완료·전달·큐·프레임 동기화 모델 — 026

2026-10-05. 분석 후보 NES-R2-PACKET-PACING-026 / 구현 NES-P2-RDY-014.
최근 실제 SNES 실행은025, NES CPU 기능017, 자원018이다.
이번에는 기존022..025의 실제 기록에 연결한 모델과 독립 검증기를 실행했다.
새 에뮬레이터/RTL/Questa/Quartus/실기 실행은 없다. 이전025의224hash 및 상태6파일을 보존했다.

## 입력 시간 기준과 가정

021의 fine_x/sprite/split/banks32 sourceframes6..9를 검증하고,
022..025의 packet header release tick, raw SNES phase 시작/끝, 캡처 시각 및 기존 manifest hash를 대조했다.
source line0 dot5의 tick에서20을 뺀 값을 frame anchor로 정의한다.
마지막 실제 BG plane은 anchor+326984ticks, 인접 source frame 차이는357364/357368/357364ticks다.
기존 SNES 관측도 frame 간격357364 또는357368ticks였다.
두 에뮬레이터의 절대 시작 시각을 서로 빼서 동기화된 것으로 취급하지 않는다.

모델은 nominal NES/SNES frame 기간을357364,357368 반복으로 놓고,
source 시작 위상과 상대 속도 ppm을 별도 입력으로 둔다. 실제 보드 클록/위상/드리프트 실측은 아니다.
VBlank 시작327360, poll112, frame끝4tick guard, 표본별 최대 소비 시간을 사용한다.
아직 구현되지 않은 ready 대기 이후에도 같은 소비 시간이 든다는 가정이다.
encode1024ticks, CDC 가시화8ticks, 직렬 전달2 또는4ticks/B는 설계 탐색값이며 측정값이 아니다.

slot은 마지막fetch에서 claim하고 encode→직렬전달→ready→SNES소비→commit까지 유지한다.
commit 전에 slot을 반환하지 않는다. 전달은 직렬이며 앞 packet의 전달이 끝나야 다음 것을 보낸다.
producer frame 시작부터 마지막fetch까지 필요한 scratch 저장 공간은 이 모델에 포함하지 않는다.
따라서 slot 수는 전체 영상 RAM이나 실물 FIFO 용량의 증명이 아니다.

## 정렬된 위상에서의 전달 예산

짧은 frame끝−4−마지막fetch−관측최대소비시간으로 생산·전달의 총 허용량을 계산했다.

| 표본 | packet B | 소비 clocks | 생산·전달 허용 clocks | encode1024+CDC8 이후 | 정수 clocks/B 상한 |
| --- | ---: | ---: | ---: | ---: | ---: |
|022 fine-X|2008|19618|10758|9726|4|
|023 sprite|2052|21470|8906|7874|3|
|024 split|2328|22788|7588|6556|2|
|025 banks32|2008|19732|10644|9612|4|

같은 frame에 표시하는 정렬 위상에서 전달2ticks/B 가정은 네 표본 모두 통과했다.
4ticks/B는 sprite가334ticks, split이2756ticks 늦었다. 실제 물리 버스가 이 속도라는 뜻은 아니다.
split은2ticks/B일 때 source 위상1900까지 경계 통과,1901부터1tick 실패했다.
소비자가 packet이 올 때까지 기다릴 수 있어야 하는 모델이며 기존 ROM 소비자에 그 대기를 구현한 결과는 아니다.

## 위상·소유권·장기 속도 차이

split을16frames 반복하는 시간 모델로 한 scanline 간격의263개 위상을 샘플링했다.

| 표시 frame index 지연 | slots | 통과 위상 |
| --- | ---: | ---: |
|0|2|2/263|
|1|2|263/263|
|2|2|245/263;18조건 slot 부족|
|2|3|263/263|

한 frame index 지연은 시작 버퍼링 시나리오다. 정상 frame 삭제/반복/감속을 채택하지 않았다.
지연을 늘리면 필요한 소유 slot 수가 늘 수 있다.263개 표본 통과는 연속 위상 전체에 대한 증명이 아니다.
nominal0ppm/위상0/지연1/2slots는60,000frames 시간 모델에서 통과했고 최대 소유2slots였다.
이는60,000개의 새로운 화면이나 실제 장기 SNES 재생 검증이 아니다.

같은 조건에 상대 속도 오차를 주면 다음 첫 실패가 발생했다. 양수는 NES producer가 더 빠른 가정이다.

| 가정한 ppm | 첫 실패 source frame | 결과 |
| --- | ---: | --- |
|-1000|1005|소비 기한 초과|
|-100|10053|소비 기한 초과|
|0|없음/60000까지|시간 모델 통과|
|+100|9350|3번째 slot 필요|
|+1000|936|3번째 slot 필요|

finite queue는 지속적인 서로 다른 생산·소비 속도를 무한히 흡수하지 못한다.
실제 클록이 공통 기준인지, NES enable 생성과 SNES frame 간 위상 관계를 어떻게 유지할지 확인해야 한다.
버퍼를 늘리는 것만으로 정상 frame 무손실/정상 속도를 보장할 수 없다.
모델은 첫 deadline/overflow를 실패로 기록하며, 이후 가상 계산을 실행 성공으로 사용하지 않는다.
실패를 없애려고 frame을 버리거나 반복하거나 NES를 멈추는 정책은 넣지 않았다.

## 검증과 후속 구현 계약

별도 tick-by-tick 참조 모델300개 결정적 난수 조건과13개 경계·회귀 검사를 통과했다.
딱 기한에 끝나는 경우/1tick 늦는 경우,2KiB에2328B 거부,slot 중복 소유,
빠름/느림의 장기 실패를 확인했다.
초기 수기 테스트는 phase357363/lag1을 실패로 잘못 예상했다.
이는 사실상 phase0/lag0와 같은 빠른 전달 조건이므로 통과가 맞다.
300개 독립 참조 검사는 이미 통과했으며, 모델 방정식을 완화하지 않고 기대값을 고쳤다.
phase1900/1901 실패 경계를 추가했고 초기 소스/실패 로그/설명을 보존했다.

현재 저장 후보는3KiB×2 data slots=6KiB 또는4KiB×2=8KiB다. 채택한 FIFO 깊이는 아니다.
길이/세대/sequence/ready/소유권 metadata,producer scratch,CDC 구조/동기화 비용은 별도다.
다음 구현은 기존 보드의 클록·enable 경로를 확인하고,
FREE→WRITING→READY→READING→FREE 프로토콜과 ready-gated consumer를 실제 인터페이스로 연결하는 것이다.
reset/오래된 세대/잘못된 길이/반쯤 쓰인 packet에서 DMA가 시작되지 않게 해야 한다.
025CHR와023OBJ의 VRAM 충돌 및024patch 결합도 해결한 뒤018 자원 구성을 확대한다.

R2/R4 완료나 하드웨어 기한 보장은 아니다. GBC C44/0.9.0, 기존 코어와 upstream 보존.
동시240줄/최종색/DMC/SMB3/전체board fit·STA/실기/HDL 반입 hold는 남아 있다.

[모델 JSON](packet-pacing-model.json), [테스트](packet-pacing-tests.json),
[재현 계약](../docs/nes-packet-pacing-contract.md), [증거](packet-pacing-artifacts.json).
