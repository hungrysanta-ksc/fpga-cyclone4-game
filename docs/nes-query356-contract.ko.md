# NES356 실제 collector query와 host source 교체 검증

338 RTL·355 ARM을 기준으로 작성한 별도 후보다. 선택 기준은 시간과 전체 회로 비용의 동시 개선이며, 삭제한 레지스터 수로 합성 이득을 추정하지 않는다. 현재 선택 기준은338 RTL·355 ARM으로 유지한다.

## 실제 교체 경계

`nes_query356.py`는 기존 생성 경로 끝에서 세 RTL 파일을 바꾼다. encoder와 source phase RAM A, transport producer를 host clock으로 이동한다. validator는 기존 host clock과 phase RAM B를 유지한다. 두 포트를 하나로 합쳤다고 주장하지 않는다.

- collector는 NES clock에 남고355 query bridge로32bit(kind/index/generation) 요청과65bit(hit/data) 응답을 전달한다. 기존 q_cursor 선행 주소, q_held/q_have/q_pending을 유지하고 수락 handshake 뒤에만 pending을 세운다. MASK·SHIFT와 fixed-block source 압축/CRC는 그대로다.
- 두40bit descriptor mailbox와 publish/sent 반환 제어를 삭제한다. 같은 host clock의 busy 두 bit와 bank별24bit(length/CRC)만 남긴다. generation은 collector lease가 고정한 현재 문맥을 사용한다. 마지막 POP/input ACK 전에 다른 frame을 수락하지 않는다.
-17bit ACK mailbox와 ACK payload 저장,source/host fault 교차 동기화를 삭제한다. host의 ack_pending은 encoder의 ACK 수락까지 유지한다. D4/D5 prefix generation/token/CRC,전체 read_seen,다음 bank 미완료 검사와 immutable bank는 유지한다.
- source cursor의 출력 단계 NES plan 갱신을 삭제하고 bridge의 NES cursor가 plan을 맡는다. SPI payload read_address와 source/base RAM 주소 계산은 남는다. source 주소/응답 제어 전체가 사라졌다는 결과가 아니다.
- START,input DONE,최종 display ACK는 별도1bit mailbox로 전달한다. 입력 완료 후 NES lease가 성립하는 동안 handoff를 유지하고,표시 종료의 lease 해제와 host 최종 ACK 수신 사이도 구분한다. 이 추가 CDC/상태/cursor 비용을 whole MAP에 포함한다.

metadata는 collector/display lease 아래 고정된 bundled data다. 소유권 level을 host에 동기화하고 identity/generation/epoch 검사는 유지한다. STOP은 새 source 쓰기를 막지만, 실제 collector가 응답을 취소하면 query bridge의 drain이 끝나지 않는다. handoff의 대기 중 source DONE도 취소 뒤 공개된다. 아래 오류 주입 결과 때문에 이 교체를 안전한 후보로 선택하지 않는다. 한쪽 mailbox만 reset하지 않는다. 최종 ACK는 독립 expected/CRC/coverage와12B display 읽기/token 완료 뒤에만 허용된다.

## 측정 방법

355 ARM 코드를 그대로 사용하고 실제 ARM ELF의 PT_LOAD를 비교한다. 동일 시작/ROM 위상,제한 ROM 연속,일반 ROM 연속의3프레임씩 비교한다. 실제 collector query,source byte 검사,압축 전송,ARM refill·IRQ,2슬롯/staging·tile ROM 경쟁,기존 ordinary65816 trace와 map/tile/display bus model을 포함한다. 기존 VBlank 계약을 유지한다. source prefix/reply/decoder는 실제 M4 명령 계측치를 각 실제 SPI transaction에 적용하며,출력 planner/refill은 ARM 실행기를 연결한다. 전체 firmware RUN/전체65816/물리 WCET·60fps/CDC STA 증명은 아니다.

