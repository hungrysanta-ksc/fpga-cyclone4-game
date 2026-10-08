# NES108 진단 전용 CSS/NMI 고장 종료 구현

진단 세션에 한정한 CSS/NMI 고장 종료 경로를 구현했다. HSE 고장 시 직접 RESET·nCONFIG·SPI를 정리하고 복귀하지 않으며, 정상 종료 때 CSS를 해제한다. 실제 C 호스트63건/보호 제거 대조4건과 최종 ARM 벡터·종료 경로 검증을 통과했다.

이번 목표인 독립된 소프트웨어 종료 경로의 구현·호스트/ARM 검증은 완료했다. 전체 native 세션에 새 CSS 모델을 연결한 회귀와 실기 전기적 조건은 미완료다. 설치·실기 시작·8µs 차단 승인은 하지 않는다.

## 변경된 동작

실제 nes_menu_sd_probe에서 USB IRQ 차단·SNES RESET·CF86 세션 진입·진단 시작 다음, 첫 파일 열기 전에 CSS를 확보한다. 진단 활성/공유 fault/USB IRQ/PA0·PA1 출력/RESET LOW/GPIO clock/HSE·PLL 상태를 검사한다. 기존 CSS가 켜졌거나 CSSF가 있으면 인수하거나 지우지 않고 거부한다. 기존 CSS 이전 상태는 OFF만 허용하고 정상 종료 시 OFF로 돌린다.

NMI는 소유 중이면 원인이 CSS인지 다른 NMI인지 고정한다. PRIMASK로 일반 IRQ를 막고 RESET LOW·USB IRQ 차단·nCONFIG LOW·CS HIGH·SCK/MOSI LOW·MISO 입력·SPI1 reset 유지·CSSF 처리를 수행한다. UART/printf/SD/FatFS/시간 대기/일반 오류 관찰 함수를 호출하지 않고 영구 루프에서 끝난다. HSI로 전환된 뒤84MHz 전제의 일반 코드로 exception-return하지 않는다. fault는 별도의 volatile32비트 값이며 기존 nes_return_failed에 OR로 연결한다. report 구조체는 NMI에서 수정하지 않는다. 기존 reset API나 diag_leave로 fault를 지울 수 없다.

정상 nes_diag_leave는 CSS 해제를 먼저 검사한다. 공유 fault이면 해제하지 않고 기존 blocked 경로로 간다. CSS를 끄기 전후 HSE/CSSF를 검사한다. 정상 종료 경계의 늦은 CSS NMI를 위해 claimed 이력은 전원 재시작까지 유지한다. 따라서 이전 진단 이후 CSSF가 있는 NMI도 보수적으로 차단한다. 최초 진단 전 NMI와 소유권 해제 후 CSSF 없는 NMI는 기존처럼 복귀 없는 미처리 루프이며 추가 GPIO 차단을 하지 않는다.

RESET은 기존 코드가 방향으로 assert/release하는 방식이다. open-drain을 새 전제로 요구하지 않고 기존 output type을 보존하며 HIGH를 출력하지 않는다. 실제 핀은 PA0 RESET, PA1 nCONFIG, PA4 CS이며 최종 생성 설정과 대조했다. 일반 부팅/GBC의 CSS를 전역으로 켜지 않았다. GBC 원본 해시 보존은 실기 재실행을 뜻하지 않는다.

## 검증 범위

| 검사 | 결과 | 한계 |
|---|---|---|
| 실제108 C + 실제 runtime 전체 + return predicate/reset 함수 본문 |63건 PASS:18진입 거부, 정상 IRQ 상태, 공유 fault, 활성/비활성 NMI, 늦은 CSS, 종료 실패,17개 MMIO 경계의 전/후 주입34건 등| MMIO·CSS 전환·NVIC·시간은 모델. 전체 instruction interleaving/실제 HSE 감지 시간 아님 |
| 보호 제거 대조 | nCONFIG store, sticky fault 연결, CSS 해제, 늦은 CSS 처리 제거4건 모두 거부 | 해당 인과 경계만 검증 |
| 최종 ARM | NMI 강한 심볼0x08018d30, vector word0x08018d31. stop108은 store 명령15개(첫 fault store는 조건부), 하위 호출0, DSB3/ISB2 및 복귀 없는 루프 | 실행/사이클 측정 아님.14개 MMIO store와 조건부 RAM fault store의 정적 명령 수 |
| 제품 연결 | 실제 probe의 첫 f_open 전 CSS begin, 실제 leave의 observer 전 CSS end, return_failed의 CSS latch 연결 확인 | 전체104 native SD/FatFS/main harness에 새 CSS 연결은 다음 작업 |
| 최종 파일 | ARM 183220 bytes, SHA256 `394c1c442b6d767b5d41f891151eed12e82954b624a0b53a346dad8dc948692c`; ELF `98d53c9e64f98d815983eb9b9ec5765fe8862389b85cef01e7e68f0f27829db3` | 컴파일 산출물, 설치 패키지 아님 |

