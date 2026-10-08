# NES103 공유 오류 확정 시 출력 전 SPI 차단

공유 오류가 확정되면 observer에서 LED·틱 조회·UART보다 먼저 RESET/USB 보호와 SPI·GPIO 차단을 수행한다. 이후 UART 출력/flush도 대기 없이 생략한다. 보고서 오류만 있는 복구 경로는 유지한다.

PR52 병합 `03f2ac3815e01d8a4b8be88b3fc1d749762a83ac`와 기존 head37421a1 포함을 확인했다. **공유 오류 래치→observer→차단의 소프트웨어 경로 및 UART 억제 목표는 완료했다.** 물리 고장 발생부터 오류 감지까지의 시간, 전체 timer/CIC/IRQ 통합과 실기 검증은 미완료다.

## 변경과 이유

102는 최종 `nes_diag_blocked`에 도달하면 SPI를 차단했지만, 먼저 호출된 observer는 printf를 실행했다. 실제 UART는 문자별 1tick/100000poll 대기 제한을 갖고 있어도 한 줄마다 반복될 수 있다. 원본102 observer/UART를 연결한 대조는 아직 SPI가 살아 있는 상태로 UART 상태를 읽어 실패한다.

103은 `active && nes_return_failed()`인 observer 진입에서 USB IRQ 차단→SNES RESET 유지→기존102 정리 helper→return을 수행한다. LED 소유권 변경·틱 읽기·진행률 나눗셈·printf를 거치지 않는다. `nes_return_fail`과 nativeSD의 `nes_diag_sd_error`는 기존대로 래치를 먼저 세우고 런타임/observer를 호출한다. 이 두 경로의 오류 저장 및 최초 오류 보존 코드는 바꾸지 않았다.

`uart_putc`와 `uart_flush`도 같은 active/shared 조건에서 dropped 계수만 올리고 반환한다. 줄바꿈의 CR 재귀, wait_start, TXE 조회, DR 쓰기보다 앞이다. UART 지연 자체는 새로운 공유 오류로 승격하지 않으며 정상·복구 가능한 출력의 기존 문자별 예산도 늘리지 않았다. inactive legacy 경로는 같은 보호를 적용하지 않는다.

`report.error`만으로 차단하지 않는다. 복구 가능한 구성/보고 오류가 있을 수 있기 때문이다. 정지 helper는102와 동일한12 MMIO 쓰기/3배리어이며 자동 재개·SPI reset 해제·추가 SD 보고를 허용하지 않는다. 반복 observer와 최종 blocked 진입은 같은 차단을 재적용한다.

생산 변경은 `nes_diag_platform.c`, `stm32f4xx/uart.c`, VERSION `CF86-OBS103` 세 파일뿐이다. main/load, SPI101, RTC099, nativeSD, printf, timer, CIC, GBC 원문을 유지했다.

## 검증 결과

|범위|결과|
|---|---|
|unit03|실제 observer/runtime/shared-fail/nativeSD-fail/printf/UART/RESET/정리 함수 17경우|
|main04 + FAT32-96-02|기존 실제 main2구간/full load/RTC/SRAM/FPGA/SPI/FatFS/nativeSD에 실제 observer/printf/UART 연결 21경우: 정상3·오류18|
|stall02|UART TXE가 계속 LOW인 조건에서 오류경로16경우 추가 통과|
|대조|차단 호출·putc 억제·flush 억제·공유 오류 구분·출력 순서의5개 대조 + 원본102 대조1개 예상 실패|
|ARM|182632바이트, SHA `246310901db820670e8558680dd40aa137706fc282c542c2e00f50baef845934`|
|ELF|`b576265684aa5826073300dab44171e9e16f5b5af09ca0640c3b8e2301ff3b03`; active/shared 분기→RESET→차단 tail-call, UART 오류분기의 wait 이전 return 확인|
|MMIO|최종 ARM helper를16초기값에서 해석, 기존12쓰기/배리어3,9,12와 일치|

총54 호스트 실행은 서로 다른 검증 층의 합계이며 54개의 실기 고장 유형이라는 뜻이 아니다. 정상 경로는 메뉴65536바이트 비교, 보고쓰기5회가 RESET 해제보다 앞서는 순서와 기존 SD/SRAM 계수를 유지한다. 오류 경로는 기존 quiet 검사를 유지하고 공유 오류 observer의 추가 tick/UART 접근 없이 핀 정리 완료를 확인했다.

