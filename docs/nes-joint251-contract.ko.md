# NES251 — 단계별 RAM 공유와 ARM HDMA 검사 이전

2026-10-19. PR129, `codex/nes-typed-schedule-248`. 기준은 병합된 PR128의 `64640645e3e37adb697d0293a509d0329e4eae4e`이며 production227은 그대로다. [현재 계획](nes-joint251-plan.json), [검증 집계](../analysis/joint251-verification.json), [조건별 일정](../analysis/joint251-schedules.csv).

**공유 RAM은 메모리 한 개를 줄였지만 논리 33LE를 늘렸다. HDMA 의미검사 이전은 시간 후보로 유지하되, 실행시간·전송 봉인·전체 회로 여유가 입증되기 전에는 P2 구현으로 선택하지 않는다.** 독립 source/receipt의 FSM과 데이터 연산은 아직 합쳐지지 않았다. 이번 결과를 제어 전체 통합의 실패나 성공으로 확대하지 않는다.

## 실행한 단계별 소유권

| 단계 | RAM 소유자와 범위 | 다음 단계 조건 |
|---|---|---|
| 공통 reset | 검증기가 0..753 초기화, source 시작 금지 | 754회 clear 완료 |
| 입력 source | source A/B 포트가 512..1023 scratch 사용 | 마지막 출력 수락 후 ARM 입력 확정 ACK |
| 출력 계획·검증 | 검증기가 332..753 임시 영역을 clear 후 사용, 0..331 양쪽 bank 유효성 갱신 | 범위·manifest 검사와 all-consumed 완료 |
| 표시 대기 | 검사 결과 보존, 다음 source 시작 금지 | **최종 display ACK** |
| STOP/fault | RAM 쓰기·게시·새 시작 차단 | 공통 reset 뒤 cold 시작 |

0..331의 영속 validity 332B는 source 동안 보존한다. 512..753의 겹치는 부분은 입력 확정 이후에만 덮어쓴다. source의 입력 확정 ACK와 최종 display ACK는 서로 다른 사건이다. 수명 전환은 동일 clock의 parsed fixture 입력에서 시험했다. 실제 SPI 패킷·collector/query·CDC와 표시 ACK 전달 회로는 연결하지 않았다. 이 순서가 실제 RUN의 프레임 간 겹침을 얼마나 제한하는지도 아직 측정하지 않았다.

`phase03`은 기존 71개 기록 프레임에서 source 출력·base, 검증 RAM 전부와 영속 validity 보존을 검사했다. 초기화 뒤 두 cold 재생을 추가해 출력 검사 중 STOP과 봉인 후 STOP에서 후속 쓰기/게시/시작이 막히는 것을 확인했다. 기존 source abort와 잘못된 cold serial도 유지했다. 총 base 321054B, persistent 24236B, receipt 54288B 비교, 4개 종료·cold 검사 PASS. 출력 단계의 조기 source 요청은 ready로 backpressure하며 오류로 판정하지 않는다. source 바이트의 긴 stall 및 두 RAM 포트 충돌 검사도 유지했다.

71프레임의 source prepare 사이클 및 receipt 사이클은 각각249/250과 **동일**하다. source 전체 사이클은 시험벤치의 주기적인 byte-ready 위상이 바뀌므로 byte-exact timing이라고 주장하지 않는다. per-frame 전환에는 별도로 2 FPGA clock을 일정에 배정했다. reset clear는 정상 프레임 비용이 아니다.

## 같은 국소 경계의 합성 결과

| 항목 | 250 독립 RAM | 251 공유 RAM | 차이 |
|---|---:|---:|---:|
| MAP LE | 1506 | 1539 | +33 |
| 조합 논리 | 1489 | 1522 | +33 |
| FF | 408 | 410 | +2 |
| 메모리 비트 | 49152 | 45056 | −4096 |
| 임시 RAM | 512×8 TDP + 1024×8 single | 1024×8 TDP 하나 | M9K RAM instance 하나 감소 |

공유 RAM과 base4096×8/512×8 모두 M9K로 추론되며 FF 대체는 아니다. 전체 보드의 이전56/56 시나리오는 산술상55/56으로 낮아지지만, 새 FIT를 실행하지 않았으므로 배치된 여유 한 개를 확보했다고 말하지 않는다. 기존240의 **490LE·40LAB 부족**과 mapper 여유도 해결하지 못했다.

