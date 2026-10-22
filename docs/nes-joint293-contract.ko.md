# NES293 BG 확정 batch의 실제 refill·IRQ·ROM 연결

NES293 BG 확정·실제 refill/IRQ/ROM 연결 후보는 미채택. 원래 BG/OBJ batch 용량을 예약해 정렬 경계를 유지했고 native71의 plan 순서·1039명령/73260B 일치·fixture0 PASS. BG 전후 STOP/실제 ISR·생산 실패·정상/제한3씩 최종ACK PASS. 정상907 15.407088ms(+0.092090), 제한907 18.094783ms(+0.095135), 부족1.428116ms. 선행 tile 변환은 생겼지만 planner 종료 전 DMA 소비0. ARM text+172/BSS+8/stack1296B; RTL287 동일·새MAP 없음·절감0·2263comb 부족 유지.

기능 기준289·성능 기준287을 유지한다. 이번 후보는 재현 가능한 실험으로 보존하며 생산 경로로 채택하지 않는다. 정상과 제한 ROM에서 warm907 시간이 모두 늘었고 회로 부족도 줄지 않았다. 제한905의 이득 -0.072317ms는906의 +0.072317ms와 상쇄되므로 별도 성능 개선으로 선택하지 않는다.

## 구현과 정렬 실패 수정

`nes_bg293.py`가 실제 ARM 생성 C에 BG 완료 경계(`phase==2 && g==groups`) flush를 넣는다. `next_step286`의 마지막 OBJ/OAM 계산 전에 불변 batch가 만들어지면 기존 `prefill287`이 E9, plan bank credit, IRQ/ROM 경로로 전송한다. pending 배열을 읽는 우회 경로는 없다.

처음의 단순 flush는 native01에서952의 tile 순서 불일치를 검출했다. 원래 BG와 OBJ가 섞이는 batch의 정렬 경계가 바뀌었기 때문이다. 수정본은 BG가 차지했던 byte/plan 수를8B 상태에 예약하고 첫 OBJ batch의 남은 용량에 반영한다. 정상 flush에서 예약을 해제한다. 이렇게 원래 flat plan 순서와 DMA 묶음 경계를 유지한다. 원래71프레임 중28개만 파일 batch가1개/3B 늘고43개는 파일 크기·batch 수가 같다. 실제 live E9는 plan refill 분할 때문에 시험한3개 모두1회 증가한다. 파일 framing과 SPI 거래 수를 같다고 가정하지 않는다.

native02에서71개 plan의 encoded record 순서, 실제 생산된 ordinary/map/manifest 명령1039개/73260B가289와 byte 단위 일치했다. fixture 메모리를 poison한 상태에서 read0이다. flat 순서 비교로 framing 변경만 허용했으며 명령 oracle을 완화하지 않았다. 최초 native01 실패, naive test01 PASS3, 수정 test02를 별도 보존한다.

## 실제 일정 비교

단위ms. source280 실행 기록과 새 ARM/실제 SPI·IRQ·tile ROM·출력 RTL 일정을 합산한 **진단 전체 시간**이다. CPI1/84MHz, IRQ entry/exit24cycle 할당, 일반65816 기존 trace, map/tile/display bus 모델의 범위는 그대로다. fullRUN·새 전체65816 실행·hardware WCET·물리60fps가 아니다.

| 조건/프레임 | native289 | BG293 | 변화 | E9(변화) | IRQ wait |
|---|---:|---:|---:|---:|---:|
| 정상/905 | 79.998358 | 80.128857 | +0.130498 | 9 (+1) | 10 |
| 정상/906 | 56.574003 | 56.702138 | +0.128135 | 8 (+1) | 16 |
| 정상/907 | 15.314998 | 15.407088 | +0.092090 | 3 (+1) | 7 |
| 제한 ROM/905 | 105.718595 | 105.646278 | -0.072317 | 9 (+1) | 13 |
| 제한 ROM/906 | 114.910303 | 114.982620 | +0.072317 | 8 (+1) | 27 |
| 제한 ROM/907 | 17.999648 | 18.094783 | +0.095135 | 3 (+1) | 8 |

