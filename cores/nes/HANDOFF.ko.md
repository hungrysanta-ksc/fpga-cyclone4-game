# NES 현재 인계 —102 최종 오류 정지

최종 오류 정지 함수에 CS 해제→GPIO 분리→SPI1 리셋 유지 경로를 연결했다. 핀/레지스터 시작상태1024·실제 main 통합21·보호제거6·원본반례1·ARM MMIO16해석을 통과했다. 최초 오류부터 정지 진입까지의 지연과 실기 전기적 효과는 미검증이다.

PR51 병합 `bedfad5bf53d8c94a0da51f4c50e9406dbd4f8ed`와 head1f10e4dc 포함 확인. 현재 `codex/nes-spi-quiesce-102`. [102 결과](../../analysis/QUIESCE102-RESULT.ko.md)·[102 계약](../../docs/nes-quiesce102-contract.md)을 먼저 읽는다. PR은 사용자만 병합, 한국어 제목과 작업 목표/작업 내용/작업 결과 세 절을 유지한다.

## 다음 우선 작업

1. 실제 UART/printf·observer·timer·CIC와 오류 전달 경로를 연결해 최초 오류부터102 정지 함수 진입까지의 지연/종료를 검증한다. 이후 최종 ARM/FPGA·044 복원 조합, 외부IO/공통고장과 관측 가능한 제한 실기를 확정한다.
2. 102 정리는 **nes_diag_blocked 진입 이후**의 보장이다. `nes_return_fail`/nativeSD 오류가 observer의 printf를 먼저 부르므로, 최초 오류 시점부터 핀이 정지됐다고 쓰지 않는다. 실제 UART/printf·observer의 대기/재귀/공유예산과 하위 timer/CIC 반환을 다음에 연결한다. 정상 수신/보고에 필요한 recoverable 오류와 공유 terminal 오류를 구분하고, 무조건 모든 report.error에서 peripheral reset을 걸지 않는다.
3. 정리 helper는 CS HIGH→SCK/MOSI latchLOW+GPIO out/MISO input→CR2=0/SPE=0/RCC SPI1RST 유지,12writes/3DSB/대기없음이다. RESET/USB 보호 뒤 표시 전에 호출한다. 부분 명령은 폐기하며 자동 재개/STOP전송/SD로그/메뉴복원을 강행하지 않는다. Cortex/APB/GPIO 고장이나 pad delay는 이 모델로 닫히지 않는다.
4. 실제 snes_reset 출력 쓰기는 연결했지만 RESET 입력감지/콘솔/초기화 전체는 모델이다. PA0 LOW latch는 기존 snes_init 전제. 다른 IRQ/DMA가 SPI와 핀을 동시사용하지 않는 진단 소유권도 전제다. CR2 disable은 이미 발행된 DMA 버스 요청 전체취소를 뜻하지 않는다.
5. 바뀌지 않으면102 ARM과097 ASM을 재사용한다. 새 production C가 바뀌면 원문/ARM 연결을 다시 검증한다. 최종쌍/정확044복원/외부IO/두클록정지lockedHIGH CE9us/관측절차 전 installable=false. 사용자에게 기존 저장·클록·복원·부품·LED·분해·PC USB 질문/시험을 반복하지 않는다.

## 완료·증거·실패

- 생산 변경은 nes_diag_platform.c와 VERSION CF86-STOP102. SPI101 TXE→BSY/공유예산/RTC099/CS100/main/native/CF86/GBC 소스 보존.102 helper는 최종정지 전용이며 범용 SPI 오류마다 즉시 호출되는 것이 아니다.
- 최종 pins01=1024, main02=18/fat32-96-02=3, negative-cs/clock/miso/reset/order/call01=6 + baseline01=1. ARM MMIO16초기값에서12stores/배리어3,9,12 비교. main 정상3/오류18은 실제 blocked 호출/핀상태 확인. 기존101위상336은 동일SPI소스의 과거 증거이며 새 실행이 아니다.
- ARM01 182556 SHA `4d1c504b8ba2c343180d1a3265a79773e1acd3c51b160dab09e347b9b7ef325f`; ELF `a29fb0bdd0a14375304bddd55023400a55ae03a279ed0e3e0843bc3c654dc25b`. 고정100builder의 obj-nes-100/보조 이름은 역사적 이름. 새RTL/fit/STA/ASM/Questa/실기/설치패키지 없음.
- 최초 main01/fat32-96-01은 호스트 include순서 컴파일 실패, 최종02에서 수정. 생산코드/ARM변경 없음. Make dependency재시도도 보존. 완료finalizer/044–102archive 수정금지. 실제전체observer/UART/timer/CIC/부팅/메뉴루프 미완료.
- 098 메뉴주소0xC00000 수정·099 RTC 오류17·094 sticky session 유지. 보고서 RTC 실패0바이트 가능; status 오류는RESET해제1회후재보호할 수 있음. 준비TXT를 최종메뉴성공으로 쓰지 않는다.
-097 동일086fit RBF510856 SHA6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1/packed219453 SHA6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805,071encoder/no089terminalFF. 사용자base legacyEOFpadding/원본HDL동등성 미증명.044복원169056 SHA1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b.

## 실기·게임 목표

084 저장/재읽기/화면/044복원/메뉴/GBC,092 클록활동/TXT/복원 PASS 유지. 외부 실기는 사용자 패키지실행→로그반환 방식. SPI가 정지되면 화면/TXT를 새로 출력할 수 있다고 약속하지 않는다.

준비도4완료/7부분/1미완료·설치false. 첫 게임 SMB3(J),mapper4,PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49.80/96KiB진단은384KiB지원이 아니다. 전체 코어자원/DMC/IRQ/영상/입력/음향 별도. ROM/바이너리/사용자자료/라이선스는 Git 금지.
