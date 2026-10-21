# NES291 제어 교체 경계와 RAM 소유권 감사

기능 기준289·성능 기준287을 유지한다. NES290의 끝 주소/조기BEGIN 후보는 계속 미채택이다. 이번 단계는 실제 생성 RTL, 기존 전체 Quartus Lite 보고서, 정상·제한ROM 실행 로그를 다시 대조한 **구조 감사**다. 새 RTL·시뮬레이션·MAP을 수행하거나 절감량을 측정한 단계가 아니다.

결론은 **작은 대기 제어 제거만으로 시간·회로 부족을 함께 해결할 근거가 없다**이다. 합칠 제어와 유지할 소유권은 아래처럼 확정했지만, 목표 회로량에 들어가는 구현 후보는 아직 확정하지 않았다. 합성되지 않은 제어를 0개로 계산하지 않는다.

## 고정 경계와 필요한 축소 폭

287 whole MAP의 own comb를 계층별로 다시 합산했다. 합계17671, 디바이스 한도15408, 부족2263이다. 부모의 inclusive 수치와 자식 수치를 더하지 않았다.

| 경계 | 기존 comb | 나머지를 유지할 때 새 구현 예산 | 128개 여유 포함 |
|---|---:|---:|---:|
| host 단독 | 2361 | 98 | -30 |
| validator 단독 | 1090 | -1173 | -1301 |
| queue+plan+SPI만 | 1355 | -908 | -1036 |
| host+validator | 3451 | 1188 | 1060 |
| 기존 고정 경계 전체 | 4853 | 2590 | 2462 |

고정 경계는 host2361/validator1090/queue129/plan568/SPI658/glue47이다. 경계 밖12818을 그대로 부담한다. 음수는 해당 블록을 전부 없애는 불가능한 가정에서도 부족하다는 뜻이다. host+validator만 바꾼다면 **65.575% 축소**가 필요하다. 이 표는 필요한 예산이며 실제 새 회로 추정치가 아니다. 전체 회로 재매핑으로 경계 밖이 달라지면 예산도 다시 계산해야 한다.

source encoder1346과 transport425, tile producer204, aperture167, admission/final mailbox 등의 기존 비용은 별도 계층에 남아 있다. 이 값들은 위 host own2361에 포함되어 있지 않다. 이들을 삭제했다고 계산하지 않았으며, 공유할 경우 새 CDC·중재·동시성 비용을 포함한 경계 변경부터 필요하다.

## 제거 대상과 남길 검사

`analysis/joint291-ownership.csv`는 실제289 생성 RTL의 파일·행·문자열 anchor, 수명, 제거/보존 결정을 연결한다. 이것은 검토한 계약이며 자동 liveness/formal 증명이 아니다.

1. **단일 packet read 실행 제어**: header/H2/map/manifest의 HREAD/HCAP/PREAD/PCAP 진행을 한 소유자로 둔다. NORMAL의 SNES 주소는 같은 queue read port에 중재한다. queue에는 다음 E1 쓰기가 동시에 가능하므로 queue RAM을 phase RAM에 단순 겹치지 않는다. registered read latency, qtag, 순차 실소비 검사는 남긴다.
2. **descriptor→receipt의 단일 완료 경로**: host의 OTILE/OSELECT/SEND/WAIT_RECEIPT/ORET 중계와 validator range 완료를 같은 host-clock 제어 안에서 연결하는 것이 교체 대상이다. 원본 descriptor는 검사가 끝날 때까지 유지한다. 독립 domain/alignment/duplicate/CRC 검사와 RAM read-before-write는 남는다. 이 제어 이름들이 모두 실제 독립 LUT 비용이라는 뜻은 아니다.
3. **manifest decode→RAM 비교의 단일 진행 제어**: ORLE/OCHECKNEXT의 ready 왕복을 validator 비교 완료 continuation으로 대체할 수 있다. compressed offset·RLE remaining과 expanded manifest cursor는 동시에 필요하므로 하나로 합치지 않는다. 요구조건166B+map256B, cold full-map, raw0, persistent-valid 비교는 유지한다. 두 RAM 주소를 연속 비교하는 checked_byte도 유지한다.
4. **retire 한 곳에서 결정**: ordinary는 정확한 payload read와12B ACK를 확인한 다음 CRC tap과 receipt walk 완료까지 기다린다. batch map은 각 범위 DMA·receipt 이후 다음 범위로 가고 마지막 범위에서만 credit을 돌려준다. packet_seq/accepted/retired/token은 서로 다른 수명을 가지므로 합치지 않는다.
5. **최종 표시 별도 완료**: seal·12B 표시 순차 읽기·token/mask·owner NONE·queue/tile 요청 없음이 충족된 경우에만 기존 final mailbox를 통해 lease를 반환한다. packet ACK나 staging 완료로 대신하지 않는다.

이 목록은 기존 host·validator 두 FSM을 단순히 한 enum으로 합치자는 제안이 아니다. payload CRC tap은 NORMAL read/ACK 관측과 동시에 동작한다. 이를 직렬화하면 실소비 byte를 놓치거나 SNES 대기를 늘릴 수 있다. packet reader와 CRC 진행 상태를 모두 공유하는 안은 제외한다. `at`는 이미 header/ACK/display에서 재사용하므로 또 새로운 절감으로 세지 않는다. `v_map_end`는 다음 descriptor까지 남아야 하므로 range walk cursor와 별개다.

