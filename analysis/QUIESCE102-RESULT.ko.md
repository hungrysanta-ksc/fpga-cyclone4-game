# NES102 최종 오류 정지의 SPI·핀 차단

최종 오류 정지 함수에 CS 해제→GPIO 분리→SPI1 리셋 유지 경로를 연결했다. 핀/레지스터 시작상태1024·실제 main 통합21·보호제거6·원본반례1·ARM MMIO16해석을 통과했다. 최초 오류부터 정지 진입까지의 지연과 실기 전기적 효과는 미검증이다.

PR51 병합 `bedfad5bf53d8c94a0da51f4c50e9406dbd4f8ed`와 이전 head 포함을 확인했다. 이번 범위인 **nes_diag_blocked 진입 후 종료 동작의 구현과 C/ARM 레지스터 검증**은 완료했다. 전체 고장 반응시간·전기적 핀 차단·주변장치 통합·실기 승인은 아직 미완료다.

## 변경 동작

기존101 blocked는 USB IRQ 차단·SNES RESET 유지 뒤 상태 표시와 CPU 루프만 실행했다. SPI SPE/AF와 대기 전송은 남아 있었으며 원본 플랫폼 함수를 새 시험에 연결하면 종료 상태 검사가 실패한다.

102는 USB IRQ 차단과 실제 `snes_reset(1)` 뒤, 상태 표시보다 먼저 다음의 대기 없는 정리 함수를 호출한다.

1. PA4 CS latch HIGH, push-pull/output을 설정하고 배리어를 실행한다.
2. PB3 SCK/PB5 MOSI latch LOW를 미리 기록하고 push-pull/output으로 전환한다. PB4 MISO는 input으로 전환한다. AFR 값과 다른 핀은 그대로 두며 MODER로 SPI 연결을 분리한다.
3. SPI1 CR2 요청/인터럽트를 끄고 SPE를 지운 뒤 RCC SPI1RST를 설정해 유지한다. 리셋 해제나 재시도는 하지 않는다.
4. 상태 표시 후 기존 무한 정지 루프에 남는다. 외부 전원/리셋 개입이 필요하다.

이 정리에는 BSY/TXE/RXNE/READY 확인, DR 접근, 타이머, UART, SD, SPI 거래, DMA 완료 대기가 없다. 이미 출력된 부분 명령을 정상 완료로 간주하거나 되돌리지는 않는다. FPGA 메모리 제어와 전기적 취소시간은 별도다.

