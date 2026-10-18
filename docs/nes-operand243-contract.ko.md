# NES243: scratch 피연산자와 공유 byte 연산기

## 작업 의미

60fps용 증분 전송 인코더의 FPGA 자원 부족을 해결하기 위한 데이터 경로 구현이다.242의 접근 비용 모델을 실제 RTL로 옮긴 첫 단계다. **전체 인코더를 바꾼 시험판은 아니며**, 생산227과 기준240은 그대로다.240의490LE·40LAB 부족을 해결했다고 판정하지 않는다.

## 구현 범위

`nes_operand243.sv`는 기존 scratch를 대체할512×8 true dual-port RAM, 동기512×18 명령 ROM,8bit accumulator와9bit carry 연산, 비교·XOR·주소 생성,32bit 인자 snapshot, 독립 송신 byte latch를 가진다. wide offset/count를 별도 레지스터로 복제하지 않는다. 바이트 연산에서 carry를 다음 바이트까지 유지하고13bit 필드는 상위 byte를31로 마스킹한다.

- RF는104..127의24B,17필드164bit다.242의 hot5는 향후 외부 제어기에 유지한다. 이 kernel에는 hot5나 기존 frame epoch/CRC/offset 회로가 없다.
- B 포트는 `{4'b0011,index}`로104..127에만 쓰며 index0..7은 오류다. A 포트는 그 범위를 거절한다.488개의 비RF 주소에서 쓰기와1cycle read-valid를 검사했다. 유효하지 않은 payload_q는 의미가 없으며 RAM read 자체는 매 cycle 실행된다.
- scratch와 program ROM에는 reset을 걸지 않는다. reset/abort/lease loss는 쓰기와 출력 공개를 차단한다. 부분 RF 변경은 rollback하지 않는다. 공통 reset 후 INIT와 사용 전 초기화가 필요하다.
- 프로그램은95word다. INIT,ROW_BYTE,COUNT,MASK,DISPATCH,RAW_INCREMENT,GROUP_DONE7개의 실제 연산 routine은83word이며 출력 유지·잘못된 명령 시험에12word를 쓴다. **전체 codec이512word에 들어간다는 증명이 아니다.**
- 한 명령은 기본 FETCH/EXEC2cycle, RF 읽기는 READ를 더해3cycle이다. 현재 시험의 개별 연산 최대46cycle은 약2.091µs(22MHz)이나 전체 frame 비용이 아니다. 실제 memory latency/분기/명령 fetch를 포함하며242의 이상적 issue 비용과 같지 않다.
- entry는 외부 제어기가 선택하는 신뢰된 프로그램 주소다. 인자는 start 승인 시 저장하며 다음 cycle에 바뀌어도 결과가 같다. 임의 entry/program을 승인하는 loader가 아니다.
- OUT은 byte latch를 채운다. byte_ready가 낮아도 뒤의 RF 작업은 진행하고 두 번째 OUT만 대기한다. done 후에도 미전송 byte가 있으면 새 start를 금지한다. abort/reset/lease loss는 공개를 취소한다. kernel 최초 오류는 유지하지만 **기존 host/NES 최초 오류 문제가 해결된 것은 아니다.**

## 검사 결과와 한계

기존240 합성용 소스는 변경하지 않았다. simulation-only observer를 추가해 기존24정상+17경계41검사/7view stall을 다시 실행했다. 상태별 처음64개와 이후257개마다 한 번을 골라 실제 연산 전후를 관측했다. INIT36/ROW_BYTE198/COUNT143/MASK327/DISPATCH87/RAW_INCREMENT147/GROUP_DONE68, 총1006개다. 이는 실제240 RTL이지만 **합성 stimulus이며 SMB3의71프레임 replay가 아니다.**

이1006개와1792개 경계·무작위 준비 RF 사례를 독립 kernel에 입력해24B 결과 전체와 비RF 보존을 확인했다. TB가 idle 상태의 RF를 직접 준비하므로 연속 codec 수명·완전 초기화 proof가 아니다. 관측 중 읽지도 쓰지도 않는 old_byte 미정 byte1건만0으로 치환했다. 의미상 읽는 입력은 모두 알려진 값인지 검사하고, 쓰는 결과의 X는 허용하지 않았다. 이런 전제는 새 전체 제어기에서 다시 보장해야 한다.

