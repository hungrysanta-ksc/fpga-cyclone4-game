# NES250 — 공동 회로 비용과 남는 SNES 검사 실측

2026-10-19. 사용자 승인으로 NES249 커밋 `11e59b6`을 PR129에 push하고 설명을 갱신한 뒤, 같은 브랜치에서 후속 검토했다. **249의 독립 source + 독립 receipt 코어 구성은 P2 후보로 채택하지 않는다.** 회로 여유가 없고, 미계측 비용을 담을 시간도 크게 줄었다. 고정 블록 wire 방식 자체의 불가능성을 증명한 것은 아니다.

## SNES에서 실제로 남는 작업

기존2472 진단 ROM/실제 C 송신기를 그대로 실행하고 instruction callback만 추가했다. SEAL의 `validate181`, `mark212`의 비트맵 반복, 그 뒤 DMA 주소 계산·명령 추가, `append212`, coverage 경계를 구분했다. 실제 명령을 건너뛰거나 실행 ROM을 변경하지 않았다.

71프레임/1039 ACK/178 tile retire/132270 VRAM bytes/426 commands/최대13개 list/67개 single-VBlank commit이 기존과 같다. 같은 요청 packet 및 expected 출력 oracle도 byte 비교했다. Mesen의 기존 uninitialized-memory 진단 로그는 보존했으며 이를 새 제품 무결성 보증으로 해석하지 않는다. 검사한 staging/VRAM oracle와 Lua assertion은 통과했다.

| 실측 구간, warm69 | 범위 |
|---|---:|
| `validate181` layout/HDMA 표 검사 | **0.651945..0.653807ms/frame** |
| 비트맵 뒤 명령 작성 및 비트맵이 없는 수신 경로 합계 | 5706..20906 master clocks |
| 비트맵 반복만 제외한 기존 `mark212` 합계 | 9862..42444 master clocks |

700개 수신 구간을 관찰했다. 첫 번째 잔존 정책 `command_tail`은 범위 입장 검사도 FPGA로 옮기고 명령 작성 등만 SNES에 남긴다는 가정이다. 두 번째 `only_bitmap_removed`는 비트맵 반복만 옮기므로 기존 범위 준비·검사가 더 남는다. **두 값 모두 기존 코드의 관찰 구간을 일정에 대입한 것이며, 새 consumer의 실행 시간은 아니다.** HDMA 검사는 두 정책 모두 그대로 남긴다.

## 실제 receipt/validity 코어

249의754B 정책을 동기1024×8 RAM 코어로 구현해 실행했다. 두 화면 validity332B, 현재 received166B, map receipt256B를 쓴다. 범위 bounds/중복, map 순서, 사용 pattern의 validity, metadata exact receipt/full validity, map manifest 일치와 cold 전체 coverage를 검사한다. 최종422 expected bytes를 받은 뒤 `all_consumed`일 때만 seal하고, display ACK 뒤에만 다음 프레임을 받는다. abort/fault 후에는 reset·cold 재시작이 필요하다.

여기서 범위와 expected bytes는 **이미 분해된 시험 입력**이다. 실제 packet parser/CRC/epoch·serial·token/certificate binding, section 의미 검증, query/projector, FIFO read-port 중재, CDC는 구현하지 않았다. `all_consumed`와 display ACK도 실제 경로에 결합되지 않은 입력이다. 이 코어만으로 최종 표시 소유권이 해결됐다고 보지 않는다.

- 기록71프레임, RAM53534B exact 비교 통과. 첫 시험8개 guard 이후, 같은 RTL에 raw2→0 양쪽 validity 무효화, 미소비 finish 거부, cold map 누락을 추가해 **12개 검사** 통과.
- 기록71프레임은 모두 raw_count2였으므로 normal 전환은 별도 directed 검사다.
- warm 실행은 **1775..1907코어클록**,22MHz 환산0.080682..0.086682ms. BEGIN clear부터 range/coverage와 TB의 유한 command 간격을 포함한다. reset 전체 clear, 실제 packet 입력 대기, parser/CDC 및 display 대기는 제외한다. 22MHz는 환산 기준이며 새 STA로 입증한 주파수가 아니다.
- 선택 `receipt02`. 앞선 `receipt01`과 RTL 및71프레임 cycles.csv는 같으며, 동일 RTL의 MAP을 반복하지 않았다.

## source와 함께 합성한 비용

통과한249 source RTL과 receipt 코어를 같은 clk/reset/abort를 쓰는 합성 top에 함께 넣었다. 각자 별도 입력을 갖는 **모듈 묶음**이며 실제 end-to-end 결합 실행은 아니다.

| MAP 경계 | combinational | FF | LE | memory bits |
|---|---:|---:|---:|---:|
| 공동 top | **1489** | **408** | **1506** | **49152** |
| 그 안의 source child | 1065 | 307 | 상위에 포함 | 40960 |
| 그 안의 receipt child | 423 | 101 | 상위에 포함 | 8192 |

source의 base4096×8+512×8/scratch512×8 true dual port와 receipt1024×8 single port가 M9K로 추론됐다. FF 대체가 아니다. 249 source 단독1079LE와 비교하면 공동 top은427LE 증가했지만, 이것을 whole-board FIT 증가량으로 보아서는 안 된다. 합성 맥락에 따라 source comb도1062→1065로 달라졌다.