251 계층은 source922comb/307FF, receipt356comb/101FF, parent244comb/2FF다. RAM을 외부로 옮기면서 기존 주소·쓰기 논리 일부가 parent로 이동했다. 따라서 parent244를 순수 추가 비용으로 보거나, child 감소분을 회수량으로 더하면 안 된다. 같은 top 합계의 +33만 유효한 비교다. 기존240 encoder1399comb와 비교해도 신규 source+receipt1522comb는 낮지 않으며, 이 비교에는 query/parser/CRC/certificate/CDC와 기존 transport의 실제 대체 비용이 빠져 있다. standalone MAP을 full-board FIT에서 빼지 않는다.

공유할 수 있는 제어는 단계 소유권과 RAM 접근 선택까지 실행했다. source의 admission/base serial/epoch/CRC와 receipt의 range/check/validity 상태는 별도다. 이후 제어 통합 후보는 실제 packet 수신·소비와 같은 주소/CRC 실행기를 재사용하고 기존 source/query/transport 제어를 **없애는** 구성이어야 한다. 아직 없는 parser/봉인 회로를 무료로 추가하거나, 레지스터 폭의 합을 LE 절약으로 환산하지 않는다. control-only ROM·작은 counter 튜닝의 반복 근거도 없다.

## ARM 계획 단계의 HDMA 의미검사

[C 함수](../tools/nes_hdma251.c)는 실제233의 `nes_native_video165` 후보 버퍼를 직접 읽는다. 새 프레임 복사나 영속 상태를 추가하지 않는다. 스크롤 count<128/총224행/종료 위치, raw 표의 세 count와 terminator 일치, mode/MOSAIC, A/B map 주소, enable/window, raw 행 수 및 길이를 확인한다. 기존 sink의 mask·patch count·크기 제한도 포함한다. raw 모드에서는 SNES가 검사하지 않던 후보의 `hdma_size`와 실제 스크롤 종료 위치의 일치도 추가로 요구한다. 송신 후의3418B section 길이 검사는 수신 측 framing에 남겨야 한다.

호스트에서 실제71프레임과 제어표의 단일 바이트 변조를 독립 wire-layout oracle과 비교했다. 무시되는 padding이나 허용되는 스크롤 좌표 변경을 오류라고 세지 않는다. 총 **97779사례: 승인92162, 거부5617**. 기록 프레임은 scroll4/patch4 runs뿐이므로, 저장 한계인224 scroll runs/16 patch runs와 종료 경계도 별도 검사했다. 이는 변조된 모든 표를 실제 SNES에서 실행한 시험이나 formal proof가 아니다.

실제 설정인 Cortex-M4/84MHz 대상으로 컴파일한 결과는 text300B, data/bss0B, 정적 함수 스택36B다. 함수는 기존 planner가 `valid`를 세운 뒤, sink가 metadata를 보내기 전에 호출하는 후보이며 실제 RUN에는 아직 연결하지 않았다. 233의 전체 RUN/IRQ 여유1616B를 이번에 재승인하거나 단순히36B를 뺀 값으로 보고하지 않는다. 호스트 실행시간은 MCU 시간으로 사용하지 않았다. MCU cycle·IRQ·Flash/cache·전체 계획 호출경로 비용은 미측정이다.

검사된 후보는 송신·표시까지 immutable해야 한다. FPGA의 범위/순서/CRC와 receipt 검사가 epoch, frame serial, target bank, section 길이 및 내용 식별값과 결합되어야 SNES의 `validate181`을 제거할 수 있다. 검사 전/후 mutation, 전송 오류, 누락, STOP과 재시작을 검증하지 않은 단순 `validated` 비트는 대체 증거가 아니다. 기존32B certificate 예산의 필드 배치·digest 누산·게시 조건은 아직 구현하지 않았으며, 추가32B 전송도 따로 비교했다.

## 시간과 메모리·논리의 공동 판단

250의 실제 SNES `validate181`은 warm69에서0.651945..0.653807ms였다. 이를 제거하고 phase 전환2clock, **추가 ARM 검사·봉인 작업의 배정치** 0/8000/32000cycles, 추가 전송0/32B를 반영한1656개 조건부 일정을 계산했다. 8000/32000은 실측 또는 상한이 아니다. 추가32B는2.625MHz에서0.097524ms이며 패킷별 고정 framing/상태 조회가 더 생기면 별도 비용이다.

