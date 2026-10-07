# NES067 진단 메모리 준비·유지 구간 계약

후보 **NES-DIAG-MEMORY-067**, FPGA 식별 `CF67`, F0=A5/F1=44/protocol59. CPU/PPU가 없는 적재·CHECK 진단이다. 기존061 생성기, 전체 NES 코어 loader/reader,065 ARM 및066 파일 쌍은 변경하지 않는다. 설치 가능한 새 쌍은 없다.

## 구현 경계

`tools/nes_diag_memory_timing.py`는061 물리 진단을 생성한 다음 두 진단 전용 템플릿만 대체하고 CF 응답을67로 바꾼다. 모듈 이름은 생성 결과 안에서 기존 이름을 사용한다. `src/nes/diagnostic/` 파일을 전체 코어 빌드에 함께 넣으면 중복 모듈이 되므로 이 생성기를 통해서만 사용한다.

8MHz에서 한 클록은125ns다. 아래 값은 RTL의 명목 구간이며 routed/PCB slack이 아니다.

| 동작 | 순서와 조건 |
| --- | --- |
| 쓰기 | 주소·칩·byte lane·데이터를 latch → SETUP1 → WRITE3 → HOLD1 → RELEASE1 → RECEIVE |
| 쓰기 핀 | SETUP부터 데이터/byte enable 유효. CE는 WRITE/HOLD, WE는 WRITE만 LOW. RELEASE에서 데이터 구동과 CE를 해제하고 다음 클록에 바이트 수 증가 |
| 읽기 | 주소·칩·lane latch → SETUP1 → ACTIVE3 끝에서 샘플 → HOLD1 → RELEASE1 → 완료 응답 |
| 읽기 핀 | ACTIVE와 HOLD 모두 CE/OE LOW. 읽기는 두 byte enable LOW, lane으로 반환 byte 선택. 핀 해제 뒤 완료 응답 |
| 오류 | WRITE 중 프로토콜 오류는 쓰기를 끝내고 HOLD/RELEASE 후 실패. 공통 reset/lock 상실은 클록이 멈춰도 핀 해제, 이미지 무효화 |
| 실행 금지 | START 명령 거부와 boot.start=0 두 장벽 유지. RUN용 CDC 분기는 남아 있지만 이 진단에서 실제 코어 실행을 검증하지 않음 |

기존065 펌웨어는 CF61을 기대한다. CF67을 기존066 압축 파일 또는065 ARM과 섞어 설치하지 않는다. 다음 MCU 변경은 구형/다른 ID 거부, 실제 호출/ELF, 복구·SD 보호까지 함께 검증해야 한다.

## 이번 검증의 의미

1. `diag_memory_timing_tb.sv`: 실제 생성 loader/reader/boot의 모든80/96KiB write/read byte와 tag를 비교한다. SPI·MCU를 거치지 않는 핀 모형이다. 0/2/20ns 지연의 네 정상 경우, 각9회 취소/복구 검사. 세 보호 구간 제거와126ns 주소 지연은 정확한 assertion 실패를 요구한다. 0/2/20ns는 측정값이나 전 범위 min/max 보증이 아니다.
2. `nes_diag_memory_wave.py`:060에서 보존한 실제 C GPIO 파형을 새 물리 top에 재생한다. load는256 pin bytes, CHECK는96KiB를 TB loader로 준비한 뒤256 bytes/ACK를 검사한다. 각 단계는 SD 오류 STOP까지다. 전체80/96KiB SPI 성공 세션으로 확대하지 않는다. CF67 query는 TB가 수행하며 원래060 C의 MCU ID 검사 증명이 아니다.
3. Standard25.1 map/fit/STA: 새 소스/135핀의 내부 timing만 검사한다. 외부 IO는 여전히 미제약이다. 디지털 PLL stub 또는 reset 강제 시험은 실제 PLL의 클록 상실 감지 시간 보증이 아니다.

쓰기 tWP46ns·tDW23ns, read access70ns, 출력 해제0/8ns 가정을 핀 모형에 넣었다. bounded C replay는 기존061의70ns read/35ns disable/350ns WE 모델을 보존한다. 서로 다른 모델 목적을 혼합하지 않는다. 주소 관측의2ps 델타 유예보다 작은 위반은 검사하지 않는다. CE 최대8µs monitor는 CE 해제 시 검사하므로 무한 정지 검출기가 아니다.

## 재현 명령

공개 생성/단위 테스트는 저장소 소스와 설치된 도구로 실행할 수 있다. bounded waveform은 별도 private060 host evidence가 필요하다. frozen evidence verifier는 공개 clone만으로 실행한 검증이 아니다. 경로 변수는 실행 환경에 맞게 지정하고 출력은 존재하지 않는 ASCII 임시 폴더를 쓴다.

```powershell
# $Python, $FloatWrapper, $QuestaBin은 기존 환경의 절대 경로.
& ./tools/run_nes_diag_memory.ps1 -Python $Python -FloatWrapper $FloatWrapper -QuestaBin $QuestaBin -Out $FreshUnit
& $Python -B -X utf8 ./tools/nes_diag_memory_timing.py --out $FreshFit --quartus-bin $QuartusStandardBin
& ./tools/run_nes_diag_memory_wave.ps1 -Python $Python -FloatWrapper $FloatWrapper -QuestaBin $QuestaBin -Out $FreshWave -HostRun $Frozen060Host
& $Python -B -X utf8 ./tools/verify_nes_diag_memory.py --evidence $Frozen067Evidence
```

Questa는 기존 Starter FLOAT wrapper를 순차 사용한다. 실행기 자체가 private 임시 wrapper와 서버의 수명을 관리한다. 라이선스 smoke/상속된 uncounted 경로를 반복하지 않는다. 새 프로젝트에서061 fit DB를 재활용하지 말고 새 map/fit/STA를 만든다.

## 아직 필요한 조건

외부 min/max 및 SPI/SNES 제약·예외 근거, 전원 안정 후 tPU150µs, 실제 클록 상실/CE 최대8µs, 전체 C80/96KiB 회귀, CF67 MCU/ARM·새 ASM/압축·동일 소스 manifest, 사용자 SD 원본/base/menu 및 백업/복원, 외부 실기 TXT/화면 관측이 남는다. 상세 다음 순서와 중단 조건은 [Sol 인계](development/NES-067-SOL-HANDOFF.ko.md)를 따른다.
