# 현재 NES 인계

현재 브랜치는 codex/nes-whole-budget-580 / PR151이다. PR150 병합 `588fa177ed1a82056a5cc86813506c3f2024cc70` 확인 뒤 분기했다. [591 실제 ARM·예산](../../docs/nes-roles591-results.ko.md), [590 역할·요청 비용](../../docs/nes-roles590-results.ko.md), [589 실제 source 결과](../../docs/nes-source589-results.ko.md), [588 source 예산](../../docs/nes-source588-results.ko.md), [587 검사 소유권](../../docs/nes-ownership587-results.ko.md), [586 실제 ARM 결합](../../docs/nes-combined586-results.ko.md), [585 교체·RAM 예산](../../docs/nes-ownership585-results.ko.md), [584 transport 비용](../../docs/nes-transport584-results.ko.md), [583 행·진행 응답](../../docs/nes-row583-results.ko.md), [582 ABI 예산](../../docs/nes-abi582-results.ko.md), [581 본문·순서 조사](../../docs/nes-body581-results.ko.md), [580 전체 비용표](../../docs/nes-whole580-results.ko.md), [선택 manifest](../../analysis/whole580-manifest.json)를 먼저 읽는다.

## 현재 작업

실측 기준은 **MMC577**(13.95fps/5–55초13.86fps)이다. 실행·메뉴 정상, 선택576 FPGA·ARM577을 유지한다. 현재 실행 순서는 [579 회고](../../docs/nes-retrospective579.ko.md)와 [보완 계획](../../docs/nes-retrospective579-plan.json)이며 499/504의 오래된 NEXT를 대체한다. 이번 제품 구현은 시작하지 않았다.

## 최신 실기와 비교 기준

MMC577 실기에서 실행과 메뉴 복귀가 정상이고 개선 체감이 보고됐다. 한 실행은 60.08초에 838화면(13.95fps), 5–55초 13.86fps다. MMC558 대비 5–40초는 13.66→13.77fps, 40–55초는 13.87→14.07fps로 소폭 증가했다. 동일 장면의 인과적 가속률은 아니다. [실기 비교](../../docs/nes-hardware578-results.ko.md)

**MMC509 /507 FPGA /489 SNES**:60.08초770회 **12.82fps**, 실행·입력 흔적·STOP/base 복구와 사용자 메뉴 복귀 정상. 체감 개선은 작았다. 이전 MMC502는60.07초636회10.59fps이며 복구 기준으로 보존한다. 같은 동선·첫 레벨 전용 비교는 아니다. 원본 로그는 `probes/nes-hardware510/run01`, 선택 증거는 `termination01`/`analysis02.json`이다.

[MMC509 패키지](../../analysis/service509-package.json)와 `probes/nes-service509/trial01/MMC509-OVERLAP.zip`, ARM03,507 board01,489 client04를 고정한다. 게임 ROM/save/RESTORE는 전달하지 않는다. 사용자가 SD에 설치해3개 로그를 반환하는 절차이며 보드·SD를 PC에 연결하도록 요청하지 않는다.502 ZIP/기존 백업·GBC/save는 변경하지 않는다.

수신19.88 / 계획·공급14.30 / 출력·최종ACK43.17ms다. 계획17.02ms 감소에는 bulk 대기를 SEAL로 옮긴 효과가 포함된다. 마지막771번째 ordinary section5 요청은4credit 대기 중60초 제한에 걸려 제외했다. 실제 ARM03로1/2/2·pending4를 재현했고 진짜IO/CRC를 구분했다. 전체 무손실·모든 mapper·60fps는 아니다.

## 다음 작업 순서