정상3 합계는+0.350723ms, 제한3 합계는+0.095135ms다. 제한907의60Hz 초과는1.332981→1.428116ms로 커졌다. 정상907 여유1.259579ms만으로 전체60fps를 주장하지 않는다. cold905/906은 따로 표시했다. 이번 full71은 기능 검증이며 full71 시간 측정은 아니다. 공동 후보 부적합이 확인되어 unchanged RTL의 반복 MAP/FIT이나 heavy71 재일정을 수행하지 않았다.

정상905/906/907에서 마지막 planner 단계 시작 전에 각각82/14/6개 tile 변환이 시작됐다. 제한 ROM에서는30/1/1개다. 그러나 두 조건 모두 마지막 단계 종료 전 `tile_consume/map_consume`은0건이다. 첫 소비는 마지막 단계 종료 후 정상907 1.066793ms, 제한907 3.752438ms다. native 출력 생산기가 여전히 전체 planner 완료 후 `frame259`에서 DMA 명령을 만들기 때문이다. 조기 E9/ROM 변환과 조기 SNES DMA 완료를 구분해야 한다.

E2 polling, IRQ wait/timer fallback, SPI byte, slot 대기와 core ROM 우선권 횟수는 공개 CSV에 전부 포함한다. 제한907 slot wait91816cycle은 추가 공급만으로 남은 ROM 경쟁이 없어지지 않았음을 보여준다. planner의 마지막 step 비용만 전체 시간에서 차감하지 않는다.

## 독립 검사·STOP·ACK

- native02 기존6 guards, guards01 생산 실패/잘못된 batch8 guards PASS. 이 경로의 dispatch는 인터셉트하므로 실제 ACK 증거로 세지 않는다.
- bg-guards01은907 BG 전·후 및 최종 planning 후 STOP을 주입했다. 다음 plan/produce/commit 거절, 이미 발행한 prefix 불변을 확인했다. RAM 전체 소거를 뜻하지 않는다.
- BG flush 진입 지점에 PB8 edge를 주입하여 실제 compiled ISR,8word exception frame 복귀 후 batch와 예약 상태 일치를 확인했다. 기존 IRQ8cases/33exceptions도 동일 ELF로 PASS(`guard_nes_irq293.py`). 이것은 제한 ROM 실행 도중 STOP을 함께 주입한 시험은 아니다.
- test02/window01 각3프레임은 실제 E1 명령 일치, 최대4credit, plan bank/ROM 경로와 최종 표시 ACK를 확인하고 `finish267` 다음에만 `commit285`를 실행했다. 독립 validator·CRC·receipt·STOP RTL은287과 hash가 같다. 기존287의 부정시험을 새 실행으로 세지 않는다. 새 RTL 부정시험이나 token wrap 시험은 없다.

ARM text26450→26622B(+172), BSS47060→47068B(+8), live 관측stack1296B 동일이다. 이 BSS에는 시험용 output/material 저장소가 포함되며 target RAM 예산에서 제외했다고 주장하지 않는다.

## 공동 제어 검토와 Quartus Lite 비용

| 범위 | 기존 comb | 새 구현 최대 예산 | 이번 측정 절감 |
|---|---:|---:|---:|
| host+validator | 3451 | 1188 | 0 |
| queue/plan/SPI/host/validator/glue | 4853 | 2590 | 0 |
| 위 범위+source encoder/transport | 6624 | 4361 | 0 |

실제287 whole Lite MAP은22569LE/17671comb/9025FF/307808bits다. 한도15408comb 대비2263 부족을 그대로 부담한다. 이번 합성 대상 RTL hash가 기준과 같으므로 기존 전체 보고서를 사용하며 **새 Quartus MAP 측정은 없다**. ARM 조기 batch를 FPGA 제어 삭제로 계산하지 않는다.

