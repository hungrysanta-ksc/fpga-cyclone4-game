# 613: 실제 608 프로그램을 포함한 MMC613 전달본

## 목표

612 보드·610 ARM·608 SNES의 검증 조합을 새 이름의 설치 파일로 묶는다. 실기 기준은 MMC577이며, 새 성능 수치는 사용자 로그를 받은 뒤 판정한다.

## 작업내용

패키징 시 612 보드의 sink-program.hex가 아직 선택 576의 기존 프로그램임을 확인했다. 611/612 시간 비교는 별도의 실제 608 CPU 프로그램을 사용했으므로, 이름만 바꾼 비트스트림을 전달하지 않았다. `prepare_nes_trial613.py board`가 612 전체 입력 해시를 확인하고 **sink-program.hex 하나만 608 프로그램으로 교체**했다. 본문·벡터 5,120 B를 실제 nes_sink_bus165 ROM 버스에서 모두 읽어 원래 sink165.sfc와 대조하고 gap·STOP status·클록 정지 reset도 확인했다.

ARM은 610의 세 파일에 있는 동일 길이 577 표기를 613으로 바꿔 전체 링크했다. FPGA·ROM 경로, 메뉴 marker, 세 로그 이름이 새 번호로 일치한다. CRC·기능 코드·발행 일정은 바꾸지 않았다.

## 성과

- 전체 ARM 링크 212,992 B, Flash 여유 0, BSS 18,592 B. 이전 ELF의 792개 함수 주소·크기·바이트와 일치하며, firmware 내용은 표기와 헤더 CRC 변경만 있다.
- 실제 ARM의 5–40초·40–55초 집계, marker·메뉴 prepare/release, OBJ 뒤 map·STOP·잘못된 ACK, prelude CRC/모호한 응답·최종 ACK 없는 retire 차단을 통과했다. base 복구는 normal/program/done/busy/token 5조건을 새 경로명으로 실행했다. 이는 장치가 아닌 peripheral 응답 모델을 사용한 실행이다.
- 최종 608 ROM을 포함한 보드의 **새 전체 FIT·STA**를 실행했다. LE 15,332/15,408, 조합 논리 14,359, FF 8,474, M9K 56/56이다. 전체 setup/hold/recovery/removal 최소값은 +0.487/+0.163/+1.652/+0.490 ns이고, 보고된 모든 경로 행은 612와 같다. ROM_OE +0.592 ns를 유지한다.
- ROM 버스에서 5,120 B 일치, actual programmer/FatFS의 BI3→RBF 전송과 encode/decode 일치, 최종 ZIP 파일별 해시·압축 무결성을 확인했다. 첫 programmer 실행의 sandbox Windows DLL 재배치 오류는 보존했고, 정상 실행 환경의 두 번째 검사에서 통과했다. 실제 보드 재구성은 사용자가 수행한다.
- 610 ARM 명령과 608 프로그램, 612 회로 timing이 유지되므로 611 두 위상의 시간 근거를 그대로 연결한다. 새 전체 ARM 일정을 다시 실행하거나 실기 FPS가 개선됐다고 주장하지 않는다. BG 48회·OBJ 1,200회·957 최종 대기 0회는 검증된 구성의 기대값이다.

산출물은 저장소 부모 `probes/nes-trial613/trial01/MMC613-TRIAL.zip`이다. 내부 01-MMC613-SD-ROOT에는 firmware.stm, fpga_mmc613.bi3, NES MMC3 613.nh1, 기존 메뉴 복귀용 fpga_base.bi3·m3nu.bin을 넣었다. ROM·세이브·RESTORE는 제외했다. [설치 안내](nes-mmc613-trial.ko.md)와 [패키지 manifest](../analysis/trial613-package.json)를 참조한다.

## 후속작업

사용자가 기존 MMC577과 비슷한 첫 레벨 동선으로 시험하고 nes-progress-mmc613.txt·nes-budget-mmc613.txt·nes-game-last-mmc613.txt를 전달한다. 시작 실패가 있으면 성공 실행과 분리한다. 5–40초·40–55초의 실제 표시 간격·출력/최종 ACK 비용·게임 진행과 약 60초 메뉴 복귀를 확인한다. 수신 전 기존 기준 FPS를 수정하거나 같은 RTL/펌웨어를 다시 최적화하지 않는다.

전체 외부 IO 전기적 sign-off, 장기 신뢰성, 지속 60fps는 미완료다. 여유는 76 LE·M9K 0·Flash 0이므로 후속 기능 추가에는 실제 삭제 비용이 필요하다.

## 재현

`prepare_nes_trial613.py`의 arm/board 모드 → 기존 `build_nes_trial577.ps1` 전체 링크와 Lite 전체 compile → `check_nes_trial613.py`와 단일 FLOAT의 `check_nes_rom613.py` → `report_nes_oe612.tcl` → CPF SOF/RBF 변환·BI3 encode → `test_nes_nrom458_programmer.py` → `package_nes_trial613.py` 순서다. 선택 폴더는 probes/nes-trial613/ARM01·checks01·trial01, Temp/nes-trial613-board01·rom01·image01·programmer02다. 비공개 재개 근거는 probes/nes-trial613/archive01에 보관한다.
