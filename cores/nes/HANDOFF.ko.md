# 현재 NES 인계

현재 브랜치는 `codex/nes-output-budget-668` / [PR155](../../docs/progress/pr-155.md)다. PR154는 master `3f8292795b8a5e53d6cf250fcc568223e748a3d6`에 병합됐다. 사용자 지정 개발·실기 기준은 MMC666이며 [667 실기 분석](../../docs/nes-hardware667-results.ko.md)과 [설치 안내](../../docs/nes-mmc666-trial.ko.md)를 따른다. MMC662는 이전 비교 기준으로 보존한다.

## 현재 작업

**668 두 후보 검증 완료·둘 다 기각, MMC666 유지.** [668 비용·결과·다음 순서](../../docs/nes-output668-results.ko.md) · [검증 JSON](../../analysis/output668-verification.json). 같은 map/OBJ의 실제 ARM·65816 재생에서 반복 탐색은 약 0.75→0.14–0.18ms로 줄었지만, 위상 1의 선행 DMA가 감소해 마지막 ACK가 0.215ms 늦어졌다. map 소비 완료를 기다리는 결합 후보는 911의 업로드 VBlank를 하나 놓쳐 마지막 ACK가 16.849/16.640ms 늦어졌다. 안전 검사는 통과했으나 시간 조건은 실패했다.

다음은 954·957의 수락 범위·명령 병합·빈 큐 DMA 기회를 함께 검토한다. 911 SEAL 수락189/검사 완료214번 선의 기존 여유, 951 공개선·952 3회 이하·957 추가 대기0회·STOP·독립 검사·메뉴 복귀와 두 위상의 밀집 평균·마지막 ACK 동시 개선을 요구한다. 단독 탐색/일괄 drain/위상별 고정 지연 반복은 보류한다.

선택 산출물은 `probes/nes-trial666/arm01/src` ARM, `probes/nes-entry665/client02` 65816, ASCII Temp `nes-entry665-board01`이다. MMC666 패키지 SHA256 `67dfd6e294542c188463b889cd27f98587ae6db4fc582e52b43075f9304d4b56`, [패키지 근거](../../analysis/trial666-package.json). Flash 212,496B·여유496B, data/BSS10,040/19,544B, 전체15,324LE·962LAB·56M9K. 새 ZIP은 만들지 않았다. ROM/save/RESTORE 제외·사용자 SD 설치 방식은 유지한다.

## 최신 실기와 비교 기준

MMC666은 60.32초에 1,221회(20.24fps), 5–40초19.63fps·40–55초19.33fps·5–55초19.54fps다. 출력·최종 ACK는26.84ms이며 map/OBJ 작업량이 달라 MMC662 대비 구현 가속을 단정하지 않는다. 실행·STOP·캡처 회복·메뉴 복귀를 확인했다. [실기 비교](../../docs/nes-hardware667-results.ko.md)

**MMC509 /507 FPGA /489 SNES**:60.08초770회 **12.82fps**, 실행·입력 흔적·STOP/base 복구와 사용자 메뉴 복귀 정상. 체감 개선은 작았다. 이전 MMC502는60.07초636회10.59fps이며 복구 기준으로 보존한다. 같은 동선·첫 레벨 전용 비교는 아니다. 원본 로그는 `probes/nes-hardware510/run01`, 선택 증거는 `termination01`/`analysis02.json`이다.

[MMC509 패키지](../../analysis/service509-package.json)와 `probes/nes-service509/trial01/MMC509-OVERLAP.zip`, ARM03,507 board01,489 client04를 고정한다. 게임 ROM/save/RESTORE는 전달하지 않는다. 사용자가 SD에 설치해3개 로그를 반환하는 절차이며 보드·SD를 PC에 연결하도록 요청하지 않는다.502 ZIP/기존 백업·GBC/save는 변경하지 않는다.

수신19.88 / 계획·공급14.30 / 출력·최종ACK43.17ms다. 계획17.02ms 감소에는 bulk 대기를 SEAL로 옮긴 효과가 포함된다. 마지막771번째 ordinary section5 요청은4credit 대기 중60초 제한에 걸려 제외했다. 실제 ARM03로1/2/2·pending4를 재현했고 진짜IO/CRC를 구분했다. 전체 무손실·모든 mapper·60fps는 아니다.

## 다음 작업 순서