## RAM 포트 계약

| 저장소 | 현재 소유자와 동시성 | 유지 조건 |
|---|---|---|
| 4packet queue | host-clock E1 write + head read | CRC admission 뒤 불변, parser_retire 전 재사용 금지 |
| phase RAM port A | NES-clock source | source/display lease가 주소 중첩을 분리 |
| phase RAM port B | host-clock validator | receipt/validity/CRC/H2/display의 유일한 writer 유지 |
| tile/map aperture | tile 또는 map producer + SNES 소비 | token·exact-read·consume 뒤에만 반환 |
| E9 plan 두 bank | host 다음 bank write + NES sealed bank 소비 | tile_done/EA까지 불변, CDC/credit 유지 |

phase RAM은 이미 양 clock의 서로 다른 포트를 사용한다. host의 queue packet 진행과 validator의 metadata RAM 진행은 같은 clock이지만 서로 다른 주소·데이터가 동시에 살아 있다. RAM 주소 register만 겹치는 변경을 전체 port 소유권 통합이라고 부르지 않는다. STOP/fault가 각 write enable을 차단하는 기존 계약도 그대로다.

## 시간 부족의 위치

실행 로그의 `parser`는 OSETUP부터 qretire까지, `receipt`는 map range 수락부터 WAIT_RECEIPT 완료까지다. header 읽기, SNES payload/ACK, CRC tap 전체, ARM planner, SPI, ROM 대기 전체를 측정한 구간은 아니다.

| 289 일정 | 전체 진단 시간 | parser 구간 합계 | map receipt 구간 합계 |
|---|---:|---:|---:|
| 정상907 | 15.314998ms | 0.019332ms | 0.000250ms |
| 제한ROM907 | 17.999648ms | 0.019333ms | 0.000252ms |

제한907의 60Hz 초과분은 **1.332981ms**다. 위 두 구간을 고정 일정에서 전부0으로 놓아도17.980063ms, 초과1.313396ms다. 이는 제거 가능한 실제 상한이나 새 일정 예측이 아니다. 불가능한 전량 제거 가정에 겹친 구간의 중복 합산 가능성까지 허용한 진단이며, polling/ROM 위상이 바뀐 후의 시간을 보장하지 않는다. 그럼에도 단순 ready 대기 제거에 ms 단위 순수 가속을 배정할 근거는 없다.

290의 native71 기록도 재대조했다. 조기 완료 DMA는906의5개뿐이고 warm69는0이다. 따라서 고정 batch 분할만으로 warm planner를 숨긴다는 가정은 계속 제외한다. 첫 완결 tile 범위를 더 빨리 만드는 planner 순서 변경은 별도 범위로 검토해야 하며, E9 계획의 완결·변경 row·ROM 소비 순서와 실제 packet 증가/추가 ACK 비용을 함께 계산해야 한다.

289 실제 ARM text26450B/BSS47060B/관측stack1296B를 그대로 부담한다. 287의 full71 warm 최대26.375411ms(954)는 기존 성능 자료이며, native289의 full71 시간으로 바꿔 부르지 않는다. 289 새 일정은 정상/제한3씩뿐이다. source280 replay와 일반65816 CPU279 trace, CPI1/84MHz 가정, fullRUN/live65816/WCET/물리60fps 미증명도 그대로다.

## 이번 검증과 다음 작업

`tools/audit_nes_joint291.py` analysis02 PASS: 기존 입력 hash, 289↔287 RTL 동일성, whole own 합계,5가지 교체 예산,11개 소유권 anchor,6개 기존 일정의 구간 합계,71개 선행DMA 기록을 검산했다. 분석 결과와 CSV를 공개한다. 기존 기능 PASS를 새 기능 시험으로 세지 않으며 새 MAP/FIT/STA는 없다. 회로 부족2263과 실제 최적화 미완료 상태는 변하지 않았다.

다음은 위 **packet read/descriptor admission/manifest comparison/retire를 함께 소유하는 실행 제어**의 구체적인 datapath·state 전이와 독립 검사 경계를 설계하고,3451→1188을 뒷받침할 수 있는 제거 논리를 확인하는 것이다. 조건 없는 절감 숫자는 배정하지 않는다. 그 규모의 근거를 찾지 못하면 queue/plan/source를 포함한 역할 배치 변경과 비용을 비교한다. 동시에 시간 쪽은 최초 완결 tile 범위까지의 실제 ARM 생산·ROM 소비 경로를 따로 줄여야 한다. 근거 없는 cursor·FSM 비트·seed 반복은 하지 않는다.

실제 교체 후보가 정해진 뒤에만 독립 검사/STOP/최종ACK와 native ARM/IRQ/공유SPI/ROM을 연결해 정상71·heavy7·제한ROM 및 matched whole Lite를 수행한다. production227/GBC164/saveSRAM은 변경하지 않았고 자동 merge하지 않는다.
