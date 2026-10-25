# NES349 — active record·header·RAM 포트 교체 범위 재검토

338 RTL·336 ARM을 유지한다. 이번 결과는 기존 RTL의 소유권 감사와 기존 측정의 재계산이다. 새 RTL/ARM 실행·Quartus MAP·FIT·STA를 수행하지 않았고, 새 면적/시간 절감은 입증하지 않았다. 348의 독립 A/B 실패를 보존하며 두 후보의 절감을 합산하지 않는다. `tools/analyze_nes_owner349.py`가 기존 2,197개 증거 파일을 재해시하고 9개 일정/프레임의 실제 ARM E1 전송으로 로더 작업량을 계산한다. 정적 검사 PASS는 새 하드웨어 동작 검증을 뜻하지 않는다.

## 결론과 수정한 방향

남은 header 별칭 제거·active record의 RAM 이동만으로 4.023ms와 1,866comb 부족을 해결할 근거는 없다. `header[]`, `record312`, `length/first/count/token`은 이미 배선이며 중복 레지스터가 아니다. active record는 121bit이지만 그 비트 수를 comb 절감으로 바꿔 계산할 수 없다. 기존 347의 host/queue/plan 1,374comb + source 647comb 절감 배분은 달성 예측에서 제외한다. 348의 실제 전체 결과는 source +46comb, 공동 제어 +3comb였기 때문이다.

다음 구현 후보는 **원본 압축 packet RAM을 유지한 host 실행 포트의 단일 소유자**로 한정한다. 수신/실행 context를 합치거나 독립 expected를 actual receipt로 대체하지 않는다. 다만 이 후보도 단독으로 전체 목표를 닫는 구조로 승인하지 않는다. 실제 삭제할 기존 출력식과 새 제어를 대응시킨 뒤, 전체 비용으로 손익이 성립할 때만 구현한다. 단순 HLOAD 상태명/주소 mux 이동이나 반복 합성은 하지 않는다.

## 실제 저장과 삭제 가능한 경계

기준 파일은 `probes/nes-ingress338/window03/nes_mux260.sv`, `nes_queue260.sv`이다.

| 대상 | 현재 실체 | 교체/유지 판단 |
|---|---|---|
| header[0..20], 192bit record312 | active305의 wire view, 72bit zero 등 | 저장 절감 0. API 정리만으로 면적 이득 계상 금지 |
| active305 | op/section16 + start/encoded/span48 + token32 + left8 + endpos17 =121bit | 실행 중 변경되는 context. start/span은 batch descriptor로 덮고 token/left는 consume 후 갱신한다. ingress header로 직접 alias 불가 |
| HLOAD/HCHECK + field338 | RAM 필드 선택과 active 바이트별 load; seq 재검사 | 실제 교체 후보. 물리 byte cursor가 header/descriptor/payload를 읽고 필요한 field만 latch하는 구조와 비교. CHECK 의미검사는 유지 |
| parser_address/cursor/qlen | 현재 byte 위치, batch 다음 descriptor, packet 한계 | 동시에 필요한 값은 유지. cursor는 현재 range 끝을 보관하므로 단순히 parser_address와 동치가 아님 |
| canonical_address313/queue read_address312 | expected 주소와 packet 주소의 port B 선택 | 주소 생성 소유자를 host에 모을 수 있으나 물리 두 주소영역 선택은 여전히 필요. mux를 상위로 옮긴 것만으로 삭제 계상 금지 |
| expected read/write 요청과 held byte | 원본 packet→expected 저장, 최종 expected 순회 | 공통 ISSUE/WAIT/ADVANCE에 grant 단위로 통합할 후보. outstanding read의 owner/tag와 returned data 유효성 유지 |
| accepted/retired/consumed 및 identity/token | 저장 승인/저장 반환/실제 소비와 재사용 방지 | 세 사건은 다르다. 함께 하나의 완료 counter로 대체하지 않음 |
| independent CRC/coverage/receipt | 실제 read event와 기대값의 독립 검사 | 유지. parser 성공이나 DMA 시작을 완료로 간주하지 않음 |

HLOAD의 10/14/15개 field에 대응하는 물리 주소는 0,1,2,3,10,11,14,15,12,13,16,17,18,19,20이다. 이를 원본 header의 순차 16/20/21B 읽기로 바꾸면 field mux 대신 field decode가 필요하고 **packet당 6 host clocks 증가**한다. 동일 wire ABI에서 주소만 단순화하는 후보는 면적 감소가 합성으로 확인되기 전에는 채택하지 않는다. payload를 RAM에 다시 복사하는 새 normalized record는 추가하지 않는다.