1. R1은580 전체비용표와581 제한 조사로 결측을 명시하고 마감했다. 53개 입력·106D1경계·3378E1 publish/load/ACK와 map/palette/OAM 복원을 대조했다. 물리 ROM/capture/입력 지연·대표 장면·clean-clone 전체실행은 여전히 미완료다. 같은 분석을 반복하지 않는다.
2. [591 실제 ARM·예산](../../docs/nes-roles591-results.ko.md): 8B 요약·묶음요청을 실제577 ARM packet/BEGIN/mapcodec 교체로 구현해 53입력/18조건을 통과했다. 단일 sealed source는 Python 모델이다. MAP_ACCEPT 왕복과 단계 D0가 필요해 dense 입력I/O는590의6.775→7.121ms로 정정했다. 전체FW214760B는 한도1768B 초과이며 cold도 계산 포함 회귀했다. 첫 ARM gate 실패로 새FPGA구현/Quartus MAP/두위상 첫BG·마지막ACK 시험은 실행하지 않았다. 다음은 old nonmap/record+new phase/identity 완료 제어의 실제 삭제와 전체Flash 예산 확정이다. 새adapter·CRC/helper/opcode/seed 미세조정이나589범용FPGA로 돌아가지 않는다. MMC577/독립검사/STOP/최종ACK·EA/메뉴/README를 유지한다.
3. R3: 후보 하나만 구현·동일입력/두위상·대표장면 검증. 같은 가설 두 변형에 종단 이득이 없으면 새 증거 전까지 보류한다. 안정성 보완은 성능과 별도 판정한다.
4. R4: 의미 있는 후보만 고유파일명/RESTORE없이 실기. 5–40/40–55초, STOP·독립검사·최종ACK·VBlank·메뉴 유지. 외부IO/capture/지속60fps는 별도 미완료다.

512·514의 제외 근거는 [전송 형식 비교](../../docs/nes-transfer512-results.ko.md)와 [해당 PR 기록](../../docs/progress/pr-141.md)에 남아 있다.

## 재현 위치와 실패 보존

공개 entry는 `tools/nes_raw506.py`와 `test_nes_raw506_*`, `prepare_nes_raw506_board.py`, `analyze_nes_raw506.py`다. 저장소 부모의 `probes/nes-raw506`에 candidate01/ARM02/arm-test02/guards01/clock01/analysis03을 보존한다. Temp의 `nes-raw506-rtl02`, `nes-raw506-board01`, `nes-raw506-joint11`(후보)/`joint13`(기준)이 선택 근거다. Temp 시험과 보드 원본의 보관본은 `probes/nes-raw506/archive01/evidence.zip`과 파일별 SHA inventory에 있다. 공개 검증에는 입력·firmware·보고서 SHA를 기록하고 상용 ROM/raw/바이너리/license는 넣지 않는다.

joint05/06은 atomic DMA overshoot를 ARM 대기로 더하고 capture를 EA 뒤로 늦춘 시간 모형이라 기능 근거로만 남긴다.11/13은 미래 ACK를 시각까지 보류하고 COMMIT에서 다음 capture를 재개한다. 초기 END 상태 오류·Windows 공유 잠금·emulator 초기 RPC watchdog(정확한 원인 미확정)·nominal SDC 누락·분석 문자 인코딩 실패도 남긴다. 이를 제품이나 새 Questa license 실패로 오인하지 않는다.

Questa는 기존 Starter FLOAT1좌석 wrapper로 순서대로 실행한다. Quartus는 Lite를 사용한다. README는 실기 상태나 중요한 작업 경계가 바뀔 때만 갱신하며 PR은 목표/작업내용/성과/후속작업 양식을 유지한다.

507 선택 근거는 `probes/nes-fault507`과 Temp의 `nes-fault507-test02`, `nes-fault507-board01`, `nes-fault507-trace01`이다. test01의 STOP offset 오류와 최초 wrapper sandbox 실패는 보존한다. 단일 Lite FIT 뒤 같은 DB에서 경로를 분석했으며 추가 seed를 시도하지 않았다.

507 공개 entry는 `tools/nes_fault507.py`, `test_nes_fault507.py`, `trace_nes_fault507_schedule.py`, `analyze_nes_fault507.py`다. 선택 집계는 `probes/nes-fault507/analysis02`, 보관본은 `archive01/evidence.zip`과 파일별 SHA inventory다.

508 entry는 `tools/nes_overlap508.py`, `test_nes_overlap508_arm.py`, `analyze_nes_overlap508.py`이며 공동 일정은 기존 `test_nes_raw506_joint.py`를 사용한다. 선택은 `probes/nes-overlap508/candidate03`(ARM02동일코드)/`ARM02`/`arm-test02`/`analysis01`/Temp `nes-overlap508-joint01`이다. ARM01의 Flash4B 초과를 보존한다. `archive01/evidence.zip`의15889개 파일을 전부 SHA로 검증했으며 license/상용ROM/raw/firmware는 Git에 넣지 않는다.

509 entry는 `tools/*service509*.py`다. 선택 ARM01/ARM03,arm-test01,parity02,analysis01,trial01과Temp rom03/joint01/calendar01·02/assembly01/programmer02를사용한다. private archive01은Temp원본을SHA로보존한다. ARM02 상대경로/rom01·02 harness/프로그램검사01 sandboxDLL 실패도보존하며새라이선스문제로오인하지않는다.
