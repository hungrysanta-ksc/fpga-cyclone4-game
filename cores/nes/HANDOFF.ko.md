# NES 현재 인계 —103 공유 오류 관측

공유 오류가 확정되면 observer에서 LED·틱 조회·UART보다 먼저 RESET/USB 보호와 SPI·GPIO 차단을 수행한다. 이후 UART 출력/flush도 대기 없이 생략한다. 보고서 오류만 있는 복구 경로는 유지한다.

PR52 병합03f2ac3815e01d8a4b8be88b3fc1d749762a83ac/head37421a1 포함 확인. 현재 codex/nes-fault-observer-103. [103 결과](../../analysis/OBSERVER103-RESULT.ko.md)·[103 계약](../../docs/nes-observer103-contract.md)을 먼저 읽는다. PR은 사용자만 병합하며 제목 한국어·작업 목표/작업 내용/작업 결과3절을 지킨다.

## 바로 다음 작업

1. 실제 timer의 delay_us/delay_ms/nes_return_delay, SysTick/LED/CIC와 RESET 감지 경로를 현재 main에 연결한다. 공유 오류가 기록되기 전의 대기와 IRQ 전제를 검증한 뒤 최종 ARM/FPGA·044 복원 조합, 외부IO/공통고장·관측 가능한 제한 실기를 확정한다.
2. 이번 보장은 shared fault 래치→실제 observer→정리 함수 경로다. 하드웨어 고장부터 오류 감지 시간·진행중 printf의 IRQ 선점·전체 worst-case MCU시간을 완료로 쓰지 않는다. timer/CIC 원문은 이미 ARM에 있으나 호스트 main에서는 모델이다. 새 반복 storage/clock 시험 대신 남은 실제 하위 함수를 연결한다.
3. 실제 timer.c의 nes_return_delay는 local tick/poll 제한 뒤 nes_return_fail, delay_us/ms는 active 때 그 helper로 분기한다. SysTick_Handler는 LED/sdn_changed/CIC 초기화를 부른다. CIC get_cic_state는 고정 샘플 반복과 printf를 사용한다. 해당 몸체/IRQ 영향·RESET 입력을 아직 실행 검증하지 않았다. sleep_ms 경로의 진단 도달 여부도 확인한다.
4. active&&nes_return_failed 조건을 report.error로 바꾸지 않는다. 전자는 비가역 SPI reset을 허용하는 공유 fault이고 후자는 복구 가능한 보고 오류일 수 있다. UART timeout은 dropped만 올리며 새 shared fault로 승격하지 않는다. UART inactive의 legacy 동작도 유지한다.
5. helper102는 그대로12stores/3DSB이며 CS HIGH→SCK/MOSI LOW GPIO/MISO input→CR2zero/SPEclear/SPI1RST 유지한다. observer와 blocked에서 반복할 수 있다. 오류 이후 재설정/추가 IO/자동 SD보고/메뉴 복원 금지. SysTick LED나 다른 IRQ 전체를 막았다는 뜻은 아니다.
6. 생산코드가 바뀌지 않으면103 ARM과097 ASM을 재사용한다. 정확044복원과 외부IO/공통고장/관측절차가 끝나기 전 설치false. PA0 LOW latch/CPU·APB·GPIO 실행/foreground 소유권 전제 및 두클록정지lockedHIGH CE9us 반례를 유지한다.

## 최종 증거와 실패

- unit03=17, main04=18 + fat32-96-02=3, stall02=16. control-baseline/observer/uart/flush/scope/order-02 총6 예상 실패. 제품 별도 모듈 printf까지 연결한 최종 통합을 사용한다.102 pins1024·101 phases336은 과거 증거이며 새 실행이 아니다.
- ARM01 182632 SHA `246310901db820670e8558680dd40aa137706fc282c542c2e00f50baef845934`; ELF `b576265684aa5826073300dab44171e9e16f5b5af09ca0640c3b8e2301ff3b03`. 최종check103-final.json, 실제 active/shared 분기/출력 이전 반환과 MMIO16 해석 PASS. 생산 platform/UART/VERSION만 변경, main/runtime/nativeSD/RTC/SPI/printf/timer/CIC/GBC 보존. 새RTL/fit/STA/ASM/Questa/실기/설치패키지 없음.
- unit01은 fault 식별자 문자열 치환이 SD 변수 이름까지 바꿔 컴파일 실패했다. 단어 경계 치환으로 수정했다. main01은 MinGW stdio의 printf 선언과 이름 매크로 충돌, main02는 inactive LED 복원도 active 전용 IO로 취급한 모델 assertion 실패였다. 헤더 순서와 LED 모델만 수정했다. 초기 order 대조는 앞선 printf가 새 UART 보호에 막혀 정상 통과했으므로 보호 제거 대조로 채택하지 않았다. 최종 대조는 LED/tick 호출을 차단 앞에 옮겨 순서 위반을 검출한다. main03/첫 FAT32·stall은 일부 별도 모듈 printf가 libc로 연결된 중간 시험이며 최종04/02는 제품 모듈 전체 printf를 연결했다. Make 최초 의존성 실패·재시도와 기존 C 경고를 보존했다. 비승격 objdump 실행은 Windows DLL 재할당 오류로 실패했고 같은 바이너리를 승인된 범위의 실행으로 읽었다. 첫 문서 finalizer는 동결 이전에 한글 README를 cp949로 읽어 실패했다. UTF-8을 명시한 뒤 완료했으며 그 이전 세 문서만 재작성했다. 자동 승인 거절·라이선스 오류는 없었다.
- 완료finalizer/044–103archive 수정 금지. formatter/LED/전달 모델과 실제 제품 몸체를 구분한다. UART 레지스터는 모형이며 PIN/wire/baud/MCU 시간 미검증이다.
-097 동일086fit RBF510856 SHA6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1/packed219453 SHA6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805,071encoder/no089terminalFF. 받은base legacyEOFpadding/원본HDL동등성 미증명.044복원169056 SHA1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b.

## 실기와 게임 목표

084 저장/재읽기/화면/044복원/메뉴/GBC,092 클록활동/TXT/복원 PASS 유지. 부품·LED·분해·PC USB·기존 저장/클록/복원 질문/시험을 반복하지 않는다. 사용자가 외부 실기에서 패키지 실행→로그 반환하는 방식이며 오류 뒤 새 화면/TXT를 약속하지 않는다.

준비도4완료/7부분/1미완료·설치false. SMB3(J) mapper4·PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49 첫 목표 유지.80/96KiB진단은384KiB지원이 아니다. CPU/PPU/APU/DMC/IRQ/영상/입력/음향 실기 및 mapper 확장은 별도. ROM/바이너리/사용자자료/라이선스 Git 금지.
