# NES244: 공유 연산기의 literal 수명·송신·RAM 중재

## 작업 의미

243은 RF 연산만 가능했고 payload를 쓸 수 없었다.244는 **literal 축적부터 flush, 작은 raster literal 축적, 실제 record 송신까지 같은 scratch/ALU에서 실행**한다. 넓은 상태 레지스터를 복제하지 않고 기존240의 갱신 경로를 대체하기 위한 구현이다. 외부240 전체 제어기와의 연결은 아직 없으며 생산판은227이다. 전체240의490LE·40LAB 부족이나60fps를 해결했다고 판단하지 않는다.

## 구현

`nes_operand244.sv`에 간접 payload 읽기·쓰기,9bit 주소 latch,8bit 임시값,즉시값 비교,record 길이 handshake 및 결과 byte를 추가했다. 기존의24B RF104..127과512×8 scratch,512×18 동기 ROM,8bit ALU/carry,출력 byte latch를 유지한다. RF와 payload에 별도 RAM이나 wide operand shadow를 두지 않는다.

- A 포트는 RF 주소를 거절한다. B가 payload에 접근할 때 같은 주소의 read/write 충돌은 B를 우선하고 A를 대기시킨다. 두 포트의 read는 항상 clock하며 RAM에 reset을 걸지 않는다.
- 단일 cycle의 충돌 회피만으로는 아직 송신하지 않은 byte를 보호하지 못한다. 따라서 명령이 busy인 동안 C80..91과 L256..495에 대한 외부 쓰기를 차단한다. 무관한 영역의 접근은 가능하다. 부분 쓰기는 abort 시 rollback하지 않으며 공통 reset/초기화가 필요하다.
- literal routine은 동일 byte/gap3/길이240 경계를 처리하고 LAPPEND를 실행한다. 결과0=소비 완료,1=raster expensive,2=flush 후 같은 입력 재시도,3=flush 후 다음 입력이다. **결과2에서 입력을 두 번 소비하지 않도록 외부 제어기가 원래 new_byte를 유지해야 한다.** 승인 인자는 여전히 start 순간 snapshot이다.
- flush는 빈 literal,13byte 이상 raster expensive,작은 cheap literal,일반/RAW literal을 구별한다. cheap은 C에 header와 L payload를 복사한다. 일반 literal은 header를 P에 복사하지 않고 직접 byte latch로 보내며 L을 순서대로 읽는다. 결과 byte와 C/RF/L 최종 상태는240과 비교했다. P208..210의 동일한 중간 쓰기나 cycle 동일성은 요구하지 않는다.
- 일반 record는 길이를 승인받은 뒤 byte를 공개한다. stalled byte와 record 길이는 유지된다. 마지막 byte를 latch에 넣은 뒤 RF counter/clear와 done이 먼저 일어날 수 있지만,미전송 byte가 남으면 start_ready가 낮다. **done/record handshake는 최종 displayACK 또는 frame commit이 아니다.** 실제 최종 lease/retire는 외부 연결에서 보장해야 한다.
- standalone 프로그램301/512word다.243의83word 연산+12word 시험 entry를 포함한다. 새 code의 port/negative 시험21word를 빼면 실제 routine268word와 시험33word다. 아직 전체 codec이512word 안에 들어간다는 증명은 없다.

## 검증

test01은 기능 검사,그 소스로 map01을1회 실행했다. test02는 **RTL/assembler/program 변경 없이** 실제240의 FLUSH→LDONE→SBYTE 송신 관측을 추가한 최종 superset이다. 실패한 test/FIT/seed 시도는 없다.

