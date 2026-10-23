# NES320 — 남은 실행기 교체 범위와 시간·회로 예산

이번 단계는 **319 실제 결과를 재분석한 설계 검토**다. 새 RTL/ARM 실행/Quartus 합성을 수행하지 않았다. 기준은315 RTL에서319의 소유권 변경을 적용하고317 metadata 선행 발행 ARM을 사용하는 후보이며 production 채택은 아니다. `analysis/budget320-verification.json`은319 전체 MAP, 실제 ARM/IRQ/2슬롯 일정15건, 현재 RTL을 해시로 결합한다.

## 결론

작은 cursor/admission 공유나 manifest 종료 체인만 줄이는 방향은 부족하다. **host 실행·검증 RAM 서비스와 NES source·plan 실행을 클록별 두 실행기로 대체**하는 넓은 후보를 다음 구현 대상으로 삼는다. 독립 검사는 상태기계 개수와 구분한다. 기대값과 실제 소비 증거를 합치거나 CRC·coverage 검사를 생략하는 방식은 채택하지 않는다. 이 후보의 시간·회로 동시 달성 가능성은 아직 미검증이다.

## 현재 전체 비용과 재설정한 예산

| 비중복 경계 | 현재 comb | 유지 밖의 비용이 같을 때 필요한 상한 |
|---|---:|---:|
| host+validator | 3,492 | 이것만 바꾸면1,076 (69.2% 감소 필요) |
| host+validator+queue/SPI | 4,465 | 이것만 바꾸면2,049 (54.1%) |
| source+plan | 2,235 | 이것만으로 해결 불가능: 전부 제거해도181 부족 |
| 모든 교체 경계 | 6,700 | 4,284 (36.1%),128 여유 목표4,156 |
| 경계 밖 | 11,124 | 기존 구현 유지, 자동 절감으로 계산하지 않음 |
| 전체 | 17,824 | 15,408,128 여유 목표15,280 |

전체 기준22,618LE/17,824comb/9,022FF/307,808RAM bits. MAP 결과이고 FIT/STA 성공을 뜻하지 않는다. source1,774와 plan461에는 필요한 datapath·mailbox도 포함되어 있어 전량 제거 가능한 제어 비용이 아니다. host/validator3,492도 순수 FSM 비용이 아니다. 지역별 예상 절감을 임의 배분하지 않고 전체4,284를 합성 통과 조건으로 둔다. 기존318의4,255는315 경계 밖 비용 기준이었다. 현재 기준4,284와29 차이는319의 경계 밖 mapping 변화이며 구조 절감으로 귀속하지 않는다.

## 실제 삭제·추가·유지 경계

| 경계 | 삭제/대체할 기존 실행 | 새 실행 소유권 | 반드시 유지 |
|---|---|---|---|
| host descriptor | HLOAD315/HCHECK315, DREAD/DCAP/DCHECK, ordinary/typed별 다음 주소·종료 분기 | 한 active record의 read/capture/dispatch/advance. descriptor load와 payload 소비의 주소 소유권 명시 | 길이/범위/세대/token/sequence 검사, batch 마지막 저장 반환과 DMA 완료 분리 |
| host manifest | MREAD313/MCAP313/MNEXT313/MISSUE313/MWAIT313 및 hash/cert/finish continuation | 같은 실행기의 canonical read 또는 expanded byte 작업. 기존 parser FSM과 새 실행기를 병존시키지 않음 | op15 선행 저장, op10/11 순서, op3 coverage fence, independent expected/actual 비교 |
| validator receipt | V_RREAD/V_RWRITE/V_PREAD/V_PWRITE의 별도 진행/주소 continuation | host 실행기가 요청·RAM latency·commit 단계를 소유하는 고정 port-B 서비스 | 실제 consume에만 receipt 갱신, 중복 receipt 거부, CRC coverage, persistent bank valid |
| validator 검사 | V_CHECKREAD/TEST 및 P-check의 중복 read/return 제어 | 공통 RAM 서비스가 읽고 별도 검사 predicate가 승인/first fault 결정 | validator의 독립 expected 위치/실제 범위 증거. host next-address를 그대로 정답으로 사용 금지 |
| NES source/plan | encoder의 phase 종료와 plan WAIT/READ/CAPTURE/CHECK/READY/RUN/ENDING의 별도 decode·advance 소유권 | source phase 종료 후 plan phase로 넘어가는 NES-clock 실행기. plan 전용 state register와 별도 next-address mux 제거 | source 압축 형식/CRC, plan shape/lease/세대/순서, decoded fields를 tile_done까지 유지 |
| queue/SPI | host terminal과 중복된 clear/load/completion 소유권 | SPI는 입고·CRC/seal·응답 snapshot, host는 slot 저장 반환 및 소비 완료를 각각 단일 갱신점으로 소유 | 2슬롯, 저장 credit≠consume, 전송 중 admission 안정성, CDC mailbox |

공통 RAM 서비스가 checker의 반환을 기다리는 동안 같은 포트를 다른 작업에 내주려면 별도 pending 문맥이 필요하다. 첫 후보는 한 outstanding RAM 작업만 허용하고 읽기 지연/검사/commit을 명시한다. 검증을 직렬화하면서 DMA 공급이 늦어지면 시간 실패다. 별도 observer FSM을 남기고 이름만 공동 실행기로 바꾼 구현은 완료로 인정하지 않는다. 독립 cursor/coverage 저장은 제거 목표에서 제외한다.

## 클록별 포트 계약과 STOP

