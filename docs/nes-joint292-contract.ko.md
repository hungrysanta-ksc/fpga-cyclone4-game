# NES292 실제 ARM batch 확정 시점과 공동 제어 설계

기능 기준289·성능 기준287을 유지한다. 기존 M4 ELF를 실제로71프레임 실행해2130번 planner step의 명령 수, 확정된 E9 batch, 미확정 batch 내용, 닫힌 DMA 범위를 새로 기록했다. 명령 생산은 기존71프레임과 같고 fixture 명령 read0이다. FPGA·SNES와 연결한 새 일정은 아니다. 회로 부족2263과60fps 미달 상태는 그대로다.

## 조기 DMA가 없었던 원인

warm69 모두 첫 확정 batch가 **step29, 마지막 단계**에서 나왔다. step0..28은 BG row 처리이며, 마지막 단계가 OBJ/OAM·palette·raw 마무리와 최종 flush를 수행한다. 시작 시에는3B의 slot0 blank plan이 이미 pending이다. 기존15개/240B batch 정책 때문에 중간의 적은 BG 변경 계획이 ARM buffer에 남아 있고, `output_size285`가0이므로 refill이 읽을 수 없다.

이는 그래픽 계획이 전혀 없었다는 뜻은 아니다. 907은step5부터 추가 BG 계획이 있고, 마지막 단계 직전6개/38B가 대기한다. 954는11개/73B,962·963·970은13개/87B가 대기한다. 다만 중간 buffer는 `order247_insert`가 삽입 정렬하므로 아직 불변 전송 자료가 아니다.

미확정 batch를 그 순간 동결한다고 **가정한 분석**도 수행했다. warm32개에서 범위가 닫히지만31개는slot0의16B blank 범위만 닫힌다. 실제 그래픽 범위가 조기에 닫히는 경우는930 하나다. 이 가정은 새 SPI 전송이나 올바른 조기 lease/ACK를 검증한 것이 아니다. 이후 insert가 순서를 바꿀 수 있고 DMA packet/token 개수도 바뀔 수 있다.

또한 warm24개는 최종 tile 계획 자체가blank 한 개뿐이다. 기존 resident 코드가kind2를 bank hit 생략에서 제외하고 있어, 이16B를 매번 다시 생산한다. 이를 재사용하도록 바꾼 실험은 이번에 하지 않았다. 생략하려면 양 bank 초기화·STOP 무효화·required coverage·최종 token 규약을 함께 검증해야 하며, 이를 큰 ROM 가속 후보로 계산하지 않는다.

## 다음에 비교할 실행 경계

첫 후보는 **BG row 처리가 끝난 경계에서 pending batch를 확정하고 E9 refill을 수행한 뒤, 마지막 OBJ/OAM 처리를 계속하는 방식**이다. 임의의 중간 row에서 pending bytes를 읽는 것과 다르다. BG exact-key scratch는 마지막 OBJ 단계에서 재사용되므로, 이 phase 경계의 소유권도 보존해야 한다.

목표는 우선 FPGA의 BG 변환·ROM 읽기와 ARM의 마지막 계산을 겹치는 것이다. aperture는 다음 비연속/kind 전환 tile 또는 END를 받아야 마지막 범위를 seal하므로 **조기 E9 공급≠조기 DMA 완료**다. 마지막 OBJ 단계까지 유지하던 묶음을 나누면 OBJ 정렬의 batch 경계, E9 개수, CRC, credit, DMA grouping이 바뀔 수 있다. 동일 command count/wire라고 미리 가정하지 않는다.

| 프레임 | 마지막 직전 pending 계획 | 마지막 step 실제 명령 | CPI1/84MHz 환산 |
|---|---:|---:|---:|
| 907 | 6 | 49595 | 0.590417ms |
| 952 | 4 | 103139 | 1.227845ms |
| 954 | 11 | 104127 | 1.239607ms |
| 955 | 10 | 106197 | 1.264250ms |
| 962 | 13 | 81807 | 0.973893ms |
| 963 | 13 | 79345 | 0.944583ms |
| 968 | 1(blank) | 97179 | 1.156893ms |
| 970 | 13 | 73092 | 0.870143ms |

이 시간은 마지막 step 호출의 전체 계산량이지, 실제로 숨길 수 있는 시간이나 절감 예측이 아니다. 968에는 선행 BG 자료가blank뿐이므로 이 후보의 효과가 작을 수 있다. native producer의 후속 비용도 남는다. 예를 들어907의producer는87750명령(1.044643ms 환산)이며, 이 값에는 실제 dispatch/SPI/ACK 비용이 포함되지 않는다. 측정은 dispatch를 인터셉트하는 기능 probe다.

## 공동 제어의 구체적 전이

`analysis/joint292-controller.csv`에17개 전이 규칙과 guard/action/invariant를 적었다. 아직 RTL 구현·formal 검증된 FSM이 아니라 설계 계약이다. 상태 수를 LUT 절감량으로 환산하지 않는다.

