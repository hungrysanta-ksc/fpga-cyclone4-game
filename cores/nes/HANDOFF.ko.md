# 현재 NES 인계

현재 브랜치는 `codex/nes-bandwidth-dma-budget-504`, [PR140](../../docs/progress/pr-140.md)은 draft다. PR139 merge `46c0cc962397b3e757c838164b70b75fe73090a6`의 master 반영을 확인한 뒤 시작했다. 현재 판단에는 [509 계약](../../docs/nes-service509-contract.ko.md), [검증](../../analysis/service509-verification.json), [실행 계획](../../docs/nes-budget504-plan.json)을 먼저 읽는다. 과거 문서의 NEXT를 현재 지시로 적용하지 않는다.

## 선택된 실기 기준

**MMC502 /489 SNES 소비 프로그램**을 유지한다. [503 실기 분석](../../docs/nes-hardware503-results.ko.md):60.07초636최종 표시,10.59fps,실행·메뉴 복귀 정상. 수신22.14ms/계획·타일31.32ms/SEAL·최종ACK40.27ms이며 중첩 counter를 더하지 않는다.493과 동선이 같지 않아 관측 차이를 인과율로 쓰지 않는다. 전체 capture 손실률·레벨별 FPS·60Hz·MMC4/5는 미완료다.

보호할 산출물은 `probes/nes-capture502/ARM01`, `trial01/MMC502-CAPTURE.zip`, `probes/nes-output489/client04`와502보드다. GBC164/saveSRAM과 과거 원복 자료는 보존한다. 사용자에게 새 RESTORE 폴더를 전달하지 않지만 런타임 STOP/base/메뉴 복귀는 필수다. SD/보드를 PC에 연결하는 절차를 요청하지 않는다. 사용자가ZIP을 설치하고 로그를 돌려주는 방식이다.

## 개발 후보509와 제한 실기 전달

508의 bulk 우선·credit·일반 선행 공급을 유지하고 E8 공통 검사를합쳤다.34+40 linked ARM검사와12개최종RGB/DMA/ROM배정비교를통과했다.FW212956B/Flash36B/BSS18576B(502대비+4),508대비관측stack24B회복이다.507 FPGA/SNES는불변으로Lite15164LE/51M9K/관련setup+.078·hold+.139ns를재사용한다.

실제20frame 부팅 CPU·PPU·MMC3·ROM경쟁에서2386선행read/STOPguard와선택화면동등성을검증했다.8window재생의506→509 연속10간격은981.010→931.092ms다.첫레벨폐루프/실기FPS증명은아니다.

`probes/nes-service509/trial01/MMC509-OVERLAP.zip`은ROM/save/RESTORE없이준비했다.ARM03의784실행함수는시험ARM01과같고고유이름만509다.실제FatFS·프로그래머전바이트/STM3CRC/ZIP검증을완료했다.[설치](../../docs/nes-mmc509-trial.ko.md)와[manifest](../../analysis/service509-package.json)를참고한다.새실기실행·메뉴·FPS는아직확인전이다.

## 다음 작업 순서

1. 사용자설치뒤509의3개로그와첫레벨/약60초메뉴복귀를확인한다.가능하면502와같은동선으로비교한다.
2. 수신·계획·SEAL/최종표시·capture오류를초기/연속구간으로나눠비교한다.모형값을실기성과로바꾸지않는다.
3. 실제본문/framing/DMA비용으로A2예산을갱신한다.E8/ROM위상/seed미세조정은새근거전까지동결한다.

[505](../../docs/nes-early505-contract.ko.md)의 고립된 prefix DMA는 지속 warm 이득이 없어 동결한다. 기존498·전체7533B 이력cache·status/FSM/seed 미세조정을 자동 재개하지 않는다. 이력은 [PR138](../../docs/progress/pr-138.md), [PR139](../../docs/progress/pr-139.md), [PR140](../../docs/progress/pr-140.md)과 해당 계약에 보존한다.

## 재현 위치와 실패 보존

공개 entry는 `tools/nes_raw506.py`와 `test_nes_raw506_*`, `prepare_nes_raw506_board.py`, `analyze_nes_raw506.py`다. 저장소 부모의 `probes/nes-raw506`에 candidate01/ARM02/arm-test02/guards01/clock01/analysis03을 보존한다. Temp의 `nes-raw506-rtl02`, `nes-raw506-board01`, `nes-raw506-joint11`(후보)/`joint13`(기준)이 선택 근거다. Temp 시험과 보드 원본의 보관본은 `probes/nes-raw506/archive01/evidence.zip`과 파일별 SHA inventory에 있다. 공개 검증에는 입력·firmware·보고서 SHA를 기록하고 상용 ROM/raw/바이너리/license는 넣지 않는다.

joint05/06은 atomic DMA overshoot를 ARM 대기로 더하고 capture를 EA 뒤로 늦춘 시간 모형이라 기능 근거로만 남긴다.11/13은 미래 ACK를 시각까지 보류하고 COMMIT에서 다음 capture를 재개한다. 초기 END 상태 오류·Windows 공유 잠금·emulator 초기 RPC watchdog(정확한 원인 미확정)·nominal SDC 누락·분석 문자 인코딩 실패도 남긴다. 이를 제품이나 새 Questa license 실패로 오인하지 않는다.

Questa는 기존 Starter FLOAT1좌석 wrapper로 순서대로 실행한다. Quartus는 Lite를 사용한다. README는 실기 상태나 중요한 작업 경계가 바뀔 때만 갱신하며 PR은 목표/작업내용/성과/후속작업 양식을 유지한다.

507 선택 근거는 `probes/nes-fault507`과 Temp의 `nes-fault507-test02`, `nes-fault507-board01`, `nes-fault507-trace01`이다. test01의 STOP offset 오류와 최초 wrapper sandbox 실패는 보존한다. 단일 Lite FIT 뒤 같은 DB에서 경로를 분석했으며 추가 seed를 시도하지 않았다.

507 공개 entry는 `tools/nes_fault507.py`, `test_nes_fault507.py`, `trace_nes_fault507_schedule.py`, `analyze_nes_fault507.py`다. 선택 집계는 `probes/nes-fault507/analysis02`, 보관본은 `archive01/evidence.zip`과 파일별 SHA inventory다.

508 entry는 `tools/nes_overlap508.py`, `test_nes_overlap508_arm.py`, `analyze_nes_overlap508.py`이며 공동 일정은 기존 `test_nes_raw506_joint.py`를 사용한다. 선택은 `probes/nes-overlap508/candidate03`(ARM02동일코드)/`ARM02`/`arm-test02`/`analysis01`/Temp `nes-overlap508-joint01`이다. ARM01의 Flash4B 초과를 보존한다. `archive01/evidence.zip`의15889개 파일을 전부 SHA로 검증했으며 license/상용ROM/raw/firmware는 Git에 넣지 않는다.

509 entry는 `tools/*service509*.py`다. 선택 ARM01/ARM03,arm-test01,parity02,analysis01,trial01과Temp rom03/joint01/calendar01·02/assembly01/programmer02를사용한다. private archive01은Temp원본을SHA로보존한다. ARM02 상대경로/rom01·02 harness/프로그램검사01 sandboxDLL 실패도보존하며새라이선스문제로오인하지않는다.