source가 host clock으로 이동하므로 바이트/record/CRC 검사 observer도 host clock으로 옮겼다. source 시간 계수는 기존 NES clock을 유지한다. 새 START/DONE 전달 지연 누락을 피하기 위해 주 비교값은 start319→frame_done 실제 timestamp 차이다. 이전의 source cycle+output 합도 별도 저장한다. 기준355도 같은 timestamp 정의로 다시 계산한다.

실패 window01은 문자열 생성 조건,window02는 문법/선언 순서,window03은 이전 NES-clock byte observer가 host-clock source의 첫 바이트를 놓친 오류다. 실패와 수정 후 결과를 함께 보존한다. 실패를 source 정상 동작 증거로 사용하지 않는다.

## 전체 처리 시간

|warm907 실제 start→최종 ACK|338+355 기준(ms)|356 후보(ms)|차이(ms)|
|---|---:|---:|---:|
|제한 ROM·연속|20.689706|20.689706|0|
|제한 ROM·동일 시작/위상|25.051563|25.051563|0|
|일반 ROM·연속|12.007311|12.178036|+0.170725|

기존 source cycle+output 합과 위 값의 수십~수백ns 차이는 START/DONE 전달·관측 경계다. 이 변경을 성능 이득으로 계산하지 않는다. 제한 ROM 연속의60Hz 초과분은4.023039ms이며,기존 보고4.022994ms와 같은 부족 상태다.

동일 위상에서 첫 BG 요청은6.962939→7.133709ms로0.170770ms 늦었다. 실제 collector query는warm1957회,host 수락→응답369..417ns다. source 선행 읽기는 유지됐지만 codec 고속화로 이 지연을 모두 숨기지 못했다. warm source 입력 완료는2.690513→2.861238ms,source SPI668→707B,빈 polling8→11회다. prefix/reply 명령 비용과 SPI 지연은 실제 발생 횟수만큼 일정에 포함된다. 압축 record 내용,출력 명령 순서와전송 bytes는 기준과 일치한다. 연속 시작/ROM 위상 이동 효과와 동일 위상 결과를 별도로 저장한다.

## 오류 주입과 보존 검사

실제 경로의 오류 주입 8개 중 **6개 통과, 2개 실패**다.

- 통과: source record 전송 중 STOP, 부분 E1 ingress STOP, 조기 최종 ACK, 독립 expected/receipt 불일치, 진행 중 tile ROM STOP, query 응답 도착 시 STOP.
- 실패 24: collector query WAIT 중 STOP. 실제 collector는 `release_frame`에서 응답을 취소하지만, query bridge는 늦은 응답을 계속 기다려 drain이 끝나지 않는다. RAM freeze 검사까지 통과한 뒤 drain assertion에서 실패했다.
- 실패 26: 입력→표시 lease 전환 중 STOP. mailbox에 대기하던 source DONE이 취소 뒤에도 공개된다. guards02/03에서는 기존 count/queries assertion이 먼저 실패했고, guards04의 전용 `source DONE after STOP356` assertion으로 원인을 확정했다.

통과한 6개 사례에서는 취소 뒤 phase RAM·queue·staging 불변성과 완료·lease 공개 금지를 확인했다. 실패한 handoff 사례는 늦은 DONE assertion에서 먼저 중단됐으므로 이후 검사까지 통과했다고 주장하지 않는다. query 응답 취소와 늦은 DONE은 정상 일정만으로 발견되지 않는 실제 통합 결함이다.

시간·회로 회귀도 확인됐으므로 이 후보를 추가 수정하거나 선택하지 않고 실패를 보존한다. 후속 경계에는 collector의 명시적 취소 완료 신호, 늦은 응답 배제 규약, STOP 시 pending 완료 공개 차단이 필요하다. 355의 279개 clock-pause/phase 단위 시험은 합성 응답기를 사용한 별도 증거이며, 실제 collector의 취소 동작을 검증한 결과가 아니다.

별도 aperture 시험과 raw0·최종 검사·private STOP·cold reset 8사례는 통과했다. 정상 일정 9건에서는 출력 wire 순서, qualified read→private receipt→token ACK 공개, 2슬롯 credit, 12B display 읽기와 최종 lease 해제를 대조했다. 3프레임의 검증이며 71프레임 전체를 새로 실행한 것은 아니다. ARM은 355 ELF와 동일하며 기존 준비/lifetime 검증 결과를 유지한다.

