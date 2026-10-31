# 현재 NES 인계

현재 브랜치는 `codex/nes-bandwidth-dma-budget-504`, [PR140](../../docs/progress/pr-140.md)은 draft다. PR139 merge `46c0cc962397b3e757c838164b70b75fe73090a6`의 master 반영을 확인한 뒤 시작했다. 현재 판단에는 [507 계약](../../docs/nes-fault507-contract.ko.md), [검증](../../analysis/fault507-verification.json), [실행 계획](../../docs/nes-budget504-plan.json)을 먼저 읽는다. 과거 문서의 NEXT를 현재 지시로 적용하지 않는다.

## 선택된 실기 기준

**MMC502 /489 SNES 소비 프로그램**을 유지한다. [503 실기 분석](../../docs/nes-hardware503-results.ko.md):60.07초636최종 표시,10.59fps,실행·메뉴 복귀 정상. 수신22.14ms/계획·타일31.32ms/SEAL·최종ACK40.27ms이며 중첩 counter를 더하지 않는다.493과 동선이 같지 않아 관측 차이를 인과율로 쓰지 않는다. 전체 capture 손실률·레벨별 FPS·60Hz·MMC4/5는 미완료다.

보호할 산출물은 `probes/nes-capture502/ARM01`, `trial01/MMC502-CAPTURE.zip`, `probes/nes-output489/client04`와502보드다. GBC164/saveSRAM과 과거 원복 자료는 보존한다. 사용자에게 새 RESTORE 폴더를 전달하지 않지만 런타임 STOP/base/메뉴 복귀는 필수다. SD/보드를 PC에 연결하는 절차를 요청하지 않는다. 사용자가ZIP을 설치하고 로그를 돌려주는 방식이다.

## 현재507 후보와 제한

506의 raw 압축/ARM 단일 복원과 변경하지 않은489 소비기를 유지한다. 조건부 연속 일정의 2.63% 이득은 [506 근거](../../docs/nes-raw506-contract.ko.md)에 보존한다. 507은 loader SPI 오류 코드의 우선순위를 같은 클록의 비트 식으로 바꾸었다. STOP/fault/status snapshot 지연은 없다. 실제 RTL 8192조합/268serial/64fault 시점과 mutant를 통과했다.

전체 Lite는 15164LE/14172comb/8394FF/264816bits/51M9K다. 관련 setup +0.078ns/hold +0.139ns로 회복했지만 전체 reset/CDC/IO 승인은 아니다. ARM212852B/Flash140B와 SNES는506과 동일하다. loader 변경 자체의 추가 프레임 시간 이득은 없다. 실제M4/489CPU의 같은12개 일정에 함수/ROM모형 관측만 추가해 instruction/IRQ/wire/ACK/RGB 동등성을 확인했다. 첫 두 bank 뒤 END→finish 평균8.165ms, 이후 첫 ordinary까지0.289ms로 완료 대기와 공급의 겹침이 우선이다. ROM 밀도/CPI는 모형이며 실제 arbiter trace는 미완료다.

## 다음 작업 순서

1. END 수락 뒤 bulk/credit을 우선하면서 일반 packet을 한 번에 하나씩 공급할 진행 제어를 구현한다. `complete485`는 현재 마지막 opcode가7이라고 가정하므로 일반 출력과 섞기 전에 완료 watermark로 함께 교체한다.
2. runtime 구조 추가 최대8B, 새 global0B, Flash 순증 최대140B, FPGA 제어/M9K 추가0을 목표로 기존 blocking 제어를 대체한다. 아직 측정 비용이 아니다.
3. 독립 packet 검사·wrap·future/stale 완료·STOP·old identity·최종ACK→EA·VBlank를 유지하고 실제 arbiter trace와 연속 일정에 연결한다. 최종 표시 이득과 전체 Lite 결과를 함께 확인한 뒤에만 전달본을 선정한다.

[505](../../docs/nes-early505-contract.ko.md)의 고립된 prefix DMA는 지속 warm 이득이 없어 동결한다. 기존498·전체7533B 이력cache·status/FSM/seed 미세조정을 자동 재개하지 않는다. 이력은 [PR138](../../docs/progress/pr-138.md), [PR139](../../docs/progress/pr-139.md), [PR140](../../docs/progress/pr-140.md)과 해당 계약에 보존한다.

## 재현 위치와 실패 보존

공개 entry는 `tools/nes_raw506.py`와 `test_nes_raw506_*`, `prepare_nes_raw506_board.py`, `analyze_nes_raw506.py`다. 저장소 부모의 `probes/nes-raw506`에 candidate01/ARM02/arm-test02/guards01/clock01/analysis03을 보존한다. Temp의 `nes-raw506-rtl02`, `nes-raw506-board01`, `nes-raw506-joint11`(후보)/`joint13`(기준)이 선택 근거다. Temp 시험과 보드 원본의 보관본은 `probes/nes-raw506/archive01/evidence.zip`과 파일별 SHA inventory에 있다. 공개 검증에는 입력·firmware·보고서 SHA를 기록하고 상용 ROM/raw/바이너리/license는 넣지 않는다.

joint05/06은 atomic DMA overshoot를 ARM 대기로 더하고 capture를 EA 뒤로 늦춘 시간 모형이라 기능 근거로만 남긴다.11/13은 미래 ACK를 시각까지 보류하고 COMMIT에서 다음 capture를 재개한다. 초기 END 상태 오류·Windows 공유 잠금·emulator 초기 RPC watchdog(정확한 원인 미확정)·nominal SDC 누락·분석 문자 인코딩 실패도 남긴다. 이를 제품이나 새 Questa license 실패로 오인하지 않는다.

Questa는 기존 Starter FLOAT1좌석 wrapper로 순서대로 실행한다. Quartus는 Lite를 사용한다. README는 실기 상태나 중요한 작업 경계가 바뀔 때만 갱신하며 PR은 목표/작업내용/성과/후속작업 양식을 유지한다.

507 선택 근거는 `probes/nes-fault507`과 Temp의 `nes-fault507-test02`, `nes-fault507-board01`, `nes-fault507-trace01`이다. test01의 STOP offset 오류와 최초 wrapper sandbox 실패는 보존한다. 단일 Lite FIT 뒤 같은 DB에서 경로를 분석했으며 추가 seed를 시도하지 않았다.

507 공개 entry는 `tools/nes_fault507.py`, `test_nes_fault507.py`, `trace_nes_fault507_schedule.py`, `analyze_nes_fault507.py`다. 선택 집계는 `probes/nes-fault507/analysis02`, 보관본은 `archive01/evidence.zip`과 파일별 SHA inventory다.