아래는 ARM32000cycles(0.380952ms)와 추가32B를 모두 배정한 결과다.

| SNES map setup 배정 | 유지하는 작업 | 최악 시간 | 16.667ms 대비 잔여 | 초과 프레임 |
|---|---|---:|---:|---|
| 500 master clocks | 명령 tail·비트맵 없는 경로 | 16.181169ms | 0.485498ms | 없음 |
| 500 | 비트맵 loop만 제거 | 16.562037ms | 0.104630ms | 없음 |
| 1000 | 명령 tail·비트맵 없는 경로 | 17.042545ms | −0.375878ms | 954,970 |
| 1000 | 비트맵 loop만 제거 | 17.423412ms | −0.756746ms | 954,962,970 |

빠른500/명령tail 가정에서 ARM8000cycles+32B는15.895455ms/잔여0.771212ms다. ARM과 추가 전송을 모두0으로 놓은15.702693ms/잔여0.963974ms는 비용을 빠뜨린 낙관적 경계일 뿐이다. 32B 전송과2clock 전환을 낸 뒤 검사 이전 자체가 이득이 되려면 **추가 ARM 작업과 별도 봉인 비용의 합이 약0.554330ms 미만**이어야 한다. 이를 전부 ARM 시간으로 환산하면 약46564cycles/84MHz이며, 전체 프레임 승인 조건은 아니다.

기존 parser8cycles/byte, map setup, final2000master-clock 배정은 그대로다. 잔여는 기존 전체 ARM 계획/query, 새 수신 처리, SNES 일반 DMA·dispatch, SPI polling/gap, VBlank 경계가 함께 쓸 예산이다. 새로운 SNES 소비기를 실행하거나 물리60fps를 측정하지 않았다. 952/955의 VRAM burst, 최종 display ACK/lease-retire, CDC/IO/STA는 계속 열려 있다.

| 후보 | 확인한 이득 | 남은 문제 | 판단 |
|---|---|---|---|
| RAM 공유만 | 임시 M9K instance 하나 감소 | +33LE, prepare/receipt 시간 동일 | 메모리 수명 근거로 유지 |
| ARM 의미검사만 | 기존 약0.652ms SNES 검사 제거 가능, C/객체 검증 | ARM 실제 시간·전송 봉인 미결합 | 시간 후보 유지 |
| 둘을 결합 | 위 메모리 이득 + 조건부 시간 잔여 | 논리 부족, 전체 실행 미검증 | P2 미선정 |
| source/검증/packet 제어까지 대체 | 아직 측정한 절약0 | 실제로 제거할 제어·clock·CRC 수명부터 설계 필요 | 다음 공동 경계 비교 대상 |

## 재현과 보존

공개 도구는 [공유 RTL 생성](../tools/nes_phase251.py), [71프레임·STOP 시험/MAP](../tools/probe_nes_phase251.py), [HDMA 시험·ARM 객체](../tools/probe_nes_hdma251.py), [전체 비용 집계](../tools/analyze_nes_joint251.py)다. 원본 ROM/geometry/packet/빌드 로그는 private probe에만 보존한다. 실제 Questa는 기존 임시 FLOAT wrapper를 사용한다.

선택: `probes/nes-joint251/{phase03,map02,arm03,analysis02}`. phase02의 같은 RTL로 MAP을 수행했고 phase03은 STOP/조기 시작 검사를 강화했다. phase01 선언 순서 compile 실패, map01 경로 처리 실패(Quartus 실행 전), arm01 sandbox DLL 실행 실패, 중간 phase02/arm02/analysis01도 보존한다. 최종 실제 MAP은 한 번이다. production227, unplaced240, rejected241/246/2472, 5886B 진단 클라이언트, GBC164/saveSRAM을 변경하지 않았다.

다음 단계는 실제 source/query/SPI/receipt 경계에서 **기존 제어를 없애는** 최소 통합 후보의 논리·메모리·직렬화 비용과, ARM 검사 호출/내용 봉인/최종 소비 증명의 전체 비용을 함께 묶는 것이다. 그 근거 없이 새 full-board FIT·설치용 FW·실기 검증으로 넘어가지 않는다.
