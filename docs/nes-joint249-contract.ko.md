# NES249 — source 교체와 타일·최종 검사 공동 비용

2026-10-19. PR128 머지 `64640645`에서 시작한 `codex/nes-typed-schedule-248`, 열린 PR129의 후속 조사다. **가장 유망한 시간 후보는 고정 블록 source + FPGA 통합 수신·유효성 검사다. 회로 여유까지 입증한 후보는 아직 없다.** P1 비교를 유지하며 P2 제품 구현은 선정하지 않는다.

생산227, 기능 기준240(unplaced), 기각241/246/2472 CPU, 5886B 진단 이미지, GBC164와 saveSRAM은 그대로다. 프로그램을 4KiB 또는 6KiB에 고정하지 않는다. 이번 source RTL은 실험용 생성기이며 제품 collector/ARM/SNES 경로에 연결하지 않았다.

## 함께 바꿔야 하는 경계

ARM은 화면 계획과 게임 의미를 맡는다. FPGA는 map뿐 아니라 타일·CGRAM·raw의 수신 범위, 중복, 유효성, 최종 사용 범위 검사를 맡는다. SNES는 제한된 명령 작성·DMA·layout/HDMA 검증·표시를 맡는다. 기존 SNES `mark212` 전체를 단순 삭제할 수 없다. 그 안의 명령 작성 작업은 남기고 별도로 시간 예산을 잡아야 한다.

현재 map만 이전하면 앞선 타일의 `mark` 처리와 마지막 coverage 검사가 장벽으로 남는다. 통합 후보는 FPGA가 수신 중 검사 상태를 누적해 이 두 CPU 비용을 줄인다. **타일 DMA 완료를 기다리는 의존성 자체는 유지한다.** source 교체는 같은 프레임의 입력 SPI와 준비 시간을 함께 줄인다.

| 단일 byte RAM 주소 | 용도 | 크기 |
|---|---|---:|
| 0..165 / 166..331 | 두 대상 화면의 persistent validity | 332B |
| 332..497 | 현재 non-map 수신 내역 | 166B |
| 498..753 | 현재 map 수신 내역 | 256B |
| 합계 | 기존 계획의 1024×8 한 M9K에 수용 | 754B |

이것은 실제 71프레임 범위에 대한 **Python RAM 정책 검증**이다. 동기 RAM 포트·CRC parser·상태기계·CDC 회로를 합성한 결과가 아니다. 기록 중 유효성을 선반영하더라도 모든 chunk의 SNES 소비를 확인한 뒤에만 certificate를 발행한다. source typed 소비는 최종 display ACK가 아니다. dirty/resident 확정과 capture lease 해제는 최종 display ACK 후이며, STOP/abort는 미확정 상태를 무효화하고 cold 재시작해야 한다.

248에서 확인한 append-only aperture, FIFO head read/ACK 소유권 문제도 남는다. interleaved descriptor/value와 32B trailer는 정책 후보이며 실제 결합된 프로토콜이 아니다. 별도 공유 SPI 회로나 clock/reset 도메인의 공짜 통합을 가정하지 않는다.

## source 후보 비교

입력은 기존 의미 투영으로 검증한 4398B fixture다. 실제 collector query와 투영기는 이번 source 시험 밖이다.

- A: 240의 row shift와 literal/gap을 유지하고 raster codec을 제거했다. 71프레임 실제 RTL 출력·CRC·base 비교는 통과했지만 조건부 일정도 남는 시간이 없다.
- B: 32개 66B row와 나머지 36개 최대64B 블록으로 나눈다. 변경 블록은 `block ID + byte bitmap + 변경값`, 행 이동은 `row ID + 방향 + 경계2B`로 보낸다. 복잡한 literal/gap/raster 제어를 고정 블록 경로로 대체한다. 같은 512B scratch와 한 번의 base 읽기/갱신을 사용한다.
- literal-only: 행 이동까지 제거하면 입력이 커진다. 이번 공동 조건에서도 시간 예산을 초과하므로 기각한다.