- 하나의 host-clock 실행 제어가 queue header/internal payload 읽기, descriptor admission, receipt RAM walk, manifest 비교, packet retire까지 소유한다. host의 OTILE/OSELECT/SEND/WAIT_RECEIPT/ORET와 OCHECKNEXT 등의 중계 상태를 이 실행 제어의 완료 전이에 흡수하는 것이 실제 제거 대상이다.
- SNES bus 관측과 payload CRC tap은 동시에 살아 있어야 한다. 실행 제어가 CRC/RAM 작업 중이어도 ordinary packet 읽기·ordered ACK를 관측할 수 있도록 bus 활성 문맥은 별도로 유지한다. 새 bus mode/continuation selector·mux 비용도 회로에 포함해야 한다.
- ordinary는 exact read+12B ACK+CRC tap 완료 후 receipt 검사로, map은 exact DMA read+token consume 후 receipt 검사로 들어간다. 한 RAM walker에서 domain/duplicate/CRC와 persistent validity를 확인한 후에만 공통 완료 전이로 간다.
- manifest의 compressed cursor/RLE remaining과 expanded422B cursor, 두 RAM 값을 비교하는 checked_byte는 함께 살아 있으므로 유지한다. 단일 실행 제어가 decode→registered RAM read→comparison→advance를 진행한다.
- batch map은 다음 범위가 있으면 head/credit을 유지한 채 descriptor read로 돌아간다. 마지막 범위 또는 ordinary 검사 완료만 packet retire로 간다. display는seal·12B exact read·fulltoken·queue/owner empty를 별도로 확인한 뒤 기존 final mailbox를 통해 lease를 반환한다.
- STOP/fault는 모든 경로보다 우선하여 RAM write를 막고 기존 무효화/token 소각을 유지한다. 독립 범위·CRC·coverage 검사를 ARM assertion으로 대체하지 않는다.

header나 map descriptor를 일찍 버리는 방식은 제외했다. SNES가 소비하는 동안 control view와 token/length/first가 유지되어야 한다. 기존 source clock과 host clock을 하나의 FSM으로 직접 합치는 것도 제외한다. 두 clock의 state/register를 공유하려면 별도 CDC 변경이 필요하다.

## 더 넓은 교체 경계의 비용

287 전체 MAP에서 own 비용을 다시 확인했다. source encoder1346+transport425, tile producer204+aperture167을 포함한 확대 경계도 아래처럼 계산했다. 기존 작은 경계와 중복 합산하지 않았다.

| 경계 | 기존 comb | 새 구현 예산 | 필요한 축소 |
|---|---:|---:|---:|
| 291 고정 경계 | 4853 | 2590 | 46.63% |
| +source encoder/transport | 6624 | 4361 | 34.16% |
| +tile producer/aperture | 6995 | 4732 | 32.35% |

경계를 넓혀도 실제 부족량은2263으로 같다. 넓힌 블록을 제거했다고 계산하지 않는다. source/display phase RAM은 공유되어 있지만 clock·lease가 다르고, plan refill·tile ROM·SNES 소비는 동시 실행하므로 직렬화하면 시간을 잃을 수 있다. 새 CDC·RAM 중재·continuation과 검사 비용이 아직 없으므로 이 표만으로 확대안을 채택하지 않는다. 기존 host+validator만의1188 예산을 만족할 근거 역시 아직 없다.

## 검증과 한계

SELECT frontier02/analysis01. actual M4 native71/2130step, 기존 plans·ordinary/map/manifest 명령 일치, 실제 생산 DMA descriptor와 decode된 range 일치, fixture read0 PASS. frontier01의 관측보다 pending 내용·초기blank를 더 자세히 기록했으며 같은71프레임의 명령 수·계획·range·생산 비용이 같음을 검산했다. native289의 producer 명령 수도71개 모두 같다.

원본 ELF·canonical records·plan oracle·palette와 관측CSV, RTL/source anchor, 기존 whole MAP를 hash로 고정했다. source와 생산기 기존 코드가 검사에 사용되며, 이 실행은 실제ACK·STOP 재검증이나 IRQ/ROM 경쟁 실행이 아니다. 기존 STOP/최종ACK 증거를 새 시험으로 세지 않는다. 새로운 frame 시간·whole Lite/FIT/STA/physical60fps 수치는 없다.

다음은 BG phase 확정 후보를 실제ARM refill/IRQ/ROM에 연결해 extra E9·변환 시작·최초DMA·최종ACK를 비교하는 것이다. 먼저 명령 의미/정렬/credit/STOP 보존을 확인하고, 효과 없는blank-only 사례도 비용표에 남긴다. 회로 쪽은 위 공동 실행 제어의 공유 datapath와 새 context/mux 비용을 포함해 제거 근거를 확보해야 한다. 둘이 함께 성립하기 전에는 전체 목표 달성이나 후보 채택을 주장하지 않는다. production227/GBC164/saveSRAM은 그대로이며 자동 merge하지 않는다.