동일240 보고서의 기존 encoder child는1399comb/409FF다. 새 두 코어는 이미1489comb/408FF이므로 **검사기 추가가 source 국소 절감을 상쇄한다.** query/projector와 새 parser를 아직 넣지 않은 상태다. 기존 source parent2092comb/974FF에는 encoder1399,reader217,transport444와 parent32comb가 포함된다. child와 parent는 중복 합산하지 않는다. query reader를 통째로 무료 제거하는 비현실적 가정에서도 comb 절감은 작으며, 이를490 FIT LE와 환산하는 산술은 하지 않는다.

기존 whole-board 부족 **490LE/40LAB**, mapper/timing 여유, RAM 시나리오 **56/56**은 그대로 미해결이다. 공동 top의 외부 포트는 시험 인터페이스이며 실제 카트리지 pin 배치가 아니다. `map01`은 상대경로 처리에서 실패해 Quartus를 시작하지 못했다. 경로 처리만 고친 `map02`에서 MAP 한 번이 성공했다. full-board FIT/STA/IO/CDC는 실행하지 않았다.

## 실측을 넣은 공동 일정

249와 같은 gap16 범위에 실제 receipt 실행과 SNES 잔존 구간을 넣어 warm69×setup2×잔존정책2 = **276개 조건부 일정**을 계산했다. 249의 core 비용 할당은 실제 receipt 시간으로 교체하고, `validate181`은 별도 추가했다. 기존 source 준비0.474227ms, 입력COMMITTED/tile drain/4credit/manifest/SEAL/표시 표본/최종 retire는 유지한다. parser8cycles/byte와 최종고정2000 master clocks, map run setup은 여전히 할당값이다.

| map setup / 남는 SNES 작업 | 최대 | 잔여 | 초과 |
|---|---:|---:|---:|
| 500 / 명령 작성 등만 유지 | **16.354547ms** | **+0.312120ms** | 0 |
| 500 / 비트맵 반복만 제거 | 16.735415ms | −0.068748ms | 970 |
| 1000 / 명령 작성 등만 유지 | 17.215923ms | −0.549256ms | 954,970 |
| 1000 / 비트맵 반복만 제거 | 17.596790ms | −0.930124ms | 954,962,970 |

최악970의249값15.471664ms/잔여1.195003ms는 새 최선 정책에서16.354547ms/잔여0.312120ms로 바뀐다. **0.312ms는 여전히 query/투영/full ARM/ordinary copy·DMA·dispatch/poll/SPI gap/VBlank와 할당 초과분의 공동 예산**이다. 실기60fps 승인이나 새 전체 경로 시간의 상한이 아니다. 952/955의 VRAM burst 문제도 별도다.

## 판단과 다음 경계

독립 block source에 독립 receipt 코어를 추가하는 이번 구성은 시간·회로 공동 여유를 입증하지 못했다. 이 구성을 그대로 full-board FIT하거나 새 firmware를 만들지 않는다. 생산227, 기능240(unplaced), 기각241/246/2472 CPU, 5886B 진단 이미지, GBC164/saveSRAM은 유지한다.

다음은 두 가지 구조적 비용을 함께 비교해야 한다.

1. source 입력 단계와 output 검증 단계의 실제 비중첩 수명을 입증하고 임시 RAM/주소·CRC·제어를 공유할 수 있는지 검토한다. persistent validity332B는 보존해야 한다. scratch512B와 현재 received/map422B의 재사용은 phase/clock/STOP 소유권을 증명하기 전에는 회수량으로 세지 않는다. 이전에 기각한 control-only ROM/미세 opcode 루프를 재개하지 않는다.
2. ARM의 화면 계획 결과에 포함되는 HDMA 표의 생성·의미검사를 어느 경계에서 봉인할지 비교한다. SNES에서0.654ms를 삭제한다고 가정하기 전에 full ARM 비용, 전송 CRC와 정확한 certificate binding, fault 시 표시 금지까지 증명한다. 이를 FPGA에 단순 추가하면 회로 비용이 더 커질 수 있다.

전체 source/query/SPI를 포함해 어떤 기존 회로를 실제로 없애는지와 최소 소비 경계를 먼저 확정한다. 선택 근거가 생긴 뒤 whole-board/fullARM/최종display ownership과 실기 FIRSTLEVELSCROLL로 진행한다. [계획](nes-joint250-plan.json), [검증](../analysis/joint250-verification.json), [프레임 계측](../analysis/joint250-frames.csv), [공동 일정](../analysis/joint250-schedules.csv), [수신 구간](../analysis/joint250-retained.csv).

재현: `measure_nes_retained250.py`는 기존2472 진단 client/host와 사용자 ROM을 입력받는다. `probe_nes_receipt250.py`는 기존 FLOAT wrapper의 실제 Questa 실행 및 통과한 core를 이용한 단일 공동 MAP을 지원한다. `analyze_nes_joint250.py`는 private 기준 증거를 rehash하고 공개 표를 생성한다. 선택은 `snes01/receipt02/map02/analysis02`; 이전 receipt01/analysis01과 map01 실패도 private archive에 보존한다. 공개 파일에는 ROM·packet·fixture payload를 넣지 않는다.