## 전체 회로 비용

|whole Quartus Lite|338 기준|356 후보|차이|
|---|---:|---:|---:|
|LE|22144|22142|-2|
|조합 논리|17274|17303|+29|
|FF|9018|9074|+56|
|RAM bits|307808|307808|0|

조합 논리 부족은1866→1895개다. 시간 회귀와STOP 두결함도있으므로 후보를 선택하지 않는다. source transport는399→335comb,399→120FF로 줄었지만 새 query 경계는 통합 후208comb/292FF,START/DONE/final ACK mailbox는21comb/28FF다. encoder는1348→1329comb,FF395동일이다. parent inclusive 수치와 child를 합산하지 않으며 전체 own-entity 합이17303인지 확인한다. 다른 hierarchy의 합성 재분배까지 포함한 실제 whole 차이는+29comb다.

355 standalone query의125comb를 통합 비용으로 대입하면 안 된다. 실제 배선/상수 전파/plan 사용을 포함한 비용은 달랐다. encoder+transport+host 실행기+query+새 mailbox의 겹치지 않는 합만4057comb로,기존3908보다149개 많다(상위 wrapper 등은 별도).2035cap에 도달한 것이 아니다. RAM 절감도 없다. 새 source clock의84MHz 동작도 STA로 확인한 결과가 아니다. FIT/STA와 physical timing은 실행하지 않았다. MAP과 실행 RTL은 원본 hash를 각각 보존하며 transport 파일의 빈 줄 하나만 다른 것을 확인했다. 기존 async_reg 경고는 여전히 CDC sign-off가 필요함을 뜻한다.

## compact row·H2 준비 예산 재검토

355 실제 warm profile을 재사용한다(새 ARM 최적화 결과가 아니다). geometry32548명령,H2 12518명령,합45066명령은CPI1/84MHz에서0.5365ms다. 둘을 통째로 없애도 첫 BG가 앞선 ROM 창에 도달하는 데 필요한0.873217ms/73351명령에 부족하다. H2 CRC4316명령과 독립 의미검사를 실제로 제거할 수도 없으므로 현실적인 이득 상한은 더 작다.

다음 후보는 compact row를 읽을 때 공통 row 의미·scroll/H2 원재료를 함께 준비하되,canonical CRC와독립 expected는 따로 검증해야 한다. geometry 전체와H2 전체를 삭제했다고 계산하지 않는다. expand52393,begin_step39533의 요구 tile/material/dirty 준비와 첫 plan 발행까지 함께 비교해야 한다. 첫 ROM 창 부족,ROM accept 후 마감 부족,연속 프레임 전체 초과분은 서로 다른 지표여서 더하지 않는다.

FPGA의 우선 비교 후보는 두 가지다. (A) source/query를 NES clock에 유지하고 output record/receipt 실행을 같은 clock의 공통 phase 실행기로 옮겨 기존 query 왕복 추가를 피한다. SPI ingress queue의 실제 dual-clock read와 SNES 소비 추적을 함께 연결해야 하며,84→22MHz의RLE/CRC/최종 검사 비용 증가를 전부 계산해야 한다. (B) host 실행을 유지하되 collector가 안정된 row/record 단위를 공급하도록 바꿔1957개 개별 query와 source 주소 진행을 대체한다. 기존512B scratch의 동시 사용·새 buffering·STOP drain을 입증하기 전 포트나 저장을 회수했다고 계산하지 않는다. 어느 쪽도 선택된 구현은 아니다. 이번 per-query CDC 후보의 좁은 FF/카운터 튜닝을 반복하지 않는다. 추가 record 저장/credit/drain 비용과 기존 압축 이득도 전부 포함한다. source-host2035cap와queueSPI650cap는 미달성 목표이며 검증된 회수량이 아니다. production227/GBC164/saveSRAM 및 자동 merge는 변경하지 않는다.
