# NES104 타이머·인터럽트·CIC 통합

실제 timer·SysTick·LED·CIC·RESET 감지를 메뉴 복귀 경로에 연결했다. SysTick의 카드 상태 변경 알림이 진단 중 전역 printf 상태에 재진입하는 문제를 수정했다.

PR53 병합 `3dab89e66efff89e30cd777a5348a27c45d8d2bc`와 이전 head `e8c63e97a9e767a0f388d1bf615a62b4f41eab8b`의 포함을 확인했다. **이번 목표인 실제 하위 함수의 호스트 통합과 발견한 진단 ISR 출력 재진입 수정은 완료했다.** 모든 MCU 명령 경계의 IRQ 선점, 물리 시간, 최종 파일 조합 및 설치 승인은 미완료다.

## 발견과 변경

실제 SysTick_Handler는 sdn_changed를 호출한다. 기존 함수는 카드 변화 때 `printf("ch ")`를 실행했다. 실제 printf.c는 buffer/outlength/outptr/maxlen 전역 상태를 공유하므로 foreground 진단 출력 도중 호출되면 재진입한다. UART의 tick 기반 대기도 같은 SysTick ISR 안에서는 진행하지 않을 수 있다. 원본103 대조에서 ISR의 UART 접근 assertion이 발생했다.

104는 sdn_changed의 출력 한 곳을 `if(!nes_diag_active())printf("ch ");`로 바꿨다. DISK_CHANGED/DISK_REMOVED 갱신과 sd_changed 해제는 그대로 실행한다. 진단 종료 후의 legacy 출력은 유지한다. 이는 모든 legacy 출력의 재진입 문제를 해결했다는 뜻이 아니다. 생산 변경은 stm32f4xx/sdnative.c와 VERSION `CF86-IRQ104` 두 파일뿐이다.

실제 nes_return_delay/delay_us/delay_ms, SysTick_Handler와 빈 weak SysTick_Hook, LED 함수, CIC 함수 및 get_snes_reset을 기존 main2구간/full load/RTC/SRAM/FPGA/SPI/FatFS/nativeSD/observer/printf/UART 시험에 연결했다. CIC pair 호출에 계수용 문장 하나를 넣은 것과 매크로/레지스터 모형을 제품 원문과 분리해 보존한다.

## 검증 결과

|검증 층|최종 결과|
|---|---|
|units04|60건: timer10, RESET debounce1, 카드 debounce1, CIC8, UART40개 위치에서 SysTick 선점|
|main02 + fat32-96-02|23건: 정상5·오류18. 실제 CIC_PAIR/SCIC 분기 추가|
|timer-ticks-01 + timer-frozen-01|메뉴 복귀 중 TIM2 정지2건; SysTick 진행/정지 각각 오류15, RESET 유지·SPI 정리·이후 IO 금지|
|negative-*-03|원본103, wait 보호 제거, timer 정리 제거, 카드 갱신 제거, RESET 반전 제거, CIC 경계 변경 총6개 예상 실패|
|ARM01|182640바이트 SHA `7f0601cc24b3fc7288afd4b2531fffaf3aca0c67300c5c4d2bb9aa57d4ac1cca`|
|ELF|`1eeeb57746883eb96732f30b95b5e742356a383f5a7e63a3de5c9c7529f8f45f`; 진단 active 분기가 printf를 건너뛴 뒤 카드 상태를 쓰는 경로 확인|

85개의 정상 판정 실행과6개의 예상 실패 대조는 여러 검증 층의 합계다. 85개 실기 고장 유형이라는 뜻이 아니다. 기본 정상 메뉴는65536바이트 일치, SD1534명령, SPI TX139042/CS2079/읽기67584를 유지한다. 보고쓰기5회가 RESET 해제보다 앞선다. FAT32/autoboot와 기존 오류 격리는 별도 case 로그에 남는다.

timer 단위는 UIF 정상/정지, tick 진행/정지, uint32 카운트 초과, 기존 공유 오류, inactive 정상 지연,0지연 및 UINT32_MAX 근처 시작을 검사한다. 마지막은 실제 tick wrap timeout 증명이 아니다. CIC는 고정100001개 입력 샘플에서10/11 및1000/1001 경계와 LOW/HIGH를 검사한다. UART 선점은 대표 formatter 호출의40개 상태 조회 지점에서 실제 SysTick을 호출해 ISR의 UART 재진입이 없고 카드 상태 갱신이 남는지 확인한다.

