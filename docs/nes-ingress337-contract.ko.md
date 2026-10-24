# NES337 입력·ROM 경계와 제어 교체 예산

선택 구현은336 RTL/ARM을 유지한다. 이번 단계는 실제336 실행에 수동 계측을 추가해 입력 전송·첫 ROM 공급의 비용을 확인하고,다음 교체의 주소 모델과 예산을 검증한다. 새 후보 RTL이나 ARM 코드,새 MAP/FIT/STA 및 시간 절감 측정은 없다.336의 독립 expected/actual 검사·private receipt 공개·STOP/reset·최종 ACK·VBlank 계약을 그대로 유지한다.

## 재현과 범위

`probe_nes_ingress337.py`는 D4/D5의 prefix 준비·wire 완료·ARM decode와 source block 공개/input 완료 시각,실제 ARM 호출의 명령 수만 기록한다. source 입력은 기존280의 실제 ARM decoder 명령 수를 검증된 바이트 경계에 재생하고,출력 planner/refill/IRQ는 실제 M4를 실행한다. 전체 firmware RUN을 실행한 것은 아니다. 비용은 CPI1/84MHz,기존 IRQ24cycle/foreground checkpoint와 같은 SPI·ROM·2슬롯 조건이다.

고정 시작/ROM 위상·제한 연속·정상 연속에서905/906/907을 실행한다. 비계측 이벤트 전체,ARM 결과와 전송 응답,RTL hash 및 ELF 실행 image가336과 정확히 같아야 한다. binary CPU ROM과 trace,source cost·block bytes도 그대로다. 수동 계측이 일정을 바꾸면 이 분석에 사용하지 않는다. 기존13 fault와 STOP/reset 검사는 동일 RTL 근거로 유지하며 새 RTL 오류 주입으로 표시하지 않는다.

## 첫 ROM 수락을 막는 비용

제한 연속 warm907에서 source 시작258.049131ms,input 완료260.715826ms,첫 BG ROM 요청266.427826ms,수락274.905042ms다. 앞선 ROM 허용 구간 종료는259.777042174ms다. edge 추정에2 NES clocks를 더 준 낙관적 종료259.777133082ms로 비교한다. 이 결과는 해당 capture 시작·허용 구간·SPI 속도에 한정된다.

source는511B payload/3 sealed blocks다. 실제 wire668B에는8개 빈 D4 poll의104B가 포함된다. 빈 poll을 모두 없애도 성공 D4들의15B overhead와 최종8B D5를 포함한564B가 남는다.

| 낙관적 하한 또는 관측 항목 | 시간 |
|---|---:|
|source 시작→앞선 구간 종료,2clock 여유 포함|1.728002082ms|
|564B 및 성공 transaction 간격,모든 처리0|1.750857143ms|
|D5의 조기 input ACK 반영 후 wire 하한|1.746666667ms|
|위 하한이 앞선 구간을 넘는 양|18.664585µs|
|첫 E9 46B wire까지 포함한 초과|166.855061µs|
|실제 첫 source block 공개|시작 후0.455517ms|
|현재 첫 block 공개 시각 유지 시 input 하한|2.158564619ms|
|실제 input 완료→첫 ROM 요청|5.712000ms|

D5의 ACK는 마지막 상승 SCK에서 생성될 수 있으므로 마지막 반주기와 SS 뒤4µs를 input 완료의 필수 비용에 넣지 않았다. CDC/FPGA/ARM 처리도 모두0으로 놓는다. 그런 하한에서도 앞선 ROM 구간을 놓친다. 따라서 현재 시작·wire 형식·input-COMMITTED barrier를 유지한 채 ARM 계산만 줄여 그 구간에 들어가는 것은 불가능하다. 다른 시작 위상,새 source 형식 또는 실제 다른 일정까지 불가능하다는 뜻은 아니다. 첫 E9 전송 전에는 이전 D5의 남은 SS tail도 필요하지만 이 추가 하한에서는 생략해 낙관성을 유지했다.

| warm907 비교 | 동일 시작·ROM 위상 | 제한 ROM 연속 |
|---|---:|---:|
|source 시작→앞선 구간 종료 여유|6.089721952ms|1.728002082ms|
|input 완료→실제 첫 요청|5.714409ms|5.712000ms|
|요청을 앞선 구간 끝까지 당겨야 할 양|2.291427048ms|6.650692918ms|
|처리0인 input wire 하한과 구간 차이|4.343055285ms 여유|0.018664585ms 초과|