B의 실험 N5 header는 20B이며 epoch/baseSerial/serial 32비트와 generation 16비트를 유지한다. geometry count/CRC, RAW 연속 offset/6비트 값/END CRC, ACK와 abort lifetime도 유지한다. 헤더를 좁혀 얻은 절감이 아니다. 생산 프로토콜 변경으로 승인된 것은 아니다.

954번 입력 SPI는 A **2220B → B 1961B**, 259B 감소다. warm69 평균은 69.232B 감소하지만 일부 프레임은 최대110B 증가하므로 모든 입력을 줄인다고 일반화하지 않는다. B의 warm 준비 시간은 실제 fixture 실행에서 10433클록, 22MHz 환산 **0.474227ms**다. 이는 collector query/투영/ARM 비용을 포함하지 않는다.

## 처리 일정과 남는 공동 예산

같은71프레임 중 warm69에 대해 source3종 × map2종 × map setup3종 × non-map service3종 = **3726개 조건부 일정**을 비교했다. 실제 C 패킷 순서, 입력 COMMITTED, tile drain, 4credit, manifest FIFO head, SEAL, 기존 표시 비용 표본 상단과 최종 retire를 유지한다. 측정 source 준비를 직렬로 추가해 미입증 겹침 이익을 주지 않았다. cold2프레임은 codec/receipt 검증에는 포함하지만 아래 정상 스크롤 마감 판정에는 포함하지 않는다.

아래 기본 조건은 map run당500 SNES master clocks, non-map packet당500 clocks다. 둘 다 새 consumer의 계측값이 아니다. FPGA에는 입력 byte당8클록과 RAM clear/receipt/coverage 작업을, SNES 최종 고정 작업에는2000 master clocks를 **할당**했다. 이 비용이 실제 구현의 상한이라는 증거는 없다.

| source / map | 최대 조건부 시간 | 16.667ms까지 잔여 | 초과 프레임 |
|---|---:|---:|---:|
| A shift / exact64 | 17.033ms | −0.366ms | 2 |
| A shift / gap16 | 16.938ms | −0.271ms | 2 |
| B block / exact64 | 15.572ms | +1.094ms | 0 |
| B block / gap16 | **15.472ms** | **+1.195ms** | 0 |
| literal / gap16 | 18.130ms | −1.463ms | 3 |

setup을1000으로 늘리면 B/exact는16.829ms로1개 초과, B/gap16은16.333ms로 잔여0.334ms다. setup 가정에 민감하다. 954 B/gap16은 입력1961+출력1938=3899 SPI bytes, source0.474ms, FPGA 할당0.463ms, 최종고정 할당0.093ms를 포함해15.392ms다. 최악 프레임은 이 행과 다를 수 있다.

**잔여1.195ms는 ARM 전용 여유가 아니다.** 실제 query/의미투영, full ARM RUN/IRQ, 새 parser/중재/CDC, 남은 명령 작성·ordinary copy/DMA/dispatch, polling/SPI gap/VBlank 대기 및 할당 초과분이 모두 나눠 써야 한다. 특히 `validate181`의 layout/HDMA 의미 검사가2000클록 안에 들어간다고 증명하지 않았다. 952/955의 VRAM/VBlank 문제, 입력·음향·메뉴, 실물 연속 표시도 미해결이다. 이 표는 실기 FPS나 최악 실행 시간 보장이 아니다.

## 회로 검토

| 경계 | combinational | FF | standalone MAP LE | memory bits |
|---|---:|---:|---:|---:|
| A encoder | 1145 | 340 | 1147 | 40960 |
| B encoder | 1062 | 307 | 1079 | 40960 |
| 참고: 240 전체보드 보고서의 encoder child | 1399 | 409 | 같은 경계 standalone 수치 없음 | 별도 비교 불가 |

