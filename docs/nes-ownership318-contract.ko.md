# NES318 — 315 RTL + metadata 선행 발행의 source·plan 소유권 재검토

이번 단계는 **기존 실행 증거와 전체 Lite MAP를 재검산한 구조 검토**다. 새로운 RTL/ARM 실행 또는 합성을 수행하지 않았다. 기준은 `nes-metadata317/arm01`의 **315 RTL + 317 ARM 선행 op15**이며, 회로가 증가한 317 공동 terminal RTL은 제외한다. production227/GBC164/saveSRAM은 그대로다.

## 측정 기준과 ROM 위상

`analysis/ownership318-verification.json`은 기존 결과 PASS, ELF/RTL 해시, 실제 소스 및 MAP 소유 비용을 검사한다. board와 실행 transport 소스에는 빈 줄 차이만 있어 토큰 단위로 비교했다. 재실행 명령은 `python -X utf8 tools/analyze_nes_ownership318.py`다.

| 제한 ROM, frame907 | 315 기존 ARM | 315 + 선행 metadata ARM |
|---|---:|---:|
| 시작, ms | 263.660336424 | 263.146978532 |
| 첫 BG 요청, ms | 272.093212 | 271.580582 |
| 첫 cache backend 요청 수락, ms | 274.905042 | 274.905042 |
| 첫 BG tile 수락, ms | 274.905315 | 274.905315 |
| BG 요청→backend 수락, ms | 2.811830 | 3.324460 |
| 첫 BG 이후 완료, ms | 5.661364 | 5.361549 |
| 프레임 비용, ms | 16.906342576 | 17.119885468 |

시작은 0.513357892ms, BG 요청은 0.512630ms 빨라졌다. backend 요청/첫 tile 시각은 같고 BG 이후 및 절대 완료는 **0.299815ms 개선**됐다. 프레임 비용은 `완료 변화 − 시작 변화 = +0.213542892ms`다. 세 프레임 합계 개선을 warm 60fps 달성으로 바꾸어 말하지 않는다. 현재 부족은 **0.453218801ms**다.

`firstmiss305`는 최초 miss 검출이 아니다. cache는 `back_request=request && ready && !hit`, ready는 backend ready를 요구한다. 따라서 이 이벤트는 허용된 backend 요청이다. 제한 TB는 `cycle % 357368 ∈ [330088,354640)`와 `cycle % 12 == 3`을 요구하고 core 요청을 우선한다. 요청 위상은 268231→256953이지만 수락 위상은 둘 다 330092다. 같은 창을 기다리는 동안 요청을 더 앞당겨도 이 기록의 첫 ROM 수락은 빨라지지 않는다.

누적 counter는 차분해야 한다. 선행 ARM의 직전 kind2 tile→첫 BG 구간 차분은 slot-denied 73,139, core-denied 0, other 0, read 1이다. 이는 271.578400ms부터의 구간이며 정확한 요청 시작 구간이나 프레임 전체가 아니다. 실제 NES RUN 대신 고정 qualified TB와 모델 core 경쟁을 사용했으므로 물리적 ROM WCET도 아니다.

op15는 272.682210ms에 전송 완료해 첫 BG보다 2.223105ms 앞선다. 이 이득은 유지한다. op10/11 map manifest와 terminal op3는 receipt에 의존하므로 무조건 같이 앞당기지 않는다. 실제 M4 703,982 instructions, SPI 1,165B, max storage credit 2를 포함한 일정이다. IRQ 본문/진입·종료 모델도 기존 실행에 포함한다. normal01은 317 공동 RTL이므로 315+선행 ARM의 unrestricted 비교 자료로 대신 쓰지 않는다.

## 전체 회로 비용과 교체 예산

315 전체 Lite MAP: **22,664 LE / 17,870 comb / 9,040 FF / 307,808 RAM bits**. comb 목표 15,408 대비 **2,462 부족**이다. LE/배치/STA 통과를 의미하지 않는다. entity 괄호 안 own 비용을 전체 합산해 17,870과 일치시키고, 하위 비용을 포함한 부모와 자식을 중복 합산하지 않았다.