[ST RM0368 Rev6](https://www.st.com/resource/en/reference_manual/rm0368-stm32f401xbc-and-stm32f401xde-advanced-armbased-32bit-mcus-stmicroelectronics.pdf) 6.3.8(p116)의 SPI1RST와 8.3.2/8.3.10/8.3.11(p149–155)의 GPIO/AF 선택을 대조했다(2026-10-08). 이는 레지스터 동작 근거이며 보드의 전압·배선 지연·최소 CS 여유시간을 승인하지 않는다. 배리어도 아날로그 핀 정착시간 측정이 아니다.

생산 변경은 `nes_diag_platform.c`와 VERSION `CF86-STOP102`뿐이다. SPI101 정상 TXE→BSY 순서·공유 예산, RTC099, CS100, main/load/nativeSD/CF86 세션094·GBC 소스를 유지했다. 범용 SPI 오류마다 즉시 정지하도록 변경한 것은 아니며, 실제 최종 blocked 경로가 호출해야 이 정리가 실행된다.

## 검증

|범위|결과|
|---|---|
|pins01|1024 시작 상태: CS/idle latch/AF 또는 GPIO transport/CPOL/진행16단계/클록 진행·정지/진단 active·inactive 조합|
|보호 제거|CS 해제·SCK 분리·MISO input·RCC reset·CS 우선 순서·실제 호출 제거6개 예상 실패|
|원본101|원본 blocked 본문을 그대로 연결한1개 실패|
|실제 main 통합|main02 18 + FAT32-96-02 3 =21경우. 정상3/오류18, 오류마다 실제 정지 함수 도달 및 최종 핀/RESET/IRQ 상태 확인|
|ARM|182556바이트; `4d1c504b8ba2c343180d1a3265a79773e1acd3c51b160dab09e347b9b7ef325f`|
|ELF|`a29fb0bdd0a14375304bddd55023400a55ae03a279ed0e3e0843bc3c654dc25b`; RESET→정리→표시 호출과 정지 루프 확인|
|ARM MMIO|실제 직선 명령을16초기값으로 해석,12개 쓰기와 쓰기3/9/12뒤 배리어가 독립 기대값과 일치|

pins 시험은 실제 정리/blocked/RESET 함수와 GPIO 매크로/CMSIS 상수를 컴파일했다. BSRR의 latch 반영·GPIO mux·RCC reset 효과·하드웨어 진행은 모델이다. UART observer는 모델이며, 같은 모델의 assertion을 제거해 통과시킨 것이 아니라 보호 제거 대조를 보존했다. 최초 오류를 이미 가진 active 상태에서는 최초 오류가 유지된다. inactive 진입은 기존 begin 동작을 유지한다.

main 시험은 고정101의 실제 main2구간/full load/RTC/메모리/FPGA 명령/SPI/FatFS/nativeSD를 재사용하고 blocked stub을 실제102 함수로 교체했다. RESET wrapper의 계수/감지 모형에 실제 `snes_reset` GPIO 쓰기도 연결했다. RESET 입력 신호 감지와 외부 콘솔 동작은 여전히 모형이다. 정상 상태의 바이트 모델 검증과 레지스터 종료 검증은 실제 SPI 비트/FPGA RTL 동시 실행이 아니다.

## 가정과 미완료

- SNES PA0 reset latch LOW는 기존 `snes_init`의 설정을 전제로 한다. 이번 시험은 초기화 전체를 실행한 것이 아니다. CPU·AHB/APB·GPIO/RCC 쓰기가 실행되고 응답한다는 전제가 필요하다.
- 진단 소유권에서 다른 SPI master 소프트웨어/DMA가 동시에 핀을 재설정하지 않는다는 전제를 유지한다. CR2를 끈 것이 이미 발행된 DMA 버스 요청 전체의 취소 보장은 아니다.
- **최초 오류→기존 observer/UART·하위 호출 반환→blocked 진입까지의 시간 상한은 이번에 증명하지 않았다.** 정리 함수 자체는 기다리지 않지만 그 이전 경로가 다음 우선 작업이다. 정리 이후 상태 표시가 지연돼도 핀 정리는 이미 수행된 순서다.
- CS HIGH와 SCK 강제 LOW 사이 실제 pad 지연, 끊긴 프레임의 FPGA 측 영향, 두 클록 정지/lockedHIGH CE9us 반례는 미해결이다. GPIO/주변장치 고장 자체를 소프트웨어로 해결한다는 보장은 없다.
- SPI를 정지 상태에 유지하므로 이 경로에서 새 화면/TXT 저장을 보장하지 않는다. 외부 사용자가 확인할 수 있는 제한 시험의 관측/복원 절차는 별도로 설계해야 한다.

실제 UART/printf·observer·timer·CIC와 오류 전달 경로를 연결해 최초 오류부터102 정지 함수 진입까지의 지연/종료를 검증한다. 이후 최종 ARM/FPGA·044 복원 조합, 외부IO/공통고장과 관측 가능한 제한 실기를 확정한다. 준비도4완료/7부분/1미완료·설치false.084 저장/복원/메뉴/GBC와092 클록활동/로그/복원 PASS, SMB3(J) mapper4/384KiB 목표를 유지한다. 새 RTL/fit/STA/ASM/Questa/실기/설치 패키지는 없다.

## 실패 보존과 재현

첫 main01/fat32-96-01은 정리 모델을 기존 하위 모델 선언보다 앞에 include해 컴파일 실패했다. 순서만 수정한 main02/fat32-96-02가 최종이며 생산 코드와 ARM은 바뀌지 않았다. 초기 로그와 고정 빌드 도구의 첫 Make 의존성 실패·재시도를 보존했다. 자동 승인 거절/라이선스 오류는 없었다.

[102 계약](../docs/nes-quiesce102-contract.md)·[메타데이터](quiesce102-verification.json)를 따른다. 기존100 builder를 재사용해 obj-nes-100 등 역사적 출력 이름이 남지만 실제 VERSION은102다. 비공개 동결 증거가 필요한 verifier를 공개 clone 단독 재현으로 주장하지 않는다. 완료 finalizer/044–102 archive는 다시 실행하거나 수정하지 않는다.