ARM 검사는 시험에 사용한8개 제품 파일의 동일성, 실제 진단 분기·타이머 guard 호출과 빈 weak SysTick_Hook을 확인했다. timer/CIC/LED/RESET 원문은103과 동일하다. 추출한 main/load/helpers/reliable 구간에는 sleep_ms 호출이 없다. 제품 전체에는 legacy/GBC/USB sleep_ms 호출이 남으며 전체 호출 그래프나 모든 sleep을 제한했다는 주장은 하지 않는다.

## 모델과 미완료 범위

TIM2 완료, SysTick 스케줄, GPIO bit-band/BSRR/입력, 카드·CRC 원시함수, SPI 응답과 UART 레지스터는 모형이다. TIM2가 완료될 때 기존 가상 전달 시간을 진행시키며 실제 timer 주파수/명령 시간/IRQ 우선순위/지연을 측정하지 않는다. 이벤트 경계에서의 선점 시험이며 모든 MCU 명령 경계의 exhaustive IRQ 증명이 아니다. CIC 핀과 RESET 입력도 물리 콘솔 신호가 아니다.

호스트는 MinGW ABI에서 실제 C 함수를 실행한다. ARM은 최종 링크와 분기를 읽었으며 MCU 실행이 아니다. timer poll 상한은 코드의 회수 제한이지 실측 시간 상한이 아니다. SysTick LED는 계속 실행하며 모든 IRQ를 정지시키지 않는다. 카드 제거를 모든 FatFS 명령의 모든 선점 위치에 주입한 것도 아니다.

103 공유 오류→observer→정리 및102 helper의 기존 범위는 유지한다. CPU/APB/GPIO가 동작해야 하며, 이미 진행 중인 FPGA 동작의 롤백이나 두 클록 정지/lockedHIGH CE9us 반례를 해결하지 않았다. 외부IO·공통고장 검토와 최종 복원 조합을 건너뛰어 설치하지 않는다.

104 최종 ARM과097 동일 fit FPGA·정확044 복원 파일의 조합을 고정하고, 외부IO/공통고장 및 정상·실패 관측 절차를 검토해 제한 실기 가능 범위를 결정한다. 검증된 하위 함수를 다시 일반 모델로 되돌리거나 변화 없는 fit/ASM을 반복하지 않는다. 새 생산 변경이 없다면 이번 ARM을 재사용한다. 제한 실기와 전체 NES/SMB3 승인은 별도다.

준비도4완료/7부분/1미완료·installable=false.084 저장/044복원/메뉴/GBC 및092 클록활동/TXT/복원 실기 PASS를 유지한다. 부품·LED·분해·PC USB·동일 저장/클록 시험을 반복 요청하지 않는다. SMB3(J) mapper4·PRG256KiB/CHR128KiB 첫 게임 목표 유지;80/96KiB 진단은384KiB 게임 지원이 아니다. 새 RTL/fit/STA/ASM/Questa/실기/설치 패키지는 없다.

## 실패 보존과 재현

초기 단위/통합 결과와 대조를 모두 보존한다. card-state-01 대조는 disk_state가 이미 DISK_CHANGED여서 잘못 통과했다. DISK_OK로 시작해 실제 갱신 효과를 확인하도록 수정한 최종03은 예상 실패한다. units02는 비승격 MinGW 실행의 WinError623 DLL 재할당 오류로 컴파일을 시작하지 못했고 범위 지정 실행으로 통과했다. 최종 timer 정지 통합을 추가하면서 단위용200000회 harness watchdog을 단위에만 적용했다. 제품 wait의 tick/poll 예산은 바꾸지 않았다. 중간01/02와 최종03/04의 실행 driver/model 차이를 구분한다. ARM Make 최초 의존성 실패/재시도와 기존 경고도 보존한다. 자동 승인 거절·새 라이선스 오류는 없다.

[104 계약](../docs/nes-timer104-contract.md)·[메타데이터](timer104-verification.json)를 따른다. 고정 비공개 증거 없이 공개 clone만으로 모든 시험을 재현한다고 주장하지 않는다. 완료 finalizer/044–104 archive를 다시 실행하거나 수정하지 않는다.