고정 일정에서는 wire 자체가 앞선 구간을 배제하지 않는다. 준비의 선행 실행·첫 BG 발행이 후보가 될 수 있다. 제한 연속에서는 그 변경만으로는 위 input wire 하한을 넘지 못한다. 구간 끝까지 당기는 양은 필요 조건일 뿐 유효slot/core 경쟁 및 나머지 tile 처리 여유까지 포함한 충분 조건이 아니다.

빈 D4 poll8개는 모두 첫 block 공개 전에 끝났다. 그 SPI 점유를 곧바로 프레임 절감으로 빼면 producer를 기다린 시간을 지워 버린다. source-ready IRQ는 ARM 작업을 겹칠 후보지만 해당 IRQ/ARM 준비 연결과 새로운 일정을 실행하기 전에는 시간 이득으로 계산하지 않는다.

warm의 top-level 준비는 expand28670407,begin2857577,geometry_plan28635879,h2early28612060,input_commit2862591,begin_step286138843 instructions,합계267357/3.182821429ms다. 이후 BG step·SPI·응답/IRQ·첫 E9도 남는다. nested 함수 구간을 이 합계에 다시 더하지 않는다. 이전 input decode는 이미 nibble CRC를 사용하므로 새 CRC table 절감으로 다시 계산하지 않는다.

단순한 첫 요청 준비 단축보다 source block 공개/전송과 실제 BG plan 발행을 함께 바꿔야 한다. 이전 구간의 마지막 순간에 첫 tile만 수락하는 것으로 전체 frame60fps가 증명되는 것도 아니다. 나머지 BG/OBJ·staging/DMA·최종 표시까지 같은 일정에 연결해야 한다.

## 회로 경계와 이미 공유된 부분

336 whole Lite MAP은22256LE/17378comb/9066FF/307808bits다. 이번 분석은 실제 입력 파일과 보고서를 재결합하며 새 합성으로 표시하지 않는다. comb 부족1970은 그대로다.

| 겹치지 않는 범위 | 현재 comb | 설계 상한 | 필요한 순감소 |
|---|---:|---:|---:|
|host|2169|1146|1023|
|독립 validator+aperture|1160|1160|0|
|queue+SPI|851|600|251|
|source encoder+transport|1765|1100|665|
|plan path|460|297|163|
|범위 합계|6405|4303|2102|
|범위 밖|10973|10973|0|
|whole|17378|15276|2102|

이는132comb 여유를 위한 허용 예산이지 달성 예상치가 아니다. host에서47%,source에서38%에 가까운 감소가 요구된다. queue/SPI851+source transport420+plan460을 전부 없애는 불가능한 경우도1731개뿐이라239개가 여전히 부족하다. host와 source encoder의 실제 decode/주소·데이터 경로까지 교체해야 한다.

다음은 이미 구현됐으므로 새 이득에서 제외한다.

- 공통 SPI receiver·request fields·CRC8/CRC16. source 헤더의 별도 CRC8는 남지만 다중 receiver 전체가 남은 것은 아니다.
- source와 plan이 phase에 따라 쓰는 cursor319.
- source256B bank와 plan512B bank의 concatenated RAM 주소.
- plan의 shared CRC307 및 기존 input/output phase RAM 공유.
-336에서 삭제한 descriptor receipt first/end 및 범위 순회.

host/validator는 host clock,source encoder와 plan decode는 NES clock이다. 각 도메인 내부 phase 제어 공유는 비교할 수 있지만 cross-clock RAM/mailbox·generation·lease·취소를 하나의 FSM으로 공짜로 합치지 않는다. source pop,input commit,저장 credit,DMA consume,최종 표시 ACK는 서로 다른 수명 사건이다.

## 실제 삭제 후보와 주소 모델

E1 queue는 현재480/752의272B 간격 slot을 사용한다. wire header에서6B identity를 검증하고 제외해10~15B active record를 만들며,payload는 각 slot의24B 뒤에 둔다. ingress와 read 경로에는 opcode별 prefix/base 선택 및 여러 주소 덧셈이 남는다.

