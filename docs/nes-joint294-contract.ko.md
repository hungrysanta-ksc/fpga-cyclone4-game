# NES294 BG 선행 batch와 증분 native DMA

NES294 BG batch와 증분 native DMA 연결 후보 미채택. native71 plan/1039명령73260B 일치·fixture0,STOP/생산실패/H2/IRQ 및 정상·제한3씩 최종ACK PASS. warm69 중32개 조기DMA,31개는16B blank뿐. 정상907 15.423360ms(289대비+0.108362),제한907 18.093828ms(+0.094181),초과1.427162ms. RTL287 동일/회로절감0/2263comb부족;새MAP 없음.

기능 기준289와 성능 기준287은 유지한다. 293의 정렬 경계를 보존하는 BG flush와290의 증분 native producer를 결합했다. 290의 FPGA endpoint 산술 후보는 포함하지 않았다. `tiles290(0)`가 불변 batch를 읽고 kind/slot 연속성 또는2048B 한도로 이미 닫힌 range만 DMA descriptor로 발행한다. 열린 마지막 range는 상태로 유지하고 최종 planning 완료 후 `tiles290(1)`에서 마무리한다. H2/BEGIN은 COMMITTED 이후 시작하고 최종 H2 일치·SEAL·finish267 다음에만 commit한다.

## 기능과 실제 조기 소비

native01의71프레임에서 plan record 순서와 기존1039명령/73260B가 byte 단위로 일치했다. blank 초기화·BG·OBJ 순서를 변경하거나 명령 oracle을 완화하지 않았다. 기록된 명령 메모리는 poison,fixture read0이다. 이71프레임은 dispatch를 인터셉트하는 기능 시험이며 실제71개 일정을 측정한 결과가 아니다.

warm69 중32프레임에서 planner 마지막 단계 전에 descriptor가 발행됐다. 그중31프레임의 조기 출력은16B blank 범위뿐이다. 비blank 조기 범위는930의2개뿐이며906(cold)에는5개가 있다. heavy952/954/955/962/963/970도 blank1개만 조기 발행하고968은0개다. 분포는 공개 native CSV에 기록했다.

실제 SPI/ROM 연결의 정상·제한907에서 마지막 planner 단계 시작 전에1개 소비가 확인됐다. 293의 조기 변환만 있던 상태에서 실제 DMA 소비까지 연결되었지만 이는 초기 blank 타일이다. 조기 descriptor 발행과 실제 소비를 별도로 기록한다. `consumed_before_final_step_start`는 마지막 next_step 호출 직전 checkpoint까지의 소비만 세므로 마지막 단계 이후 발행된 DMA를 섞지 않는다.

## 전체 진단 일정

단위ms. source280 기록+실제M4/공유SPI/IRQ/ROM/출력RTL 일정,일반65816 기존 bus trace와 map/tile/display bus 모델,CPI1/84MHz 및 IRQ24cycle 할당의 범위를 유지한다. hardware WCET/fullRUN/live65816 전체경로/물리60fps가 아니다.

| 조건/프레임 | 기준289 | BG flush293 | 조기 DMA294 | 289대비 | 마지막 step 전 소비 |
|---|---:|---:|---:|---:|---:|
| 정상/905 | 79.998358 | 80.128857 | 80.152175 | +0.153816 | 0 |
| 정상/906 | 56.574003 | 56.702138 | 56.433459 | -0.140544 | 5 |
| 정상/907 | 15.314998 | 15.407088 | 15.423360 | +0.108362 | 1 |
| 제한ROM/905 | 105.718595 | 105.646278 | 105.966910 | +0.248315 | 0 |
| 제한ROM/906 | 114.910303 | 114.982620 | 115.759156 | +0.848853 | 5 |
| 제한ROM/907 | 17.999648 | 18.094783 | 18.093828 | +0.094181 | 1 |

정상907은293보다+0.016273ms,제한907은-0.000955ms다. 제한907의60Hz 초과는1.427162ms다. 정상906 개선이나 cold ROM 위상 변화를 warm 전체 이득으로 일반화하지 않는다. source·ARM·IRQ·polling·SPI·ROM slot/core 경쟁은 CSV에 함께 기록했다.

ARM text27182B/BSS47088B/관측stack1304B다. 289대비text+732B/BSS+28B/stack+8B를 부담한다. final producer 명령수는 중간 생산 비용을 제외하므로289의 전체 생산 명령수와 직접 차감하지 않는다. 전체 ARM 비용은 live 일정의 instructions로 반영했다.

## 유지한 검사

