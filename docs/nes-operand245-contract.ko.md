# NES245: 공유 연산기의 행 비교·shift·raster 연결

## 작업 의미

화면 전송량을 줄이는 기존240 codec의 행 이동과 raster XOR 처리를,244의 공유 연산기·RAM에 옮겼다. 단순 진단 추가가 아니라 **넓은 상태 갱신 회로를 대체하기 위한 실제 출력 경로 구현**이다. literal과 새 행 처리를 같은 RF/C/L/M 상태로 이어서 실행했다. 다만 frame 입력·header/trailer·CRC·RAW query·최종 ACK 제어는 아직 연결하지 않았다. 전체 인코더 기준은240, 생산판은227이다. 전체240의490LE·40LAB 부족과 실기60fps가 해결된 단계가 아니다.

## 회로와 수명

- 기존512×8 true dual-port scratch,24B RF104..127,8bit ALU,독립 출력 latch를 유지한다. 별도 payload RAM이나16/32bit operand shadow를 추가하지 않는다.
- ROWPAIR 명령은 O/N을 동기 RAM에서 순서대로 읽는다. 66byte 행은 동일/왼쪽2byte 이동/오른쪽2byte 이동을 비교한다. hot history4byte,7bit 내부 행 인덱스와3bit 결과를 레지스터에 둔다. 첫2byte에서는 history를 비교하지 않아 이전 명령의 history에 의존하지 않는다.7bit는 최대65인 이 내부 loop에만 적용하며 외부 offset/serial 폭을 줄이지 않는다.
- 8byte raster는 O XOR N과 기존 M을 비교하거나 M을 새로 쓴다. 같은 mask이고 rows가0이 아니면 rows도 증가시킨다. mask_set은 rows=1,RF xor_byte=마지막 XOR로 끝난다. 초기 M이 없는 첫 group에는 mask_compare를 호출하지 말고 mask_set으로 초기화한다.
- ROWRESULT는 저장된 비교 결과를 읽는다. ROWSCALE은 rows×8의 low/high byte를 만드는 고정 배선 두 가지다. 일반 barrel shifter나16bit 산술 회로를 추가하지 않는다. shared8bit ALU/carry로 expanded16과 spans16을 갱신한다.
- shift는 row_start/종류/방향과 N의 두 끝 byte를 직접 송신한다. raster는 group_start/rows와 M8byte를 직접 송신한다. P에 header 사본을 만들지 않는다. 방향 인자는 내부 계약상1 또는255다.
- cheap는 C에 쌓인 완전한 literal record들을 차례로 송신한다. cheap_i를 진행시키고 spans/expanded를 갱신한다. copy가 끝난 뒤 죽은 build_i를 레코드 길이에 재사용한다. 따라서 cheap 종료 시 build_i는 마지막 record 길이이며240의 중간 임시값과 같을 필요가 없다. 출력과 의미 있는 누적 상태는 같다. 잘못된 cost/첫 record 길이는 공개 전에 오류6으로 거절한다. 후속 record가 잘못됐다면 앞 record까지 취소되는 rollback은 없으므로 전체 frame의 common reset/invalid 처리가 필요하다.
- busy 동안 C/L뿐 아니라 O0..65,N128..193,M96..103의 외부 쓰기도 막는다. M의 B write와 같은 주소 A read는1cycle 대기한다. RAM read는 항상 clock하고 RAM 내용을 reset하지 않는다. 마지막 OUT은 latch에 있으므로 RAM이 바뀌어도 대기 중 출력 byte는 바뀌지 않는다.
- record/byte가 남으면 다음 start를 막는다. done과 record_ready는 frame/display commit이 아니다. abort/lease loss는 새 mask write가 예정된 그 edge부터 RAM 쓰기와 공개를 막으며 첫 오류를 보존한다. host/NES 전체 최초 오류 소유권 문제까지 해결했다는 뜻은 아니다.

## 검증 범위

선택 test04는 test03/map01과 **같은 RTL·assembler·program**이며,거절/취소 edge 검사를 보강한 결과다.

1. 변경하지 않은240 RTL의24정상+17경계41검사/7view를 실행하면서317개 실제 연산을 관측했다: 행 비교49,mask 비교157,mask 설정62,shift39,raster10. 준비한 시작 상태에서245로 replay했고 RF·mask 결과가 일치했다. shift/raster49records/403bytes는240 SBYTE의 실제 ready 승인 byte와 일치한다. 게임의71프레임이 아니라 합성 시험의 실제 RTL 관측이다.
2. 여기에320세트×7종류=2240개 경계·무작위 사례를 더했다. 동일/양쪽 shift/양쪽으로 해석 가능한 반복 행,마지막 byte mismatch,zero/nonzero mask,1..224행,spans/expanded의16bit carry/wrap과 cheap의 여러 record 구성을 포함한다.
3.281명령 연속 시험에서는 RF/C/L/M을 매 명령 다시 준비하지 않는다. O/N 입력만 A 포트로 갱신하며 나머지 RAM의 수명이 이어지는지 검사한다.224행 반복 mask가 누적되고 literal expensive 전환 후13byte raster record가 나온다. 별도 cheap group은 literal→flush 축적→두4byte record 송신까지 이어진다. 이것은 두 합성 group의 연결이며 전체 frame 제어기 검증은 아니다.
4. 새 시험 총2838명령,1212records/9704bytes와 명령 후 전체 scratch512B가 기준과 일치한다. prepare fixture와 continuous281명령은 구분된다. 미사용·보존된 X1024nibble 출현만0으로 채웠으며 실제 읽는 행/mask/RF/송신 byte는 알려진 값인지 확인했다.
5. 기존244의 봉인 입력을245에서 다시 실행했다.2798 RF 연산과11738 literal lifecycle 명령,299records/4078bytes,실제240 append164 및 flush166/53records10504bytes,기존 alias/출력 유지/취소 검사를 유지했다. 새 행 회로와 RAM mux가 같은 엔진에 추가됐으므로 필요한 회귀다.
6. 새 mask B write/A read collision1건과 busy 외부 쓰기 거절10건,다섯 RAM 단계×abort/lease10건을 통과했다. 취소 직전 snapshot과 취소 edge 및 이후 RAM을 비교한다. 잘못된 cheap cost/length4건과ROWPAIR mode1건은 아무 출력/메모리 변경 없이 오류6이며 나중 abort도 최초 오류를 덮지 않는다.

