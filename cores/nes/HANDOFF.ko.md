# NES 현재 인계 —121 전체 프레임70ns 통과

[121 결과](../../analysis/FRAMES121-RESULT.ko.md) · [검증 메타](../../analysis/frames121-verification.json) · [120 후보 선정](../../analysis/CORE120-RESULT.ko.md)

## 바로 이어 할 작업

정상속도 실제052 코어+READ8/70ns는 두 자체 입력×4프레임×3시작위상(3.5/0/11.25ns)을 통과했다. 픽셀·패킷·PPU 이벤트는052 기준과 일치했다. 다음은 **CF86 등록형 reader의 SETUP/ACTIVE/HOLD/RELEASE를 고속 경로에 통합하고 같은 CPU·PPU 소비 기한을 검사**한다.121의052 reader를 CF86 안전 reader와 같다고 간주하지 않는다. 추가 지연이 실패하면 요청서비스/캐시/선행 읽기를 개선한다. NES 감속·정상 프레임 버림·데이터 검사 제거는 하지 않는다.

그 뒤 동일 후보의 클록·RESET·SPI/CHECK/RUN 소유권과 실제 보드 자원/핀/내부 타이밍을 확인한다. guard085는8MHz memory/20–22MHz reference 가정이다.84MHz로 단순 교체하면 heartbeat/timeout 조건이 달라진다. raw fault의 비동기 취소와 각 도메인의 동기 reset 해제를 유지하고 검증해야 한다. 과거059 959/963LAB/가상핀/PLL0은 최종 보드 여유가 아니다. 비용을 측정하기 전에 기능을 누적하지 않는다. 실제 SNES 영상 소비자는 아직 testbench stimulus로 대체되어 있다.

## 확정된 기준과 한계

119에서는 동일 ARM116/097 CF86으로 전체80KiB 적재·비교·STOP·기본 FPGA·메뉴 복귀와 사용자044 복원이 실기로 통과했다. 메뉴 준비491.34초는 펌웨어 경과 시간이며 화면 복귀 시각을 별도 측정한 값이 아니다. 이번 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가가 타이밍을 바꿨을 가능성을 남긴다. 같은 전체80/짧은BASE/ENTRY를 반복하지 않는다.

120에서는3클록·25ns 통과,3클록·70ns CPU 오류,7·8클록·70ns 초기 구간 통과를 확인했다.8클록 핀 단위16위상8400읽기/208취소와110ns 거부 근거는 유지한다.121은 두 입력×3위상=6사례,24프레임/1,474,560픽셀이다. 정상 클록,60ms 캡처 시작,150ms watchdog을 유지했다.3위상이 모든 위상·지터·아날로그 조건을 보증하지 않는다. 고정70ns 모델이며1ps 양자화 주기는 메모리11.904ns/코어46.560ns다. SPI 로더·STM32·보드 PLL·실제 SNES 프로그램은 실행하지 않았다. 새 제품 RTL/C/ARM/fit/ASM/SD 패키지는 없다.

최소 보호·관측·종료·044 복원 경로가 준비된 새 RUN 후보는 실기를 우선한다. 전기 E1/E2·8µs·양 클록 정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률이 아니다. 첫 게임 목표는 SMB3(J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`다.

## 재현·증거·관리

`run_nes_core_frames121.ps1`에 Python/기존 FloatWrapper/QuestaBin/핀된052live Baseline/새 ASCII Out을 전달한다. FLOAT RunOnly 한 좌석으로 직렬 실행한다. 라이선스 smoke 재실행과 uncounted 경로는 금지한다. `verify_nes_frames121.py --evidence <frozen121>`은 해시·6사례·기준 화면·이벤트를 임시 사본에서 재검증하며 새 시뮬레이터 실행은 아니다. `full01`이 최종이다. 완료 finalizer를 재실행하거나 동결044–113/116/118/120/121 자료를 수정하지 않는다.

PR66 병합 `ac3baaaf10168e9574e2bed8e02c027e021e48f7`을 확인했다. PR은 한국어 제목과 작업 목표·작업 내용·작업 결과·작업 의미의4항목으로 작성하며 사용자가 병합한다. GBC152개·원래 NES334개·모든 과거 공개 핀을 보존한다. ROM·바이너리·미디어·라이선스·개인 경로는 Git에 올리지 않는다.
