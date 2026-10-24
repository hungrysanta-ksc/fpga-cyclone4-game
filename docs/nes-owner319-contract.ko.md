# NES319 — 클록별 진행 소유권 실제 연결

기준은 315 RTL + 317 metadata 선행 발행 ARM이다. 317 공동 terminal RTL은 사용하지 않는다. 이번 변경은 **host admission, source record 종료, source→plan cursor 소유권**을 실제 연결한다. host/validator/source/plan의 모든 FSM을 하나로 대체한 구현은 아니다. 검증 결과와 수치는 `analysis/owner319-verification.json`에 결합한다.

## 실제 삭제·이동·유지 범위

- host SPI 전송 소유자가 command 수락 시 E1 queue 또는 E9 plan의 admission을 한 번 저장한다. queue·plan endpoint의 개별 `can_write` register와 갱신 제어를 삭제한다. live enable/fault, seal의 CRC·길이·sequence 및 plan 의미검사는 각 실제 소비 경계에서 유지한다. SS 종료 edge의 기존 nonblocking timing을 유지하여 마지막 승인 상태를 먼저 소비하고 다음 전송에는 남기지 않는다.
- NES source encoder의 `rec_i/record_length`가 실제 마지막 byte를 결정한다. transport의 중복 8bit remaining countdown을 없애고 record-open 1bit를 사용한다. transport는 block CRC 완료 후 bank를 publish한다. source CRC, block CRC, ARM의 실제 decode 검증을 유지하며 마지막 byte accepted와 CRC 완료를 혼동하지 않는다.
- source의 13bit cursor는 input ACK 후 V_IDLE에서 0으로 전환되고, 그 이후 plan의 zero/step을 처리한다. plan의 별도 10bit read cursor와 갱신 제어를 삭제한다. source query/압축 실행 중에는 plan 입력으로 cursor를 변경하지 않는다. plan의 순서/길이/lease/세대/shape 검사 및 tile_done까지 decoded fields 유지 조건은 그대로다.
- 512B source transport, 1024B plan, 1024B queue, 1024B phase 및 tile/map staging RAM의 물리 포트와 저장 용량은 유지한다. source write/host read 및 host plan write/NES read 동시성을 직렬화하지 않는다. 새 다중 RAM crossbar나 CDC mailbox는 추가하지 않는다.
- 독립 validator, expected/actual receipt, storage credit≠consume, STOP·ROM drain, display 읽기 coverage/token·최종 ACK·VBlank 제약은 유지한다. source/plan decode FSM과 host/validator 실행 FSM은 여전히 별개이며 이번에 삭제했다고 계산하지 않는다.

## 일정 비교 방법

`probe_nes_owner319.py`는 같은 317 ARM 이미지·IRQ 처리·2슬롯·ordinary65816 bus trace를 사용한다. 고정 비교는 capture 시작을 절대 1/161/321ms 이후 같은 NES edge로 맞춘다. source enable의 실제 시각과 누적 ROM cycle을 기록하고 양쪽의 완전 일치를 검사한다. ROM qualified 조건과 core 우선순위는 바꾸지 않는다. 고정 간격의 의도적 idle은 처리 시간 절감으로 계산하지 않는다.

고정 비교와 별도로 기존 연속905..907 제한 ROM 일정, 정상 ROM 기준/후보를 실행한다. 합성은 동일 전체 보드 Quartus Lite MAP 한 회이며 FIT/seed 반복이 아니다. ARM metadata op15 선행 발행, op10/11 및 op3의 후반 순서도 유지한다.

고정 위상에서의 frame 비용은 기존 연속 일정의 0.453219ms 부족과 직접 비교할 수 없다. 위상이 바뀐 프레임의 절대 시간은 달라질 수 있으므로 같은 위상 A/B의 차이와 연속 일정의 차이를 별도로 보고한다. source cycle 비용+output 경과로 계산한 기존 지표와 실제 start319→frame_done도 함께 저장한다.

## 오류 주입과 재현

새 실제 ARM/ROM 통합 TB에 source record 도중 STOP, plan RAM 읽기 도중 STOP, 부분 E1/E9 수신 STOP, 조기 표시 ACK, expected/receipt mismatch, 물리 ROM 요청 도중 STOP을 주입한다. fault 후 phase·queue RAM freeze와 seal/lease/ACK 비노출을 확인하고 ROM 요청 도중 STOP에는 drain도 요구한다. 정상 전체 실행을 별도로 확인해 오류가 단순 정지로 가려지지 않도록 한다. 정상 경로의 unexpected-fault 검사는 주입 전까지 그대로 적용하며 의도적으로 주입한 이후에만 bounded fault/freeze 검사로 전환한다.

