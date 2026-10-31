# 현재 NES 인계

현재 브랜치는 `codex/nes-bandwidth-dma-budget-504`, [PR140](../../docs/progress/pr-140.md)은 draft다. PR139 merge `46c0cc962397b3e757c838164b70b75fe73090a6`의 master 반영을 확인한 뒤 시작했다. 현재 판단에는 [508 계약](../../docs/nes-overlap508-contract.ko.md), [검증](../../analysis/overlap508-verification.json), [실행 계획](../../docs/nes-budget504-plan.json)을 먼저 읽는다. 과거 문서의 NEXT를 현재 지시로 적용하지 않는다.

## 선택된 실기 기준

**MMC502 /489 SNES 소비 프로그램**을 유지한다. [503 실기 분석](../../docs/nes-hardware503-results.ko.md):60.07초636최종 표시,10.59fps,실행·메뉴 복귀 정상. 수신22.14ms/계획·타일31.32ms/SEAL·최종ACK40.27ms이며 중첩 counter를 더하지 않는다.493과 동선이 같지 않아 관측 차이를 인과율로 쓰지 않는다. 전체 capture 손실률·레벨별 FPS·60Hz·MMC4/5는 미완료다.

보호할 산출물은 `probes/nes-capture502/ARM01`, `trial01/MMC502-CAPTURE.zip`, `probes/nes-output489/client04`와502보드다. GBC164/saveSRAM과 과거 원복 자료는 보존한다. 사용자에게 새 RESTORE 폴더를 전달하지 않지만 런타임 STOP/base/메뉴 복귀는 필수다. SD/보드를 PC에 연결하는 절차를 요청하지 않는다. 사용자가ZIP을 설치하고 로그를 돌려주는 방식이다.

## 현재508 후보와 제한

506 입력 압축을 유지하고 END 발행/소비 대기를 분리했다. packet sequence/BUSY를 잡기 전에 ready bulk를 소비까지 우선 처리하며, head가 없는 ROM 대기에 일반 packet 하나를 공급한다. bulk_until과 검증된 retired counter로 last-opcode 의존성을 교체하고 기존 독립 ACK 검사·최종 full identity·STOP·EA·VBlank를 보존한다.

실제 M434개 검사를 통과했다. 같은 시작/ROM위상의 실제M4·489CPU12개 최종 RGB·36144DMA·3280ROM read가 같다. 506/507 대비 첫 표시 뒤11간격1230.609→1147.400ms(−6.76%),두 초기 표시 뒤10간격981.019→931.110ms(−5.09%),SPI145247→140055B다. ROM밀도/CPI는 모형으로 실제 arbiter trace·새 실기 FPS·capture 거부율·새 메뉴 시험은 미완료다.

FW212992B로 Flash 여유0B, BSS18576B(+4), runtime444B(+4), 관측 호출 stack+272B다. 새 전역 객체가 없더라도 실제 BSS는 늘었다. Flash0B 후보를 새 전달본으로 승격하지 않는다. FPGA/SNES는 변경하지 않았고507 source hash 전체를 대조했다. 전체 Lite15164LE/14172comb/8394FF/264816bits/51M9K,관련 setup+.078ns/hold+.139ns를 재사용한다. 새 Quartus 실행이나 전체reset/CDC/IO 승인을 뜻하지 않는다.

## 다음 작업 순서

1. 실제 ROM arbiter 요청/허용/반환 trace를 같은 일정에 연결해 모델의 허용 밀도와 실제 공급 지연을 구분한다.
2. 기존 진행·완료 제어의 중복을 삭제해 Flash 여유를 회복한다. BSS와 호출 stack도 함께 비교하고 독립 검사·bulk/credit 우선순위를 유지한다.
3. 초기/연속 구간과 STOP·최종 ACK·VBlank·유한 queue/bank를 재검증한 뒤 전달 후보를 선정한다. 고유 파일명·로그 marker를 사용하고 RESTORE는 생략한다.

[505](../../docs/nes-early505-contract.ko.md)의 고립된 prefix DMA는 지속 warm 이득이 없어 동결한다. 기존498·전체7533B 이력cache·status/FSM/seed 미세조정을 자동 재개하지 않는다. 이력은 [PR138](../../docs/progress/pr-138.md), [PR139](../../docs/progress/pr-139.md), [PR140](../../docs/progress/pr-140.md)과 해당 계약에 보존한다.

## 재현 위치와 실패 보존

공개 entry는 `tools/nes_raw506.py`와 `test_nes_raw506_*`, `prepare_nes_raw506_board.py`, `analyze_nes_raw506.py`다. 저장소 부모의 `probes/nes-raw506`에 candidate01/ARM02/arm-test02/guards01/clock01/analysis03을 보존한다. Temp의 `nes-raw506-rtl02`, `nes-raw506-board01`, `nes-raw506-joint11`(후보)/`joint13`(기준)이 선택 근거다. Temp 시험과 보드 원본의 보관본은 `probes/nes-raw506/archive01/evidence.zip`과 파일별 SHA inventory에 있다. 공개 검증에는 입력·firmware·보고서 SHA를 기록하고 상용 ROM/raw/바이너리/license는 넣지 않는다.

joint05/06은 atomic DMA overshoot를 ARM 대기로 더하고 capture를 EA 뒤로 늦춘 시간 모형이라 기능 근거로만 남긴다.11/13은 미래 ACK를 시각까지 보류하고 COMMIT에서 다음 capture를 재개한다. 초기 END 상태 오류·Windows 공유 잠금·emulator 초기 RPC watchdog(정확한 원인 미확정)·nominal SDC 누락·분석 문자 인코딩 실패도 남긴다. 이를 제품이나 새 Questa license 실패로 오인하지 않는다.

Questa는 기존 Starter FLOAT1좌석 wrapper로 순서대로 실행한다. Quartus는 Lite를 사용한다. README는 실기 상태나 중요한 작업 경계가 바뀔 때만 갱신하며 PR은 목표/작업내용/성과/후속작업 양식을 유지한다.

507 선택 근거는 `probes/nes-fault507`과 Temp의 `nes-fault507-test02`, `nes-fault507-board01`, `nes-fault507-trace01`이다. test01의 STOP offset 오류와 최초 wrapper sandbox 실패는 보존한다. 단일 Lite FIT 뒤 같은 DB에서 경로를 분석했으며 추가 seed를 시도하지 않았다.

507 공개 entry는 `tools/nes_fault507.py`, `test_nes_fault507.py`, `trace_nes_fault507_schedule.py`, `analyze_nes_fault507.py`다. 선택 집계는 `probes/nes-fault507/analysis02`, 보관본은 `archive01/evidence.zip`과 파일별 SHA inventory다.

508 entry는 `tools/nes_overlap508.py`, `test_nes_overlap508_arm.py`, `analyze_nes_overlap508.py`이며 공동 일정은 기존 `test_nes_raw506_joint.py`를 사용한다. 선택은 `probes/nes-overlap508/candidate03`(ARM02동일코드)/`ARM02`/`arm-test02`/`analysis01`/Temp `nes-overlap508-joint01`이다. ARM01의 Flash4B 초과를 보존한다. `archive01/evidence.zip`의15889개 파일을 전부 SHA로 검증했으며 license/상용ROM/raw/firmware는 Git에 넣지 않는다.