native 기존6개 commit/생산실패/STOP 검사, 부분 planner9개 검사, 선행/최종H2 일치9개 검사, BG 전후·조기DMA실패·발행후·최종계획후STOP/IRQ6개 검사, IRQ8cases/33exceptions를 같은ELF에 실행했다. bg-guards01의5개 PASS도 보존하고 조기 dispatch 실패를 추가한bg-guards02를 선택했다. 오류검사는 intercepted sink이며 제한ROM에서 동시에 STOP을 주입한 시험은 아니다.

정상/제한각3프레임 live는 E1 명령 일치,최대4credit,독립receipt·CRC·표시ACK 및 finish267→commit285를 확인했다. 컴파일된ISR의8word exception frame 복귀도 검사했다. FPGA RTL은287과 동일하므로 기존RTL 부정시험을 새 실행으로 세지 않는다. 새 token wrap/FIT/STA/full71 시간 검증은 없다.

## 공동 제어와 마지막 BG 범위

실제 tile producer는 `opened&&!append_ok` 또는 `wend`에서만 aperture를 SEAL한다. BG batch가 끝났다는 사실 자체는 range 종료가 아니다. ARM producer도 동일한 연속성 규칙을 사용하므로 마지막BG range를 다음 tile까지 열어 둔다. 이것이 대부분의 조기 출력이 blank에 그친 이유다.

기존END를 중간BG flush로 재사용하는 안은 제외한다. `end_sealed`는 plan SPI의 `ended`를 설정하고 이후E9를 거절하며,EA retire는 ended와accepted/owner 조건을 검사한다. 따라서 frame END와 구분되는 range 종료 계약,양쪽 순서·generation·token·CRC·credit·STOP 처리 없이는 해결되지 않는다. ARM에서 descriptor만 강제로 flush하면 FPGA의 열린 aperture와 길이가 어긋난다. 분석 도구가 실제 생성 C/RTL의 해당 anchor와 hash를 확인한다.

공동 실행기의 제거 후보는 packet reader/descriptor admission/receipt walk/manifest comparison/retire다. pre-DMA domain/alignment와 post-consume CRC/duplicate/coverage는 시점이 다르며,concurrent SNES CRC tap을 ready 왕복 하나로 대체할 수 없다. 새로운 range 종료 상태·CDC·context/mux도 비용이다. 제한907 parser+map receipt 구간 합은0.019582ms지만 이를 제거 가능한 시간이나 새 일정 예측으로 사용하지 않는다.

전체 Quartus Lite 기준22569LE/17671comb/9025FF/307808bits,한도15408comb 대비2263 부족은 그대로다. 합성RTL hash가 동일해서 새MAP을 하지 않았으며 측정 절감0이다. host+validator3451→1188 또는 고정경계4853→2590의 대체 예산을 만족하는 구현 근거는 아직 없다. source까지 확대하는6624→4361도 재분류이며 절감이 아니다. 이번에 공동제어RTL을 교체했다고 주장하지 않는다.

## 결정과 다음 작업

기존 append-불일치/최종END만으로는 마지막 BG range가 열려 남는다. 다음은 frame END와 구분되는 BG range 완료 계약을 ARM descriptor 생산과 FPGA aperture/receipt 소유권에 함께 연결하는 안과,출력/plan 제어를 단일 실행기로 대체하는 안을 비교한다. 기존 END를 중간에 재사용하거나 blank 선행DMA를 BG 개선으로 계산하지 않는다. 새 marker·CDC·token·credit 비용까지 포함해 기존 제어 제거 목록과4853→2590 예산 근거를 먼저 확정한다. 독립 pre-DMA bounds/실소비CRC/receipt/manifest/STOP/최종ACK를 유지하고,실질적 공동 후보에만 whole Lite·normal71/heavy7/restricted를 실행한다.

단순BG flush/닫힌range 조기발행 반복은 여기서 중단하고 명시적range완료와 실제제어대체가 함께 성립하는 설계를 먼저 검토한다. 후보는 미채택으로 보존한다. production227/GBC164/saveSRAM은 변경하지 않았고 자동merge하지 않는다.

선택 native01/guards01/h2guard01/bg-guards02/irq-guards01/test01/window01/analysis02. analysis01의 이전test02 경로 참조 오류를 보존하고 수정했다. 원본은 `probes/nes-joint294`,공개비교는 `analysis/joint294-*`다. live는 승인FLOAT wrapper 안에서 `probe_nes_live294.py --last 907 --irq --plans ../probes/nes-joint284/test04 --cpu-trace ../probes/nes-joint279/cpu01`,ASCII절대out/Questa bin을 지정했고 제한판에 `--rom-window 1`을 추가했다. native/guard는 같은output.elf의source와새out을 지정한다. 분석은 `analyze_nes_joint294.py --base ../probes/nes-joint294 --out <새폴더>`로 재현한다. 라이선스/private log는Git에 넣지 않는다.