| 경계 | comb | 처리 |
|---|---:|---|
| host flow own | 2,493 | packet/descriptor/manifest 실행 및 완료 소유자 재구성 |
| validator own | 1,009 | 독립 기대값·coverage·CRC 검사 유지, 명령 재해석 제거 검토 |
| queue own + SPI own | 277 + 695 | 2슬롯 및 immutable 응답 유지, 공통 host transaction 소유자 |
| source encoder | 1,345 | query/압축/CRC 및 base RAM 유지, continuation·주소 제어 교체 검토 |
| source transport inclusive | 433 | source→host 두 bank와 CDC 포함; POP≠input ACK≠display ACK |
| plan transport inclusive + endpoint + wrapper own | 369 + 94 + 2 | host→NES bank publish, plan decode/retire 소유자 |
| plan 경로 내 cache/arbiter/tile | 961 | 위 control 예산 밖에 유지; 삭제 가능한 중복 제어로 계산하지 않음 |

| 교체 범위 | 현재 comb | 다른 부분 고정 시 허용 replacement | 128 여유 포함 |
|---|---:|---:|---:|
| host/validator/queue/SPI | 4,474 | 2,012 | 1,884 |
| + source transport·plan control | 5,372 | 2,910 | 2,782 |
| + source encoder | **6,717** | **4,255** | **4,127** |

가장 넓은 경계도 **36.65% 순감소**가 필요하다. 단순히 source/plan mux를 붙이는 것으로 충족한다고 예상할 근거는 없다. 새 중재·CDC·directory·응답 저장 비용까지 replacement 안에 들어가야 한다. 위 수치는 설계 상한이며 합성 예측이 아니다. 기존 source/plan CRC 공유와 query cursor 공유를 다시 절감으로 계산하지 않는다.

## RAM 포트와 완료 소유권

| 저장소 | 실제 포트 소유자 | 동시에 유지할 조건 |
|---|---|---|
| source transport 512×8, 2×256B | NES write / host SPI read | source 생산과 D4 읽기 동시; 248B block 및 seal/POP 검증 |
| plan payload 1024×8, 2×512B | host write / NES read | 다음 E9 공급과 현재 tile 실행 동시; 마지막 plan CHECK 후 bank 반환, decoded fields는 tile_done까지 유지 |
| queue 1024×8 | SPI ingress write / host 실행 read·expected write | expected 0..445, reserved 446..479, slots 480/752; 저장 credit과 consume 분리 |
| phase 1024×8 | source NES A / validator host B | source scratch 상위512B와 output receipt 영역은 phase 전환 조건 아래 재사용; persistent valid/hash/H2는 보존 |
| tile/map staging 4096×8 | 기존 producer/host 및 SNES 소비 경로 | DMA가 읽는 동안 재사용 금지, receipt는 실제 완료 이후 |

source·plan·queue RAM을 이름만 바꿔 하나로 합치면 NES에서 source write+plan read, host에서 source read+plan write+queue 실행이 겹친다. 두 물리 포트로 무중재 처리할 수 없다. SPI가 직렬이어도 background 실행/다른 클록의 생산까지 직렬인 것은 아니다. 32B 예약 directory도 현재 사용되지 않으며 새 레코드를 넣으면 read/write 시간과 mux 비용을 계산해야 한다.

**우선 검토 후보는 RAM을 유지한 클록별 실행 소유자 2개**다.