최종 test06은2798개를 통과했다.92개 INIT 중간 abort/lease cycle,64회 payload transaction 동안128cycle 이상 송신 byte 유지, 다음 OUT의 backpressure,2개 잘못된 프로그램,3개 공개 중단(reset/abort/lease),488주소 read/write 및24RF alias 차단도 통과했다. 기존240의41검사는 새 kernel이 전체 encoder 계약을 만족한다는 뜻이 아니다.

## 합성에서 발견하고 고친 문제

map01은 scratch read에 enable을 건 형태가 RAM으로 추론되지 않았다. Quartus의 명시적 원인은 `uninferred due to asynchronous read logic`이다. scratch가4096개 FF로 풀려 standalone7796LE/4180FF였다. 정확한 도구 내부 최적화 원인을 더 추정하지 않는다. 이 결과는 기각했다.

검증된240과 같이 두 포트의 읽기를 항상 clock하고 쓰기만 enable로 제한했다. 같은 동작 검사를 test05로 통과한 뒤 map02에서 scratch512×8 true dual-port와 program512×18 ROM 두 메모리가 M9K로 추론됐다. **standalone MAP227LE/227comb/68FF**, 유효 memory11264bit(ROM의 상수4bit가 제거됨)다. source의 선언 용량은9216+4096bit다. 이 수치에서240의1399comb/409FF를 바로 빼서 절감을 계산할 수 없다. kernel은 일부 연산만 포함한다. FIT·배치·STA·whole-board 실행은 하지 않았다.

map02는 test05와 같은 RTL/assembler/program hash를 사용한다. test06은 회로를 바꾸지 않고 payload read 및 공개 중단 검사를 추가한 최종 superset이다. 성공 뒤 source를 정리하며 변경하지 않았다. ROM 입력은 정확한18bit `$readmemb`를 사용해20→18bit hex 폭 경고를 제거했다. 남은 경고는 ROM 쓰기 입력의 기본0,상수ROMbit 제거,사용하지 않는 fault[0]/[3]이다. 무시한 timing 경고나 clock waiver는 없다.

## 실패·중간 결과 보존

- test01: observer의 #1에 시간 단위가 없어 elaboration 실패. 테스트 단위 선언을 추가했다.
- test02: IDLE의 이전 generation까지 lease 조건에 넣어 INIT 관측0건. 실제 시작 승인 조건으로 수정했다.
- test03: 사용하지 않는 old_byte의 X를 숫자로 변환하다 중단. 위의 읽기·쓰기 집합 검사를 추가했다.
- test04:2798개 통과,조건부 read RTL. map01에서 RAM 추론 실패.
- test05:동기 RAM 형태 및 정확한18bit program으로 동일 검사 통과. map02가 최종 합성이다.
- test06:같은 RTL에 payload read/publication cancel 검사 추가,최종 선택.

## 다음 연결 순서

1. 기준240에서 hot5·승인 epoch/serial/generation·독립 cursor·입력 byte·CRC·record 필드는 유지한다. 다른 RF 필드는 실제 kernel RAM으로 옮기고 기존 wide update/mux를 제거한다. kernel을 기존 인코더 옆에 추가하고 양쪽 상태를 복제하지 않는다.
2. LAPPEND/FLUSH/LDONE과 literal payload 쓰기,cheap copy,header/record views,RAW wait 및 ACK 수명에 대한 명령과 포트 스케줄을 완성한다. 현재 kernel은 **B 포트로 literal payload를 쓰지 못하며**, 외부 포트와의 중재가 추가로 필요하다.242 dead FSTORE 생략도 그때 production candidate에 적용한다.
3. 명령 수·정확한 cycle·RAM 충돌·stall/cancel을 최소 reference 검증하고 전체 board MAP/FIT 자원 gate를 거친다. 통과 후보만 기존71프레임 collector→SPI→C 경로와 같은 스크롤 비용으로 비교한다. 이번 kernel 결과를71프레임 전체 출력 일치나60fps 증거로 재사용하지 않는다.
4. 새 입력 ARM RUN/IRQ,host/NES first fault,최종 displayACK/lease/retire,CDC/IO/STA,232의5개 VBlank 초과 burst가 남아 있다. 기존 shared SPI와 isolated source 시간을 단순 합산/상쇄하지 않는다.

생산227/GBC164/save SRAM,기존 봉인 자료는 유지했다. 새 firmware/ZIP/실기 시험 요청은 없다. 같은227/044 재시험,제어 ROM만 바꾸기,작은 counter/seed 탐색으로 돌아가지 않는다.