같은 생성 RTL에서 공동 완료 전이 후보를 재대조했다. `OTILE/OSELECT→ORET`, `SEND→WAIT_RECEIPT→CONSUME`, manifest byte→RAM compare의 왕복은 공동 실행 continuation에 흡수할 대상이다. 하지만 `ACKWAIT`의 `qdone && tap_idle278 && range_ready`는 실제 payload/CRC와 receipt가 모두 끝난 뒤 credit을 반환하는 조건이다. 하나의 ready로 합치면서 이 조건을 없앨 수 없다. CRC tap은 SNES 읽기와 병행하고 validator RAM read/write는 latency가 있으므로 전부 직렬화하지 않는다.

사전 descriptor domain/alignment 검사는 DMA 전에, 독립 duplicate/CRC/coverage 검사는 실소비 후에 필요하다. 이 두 시점을 단일 사후 검사로 바꾸는 안은 제외한다. manifest의 compressed offset/RLE 남은 수와 expanded422B cursor도 동시에 살아 있다. source는 다른 clock과 phase-RAM port를 사용하므로 단일 host FSM에 넣으려면 CDC/중재 비용이 추가된다. 이 비용과 bus context/continuation mux를 포함해1188 또는2590comb 안에 들어가는 구현 근거는 아직 없다. 상태 이름의 개수를 실제 LUT 절감으로 세지 않는다.

결론적으로 BG 선행 공급 단독은 기능 연결에 성공했지만 시간·회로 공동 개선 후보로는 탈락이다. 이번 결과를 기준으로 비용표를 갱신했으며 제어 통합 완료나 회로 절감을 주장하지 않는다.

## 다음 경계와 재현

BG 확정만 더 잘게 나누지 않는다. 기존 E9/plan 소비에서 확인된 완결 BG 범위를 bounded native producer가 즉시 DMA descriptor로 발행하도록 결합하고, 뒤따르는 OBJ 정렬·열린 range를 유지한다. host packet reader/descriptor admission/manifest compare/retire 공동 실행기에서 제거할 datapath와 concurrent CRC tap·새 continuation/context/mux를 명시하고4853→2590(또는 host+validator3451→1188) 근거를 확보한다. source/plan까지 확대할 때는 clock·RAM 포트·lease 중재를 포함한다. 실제 공동 후보가 있을 때만 normal71/heavy7/restricted와 matching whole Lite를 실행한다. 독립 검사·4credit/2planbank·STOP·최종ACK 유지, 단순 FSM/주소/seed 반복 금지.

선택 증거: native02/guards01/bg-guards01/irq-guards01/test02/window01/analysis02. 분석 최초 실행analysis01은 Python dependency import 오류로 중단됐고 보존했다. 최종 분석은 기존 ARM dependency loader를 사용한다. 원본 로그·ELF·생성 C/RTL·event·hash archive는 `probes/nes-joint293`에 있고 공개 JSON/CSV는 `analysis/joint293-*`다. wrapper private 로그와 라이선스는 Git에 넣지 않는다.

실행은 `probe_nes_live293.py --last 907 --irq --plans ../probes/nes-joint284/test04 --cpu-trace ../probes/nes-joint279/cpu01`에 ASCII 절대 `--out`과 승인된 Questa bin을 지정했다. 제한판은 `--rom-window 1` 추가. 승인된 FLOAT wrapper 안에서 순차 실행했다. native/guards는 같은 최종 ELF의 `--source`, 별도 `--out`을 지정한다. `analyze_nes_joint293.py --base ../probes/nes-joint293 --out <새 분석 폴더>`로 비용/원본 hash를 검산한다.

production227/GBC164/saveSRAM은 변경하지 않았다. 자동 merge하지 않는다.