## RAM 포트·수명 계약

현재 1024×8 TDP RAM은 expected 0..471, 빈 공간 472..511, packet slot0 512..767, slot1 768..1023이다.

| 시점 | port A | port B | 공개/재사용 조건 |
|---|---|---|---|
| E1 수신 | accepted bank의 원본 byte 기록 | 다른 committed head의 header/payload 또는 expected 접근 | CRC/길이/identity 통과 전 head 공개 금지 |
| head 실행 | 다음 E1을 다른 bank로 수신 가능 | HEADER → PACKET → EXPECTED 소유자 중 하나 | read 발행 후 다음 clock 응답을 해당 owner에 귀속 |
| metadata 확장 | 수신 그대로 | packet read 후 held byte의 expected write | 두 접근을 같은 port에서 동시에 처리한 것으로 계상 금지 |
| descriptor/DMA | 다음 E1 수신 가능 | parser byte 접근 또는 expected walker | immutable DMA context와 실제 read receipt 완료까지 보존 |
| retire/consume | retire 뒤에만 해당 저장 bank 재사용 | consume은 실제 DMA read 검증 후 별도 진행 | accepted−retired≤2, consumed를 저장 credit으로 쓰지 않음 |
| STOP/fault | write/commit 억제 | pending request와 response 유효성 취소, expected write 억제 | 이미 할당한 serial/token namespace를 되돌리지 않음 |
| final ACK | 새 수신 승인 정책 유지 | 최종 expected/actual 검사와 display view | 정확한 12read/token 및 VBlank 조건 뒤 공개 |

40B gap에는 21B header 두 개(42B)가 들어가지 않는다. 15B compact record +5B control을 slot마다 두는 **산술 배치**는 맞지만 무료 대안이 아니다. packet당 최소 15번 추가 RAM write, byte selection, commit 순서, 읽기/쓰기 중재와 invalidation이 생기고 mutable121bit context도 여전히 필요하다. port A의 SPI byte 간격에 넣으려면 E1 write 우선과 copy 미완료 commit 보류를 증명해야 한다. port B에 넣으면 현재 expected/parser 작업을 밀어낸다. 이번에는 이 배치를 선택하지 않는다.

실제 교체 시에는 HEADER/PACKET/EXPECTED를 단일 host port request로 만들고 outstanding 1개, 1clock RAM 응답, write grant 시에만 진행하는 규칙을 사용한다. queue 내부의 field338/load response adapter와 host의 별도 returned-byte 경로를 **함께** 없애는 것이 구현 경계다. ingress port A, SPI CRC/response snapshot, NES plan mailbox/CDC는 별도 수명이라 유지한다. 임의 stall·STOP 시 pending tag만 없애고 이미 공개한 token을 되살리지 않는다. final expected walker와 실제 소비 adapter는 공통 grant를 사용할 수 있어도 검사 데이터와 완료 근거는 독립이어야 한다.

## 시간 예산 — 위상 효과 분리

| 기준 warm907 | 전체 시간 | 의미 |
|---|---:|---|
| 제한 ROM 연속 일정 |20.689660812ms|60Hz 대비4.022994145ms 초과 |
| 동일 시작 시각/ROM 위상 |25.051199382ms|연속 일정과 다른 고정 기준. 60Hz 대비8.384532715ms 초과 |
| 정상 ROM 연속 일정 |13.410066350ms|제한 ROM 통과 증거가 아님 |

실제 warm907 E1 15packet의 HLOAD+HCHECK 작업은 185host clocks = **2.202240µs**이다. CHECK/독립 검사를 남겨 놓고 로더를 완전히 없애는 비현실적인 경우의 직접 작업 상한이다. 전체 시간 절감 상한은 아니다. IRQ/poll/ROM/VBlank 경계를 넘으면 증폭되거나 가려질 수 있으므로 반드시 동일 위상에서 다시 측정해야 한다. 순차 full-header 대안은 90host clocks =1.071360µs 추가하며 wire byte 증가는 없다.

같은 위상에서 source 완료2.666695272ms → 첫 BG ROM 요청8.381149ms 사이에 **5.714453728ms**가 있다. 이전 허용 구간의 끝6.089722ms에 닿으려면 이 구간을 **3.423026728ms 이하**, 즉 **2.291427ms 이상** 줄여야 한다. 창 끝과 같은 요청 시각만으로 grant를 보장하지 않으므로 ROM arbiter latency와 창 안 전체 필요한 read를 별도 검증한다. 후반 actual ROM accept 이후3.833249ms는 계획 상한3.180ms까지 **0.653249ms** 추가 감소가 필요하다. 두 예산을 연속 일정의4.023ms와 단순 합산/차감하지 않는다.