다음 후보는 원래 packet 전체를512/768의256B 정렬 slot에 저장한다. 공개 wire/압축/identity 검사는 유지한다. payload 주소는 `{1,bank,sn_address}`가 되고,ingress는 같은 slot과 packet byte index를 사용한다. expected0..471은 그대로이며472..511의40B는 단순 여유일 뿐 새 검증 RAM으로 자동 배정하지 않는다. 새 RAM block은 필요하지 않다.

삭제 대상으로 `field312` ingress permutation,`write_prefix312`/`ingress_base314`와 opcode별 `payload_base314`,기존 wide base+offset 가산을 잡는다. active record loader는 원래 wire 위치[0,1,2,3,10,11,14,15,12,13,16..20]를 읽어야 하므로 작은 주소 선택과 synchronous read 지연은 남는다. packet byte index−1과 expected/packet 포트 선택도 남는다. sequence·serial·generation·CRC·길이 검사,accepted/retired/consumed 및2슬롯 fullness는 유지한다. 저장 형식을 바꿔 검사를 줄이지 않는다.

`queue_layout` 모델은 normal/typed/batch의모든 허용 prefix..256 길이와 양쪽 bank1428조합,실제 실행 E1 packet을 양쪽 bank에 놓은 경우를 대조한다. active record와 payload의 모든 byte가 이전 주소와 동일하게 읽히고 expected와 겹치지 않아야 한다. 이는 주소 모델 검증이며 RTL credit/STOP/RAM inference나 회로 절감을 검증한 것은 아니다.

source transport는 이미 aligned bank다. 별도 후보는 D4 prefix에서 선택한 immutable bank descriptor를 응답 종료까지 직접 사용해 snapshot_length/CRC/token의40비트 복제를 제거하는 것이다. read_bank가 prefix POP에서 바뀐 뒤 고정되고,읽는 bank는 다음 POP 전까지 writer에게 돌아가지 않아야 한다. prefix 시점에 empty였던 bank가 도중에 ready가 되어도 응답은 empty로 고정해야 하므로 snapshot_ready/reading과 header CRC는 유지한다. wrong token/generation,미완료 read,중간 SS/STOP,동시 반대 bank 재사용을 실제 RTL에서 검증하기 전 삭제하지 않는다.40FF를40comb 절감으로 환산하지 않는다.

## 제외한 plan 단순화

현재905/906/907 E9에는94/92/10 plans가 있으며 모두 short form이다.16B 공통 base와 alternate tag tail로 통일해 decode를 줄이는 모델을 비교했다. 기존 batch 경계·최대240B/15plans와 marker 순서를 유지하고 필요한 split overhead도 계산한다.

| frame | 현재 E9 wire | 고정 base 모델 | 추가 SPI 점유 |
|---|---:|---:|---:|
|905|736B|1584B|2.584381ms|
|906|712B|1544B|2.535619ms|
|907|92B|192B|0.304762ms|

이 예에서는 추가 packet split이 없어도 비용이 크다. 새 ARM serializer/copy/CRC·IRQ 비용과 실제 경쟁은 이 수치에 포함되지 않았다. 추가 wire 점유를 그대로 frame 회귀라고 단정할 수는 없지만 시간·회로 동시 개선을 지지할 근거도 없다. 이번 교체 후보에서 제외하고 기존 짧은 plan을 유지한다. partial BG와 final end 의미를 없애지 않는다.

## 다음 구현 gate

336을 유지한 상태에서 aligned E1 slot과 immutable D4 response를 host·source 제어의 최소 실제 교체로 연결한다. source 준비 중 ARM geometry/BG 준비를 실행할 수 있는 경계,첫 complete BG plan의 조기 발행,source byte/transaction 감소 또는 capture 시작 변경을 함께 비교한다. geometry 준비는 speculative일 수 있어도 E9/ROM 공개는 input commit·lease 검증 뒤여야 한다. 새 source IRQ와 추가 ARM 상태·SPI·cold 분할·RAM 포트·취소 비용을 포함한다.

이 두 작은 회로 교체가2102개를 해결한다고 가정하지 않는다. 첫 실행에서 전체 비용과 남은 host/source datapath 제거 목록을 함께 재평가한다. 위 예산을 뒷받침하지 못하면 collector/query 인터페이스를 포함한 역할/전송 형식을 다시 검토하고 범위 밖10973도 다시 계상한다. 같은 FSM·opcode·seed·FIT 반복은 하지 않는다. fullRUN71/전체65816 polling/물리60fps/FIT/STA는 계속 미완료다.