test01은 독립 기준과 비교하다 mask_compare의 rows 증가 누락을 잡았다. 실제240의 동작까지 포함하도록 고쳤다. test02는 live 선언 순서 때문에 새 RTL compile에서 중단됐다. test03은 기능 통과와 map01에 사용됐고,test04가 최종 보강 시험이다. 실패·중간 자료를 모두 보존했다. license smoke,seed 탐색,추가 FIT는 없다.

## 비용과60fps 기준

단일 standalone MAP은 **551LE/535comb/148FF,13312 유효 memory bit**다. scratch512×8 TDP=4096bit와 program512×18 ROM=9216bit가 각각 M9K로 추론됐다.244의373LE/349comb/102FF보다178LE/186comb/46FF 늘었다. 행 처리 기능이 추가된 비용이며 전체240에서551LE를 단순 차감하면 안 된다. 전체 제어기까지 붙인 뒤 MAP/FIT를 통과해야 한다.

명령은 **453/512word**다. 이전 시험 entry33word를 포함하며 실제 routine420word,현재 남은59word다. 시험 entry를 제거하면92word가 남는 산술일 뿐 전체 frame/CRC/입력 제어가 들어간다는 증명은 아니다. 다음 연결에서 중복 dispatch/init/count routine과 외부 continuation의 실제 필요성을 따져 프로그램과 FF 예산을 함께 확정한다. ROM을 무작정 늘리지 않는다.

| 새 경로 | 관측 최대 operation cycle |
|---|---:|
|66byte 행 비교|201|
|8byte mask 비교 및 rows 누적|56|
|8byte mask 설정|45|
|shift7byte 송신 및 누적|95|
|raster13byte 송신 및 누적|206|
|cheap 여러 record 송신 및 누적|590|

이 값은 시험의 ready stall을 포함하지만 fixture 준비 시간은 제외한다. 실제 부하 전체의 상한이 아니다.22MHz 환산으로66byte 행 비교는약9.14µs,32행은약0.292ms다. 기존240의행 read/compare132cycle보다 느리므로 자원 절약과 교환되는 비용을 숨기지 않는다. 단순32행 비교에서만 차이는약0.100ms이며 literal/입력/CRC/SPI/SNES를 더해야 한다. 이전 literal 최장3982cycle도 그대로다. 이번 수치로16.67ms 또는60fps를 승인하지 않는다.

MAP의3bit row_flags에 상수0/7을 대입하는 폭 경고는 값이 정확히 들어가는 경우다. ROM의 사용하지 않는 쓰기 입력은 기본0 경고가 남는다. 검증 후 소스를 정리한다며 수정하지 않았다. FIT/STA/CDC/IO/실기 결과는 없다.

## 다음 작업과 인계

이제 행 비교·shift·raster·cheap를 다시 독립적으로 확장하는 단계는 끝낸다. 다음은 **240의 frame 입력/base write/row 수집과 공유 RF 연산기를 실제로 연결**하고 header/trailer/CRC/RAW query/ACK를 한 흐름으로 구성하는 것이다. 기존240와 새 kernel을 병렬로 남겨 wide state를 복제하지 않는다. 내부 row loop와 입력 수집 index가 중복된다면 비용을 명시하거나 수명에 따라 공유한다. hot5만 남긴다는 가정을 전체 연결 없이 절감량으로 계산하지 않는다.

literal result2의 동일 입력 재시도,group 경계에서 flush→출력→초기화 순서,RAW의 geometry counter 제외,끝 byte 전송 후 다음 입력 허용을 지킨다. current 시험의 context/literal 별도 두 호출을 최종 속도 스케줄로 승인하지 않는다. record OUT에서 CRC를 정확히 한 번 갱신하고 stalled byte를 재계산하지 않도록 한다. 더 많은 분리 kernel 시험보다 최소 전체 codec reference/cancel 후 단일 whole-board 자원 gate를 먼저 진행한다. gate를 통과한 후보만 기존71프레임 스크롤 통합으로 간다.

새 입력 full ARM RUN/IRQ,host/NES first fault,최종 source lease/displayACK/retire,CDC/IO/STA,232의5개 VBlank 초과 burst는 여전히 미완료다. 생산227/GBC164/save SRAM/이전 봉인 자료는 유지했다. 설치물·새 실기 요청·227/044 재시험은 없다.
