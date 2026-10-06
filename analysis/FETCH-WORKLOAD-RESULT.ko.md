# R2 실제 fetch 부하 분석019

2026-10-05. 후보 **NES-R2-FETCH-WORKLOAD-019**, 구현014 유지.
**기존 Mapper4 실제 RTL 기록에서 미래 참조 없는 캐시 부하를 측정했다. R2 전체 통과는 아니다.**

## 관측과 입력 검증
최신014 코어로 실행해 보존한009 자체 진단의4프레임을 사용했다.
BG fetch65,552건, 화소에 쓰이는 fetch61,440건과 전체256×240×4=245,760화소를
기존 ROM/oracle/Mesen 검증기로 다시 확인했다. 상용 SMB3를 관측한 결과는 아니다.
스크롤0·표시 sprite없음·CHR ROM 고정 데이터이며 BG 하위4KiB의 두 bank묶음만 번갈아 사용한다.

프레임당 실제 물리타일256개=4,096B, 관측 전체512개=8,192B다.
캐시는 캡처 첫 시점에 비운 것으로 모델링했다. 이미 이전 프레임이 실행된 기록이므로 게임 시작 부하의 측정은 아니다.
물리타일 주소를 현재 fetch에서 처음 확인하면16B 전체를 읽고 LRU로 교체한다. 미래 fetch나 다음 bank를 미리 보지 않는다.

## 캐시 용량별 요구량

| 논리 CHR 캐시 | 프레임1 | 프레임2 | 프레임3 | 프레임4 |
| --- | ---: | ---: | ---: | ---: |
|2KiB|15,328B|15,328B|15,328B|15,328B|
|4KiB|4,096B|4,096B|4,096B|4,096B|
|8KiB|4,096B|4,096B|0B|0B|
|16KiB|4,096B|4,096B|0B|0B|

표는 모든 BG latch에 반응하는 수요 LRU의 fill payload다. packet header·tile변환·역할별중복·map·palette·OAM 비용은 없다.
8KiB에서 이후miss0은 이 표본의 두 묶음이 모두 남기 때문이다. 일반게임의 충분한 용량이라는 뜻은 아니다.
관측union8KiB만 골라 시작 전에 넣는 것은 미래 지식이므로 이 모델에서는 하지 않았다.
ROM 전체16KiB는 로더 시점에 알 수 있어 별도의 시작 시 사전 적재 후보가 될 수 있지만, SNES VRAM배치·표시형식은 아직 검증하지 않았다.

unused fetch를 뺀 비교에서는2KiB의 프레임당15,360B가 나왔다.
접근 순서를 줄이면LRU 이력도 바뀌므로 이 값을 무조건 더 작은 하한이라고 부르지 않는다.
초기run-01의 해당 이름을 바로잡아run-02를 최종 결과로 삼았고 초기 도구·로그도 보존했다.

## 순간 부하와 전송 판정
모든BG 기준 한scanline 최대512B, rolling1364NESmasterticks 구간에도32타일=512B의 요청이 모였다.
각 신규 묶음4KiB를 단일VBlank에서 전송한다면 과거 가정8SNESclocks/B로32,768clocks다.
기존239줄 실험의raw blank30,008clocks보다2,760clocks 많으며 부가비용을 넣기 전부터 초과한다.
이는 해당 일괄 전송 방식의 제약이며 전체 구현 불가능 판정은 아니다. 239줄crop 승인도 아니다.

실제 CPU의 R0/R1 bank선언이 모두 끝난 시점부터 첫BG fetch까지는26,349~26,417NESmasterticks였다.
미래8프레임 정보 없이 사용할 수 있는 관측 사건은 있지만, 이를8SNESclocks/B와 바로 비교하지 않는다.
두 시스템의 위상·서비스지연·blank시점·buffering이 아직 연결되지 않았다.
따라서512B를 곧바로FIFO 크기로 채택하거나, 평균량만으로 화면 전송 가능성을 선언하지 않는다.

## 검증
- 네 용량 모두 miss시 즉시 공급하는 소프트웨어 재생으로245,760화소가 원본과 일치했다. 240번째 줄도 포함한다.
- 독립 재사용거리 계산9,837경우, window경계5경우, 실제prefix20경우 통과.
- 누락request·잘못된시각/타일/eviction·범위밖request·payload변조·plane누락·tick중복·물리bank변조9종 거부.
- 직전018의95개 해시를 변경 전에 확인하고 상태문서6개를 보존했다.
- 이번에는 RTL/Questa/Quartus/SNES emulator를 새로 실행하지 않았다. 기존 입력 재검증과Python 분석 실행이다.

## 다음 실행
1. 실제 trace를 compact packet으로 만들고 SNES replay의 deadline·전체240줄 accounting을 연결한다.
   source CHR bytes를 그대로SNES tile로 쓸 수 있다고 가정하지 않는다.
2. 더 많은bank·scroll·sprite·중간bank변경을 포함한 자체 Mapper4 표본으로 같은 분석을 확대한다.
3. 실제서비스속도와packet비용으로FIFO/cache를 정한 뒤018의 자원 여유에 다시 대입한다.

실제 NES→SNES 연결, 지정SMB3, full board fit/STA/실기와DMC timing은 여전히 미완료다.
[수치](fetch-workload.json), [검증](fetch-workload-tests.json), [재현 계약](../docs/nes-fetch-workload-contract.md).