A/B는 각각 통과한 RTL과 hash가 같은 단독 MAP을 한 번씩 실행했다. base4096×8 +512×8, scratch512×8 true dual port의 M9K 추론을 확인했다. FF fallback이 아니다. source query/projector, 새 통합검증기, 공유 read-port 중재는 제외됐다. 최종 B 강화 시험도 이전 MAP과 동일 RTL hash다.

240의 source parent2092comb/974FF에는 encoder child가 포함된다. 두 수치를 더하거나 B의 standalone LE를 whole-board FIT에서 빼면 안 된다. 기존 보드는15898/15408LE,1003/963LAB로 **490LE/40LAB 부족**하다. B의 국소 개선만으로 이 부족분에 새 검증기·중재·mapper/timing 여유까지 회수했다고 볼 수 없다.

RAM도 여유가 생긴 것은 아니다. 기존 시나리오 `54 + 프로그램 확장2 − semantic base1 + receipt1 = 56/56`을 유지한다. 754B는 이미 예정한 receipt 한 블록 안에 상태를 통합하는 근거다. 프로그램 크기가 달라지면 RAM 예산을 다시 계산해야 한다. 새 full-board FIT/STA/IO/CDC는 실행하지 않았다.

## 검증과 재현 경계

- 선택: `test01/map01`(A), `blocktest03/blockmap01`(B), `analysis02`. B MAP은 통과한 `blocktest02`에 결합했고03과 RTL hash가 같다.
- B RTL: 기록71 + 합성경계3 =74프레임, 출력83648B 및 base325452B 비교. 양방향 row shift, 2112/4352 경계, 마지막46B 블록의 부분 mask, raw256→0, byte stall64클록, record stall, abort/cold admission2건 통과. 모든 프로토콜 오류·serial wrap을 망라한 제품 검증은 아니다.
- Python: 독립 block decode와8개 오류 stream, receipt192726 byte 비교와155개 반례 통과. map receipt는 실제 전송 범위를 RAM bitmap과 비교했다. byte-RAM 정책 시험을 RTL fault test로 세지 않는다.
- `blocktest01`의 forward declaration compile 실패와 수정 후02, 강화03, 초기analysis01을 모두 보존했다. analysis02는 map receipt 검사와 강화 source 증거, 남은 validate181 비용의 명시를 추가했다. 분석01/02의 공통 시간표는 같다.
- 입력1279개와 실행/합성 원본 로그·fixture·generated RTL은 private probe에 보존한다. 공개 파일에는 ROM/fixture payload를 넣지 않는다.

재현 도구: `tools/probe_nes_source249.py`의 `--block --directed`로 실제 Questa 시험, `--block --map-test <통과한 시험>`으로 동일 RTL 단독 MAP, `tools/analyze_nes_joint249.py`로 공동 표를 생성한다. private247/240 기준 증거가 필요하다. Questa는 기존 FLOAT wrapper와 절대 경로 ASCII 작업 디렉터리를 사용한다. 공개 수치: [검증 집계](../analysis/joint249-verification.json), [일정](../analysis/joint249-frames.csv), [입력 wire](../analysis/joint249-wire.csv).

## 다음 선정 조건

B를 **시간 측면의 우선 조사 후보**로 남긴다. 다음은 작은 opcode/카운터 튜닝이나 자동 whole-board FIT 반복이 아니다. semantic query/projector + B encoder + 통합 range/validity validator + 실제 FIFO/read-port 소유권을 같은 교체 경계로 잡아 기존 source 경로의 어떤 회로를 제거하는지 먼저 증명한다. 유지되는 SNES 명령 작성·layout/HDMA 검사를 실제 실행해1.195ms 공동 잔여를 소비하는 비용도 확정해야 한다.

이 결합 경계에서490LE/40LAB 부족과 새 logic, mapper 여유를 회수할 근거가 없으면 B도 제품 후보로 기각하고 더 큰 경계 변경을 재검토한다. 근거가 생긴 경우에만 최소 실행 경계→전체보드 FIT/STA/CDC/IO→full ARM/최종 display ownership→FIRSTLEVELSCROLL 순으로 진행한다. [현재 계획](nes-joint249-plan.json).
