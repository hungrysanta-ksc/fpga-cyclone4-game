# NES061 — 적재·읽기 확인용 물리 보드 경계

061은 CPU/PPU가 없는 진단 top이다. 060 MCU 코드와 059 protocol59를 사용하지만 START는 허용하지 않는다. 실제 게임 경로의 클록이나 059 공동 코어는 변경하지 않는다. 설치 가능한 이미지나 메뉴 호출은 아직 없다.

## 연결과 소유권

`tools/nes_board_diagnostic.py`는 고정된044 경계와059 메모리 경로를 새 출력 폴더에 생성한다. 기존 소스와 GBC는 수정하지 않는다. 기존 `src/fpga/pin.qsf`에서 같은135개 물리 핀과 전압 설정을 가져오고 각 벡터 비트·핀의 중복/누락을 검사한다. 대상은 EP4CE15F17C8이며 다른 보드 지원을 추가하지 않는다.

- CLKIN 8MHz → SPI/PSRAM 상태 회로. 읽기/쓰기3클록 =375ns, 쓰기 후 hold1클록 =125ns. 기존 84MHz PLL과044 SNES 경계는 유지한다. SNES_SYSCLK는 NES 클록으로 사용하지 않는다.
- 원본 자료의70ns PSRAM 표기는 실제 장착 부품 사양 확인이 아니다. 시험의70ns access/35ns output-disable와350ns 최소 write pulse는 **명시한 모델 조건**이다. 실제 tAA/tOE/tWP/tDS/tDH/turnaround 및 배선 지연을 대신하지 않는다.
- PLL lock 상실은 두 영역의 리셋을 즉시 assert한다. 각 영역이 자기 클록에서 해제한다. 84MHz 리셋 해제 FF를8MHz 회로로 전달하지 않는다. MCU_RDY는 lock 및 메모리 리셋 해제를 요구한다.
- protocol59 START(63)는 verified 값과 관계없이 SPI 오류8로 거부한다. 추가로 boot의 start 입력을0에 묶는다. reader RUN 요청은0, read_reset은1이다. CHECK는 자체 소유권으로 읽는다.
- F0=A5, F1=44와 기존 상태 명령을 보존한다. 별도 CF=61은 물리 진단 후보를 식별한다. 메모리 protocol 응답은59다. 미래 메뉴는 CF까지 확인해야 하며 기존060 함수는 아직 이 검사를 호출하지 않는다.
- ROM_ZZ=1, 외부 SRAM은 비선택/고임피던스, DAC 출력0, SNES_IRQ=0은 기존 H1 shell과 같다. 실제 회로의 polarity/전압 확인은 남아 있다.
- lock 상실 중 쓰기는 즉시 중단되어 짧은 펄스가 될 수 있다. 해당 이미지와 적재 상태 전체를 폐기한다. 이를 유효한 메모리 쓰기 또는 저장 데이터 보존으로 해석하지 않는다. SPI 오류는 종전대로 이미 수락한 쓰기를 drain한다.

## 재현

공개 소스와 설치된 Python·host GCC·Questa·Quartus가 필요하다. 사용자 ROM이나 private NES core export는 필요하지 않다. 모든 출력 폴더는 새 ASCII 경로여야 한다.

```powershell
python -B tools/nes_sd_readback.py --out <host060> --gcc <gcc.exe>
./tools/run_nes_board_diagnostic_wave.ps1 -Python <python.exe> -FloatWrapper <approved-wrapper.ps1> -QuestaBin <questa-win64> -HostRun <host060> -Out <wave061>
./tools/run_nes_board_diagnostic_wave.ps1 -Python <python.exe> -FloatWrapper <approved-wrapper.ps1> -QuestaBin <questa-win64> -HostRun <host060> -Out <negative061> -Mutation fast-memory
# 별도 새 출력 폴더에서 allow-start, connected-start도 실행한다.
python -B tools/nes_board_diagnostic.py --out <fit061> --quartus-bin <quartus-bin64>
python -B tools/verify_nes_board_diagnostic.py --evidence <private061-archive>
```

마지막 verifier는 저장된 원시 근거 감사이며 새 실행이 아니다. FLOAT 실행은 기존 승인 wrapper를 사용하고 한 seat에서 순차 실행한다. 실행 snapshot·실패 로그를 보존한다.

## 검증 범위와 남은 조건

실제060 C의 GPIO 시각과 샘플을 **물리 top의 SPI 핀**에서 재생한다. 적재 trace는256바이트를 SPI로 쓴 뒤 SD 오류→STOP이다. 비교 trace는96KiB를 testbench loader 입력으로 핀에 쓴 뒤256바이트를 SPI READ/ACK하고 SD 오류→STOP이다. 전체96KiB C 전송·전체 CHECK/FINISH 실행으로 확대하지 않는다. 준비 단계와 protocol 상태 fault injection을 명시한다. PLL은 디지털 stub이며 아날로그 lock 동작 모델이 아니다.

두 단계 START 방어, idle 및 쓰기 중 lock 상실, 두 클록 정지에서 핀 해제, 재취득 후 상태 폐기·식별자·주변장치 idle을 검사한다. fast-memory 대조는84MHz로 잘못 연결했을 때 write pulse 검사가 실패해야 한다. allow-start와 connected-start는 각 방어 제거가 각각 해당 assertion에서 실패해야 한다.

Quartus는 map/fit/STA까지만 실행한다. 타이밍 도구 exit0만으로 통과를 선언하지 않고 두 클록×3corner×5검사의30개 slack을 검사한다. 외부 IO 제약은 아직 만들지 않으며 blanket false path로 숨기지 않는다. 내부 STA 통과·물리 핀 배치는 전기적 signoff 또는 설치 허가가 아니다.

다음은 실제 보드/PSRAM 사양, 외부 IO 타이밍, CF61을 확인하는 메뉴·진행/결과/로그·복구, paired MCU/FPGA 이미지·backup/rollback이다. 044 실기/GBC와 전체 코어4LAB 제약은 그대로 보존한다.