1. 이전243의 준비 RF2798개,488주소 read/write,24RF alias 차단,92개 INIT 중단 위치,출력 유지와3개 공개 취소 검사를244에서 다시 통과했다.
2. 새 continuous run은 최초 한 번 RF를 준비한 후11738명령 동안 RAM 상태를 유지했다. 초기화58회,context4898,literal4902,flush376,literal_at6,raw_append1402,dispatch48,group_done48이다.240byte 경계,동일 byte와 gap,geometry/RAW의 counter 차이,cheap 축적과13byte fallback을 포함한다.299records/4078bytes와 각 명령 후RF24B/C12B/L240B가 기준 모델과 일치했다. 여기서58회는 게임 frame 수가 아니라 합성 case 초기화 횟수다.
3. 변경하지 않은 실제240 RTL을 기존24정상+17경계41검사/7view stall로 실행하며 LAPPEND164건을 추출했다. 새 kernel에서 준비 RF로 replay해 결과와 L 쓰기가 일치했다.
4. 같은 실제240 RTL의 FLUSH166건을 추출했다. empty/expensive/cheap은 LDONE 또는 즉시 종료 후 RF/C/L을,일반 record는 실제 SBYTE의 ready 승인 byte까지 수집했다. 그중53records/10504bytes를 새 kernel이 그대로 송신했다. 각 flush는 준비한 RF/C/L에서 시작하므로 전체 연속240 제어기의 proof는 아니다.
5. 실제 관측의 미정값은 의미상 읽지 않고 변경하지 않은 RF/미사용 payload에만 허용했다. 보존된 X1056nibble 출현을0으로 채운 fixture다. 사용되는 RF와 L의 사용 길이 안의 byte,실제 출력 byte에는 X가 없음을 검사했다. 실제 RAM을 reset해서 초기화 문제를 숨긴 것이 아니다.
6. B write/A read 충돌에서 A가1cycle 대기하고,명령 중 L 외부 쓰기가 거절된다. 잘못된 간접 RF 주소와511→0 wrap을 거절한다. RF 쓰기/payload 쓰기/RAM 읽기/record stall/byte stall의5지점×abort·lease10경계를 검사했다. 취소 후 추가 RAM 쓰기가 없고 record/byte 공개가 해제된다. 기존 kernel의 sticky 오류 계약도 유지한다.

이 자료는 합성 입력이다. 새 SMB3 71프레임 replay,collector→SPI→C 전체 경로,ARM/SNES/실기/FPS는 실행하지 않았다. 무작정 검사만 늘린 것이 아니라,새 RAM 쓰기와 전체 literal 수명의 의미·중재를 확인한 것이다.

## 자원과 시간

최종 단일 MAP은 **373LE/349comb/102FF**, memory11264bit다. scratch512×8 true dual-port와 program512×18 ROM이 M9K로 추론된다. 프로그램의 상수4bit가 제거돼 유효 ROM은7168bit다.243의227LE/227comb/68FF보다 기능 확장으로146LE/122comb/34FF가 증가했다. 이것은 두 독립 kernel의 비교이며 전체240에서 얼마를 줄였다는 뜻이 아니다.

관측된 가장 긴 명령은 긴 stall을 포함한3982cycle(22MHz에서 약0.181ms)이다.240byte record를 보내는 flush가 포함돼243의46cycle 단순 연산과 비교할 수 없다. 전체 frame 준비 시간 또는16.67ms 충족 증거로 사용할 수 없다. 바이트마다 context/literal을 따로 호출하는 현 시험 스케줄도 전체 연결의 최종 스케줄로 승인하지 않는다. 기존 FSTORE/map/raster 수명에 맞춰 command 호출·fetch 비용을 함께 줄이고 실제 스크롤 경로에서 재측정해야 한다.

FIT·STA는 실행하지 않았다. 전체 자원 부족490LE/40LAB,mapper 여유는 계속 미승인이다. 남은 경고는 ROM 쓰기 입력 기본0,상수bit 제거,사용하지 않는 fault 출력이다. clock/SDC waiver가 없다.

## 다음 구현

literal의 축적·flush·송신 및 C/L 중재는 구현됐으므로 다시 독립 kernel 기초시험을 반복하지 않는다. 다음에는240의 남은 행 비교/history hot5,shift record,raster mask/group,frame header/trailer/CRC,RAW query,ACK 수명을 하나의 제어 흐름으로 연결한다. 기존widefield 갱신을 제거하며 병렬 사본을 남기지 않는다. LITERAL 결과2의 입력 재시도와 마지막 pending byte까지 start를 막는 계약을 유지한다.

명령301/512word와 추가 cycle을 기준으로 전체 프로그램/포트 스케줄을 먼저 제한한다. 단일 whole-board resource gate를 통과한 후보만 기존71프레임 스크롤 통합으로 진행한다. 또 별도 control ROM을 붙이는 방식,seed/작은 counter 반복으로 돌아가지 않는다. 현재 kernel에 일반 RET/CALL stack은 없다. 필요 시 제한된 continuation을 명시적으로 설계하고 FF/ROM/cycle 비용을 포함한다.

새 입력 full ARM RUN/IRQ,host/NES first fault,최종 display lease/ACK/retire,CDC/IO/STA,232의5개 VBlank 초과 burst는 별도 미완료다. 생산227/GBC164/save SRAM 및 이전 archive를 유지했다. 새 설치물이나227/044 재시험 요청은 없다.
