# NES109 CSS 통합 검증과 파일 조합

ARM108의 실제 CSS 진입·고장·해제 경로를 SD/FatFS·설정 전송·메뉴 복구 호스트 세션에 연결했다. 통합38건과 보호 제거 대조4건을 통과했고, ARM108/기존CF86/정확044복원11역할 조합을 새로 고정했다.

이번 목표인 CSS와 기존 진단 세션의 통합 회귀 및 변경 ARM의 파일 조합 고정은 완료했다. MCU 실행시간·외부 전기 조건·실기 성공은 미완료다. 제품 C/RTL은108/086 그대로이며 새 ARM/FPGA 빌드나 설치 패키지는 없다.

## 실제로 연결한 범위

108 최종 ARM 소스의 nes_css108.c/h, nes_diag_runtime.c, nes_menu_return.c, nes_h1_stm32.c 전체를 사용한다. 나머지는 고정104 호스트의 실제 FatFS/native SD/FPGA 설정 디코드·전송, RTC, 하위 SRAM/SPI, UART/printf, 타이머/SysTick/LED/CIC/reset 연결을 재사용한다. main의 메뉴 복구 두 구간과 load_rom은 기존 추출 경계를 유지한다. 전체 MCU 부팅/main 무한 루프·GBC 코드를 실행한 것은 아니다.

기존 모델의 PROG_B=PA6/READY=PA5를108 autoconf와 대조해 PA1/PB8로 수정했다. MISO PB4 샘플을 갱신할 때 PB8 READY를 지우지 않도록 했다. PA0 RESET은 실제 방향 제어 함수가 assert/release한다. 부팅 후 PA1 출력·RESET latch LOW·HSE/PLL·GPIO clock 및 RCC의 무관 비트는 초기 조건으로 모델링한다. 실제 전원·부팅 레지스터 측정이 아니다. PA1 출력 누락/HSE 미준비/기존 CSSON은 별도로 거부해 조건을 무조건 참으로 덮지 않았다.

## 결과

| 검사 | 통과 | 확인한 내용 |
|---|---:|---|
| 80KiB 기존 통합 회귀 |20| 정상4건과 하위 SPI/RTC/메뉴 오류16건. 정상 CSS OFF, 공유 고장에서는 보호 유지 |
| 96KiB/FAT32 |3| 자동부팅 정상1건과 전송 중/RESET release 후 하위 고장2건. 정상은 보고write5회와 CSS 해제 |
| CSS/NMI/진입 거부 |15| NMI12건과 진입 거부3건 |
| 보호 제거 대조 |4| begin/end/nCONFIG/sticky 연결을 제거한 실행 모두 거부 |
| 새11역할 조합 |정상1/거부23| 각 파일 손상·누락·추가·firmware 교환·낡은 digest/표식·역할/승인 변경 거부 |

12개 NMI 지점은 CSS 켜기 직후, 첫 SD 읽기, 진단 설정64바이트, 기본 설정 복구64바이트, ROM 전송32바이트, 메뉴256바이트, 보고 쓰기 중, RESET release 후, CSS 해제 전/후, 해제 후 USB IRQ 복구 직전의 늦은 CSS, 활성 세션의 non-CSS다. 마지막은 CSS 감지가 아닌 다른 NMI 처리 검증이다. 늦은 CSS는 이미 pending된 예외를 모델링하며 detector가 OFF 뒤 새 HSE 고장을 감지한다고 주장하지 않는다.

NMI에서는 RESET/nCONFIG LOW, CS HIGH, SCK/MOSI LOW, MISO 입력, SPI reset, CSSF 처리·interrupt enable 보존·고장 유지·복귀 없음이 확인됐다. SD edge/command, FPGA 설정/전송, 프레임, 하위 SPI byte, UART 관측값이 주입 직후부터 증가하지 않는지 검사했다. 기존 return reset과 진단 재진입으로 fault가 사라지지 않는다. GPIO/CSS/NVIC·바이트 응답·시간·terminal longjmp는 모델이며 모든 ARM instruction 경계나 실제 감지 시간을 증명하지 않는다. CSS write seam13회와108 ARM의15 store 명령은 다른 집계다(NVIC MMIO 및 RAM latch 포함 여부).

정상80KiB는 SD command1534, 하위TX139042/read67584, 메뉴65536바이트, 보고write5회와 release1회다. 96KiB 자동부팅은 기존1637 commands 경로를 유지한다. PREPARED_RESET_HELD TXT 저장은 release 증명이 아니며, NMI 시 새 TXT·자동 메뉴 복귀는 보장하지 않는다.

## 고정 파일과 보존 자료

- 새 조합 NES-PAIR-109, VERSION CF86-CSS108, manifest `788dca6e5546456340ef03579b91a46a0496724a899432df389d48f0c69aae69`. ARM108 183220bytes SHA `394c1c442b6d767b5d41f891151eed12e82954b624a0b53a346dad8dc948692c`.
- 기존097 CF86 전체510856바이트 디코드, 받은 base/menu, 자체80/96KiB fixture,094 표식2개, 정확044 복원 등11역할. 소스/바이너리8개 토큰과 보고 저장 경계를 확인했다.105 조합/manifest는 수정하지 않았다.
- 최종 normal02/fat32-96-01/fault03/negative4/pair01/pair-tests01. 초기 fault01의 제품 printf 억제와 fault02의 RCC 모델 초기화 실패를 보존했다. 모두 시험 모델/결과 출력 문제였고 생산 소스는 변경하지 않았다.
- 제품 pin/기능은 기존 근거를 재사용한다. 새 ARM/RTL/fit/STA/ASM/Questa/실기 없음. GBC/원래NES/이전 공개 고정 소스는 그대로다.

## 미완료와 다음 행동

다음은 변경된 고장 경로를 기준으로 E1 전기적 조건과 E2 고장 범위·차단 지연의 미확인 항목을 판정하는 것이다. 근거가 없는 상한을 만들지 말고, 보장 가능한 범위와 제한 실기에서 제외할 고장·데이터 손실·수동 복원 조건을 구체적으로 구분한다. 그 판단 전에는 설치·실기 시작을 승인하지 않는다. 같은 통합 시험·ARM/FPGA 빌드·파일 조합을 변화 없이 반복하지 않는다.

CSS는 HSE 고장 대응이며 HSE가 정상인 FPGA 내부 정지나 CPU/버스/공통 전원 고장의 해법은 아니다. nCONFIG high-Z는 RAM CE의 유효 HIGH 시간 보장이 아니다. 양 클록 정지·locked HIGH에서 CE9µs 반례와8µs 차단 미증명은 그대로다. [106 실기 조건](../docs/nes-trial106-decision.json)은105 참조의 역사적 판단이며 현재 파일은109다. 승인 false를 상속한다. [107 요구 근거](../docs/nes-board107-actions.ko.md)를 재사용한다.

실기 디버깅 기반의 통합 검증과 배포 준비다. 독립 시험에 머물렀던 고장 종료를 기존 전체 진단 흐름과 결합하고 파일 혼합을 검출한다. NES 코어 배선·게임 호환성 구현은 아니다.

084 저장/메뉴/GBC·092 클록/TXT/복원 성공과 준비도4완료/7부분/1미완료를 유지한다. SMB3(J) mapper4/384KiB 첫 목표도 동일하다. [현재 인계](../cores/nes/HANDOFF.ko.md) · [109 재현 계약](../docs/nes-css109-contract.md).
