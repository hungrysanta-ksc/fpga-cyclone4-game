# NES 059 — SPI 읽기 검증 계약

SPDX-License-Identifier: MIT.

059는058의 메모리 클록 CHECK 포트에 SPI 요청과 보존된 완료 응답, 순서대로 확인한 뒤 실행하는 gate를 연결한다. MCU 코드는 원본 바이트 callback과 실제 반환 데이터를 모두 비교한다. 새 함수는 GPIO callback을 사용하며 SD/메뉴 연결은 별도다.056의 기존 SD·복구 함수는 그대로이고 새 함수를 호출하지 않는다. 설치용 이미지가 아니다.

## 프로토콜

054와 같은8바이트 mode0 프레임·CRC8·arg complement·A5 tail·CS 상승 commit을 사용한다. 프로토콜 식별자는 **59**다.056의54 전용 query와 섞어 쓰면 안 된다. 응답은 command byte를 받는 시점의 snapshot이며 새 명령 결과는 다음 query로 확인한다.

| opcode | 의미 | offset / arg |
| --- | --- | --- |
| 60–62 | BEGIN/DATA/END | 기존 길이/순서 계약. BEGIN은 검증 상태를 지움 |
| 63 | START | loaded 길이 /0. VERIFIED가 아니면 SPI 오류8 |
| 64 | STOP | loaded 길이 /0. CHECK·미완료 응답·VERIFIED를 지움 |
| 65 | 일반 STATUS | side effect 없음. 길이/오류 반환 |
| 66 | CHECK OPEN | 0/0. loaded이고 RUN이 꺼져 있어야 함 |
| 67 | READ | 현재 검사 주소 /0. 단일 outstanding, 이전 DONE의 ACK 필요 |
| 68 | ACK | 반환 주소 /MCU가 원본과 비교한 바이트. DONE·주소·바이트가 일치해야 다음 주소로 이동 |
| 69 | FINISH | 전체 길이 /0. 모든 바이트 ACK 뒤 CHECK를 내리고 VERIFIED 설정 |
| 6A | CHECK STATUS | side effect 없음. 보존 데이터·주소·오류 반환 |

응답의 첫 바이트는 버린다. 이후 byte1=59,byte2=flags,byte4..6=24비트 big-endian 수다.65는 byte3=SPI 오류,byte4..6=loaded 길이,byte7=loader 오류다.6A는 byte3=보존 데이터,byte4..6=CHECK 주소,byte7 상위/하위 nibble=SPI/loader 오류다.

flags bit7=VERIFIED,6=DONE,5=CHECK,4=loader fault,3=SPI fault,2=RUN,1=loaded다. bit0은 CHECK 중 busy,그 외 load_ready다. MCU는 정확한 상태22(검사 대기),23(busy),62(DONE),82(검증 완료),86(RUN)를 확인한다. 임의의 상위 bit를 무시하지 않는다.

READ의 반환 주소가 진행 주소와 다르면 오류7이다. 성공 응답의 데이터는 별도8비트 레지스터에 보관하고 진행 주소는 ACK 전까지 바꾸지 않는다. STATUS 프레임이 수신 offset을 덮어써도 완료 응답이 바뀌지 않는다. 중복/누락/역순 ACK와 잘못된 바이트는 오류8,불법 CHECK 상태는6,058 CHECK fault는9다. 실패는 CHECK와 VERIFIED를 내리고 common reset 전까지 유지된다. 수락된 쓰기는 이전 계약대로 끝까지 진행한다.

FINISH와 START 사이에는 별도 프레임이 있으므로 CHECK를 내린 뒤 reader 양쪽의 공통 reset을 거친다. STOP도 확인 상태를 폐기하므로 RUN STOP 후 다시 START하려면 재검증해야 한다. FPGA가 승인 원본을 따로 보관하는 것은 아니므로 이 gate는 정상 MCU의 비교 순서를 보장하는 수명주기 제어이며 보안 인증이 아니다.

## MCU 호출

`nes_rom_verify()`는80/96KiB만 허용한다. source callback은 iNES header를 제외한 승인 원본의 해당 바이트를 제공한다. 함수는 READ→6A query→원본과 비교→ACK를 반복하며 최대4회 query 후 timeout으로 중단한다. 모든 바이트 뒤 FINISH와82 상태를 확인한다. `compared`는 비교한 바이트 수이며 최종 함수 성공과 별도다.