1. R1은580 전체비용표와581 제한 조사로 결측을 명시하고 마감했다. 53개 입력·106D1경계·3378E1 publish/load/ACK와 map/palette/OAM 복원을 대조했다. 물리 ROM/capture/입력 지연·대표 장면·clean-clone 전체실행은 여전히 미완료다. 같은 분석을 반복하지 않는다.
2. [594 ARM 결과](../../docs/nes-report594-results.ko.md). 594 전체 ARM이 212,064 B로 링크돼 928 B가 남았다. 같은 ELF에서 cold 905는 17.984 ms(CPI 2), 53입력·27수신 조건·3표시 ACK 조건을 통과했다. 종료 보고 때만 서식을 복원하며 기존 로그와 바이트가 같다. 595에서 이 ARM과 FPGA를 연결했다. 596의 한 페이지 예약 방식은 입력당 26페이지·고정 78거래·546 B를 줄인다. 결합 진단 MAP은 2,708 LE로 892 LE와 새 제어 비용이 남았다. 597은 595 핀 경로에서 묶음 전송으로 905·906 각각 97거래·698 B를 줄였다. 결합 진단은 2,625 LE로 809 LE 초과, 외부 생산 비용을 0으로 둬도 1,909 LE다. 598의 collector 요약은 53입력·1,537그룹에서 일치하고 905/906의 D0를 11/10회 줄였다. 결합 MAP은 4,910 LE로 새 경계 상한보다 907 LE 크다. [599 출력 실측](../../docs/nes-output599-results.ko.md)에서 상속 CRC만으로 두 위상의 기준 최종 ACK보다 12.077–15.995 ms 늦었다. [600 실제 SPI·ROM 비용](../../docs/nes-wire600-results.ko.md)에서 562/558 B를 줄였지만 필수 조회를 포함한 wire 하한은 16.808/17.030 ms였다. 601에서 현재 PPU 캡처를 재사용해 952·954의 208/272개 요청을 모두 충족했다. 두 위상의 낙관 표시 간격은 31.443–31.900 ms다. [601 검증](../../docs/nes-snoop601-results.ko.md) 602의 4 B D2는 두 장면에서 60 B를 절감했다. 한 슬롯의 D1 중첩은 0이고 두 슬롯을 가정해도 표시 전 5.144–5.587 ms가 더 필요하다. [602 검증](../../docs/nes-overlap602-results.ko.md) 603의 compact palette는 290 B를 줄이지만 65816 복원·검사가 12.014 ms로 기존 palette ACK보다 8.585–8.708 ms 늦다. [603 검증](../../docs/nes-palette603-results.ko.md) 604에서 실제 행 압축·ARM 복원으로 278 B와 첫 BG 1.668 ms를 줄였으나 두 위상의 첫 ROM 허용 시각은 같았다. [604 측정](../../docs/nes-rows604-results.ko.md) 605에서 직전 표시 뱅크 이력으로 첫 BG 48 B를 골랐다. 전체 ROM 읽기 단축은 두 위상에서 0.121–0.145 ms였고 954의 60 Hz 마감 전 ROM 공급 상한은 8/272 B였다. [605 근거](../../docs/nes-prefix605-results.ko.md) 606에서 954의 현재 캡처가 272/272 B를 보존했다. 이전 ACK 대기에 입력 6블록을 옮겨도 첫 E9는 EA 뒤 16.852 ms다. 입력을 전부 숨긴 조합에서도 필수 드라이버 비용까지 16.162 ms가 걸렸다. [606 검증](../../docs/nes-overlap606-results.ko.md) 607의 MMC577 ARM 후보는 최근 두 슬롯을 재사용해 Flash 16 B를 남겼다. 두 위상 53화면에서 밀집 25→24 VBlank, 마지막 ACK −17.799/−50.809 ms였다. 952·954의 SPI 거래는 증가했고 957 최종 대기는 0→1회여서 실기 기준은 MMC577이다. [607 검증](../../docs/nes-planner607-results.ko.md) 608에서 팔레트 DMA만 바꾸면 957의 최종 대기가 두 위상 모두 1→0회이고 밀집 구간 24 VBlank를 유지한다. ARM 조회까지 결합하면 24 / 25 VBlank로 위상 2가 회귀한다. 실기 기준은 MMC577을 유지한다. [608 검증](../../docs/nes-quiet608-results.ko.md) 609의 두 캡처 뱅크가 OBJ 96 B를 모두 공급해 마지막 OBJ 응답은 약 26 / 15 ms 앞당겨졌다. 선행 DMA가 줄어 952 표시는 두 위상 모두 한 VBlank 늦어졌고 957 최종 대기는 0회를 유지했다. 공유 포트 RTL은 229 LE·38,400 bit로 단독 추가 예산은 81 LE 부족하다. MMC577을 유지한다. [609 검증](../../docs/nes-obj609-results.ko.md) 610에서 OBJ bulk 뒤에만 map을 겹치면 두 위상 모두 952는 6→5 VBlank, 밀집 합계는 24→23, 마지막 ACK는 −49.917 / −16.670 ms이며 957 최종 대기는 0회를 유지했다. 실제 source는 1,244→1,073 LE, 산술 여유 319 LE·M9K 0개다. ARM Flash는 212,992 B로 여유가 없다. 기존 BG 적중 48회와 보드 lifecycle은 아직 함께 검증하지 않았으므로 MMC577을 유지한다. [610 검증](../../docs/nes-pace610-results.ko.md) MMC613을 실기 기준으로 삼는다. 같은 map·OBJ 작업량에서 출력 발행·65816 수락/DMA·마지막 VBlank와 ACK를 대조해 31.63 ms 중 줄일 시간을 구분한다. STOP·독립 검사·최종 ACK·메뉴 복귀를 유지한다.
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