최초 fixed01은 SV 숫자 literal 바로 뒤의 `?`가 파싱되지 않아 컴파일 실패했다. 공백을 명시한 fixed02부터 실제 실행했고 최초 로그/소스도 보존한다. 새 라이선스 문제는 없으며 기존 승인된 FLOAT wrapper를 사용했다.

guards01의 관측 변수 선언 위치 오류, guards02의 Questa `-lib` 경로 해석 실패도 보존한다. guards03은 각 실행 디렉터리에 독립적인 local work library를 복사해 실행한다. 라이선스나 전역 library 설정을 변경하지 않았다.

guards03의 STOP1..4는 통과했다. case5에서는 의도한 조기 ACK fault를 정상 경로의 flow-fault monitor가 먼저 종료시켜 freeze 확인에 도달하지 못했다. guards04는 주입 이후에만 그 monitor를 bounded fault/freeze 검사로 전환하고 case5..7을 실행한다. 주입 전 unexpected fault와 취소 후 sink acceptance 감시는 유지한다. guards03 case5 실패도 보존하며 정상 동작 통과로 세지 않는다.

## 판정과 전체 비용

| 항목 | 315 + 선행 metadata ARM | 319 후보 | 변화 |
|---|---:|---:|---:|
| 제한 연속907, ms | 17.119885468 | 17.119885468 | 0 |
| 정상 연속907, ms | 14.763186476 | 14.763186476 | 0 |
| 전체 LE | 22,664 | 22,618 | −46 |
| 전체 comb | 17,870 | 17,824 | −46 |
| 전체 FF | 9,040 | 9,022 | −18 |
| RAM bits | 307,808 | 307,808 | 0 |
| 60fps 시간 부족, ms | 0.453218801 | 0.453218801 | 0 |
| comb 부족 | 2,462 | 2,416 | −46 |

고정 시작/ROM 위상 A/B의905·906·907 모두 완료 시각, ARM 명령 수, SPI bytes가 일치한다. 세 프레임 ARM 합계4,584,771명령/SPI22,407B다. 연속 제한 일정도317 arm01의 세 프레임 완료 시각과 완전히 같다. 제한 일정 SPI22,379B, 관측 stack1304B, SysTick28회이며 정상 ROM도 별도 기준/후보가 일치한다. 새 기준 normalref01은315 RTL+동일 선행 ARM의 실제 실행이므로 이전317 공동 RTL의 정상 결과를 대신 사용하지 않는다.

6,717comb 교체 경계는 **6,700comb(−17)** 이다. 전체 −46 중 경계 밖 −29는 전체 합성의 mapping 변화다. 이를 host/source/plan 제어 자체에서 제거한 논리라고 귀속하지 않는다. source/host/validator/plan FSM 추출은 유지되고 기존 cache_index141 latch 외 새 latch/undriven은 없다. 전체 LE는 물리 배치 결과가 아니며 MAP comb 감소만으로 보드 fit을 선언하지 않는다.

**시간·회로 동시 개선 실패, production 미채택.** 실제 접합과 작은 상태 절감은 검증했지만 318의6,717→4,255 예산에는 크게 못 미친다. source/plan cursor·admission 공유를 더 미세 조정하거나 FSM 번호/seed를 바꾸는 다음 단계는 채택하지 않는다. 아직 남아 있는 host/validator의 descriptor·manifest·receipt 실행 본체와 source/plan decode 상태·주소 생성을 실제로 없애는 교체 범위를 별도로 구현해야 한다. 이번 결과를 그 전면 교체의 완료로 취급하지 않는다.

실제 ARM 명령은 실행하지만 CPI1/84MHz 및 IRQ 진입·종료 비용은 모델이다. ROM qualified/core 경쟁은 TB 모델이며 full NES RUN이 아니다. ordinary65816은 기존 실제 CPU bus trace를 재생하고 tile/map/VBlank 일부는 모델이다. 전체71/fullRUN/FITSTA/실물60fps를 입증하지 않는다. production227/GBC164/saveSRAM은 변경하지 않는다.

SELECT: fixed reference01/candidate fixed02, continuous window01, normalref01/normal01, whole board01; guards03 cases1..4 + guards04 cases5..7. 15개 정상 프레임 일정과7개 오류 주입 통과. analysis01은5개 실행의 모든 PT_LOAD 주소·크기·바이트가317 arm01까지 동일함을 확인하고 RTL/ELF/TB/CPU trace/전체 MAP/guard 로그를 해시로 결합했다. 전체 ELF container hash는 빌드별로 다르므로 동일하다고 주장하지 않는다.