unit은 UART 준비/정지와 tick 진행/정지의 조합, 복구 가능한 보고 오류, 최초 오류 보존, 중복 알림 억제, CR/LF, 늦은 printf/flush, inactive 경로를 검사한다. frozen tick+UART LOW에서 복구 가능한 한 줄은3700037번의 추가 상태 샘플을 소비할 수 있었으며, 이것은 호스트 샘플 수이지 MCU 소요시간이 아니다. 공유 오류 이후에는 이런 출력 대기를 시작하지 않는다.

main 시험의 제품 printf는 별도 컴파일 모듈까지 같은 실제 formatter/UART에 연결했다. 호스트 자체의 로그는 libc로 분리했다. 기존 `print_fresult` 표시 stub과 LED GPIO 효과, CIC, TIM2/SysTick/RESET 입력 및 카드/핀/CRC 원시함수 모델은 남는다. UART DR은 호스트 레지스터이고 실제 전송 비트나 보레이트를 재현하지 않는다. host는 MinGW ABI, ARM은 최종 링크/분기/MMIO 해석이며 ARM 실행은 아니다.

## 경계와 다음 작업

보장 시작점은 **진단 active 상태에서 공유 오류 래치가 설정되고 foreground observer가 실행되는 시점**이다. 외부 고장부터 감지까지, 이미 실행 중인 정상 printf를 인터럽트로 즉시 중단하는 것, IRQ 지연·재진입·CPU/APB 고장은 증명하지 않았다. 공유 오류/formatter는 기존 foreground 소유권 전제다. MCU 시간 상한·GPIO pad 정착·부분 FPGA 명령 롤백·이미 발행된 DMA 취소도 승인하지 않는다.

SysTick의 LED 호출은 별도 ISR이므로 observer가 LED를 건너뛴 것을 모든 ISR 정지로 해석하지 않는다. PA0 reset latch LOW와 초기 핀 설정은 기존 초기화 전제다. 공유 오류 뒤 새 TXT/화면 출력을 보장하지 않는다. 두 클록 정지/lockedHIGH CE9us 반례와 외부IO 검토가 남아 있다.

실제 timer의 delay_us/delay_ms/nes_return_delay, SysTick/LED/CIC와 RESET 감지 경로를 현재 main에 연결한다. 공유 오류가 기록되기 전의 대기와 IRQ 전제를 검증한 뒤 최종 ARM/FPGA·044 복원 조합, 외부IO/공통고장·관측 가능한 제한 실기를 확정한다.

준비도4완료/7부분/1미완료·installable=false.084 저장/044복원/메뉴/GBC와092 클록활동/TXT/복원 실기 PASS를 유지하며 반복 시험을 요구하지 않는다. SMB3(J) mapper4·PRG256KiB/CHR128KiB 첫 게임 목표도 유지한다.80/96KiB진단을384KiB게임 지원으로 쓰지 않는다. 새 RTL/fit/STA/ASM/Questa/실기/설치 패키지는 없다.

## 실패 보존

unit01은 fault 식별자 문자열 치환이 SD 변수 이름까지 바꿔 컴파일 실패했다. 단어 경계 치환으로 수정했다. main01은 MinGW stdio의 printf 선언과 이름 매크로 충돌, main02는 inactive LED 복원도 active 전용 IO로 취급한 모델 assertion 실패였다. 헤더 순서와 LED 모델만 수정했다. 초기 order 대조는 앞선 printf가 새 UART 보호에 막혀 정상 통과했으므로 보호 제거 대조로 채택하지 않았다. 최종 대조는 LED/tick 호출을 차단 앞에 옮겨 순서 위반을 검출한다. main03/첫 FAT32·stall은 일부 별도 모듈 printf가 libc로 연결된 중간 시험이며 최종04/02는 제품 모듈 전체 printf를 연결했다. Make 최초 의존성 실패·재시도와 기존 C 경고를 보존했다. 비승격 objdump 실행은 Windows DLL 재할당 오류로 실패했고 같은 바이너리를 승인된 범위의 실행으로 읽었다. 첫 문서 finalizer는 동결 이전에 한글 README를 cp949로 읽어 실패했다. UTF-8을 명시한 뒤 완료했으며 그 이전 세 문서만 재작성했다. 자동 승인 거절·라이선스 오류는 없었다.

[재현 계약](../docs/nes-observer103-contract.md)·[메타데이터](observer103-verification.json)를 따른다. 고정 비공개 증거가 필요한 시험을 공개 clone만의 완전 재현이라고 주장하지 않는다. 완료 finalizer 및044–103archive를 수정하거나 재실행하지 않는다.