`nes_rom_verified_start()`는82를 먼저 확인하고 START 뒤86을 확인한다. 데이터/tag/상태/입력 읽기 오류에서 START를 호출하지 않는다. 비교 실패 시 STOP을 시도하며 `stop_ok=false`이면 caller가 기존 base 재설정 경로로 복구해야 한다. 이 함수들은 GPIO/USB 소유권이나 콘솔 reset을 직접 해제하지 않는다. caller가 기존056 보호를 유지해야 한다. 아직 SD source callback과 메뉴 진입점에는 연결하지 않았다.

현재 실제 C 전송의 한 프레임 최소278µs에서 READ/query/ACK는834µs/바이트다. 추가 읽기 검증은80KiB 약68.3초,96KiB 약82.0초로 추정한다. SD 처리·추가 query·초기 명령을 제외한 계산이며 실기 시간 측정이 아니다. 진행/중단 표시와 burst 최적화는 보드 통합 단계에 남아 있다.

## 재현과 검증 범위

```powershell
python -B tools/nes_spi_readback_host.py --gcc $HOST_GCC --out $FRESH_HOST
python -B tools/nes_spi_readback_host.py --gcc $HOST_GCC --out $FRESH_MUTATION --mutation
./tools/run_nes_spi_readback.ps1 -Python $PYTHON -FloatWrapper $FLOAT_WRAPPER -QuestaBin $QUESTA -Out $FRESH_UNIT -Baseline unused -Mode unit
./tools/run_nes_spi_readback.ps1 -Python $PYTHON -FloatWrapper $FLOAT_WRAPPER -QuestaBin $QUESTA -Out $FRESH_WAVE -Baseline unused -Mode wave -Waveform "$FRESH_HOST/waveform.txt"
./tools/run_nes_spi_readback.ps1 -Python $PYTHON -FloatWrapper $FLOAT_WRAPPER -QuestaBin $QUESTA -Out $FRESH_LIVE -Baseline $PRIVATE_057_LIVE -Mode live
python -B tools/nes_spi_readback_checks.py --mode fit --baseline $PRIVATE_057_FIT --quartus-bin $QUARTUS_BIN --out $FRESH_FIT
```

unit/host/wave는 공개 원본과 자체 패턴만 사용한다. unit은 loaded 길이16의 독립 응답 모형으로 제어·보존·오류를 시험한다. wave는058 loader 명령 입력에 testbench stimulus를 넣어 실제 핀으로80KiB를 채운 후, 실제 C GPIO 파형의32바이트 비교/ACK와 source 실패→STOP을 재생한다. 이 적재 준비를 SPI DATA 시험이나 임의 RAM 초기화로 혼동하지 않는다. host의 두 전체 길이 검증은 C 응답 모형이며 그 자체로 RTL 통과가 아니다.

`--mutation`은 MCU 비교를 제거하고 반환 바이트를 그대로 ACK하는 잘못된 구현을 별도 복사본에 만든다. 손상 시나리오에서 verify 성공을 거부하는 host assertion이 실패해야 이 대조가 성립한다. 예상 실패 확인을 정상 구현의 통과와 구분한다.

live와fit는 고정 private057 export가 필요하다. live는 SPI DATA로 두 진단을 적재하고 SPI CHECK/ACK/FINISH 후 실제 코어를 실행한다. 시험 시간을 줄이기 위해 리셋으로 정지한 queue/host 클록만 적재·CHECK 중 마스킹한다. 원래 oscillator 위상은 유지하며 mem_clk·SPI·PSRAM 및 RUN 이후 클록/메모리 마감은 그대로다. 이 조정은 testbench에만 있고 제품 클록 gate를 추가하지 않는다. 모든 픽셀·패킷 내용과 S/E/F/D 이벤트를057과 비교하되 시작 시각 차이는 한 사례 안에서 같은 상수여야 한다.

ARM 링크 재현은 검증된 private056 준비 트리를 입력으로 `prepare_nes_spi_readback_arm.py --baseline ... --out ...` 후 `build_nes_spi_readback_arm.ps1`에 기존 ARM/GCC/make/Unix 도구와 해시 고정 mini image를 넘긴다. 두 새 함수는 section GC에서 유지하지만 호출하지 않는다. 전체 ELF 링크는 실제 STM32/SD 실행이나 SD와59 프로토콜이 연결된 펌웨어를 뜻하지 않는다.

모든 Questa 시험은 사용자 지침의 기존 Starter FLOAT 경로로 순차 실행한다. 실제 보드 클록·핀·STA·SNES 소비자·전기 타이밍과 새 실기는 별도 gate다. [기존058 계약](nes-rom-readback-port-contract.md)과 [현재 인계](../cores/nes/HANDOFF.ko.md)를 함께 따른다.