host queue port-B는 slot payload read와 canonical expected write/read를 시간 분할한다. SPI port-A 입고는 계속 병렬이다. phase port-B는 host receipt/check/hash/display 서비스 전용이며 source port-A와 물리적으로 합치지 않는다. source transport NES-write/host-read와 plan host-write/NES-read의 dual-clock bank/mailbox도 유지한다. staging의 SNES 읽기와 tile/map 생산 수명은 기존대로다. 새 범용 RAM crossbar 또는 clock 간 직접 state 공유는 예산에 넣지 않은 무료 자원으로 추가할 수 없다.

source→plan 전환은 input ACK/commit을 통과한 후에만 허용한다. plan payload 저장 반환, tile_done, BG 범위 완료, frame 종료는 각각 다르다. STOP은 두 클록의 active 작업·pending RAM write·credit publication을 취소하고 이미 수락된 ROM 요청을 drain한다. 새 작업/receipt/seal/final ACK를 노출하지 않는다. bank/token 재사용은 이전 소비와 표시 lease 종료 조건을 유지한다. display의12회 정확한 읽기/token·최종 ACK·VBlank는 그대로 유지한다.

## 실제 일정에서 얻은 하한과 목표

319 제한 ROM 연속907의 실제 이벤트를 다시 계산했다. 시각 단위ms:

| 이벤트 | 시각 | 다음 구간 |
|---|---:|---:|
| 첫 BG tile 공급 | 274.905315 | 마지막 소비까지5.125486 |
| 마지막 DMA 소비 | 280.030801 | op3 release까지0.044247 |
| op3 release | 280.075048 | frame_done까지0.191816 |
| frame_done | 280.266864 | — |

마지막 소비 이후 전체는 **0.236063ms**다. 이것을 무료로 만들어도 부족분0.453218801ms 중 **0.217155801ms**는 이전 일정에서 더 줄여야 한다. 0.044247ms 전체를 FPGA 검사 시간이라고 볼 수도 없다. 구간에는 전송/queue/검사가 겹치며 마지막0.191816ms에는 ARM 상태 응답·IRQ/retire/표시 완료가 포함된다. 구간 길이는 제거 가능한 순수 비용이 아니다. op15는 이미 ROM 대기 중 선행 발행하므로 그 전송 비용을 다시 절감으로 세지 않는다.

첫 BG 시각을 유지하는 비교에서 tail5.361549→**4.908330199ms 이하**가 필수다. 구현의 설계 목표는 마지막 소비를0.400ms 앞당기고 이후 경과를0.060ms 줄이는 총0.460ms로 둔다. 이는 측정 예측이 아니라 실험 통과 예산이다. 충족해도 여유는6.781us뿐이므로 full71/하드웨어 안전 여유로 인정하지 않는다. 이 목표를 위해서는 공통 실행기뿐 아니라 DMA/plan credit 우선 ARM 공급과 상태 응답 일정에서 실제 줄어든 stall을 증명해야 한다. 지금 trace만으로0.400ms의 제거 가능한 stall이 확보됐다고 주장할 수 없다.

ROM 요청을 앞당겨도 qualified 허용 구간과 core 우선순위 때문에 수락 시각이 같을 수 있다. 따라서 다음 비교는 동일 source 시작·ROM cycle 고정 A/B와 연속 제한/정상 ROM A/B를 따로 수행한다. 고정 위상907의 절대 지연을 연속907 부족분과 섞지 않는다.319에서 두 비교 모두 시간 차이0이었던 증거를 유지한다.

## 후보 선택과 실험 중단 조건

1. host/validator만 통합: RAM 서비스 단순화 가능성은 있으나69.2% 감소 요구와 후반0.236ms 상한 때문에 단독 해결책으로 선택하지 않는다.
2. source/plan만 통합: phase 배타성을 이용할 수 있으나 전체 비용이 부족분보다 작다. 단독 해결책으로 선택하지 않는다.
3. **두 클록 실행기+기존 ingress 완료 소유권 대체**: 위6,700 경계를 대상으로 구현할 후보. 압축 전송과 선행 metadata 유지. 대체 FSM/주소 mux의 실제 삭제 목록을 RTL diff로 확인한 뒤 동일 일정과 전체 MAP을 한 쌍으로 평가한다.

ARM에 descriptor/plan을 완전 전개하는 대안은 현재 선택하지 않는다. 추가 SPI bytes/2슬롯 압력/ARM 준비 비용과 FPGA 독립 검증 비용을 함께 계산하기 전에는 decode 제거 이득을 인정할 수 없다.

다음 구현의 필수 관측은 queue/phase RAM 요청-응답-commit, DMA 공급 가능하지만 실행기가 막은 cycle, 실제 consume, storage 반환, plan credit, IRQ 진입/응답, ROM 요청/수락이다. 이 구간이 겹치면 합산하지 않는다. 새 ARM 작업이 생기면 실제 M4 실행·stack·SPI 응답 증가까지 포함한다.319의7개 STOP/조기 ACK/mismatch/ROM-drain guard에 RAM 서비스 read→check→commit 각 경계 STOP, 2슬롯 재사용과 늦은 consume, manifest cursor 오류를 추가한다.

시간과 전체 comb 중 하나라도 개선되지 않으면 FSM 번호/seed/FIT 반복 대신 경계·프로토콜을 재검토한다. 목표 달성 전 wholeFIT/STA·실물60fps 채택을 선언하지 않는다. 실제 M4 명령 실행은 CPI1/84MHz 모델이고 ordinary65816은 기존 CPU bus trace 재생, tile/map/VBlank 일부는 모델이다. 새71프레임/fullRUN/CPU/합성 실험은 이번 검토에 없다. production227/GBC164/saveSRAM 변경 없음.