338/336을 유지하므로 348 A의 입력 압축1.296ms를 새 후보에 미리 더하지 않는다. 348 A조차 첫 요청7.085119ms로 이전 창보다0.995397ms 늦었고 fixed warm 전체 시간은 동일했다. 348 B의 연속 warm −4.182µs도 start +9.500µs와 고정 위상 후반 +5.318µs를 분리하면 구조적 개선이 아니다.

ARM 우선 계측 범위는 full COMMIT 이후 geometry/first-map/first-E9까지다. 기존 SPI/IRQ/credit 서비스 우선순위, clear→BG→mark→OBJ 순서와 tile 선행 생산을 유지한 채 immutable preparation을 재사용할 수 있는 지점만 후보로 삼는다. early BG prefix/추가 E9/내부32B plan 확장은 344/348 회귀가 있으므로 재도입하지 않는다. 새 준비/검사/응답 byte와 IRQ instructions를 모두 포함한다. source completion·request·accept·post-ROM·absolute finish를 각각 기록한다.

## Quartus Lite 전체 비용과 중단 기준

338 전체 MAP은 22,144LE / **17,274comb** /9,018FF /307,808RAMbit다. device15408 대비1866comb 부족;155comb 여유를 둔 cap15253까지 **2021comb 순감소**가 필요하다. 이 값은 FIT 성공 보장이 아니다.

| 중복 없는 own 비용 묶음 |338 comb|이번 예산 판단 |
|---|---:|---|
| host |2161|active121bit/별칭만으로 비용을 추정하지 않음 |
| queue + SPI |798|ingress·response·credit 유지 비용 포함 |
| plan |459|CDC/decoded live context 유지 |
| source |1747|이번 baseline 유지, 절감 선계상0 |
| validator/aperture |1159|독립 검사 유지, 절감 선계상0 |
| 나머지 전체 |10950|삭제를 입증하지 않았으므로 유지 |
| 합계 |17274|net2021 미확보 |

source/validator/outside를 유지하면 host+queue+plan3418을 **1397comb 이하**로 줄여야 한다. **59.13% 순삭제** 요구이므로 header/port 정리만으로 달성 가능하다고 볼 근거가 없다. 347의2044 joint cap만 달성하면15900comb로 여전히492 부족하다. `candidate_comb`, `candidate_time_gain`은 null이다. 새 FSM/control RAM/주소 arbiter/commit state/port stall/응답 증가를 모두 추가 비용으로 계상하고, parent inclusive+child를 중복 합산하지 않는다.

다음 실행 순서와 gate:

1. 338에서 header/descriptor/expected의 RAM read 발행·응답·write grant·STOP 취소를 같은 trace에 계측한다. 새 port owner가 제거할 기존 case/주소식/응답 adapter를 1:1 목록으로 확정한다. 유지되는 mux를 삭제 항목에 넣지 않는다.
2. ARM first-BG 구간의2.291427ms 요구와 post-ROM0.653249ms 요구를 각각 다룬다. 독립 일정 후보와 port 후보를 분리 검증하고 cold905/906, warm907, 동일 위상/연속/정상 ROM 및2slot 응답 비용을 함께 비교한다. 앞 프레임 단축으로 warm 시작만 이동한 것을 이득으로 세지 않는다.
3. 삭제 범위만으로2021comb를 설명하지 못하면 작은 header 후보를 전체 목표 해법으로 밀지 않는다. 더 넓은 host 실행/독립 검사 인터페이스 경계를 다시 설계하되 retained checker 비용을 무료로 만들지 않는다. 정당화된 후보 한 번의 동일 경계 whole Lite MAP 후 비용 회귀면 중단; seed/FIT 반복 금지.

구현 승인 전 검증 목록은 simultaneous ingress/active bank, CRC reject, queue wrap/full/credit, pending read 중 STOP, final expected walk 중 STOP, stale token/late receipt, 중간 batch 취소, RAM freeze, raw0, exact finalACK/VBlank다. 기존348 PASS는 유지되지만 새 구조에 자동 승계하지 않는다. full firmware RUN/실물 ARM WCET/full65816/whole pixels/FIT/STA/실물60fps는 여전히 미검증이다. Production227/GBC164/saveSRAM 및 PR 자동 merge는 변경하지 않는다.