1. host transaction 소유자가 D4/D5, E1, E9의 수신·송신 진행/immutable snapshot/seal을 관리한다. raw bytes를 복사하는 추가 버퍼 대신 기존 bank와 범위를 참조한다. queue/plan/source endpoint의 중복 진행과 완료 dispatch를 실제 삭제 대상으로 명시한다. 클록이 다른 source producer 상태를 host로 직접 옮기지는 않는다.
2. NES 실행 소유자가 input source 작업과 output plan decode의 phase 전환을 담당한다. 기존 source query continuation과 plan READ/CAPTURE 진행 중 공유 가능한 부분만 대체한다. source 압축과 plan 의미검사 자체는 유지하고, ROM 캐시/변환기는 그대로 둔다. source drain/input COMMITTED 확인 전 port owner를 plan으로 바꾸지 않는다.
3. validator는 host 명령을 다시 decode하지 않는 독립 관찰자로 둔다. 실제 accepted byte, actual DMA completion, generation/token 및 expected canonical record를 입력으로 검사한다. 명령 count만 receipt로 인정하거나 producer CRC를 정답으로 돌려 쓰지 않는다. 하나의 주소 cursor를 모든 검사에 복사하는 방식은 독립성을 훼손하므로 제외한다.
4. 완료는 `stored → published → consumed → verified → displayed`로 분리한다. slot bank 반환, plan bank 반환, tile_done, input COMMITTED, final ACK는 같은 event가 아니다. STOP은 양쪽 publish/쓰기와 stale completion을 차단하고 물리 ROM 응답은 drain한다. final ACK는 exact display read coverage·token·VBlank 이후에만 허용한다.

대안인 단일 host/NES 전역 FSM 및 shared RAM crossbar는 이번 우선 후보에서 제외한다. CDC와 추가 port 중재 비용이 늘고 이미 확보한 source/plan 공급 overlap을 잃는다. RAM phase 공유만으로 comb 부족을 해결했다고 판단하지 않는다.

## 시간·면적 동시 검증 계약

첫 BG 수락을 유지할 경우, 현재 시작에서 60fps를 맞추려면 BG 이후 5.361549ms를 **4.908330199ms 이하**로 낮춰야 한다(8.45% 이상). 이는 필요 조건이며 달성 예측이 아니다. metadata prep를 더 앞당기는 것만으로 고정 창 대기를 줄이는 효과는 이 구간에서 이미 소진됐다. DMA/plan credit·IRQ 처리 우선권을 유지한 host dispatch 단축, 마지막 DMA 이후 verified/display 경로 단축을 함께 계측해야 한다. 선행 source/plan 계산이 이전 허용 창에 들어가는지는 별도 검증 없이 절감에 포함하지 않는다.

다음 구현의 첫 gate:

- 315+선행 ARM을 별도 unrestricted ROM 기준으로 실행하고, 기존 제한 연속905..907 일정도 유지한다.
- 동일 **절대 ROM 위상과 시작시각**을 강제한 A/B를 추가해 service 비용을 분리한다. 그 후 시작 위상 경계(창 직전/직후, core 경쟁)에서 공급·STOP·credit을 검증한다. 임의 delay로 warm 측정값만 낮추지 않는다.
- 새 source/plan 소유자에서 concurrent publish/POP/E9/2-slot full, partial packet STOP, stale response, 마지막 plan bank 조기 반환 후 tile_done 지연, expected/actual mismatch, premature ACK를 검사한다. 기존 독립 검사/STOP/final ACK/VBlank 증거는 유지하되 새 구조 검증을 대체하지 않는다.
- 실제 M4 ARM·IRQ·SPI 응답·port stall을 모두 계상하고, 제한907 ≤16.666667ms와 절대 완료/세 프레임 합계/BG 이후 비회귀를 함께 확인한다. 모델서비스 한계는 계속 표시한다.
- 동일 전체 보드 Lite MAP에서 comb ≤15,408, RAM ≤307,808 및 새 latch/undriven 없음. 이후에만 whole71/full RUN/배치·STA를 검토한다.

이번 결론: **metadata 선행 발행은 보존하고, source encoder까지 포함한 6,717→4,255 comb 경계와 클록별 포트 소유자 구조를 다음 구현의 검증 후보로 정한다.** 아직 시간·회로 동시 절감이 입증된 후보는 없으며 현재 부족 0.453219ms/2,462 comb는 그대로다.
