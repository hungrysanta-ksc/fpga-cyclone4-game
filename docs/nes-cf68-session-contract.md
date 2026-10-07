# NES070 전체 CF68 통신 검증 계약

MCU069의 실제 C 캡처를 변경 없는 FPGA068/CF68 물리 top에 재생한다. CPU/PPU와 START는 연결하지 않는다. 설치 파일 쌍 및 실제 STM32/SD/SNES 실행과 별개인 디지털 검증이다.

## 입력과 시간

동결069 `evidence-complete/session`의 실제 C·플랫폼·파일·trace·진단 fixture 해시를 확인한다. 새 materializer의 C와 같아야 한다. FPGA068 동결 manifest 및 fit03의15개 생산 SV 해시와 새 생성물을 대조하고, 비교한 생산 경계는 별도 파일로 보존한다.

8MHz 입력은 모든 프레임·idle에서 계속 동작한다. locked 해제 뒤 초기181µs까지 READY와 메모리 핀이 비활성인지 확인한다. READY는 시뮬레이션 시각201.0625µs, locked 해제 후200.0625µs에 올라오며 그 뒤 캡처 원점을 시작한다. 이는 GPIO 재생 전 준비 경계를 모델링한 것이며 실제 MCU polling 시간·전원 상승의 측정이 아니다. READY timeout은 시뮬레이션 시각252µs다. 원시 `%t` 출력은1ps 단위이므로 `ready_ns=201062500`이라는 기존 label의 숫자는201062.5ns로 해석한다.

CS/MOSI/SCK/sample 시간은 동결 C의2µs 명시 지연 템플릿을 재구성한다. 모든 응답 비트 중 명령 byte 뒤 C가 소비하는 비트를 대조한다. SD/CPU 실행 지연·interrupt jitter·비동기 위상 sweep은 모델링하지 않는다. GPIO 반환·base 설정·메뉴 복귀는069 host/ARM 근거를 재사용하며 이번 보드 재생은 진단 STOP에서 끝난다.

## 메모리와 완료

RAM은 초기화하지 않는다. 실제 핀 WE가 순차 byte를 적재하며, 모든 주소·chip·쓰기 byte lane·읽기 word enable을 확인한다. 각 CHECK 응답의 byte/tag는 캡처와 비교하고 마지막 ACK·FINISH·status·STOP까지 재생한다. 종료 시 전체 RAM byte, 적재/읽기/ACK count, verified 해제와 PSRAM·SNES·SRAM 버스 소유권 반환이 일치해야 한다.

핀 RAM의70ns 접근·35ns 출력 해제·350ns 최소 WE는 기존 bounded 재생과 같은 모형 가정이다. EBLL 규격의 모든 min/max·전압·PCB 지연을 승인하는 모델은 아니다.068의 전원 안정 가정·조건부 외부 예산 및 lockedHIGH 쓰기 클록 정지 반례는 그대로 남는다.

## 미사용 영역의 시험 변경

reset-held H1 queue/host 입력만 별도 clock 표현을 사용한다. 입력 net force로 공유 PLL을 정지하지 않는다. `MaskLink=0/ParkLegacy=0`은 원래 클록으로 초기64프레임을 비교한다. `MaskLink=1/ParkLegacy=1`은 CF68/F0A5/F144 뒤 사용하지 않는84MHz legacy stub을 멈춘다. 이후 모든 명령이6x이고 reply가8MHz loader에서 나오는지 검사한다.8MHz SPI·PSRAM은 정지하거나 가속하지 않는다. 이 변경은 실제 PLL·보드 설계 변경이나 전체 보드 모든 클록의 free-running 증명이 아니다.

`LimitFrames`는 prefix 검사만 수행한다. 전체 성공은 두 geometry의 모든 프레임·물리 쓰기/읽기·응답·ACK·최종 완료 상태·핀 반환을 요구한다. CF 응답의 C 소비 비트 하나를 바꾸는 대조는 첫 frame bit8의 sample assertion에서 실패해야 한다. 이전063/069 성공을 새 전체 성공으로 대신하지 않는다.

## 실행

```powershell
& ./tools/run_nes_cf68_session.ps1 -Python $Python -FloatWrapper $FloatWrapper -QuestaBin $QuestaBin -HostRun $Frozen069Session -FpgaEvidence $Frozen068 -Out $FreshASCIIOut -Case fine_x -MaskLink 1 -ParkLegacy 1
# banks32를 새 출력 폴더에서 반복한다. 모든 경로는 절대 경로다.
# prefix: -LimitFrames 64 -MaskLink 0 -ParkLegacy 0
# 오류 대조: -Mutation response
& $Python -B -X utf8 ./tools/verify_nes_cf68_session.py --evidence $Frozen070
```

기존 Starter FLOAT 한 좌석으로 순차 실행한다. 실행기·testbench·materializer snapshot과 raw 로그는 private 증거에 보존한다. 공개 clone만으로 동결 입력을 얻을 수 없으며 이 감사는 private 증거를 요구한다. 다음은 같은068 fit의 Standard ASM/압축 실제 C roundtrip과069 ARM 쌍, 실제 SD 원본/base/menu 및 독립 백업/복구를 검증하는 단계다.
