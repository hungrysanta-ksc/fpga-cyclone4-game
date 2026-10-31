# 현재 NES 인계

현재 브랜치는 `codex/nes-bandwidth-dma-budget-504`, [PR140](../../docs/progress/pr-140.md)은 draft다. PR139 merge `46c0cc962397b3e757c838164b70b75fe73090a6`의 master 반영을 확인한 뒤 시작했다. 현재 판단에는 [506 계약](../../docs/nes-raw506-contract.ko.md), [검증](../../analysis/raw506-verification.json), [실행 계획](../../docs/nes-budget504-plan.json)을 먼저 읽는다. 과거 문서의 NEXT를 현재 지시로 적용하지 않는다.

## 선택된 실기 기준

**MMC502 /489 SNES 소비 프로그램**을 유지한다. [503 실기 분석](../../docs/nes-hardware503-results.ko.md):60.07초636최종 표시,10.59fps,실행·메뉴 복귀 정상. 수신22.14ms/계획·타일31.32ms/SEAL·최종ACK40.27ms이며 중첩 counter를 더하지 않는다.493과 동선이 같지 않아 관측 차이를 인과율로 쓰지 않는다. 전체 capture 손실률·레벨별 FPS·60Hz·MMC4/5는 미완료다.

보호할 산출물은 `probes/nes-capture502/ARM01`, `trial01/MMC502-CAPTURE.zip`, `probes/nes-output489/client04`와502보드다. GBC164/saveSRAM과 과거 원복 자료는 보존한다. 사용자에게 새 RESTORE 폴더를 전달하지 않지만 런타임 STOP/base/메뉴 복귀는 필수다. SD/보드를 PC에 연결하는 절차를 요청하지 않는다. 사용자가ZIP을 설치하고 로그를 돌려주는 방식이다.

## 현재506 후보와 제한

raw 동일색10..256개를 정확히 한 record로 보내고 ARM에서 한 번 검증·복원한다. 기존 per-pixel logical_record 호출을 삭제했다.2233 ABI로 잘못 섞인 구형 수신을 거부한다. 독립 coverage/CRC·STOP·COMMIT·최종 ACK·VBlank를 보존한다.

실제 linked ARM과 exporter의12개 입력 의미/plan/ordinary/SEAL이 같고 RTL14정상+2거부,ARM8span+4입력 거부를 통과했다. 실제 runtime/service/SysTick과489CPU에 실기 SPI 평균 비용·명시적인 CPI2/ROM 밀도 모형을 연결한12개 비교에서 wire153311→145247B,첫 프레임 뒤11표시 간격1263.881→1230.609ms(−33.272ms/2.63%)였다.12RGB/36144VRAM DMA가 같다. 새 실기 FPS나 전체NES/PSRAM RTL 시간 증명은 아니다.

FW+8B=212852B/Flash140B 남음/BSS동일. 전체 Lite15198LE/14168comb/8399FF/51M9K다. LE−89는packing 결과이고 조합 함수는33개 늘었다. **loader fault→error_code[2] setup−1.276ns로 실기 승격 보류**다. 변경 코드와 일치한 FIT/STA 결과이며 seed 재시도는 하지 않았다. 전체reset/CDC/IO도 별도 미완료다.

## 다음 작업 순서

1. 168MHz loader 오류 전달의 타이밍 경계를 추적한다. 기존 응답·STOP 의미를 보존할 논리/등록 경계와 검사·비용을 정한다.
2. 입력 압축은 유지하고 첫 bulk 이후 BG/OBJ 계획·ordinary 준비가 ROM 대기와 겹칠 수 있는 포트/수명을 정한다. 후보의 SEAL→ACK 평균24.451ms가 남아 있어 입력 절감만으로60Hz에 도달하지 않는다.
3. 실제 ROM arbiter trace를 연결해 같은 입력·시작 위상과 연속 일정을 비교한다. 첫 프레임과 두 bank 초기 채우기 뒤를 분리한다. 전체 Lite timing을 다시 만족할 때만 고유 번호의 전달본을 준비한다.

[505](../../docs/nes-early505-contract.ko.md)의 고립된 prefix DMA는 지속 warm 이득이 없어 동결한다. 기존498·전체7533B 이력cache·status/FSM/seed 미세조정을 자동 재개하지 않는다. 이력은 [PR138](../../docs/progress/pr-138.md), [PR139](../../docs/progress/pr-139.md), [PR140](../../docs/progress/pr-140.md)과 해당 계약에 보존한다.

## 재현 위치와 실패 보존

공개 entry는 `tools/nes_raw506.py`와 `test_nes_raw506_*`, `prepare_nes_raw506_board.py`, `analyze_nes_raw506.py`다. 저장소 부모의 `probes/nes-raw506`에 candidate01/ARM02/arm-test02/guards01/clock01/analysis03을 보존한다. Temp의 `nes-raw506-rtl02`, `nes-raw506-board01`, `nes-raw506-joint11`(후보)/`joint13`(기준)이 선택 근거다. Temp 시험과 보드 원본의 보관본은 `probes/nes-raw506/archive01/evidence.zip`과 파일별 SHA inventory에 있다. 공개 검증에는 입력·firmware·보고서 SHA를 기록하고 상용 ROM/raw/바이너리/license는 넣지 않는다.

joint05/06은 atomic DMA overshoot를 ARM 대기로 더하고 capture를 EA 뒤로 늦춘 시간 모형이라 기능 근거로만 남긴다.11/13은 미래 ACK를 시각까지 보류하고 COMMIT에서 다음 capture를 재개한다. 초기 END 상태 오류·Windows 공유 잠금·emulator 초기 RPC watchdog(정확한 원인 미확정)·nominal SDC 누락·분석 문자 인코딩 실패도 남긴다. 이를 제품이나 새 Questa license 실패로 오인하지 않는다.

Questa는 기존 Starter FLOAT1좌석 wrapper로 순서대로 실행한다. Quartus는 Lite를 사용한다. README는 실기 상태나 중요한 작업 경계가 바뀔 때만 갱신하며 PR은 목표/작업내용/성과/후속작업 양식을 유지한다.