VERSION은 CF86-CSS108이다. 기존094 표식/보고 candidate 이름은 유지한다. 저장 TXT의 PREPARED_RESET_HELD는 RESET 해제 성공이 아니며, NMI 종료는 새 TXT/메뉴 반환을 보장하지 않는다. NMI에서 nCONFIG를 내리므로 FPGA 설정·진단 중 데이터는 보존을 보장하지 않는다. 외부 전원 재시작과 정확044 복원 절차가 필요하다.

[ST RM0368 §6.2.7/§6.3.1](https://www.st.com/resource/en/reference_manual/rm0368-stm32f401xbc-and-stm32f401xde-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)의 CSS·HSI·NMI 및 CSSON 소프트웨어 설정/해제 의미를 따랐다. CSSF는 W1C로 처리하며 RCC interrupt enable bits는 보존한다. 일반 고장 observer를 NMI에서 재사용하지 않는다.

## 보존한 실패와 미결 사항

units01은 제한 환경의 MinGW DLL WinError623으로 컴파일 전 실패했다. 자동 승인 검토가 시간 초과된 실행은 허용된1회 재시도로 진행됐다. 안전성 거부는 아니었다. units02는 테스트가 실제11개보다 많은 활성화 MMIO 경계를 열거해 case122에서 실패했고 최종63건으로 바로잡았다. ARM 검사 초기3회는 매크로 괄호·CR 줄 끝·objdump 공백 기대 문제였다. 같은 ELF로 검사기를 수정했고 arm-check04에서 통과했다. Make 최초 dependency 실패/재시도와 원시 로그를 보존했다.

새 전체 native 세션, FPGA/fit/STA/ASM/Questa/실기는 수행하지 않았다.105 조합은104 ARM을 가리키는 역사적 조합이며108로 자동 승격하지 않는다. 기존086 양 클록 정지/locked HIGH CE9µs 반례도 해결됐다고 쓰지 않는다. CSS는 HSE 고장에 한정된다. HSE가 살아 있는 FPGA 내부 정지, CPU/버스/전원 고장을 보호한다고 주장하지 않는다. nCONFIG high-Z와 실제 RAM CE의 유효 HIGH 도달은 다르므로 E1/E2는 미결이다.

## 다음 목표와 작업 의미

다음은108을 기존104/097의 전체 SD·FatFS·main/menu 호스트 경로에 연결하는 통합 회귀다. 진입 거부·정상 반환·복구 중 고장·정상 종료 경계의 실제 CSS 연결을 검증하고, 모델 핀과 실제 PA0/PA1/PA4 매핑 차이를 명시적으로 해결한다. 108 ARM을105 파일 조합에 반영하는 것은 이 회귀 후 한 번만 한다. E1 전기적 범위와 E2 감지부터 CE HIGH까지의 최악 지연/고장 범위 판단은 여전히 별도다.

실기 디버깅 기반의 고장 종료 기능 구현이다. 이전 미처리 NMI 루프에 없던 진단 소유권·고장 고정·직접 출력 차단을 추가했다. 게임 실행 배선이나 SMB3 호환성을 구현한 것은 아니다.

084 저장/메뉴/GBC·092 클록/TXT/복원 성공, 준비도4완료/7부분/1미완료, SMB3(J) mapper4/384KiB 첫 목표는 유지한다. [현재 인계](../cores/nes/HANDOFF.ko.md)와 [108 검증 계약](../docs/nes-css108-contract.md)을 따른다.
