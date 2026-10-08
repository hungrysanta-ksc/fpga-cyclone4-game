# NES 현재 인계 —104 타이머·IRQ 통합

실제 timer·SysTick·LED·CIC·RESET 감지를 메뉴 복귀 경로에 연결했다. SysTick의 카드 상태 변경 알림이 진단 중 전역 printf 상태에 재진입하는 문제를 수정했다.

PR53 병합3dab89e66efff89e30cd777a5348a27c45d8d2bc/head e8c63e97a9e767a0f388d1bf615a62b4f41eab8b 포함 확인. 현재 codex/nes-timer-irq-104. [104 결과](../../analysis/TIMER104-RESULT.ko.md)·[104 계약](../../docs/nes-timer104-contract.md)을 먼저 읽는다. 제목 한국어, PR 본문은 작업 목표/작업 내용/작업 결과3절. 사용자만 병합한다.

## 다음 작업 순서

1. 104 최종 ARM과097 동일 fit FPGA·정확044 복원 파일의 조합을 고정하고, 외부IO/공통고장 및 정상·실패 관측 절차를 검토해 제한 실기 가능 범위를 결정한다. 다음 단계의 중심은 파일 조합과 실기 진입 판단이다. 이미 통과한 타이머·저장·클록 검사를 반복하는 대신 남은 가정을 좁힌다.
2. ARM104/CF86의097 ASM/기존 base·menu/정확044 복원 해시를 한 manifest로 대조한다. 제품 소스 변화가 없으면 ARM/fit/ASM을 재생성하지 않는다. 받은base의 legacyEOFpadding과 원본HDL 동등성 미증명은 유지한다.
3. 외부 PSRAM 타이밍/비동기 차단/공통고장 정책을 검토한다. 두클록정지/lockedHIGH CE9us 반례는 미해결이다. CPU/APB/GPIO 동작·PA0LOW 초기 latch/foreground 소유권 전제도 남아 있다. 부분 FPGA 명령 롤백 또는 절대 물리 보호를 주장하지 않는다.
4. 정상 완료와 오류 정지를 사용자가 구분할 관측절차를 마련한다. 공유 오류 뒤 새 화면/TXT 보장은 없다. 실기는 외부에 있으며 패키지 전달→사용자 실행→로그 반환 방식이다. 아직 설치false이며 이 단계에서 자동 배포하지 않는다.
5. 그 후384KiB/mapper4·IRQ·CPU/PPU/APU/DMC·영상/입력/음향으로 진행한다. SMB3 첫 실기는 타이틀→월드맵→1-1 플레이 범위이며 전체 호환성 완료로 쓰지 않는다.

## 이번 코드와 증거

- sdn_changed의 `printf("ch ")`만 active 진단에서 생략한다. 카드 상태/변화 플래그는 그대로 갱신한다. 생산 변경은 nativeSD+VERSION 두 파일. legacy inactive printf 재진입까지 해결한 것이 아니다.
- 실제 timer/SysTick/빈 weak hook/LED/CIC/RESET 감지를 기존 실제 main2구간/load/RTC/SRAM/SPI/FatFS/observer/printf/UART에 연결했다. TIM2/GPIO/IRQ 스케줄/시간은 모델이다. 전체 main/모든 IRQ 선점/MCU 실시간 증명이 아니다.
- 최종units04=60,main02=20,FAT32-96-02=3,timer-ticks/frozen-01=각1; negative-baseline/timer-bound/timer-cleanup/card-state/reset-invert/cic-threshold-03=6 예상 실패. 정상5/기존오류18/추가timer오류2. ARMcheck104.json PASS.
- ARM01 182640 SHA `7f0601cc24b3fc7288afd4b2531fffaf3aca0c67300c5c4d2bb9aa57d4ac1cca`; ELF `1eeeb57746883eb96732f30b95b5e742356a383f5a7e63a3de5c9c7529f8f45f`.103 timer/CIC/LED/RESET/SPI/RTC/observer 원문 유지. 새RTL/fit/STA/ASM/Questa/실기/설치패키지 없음.
- sleep_ms는 검사한 main/load/helpers/reliable 추출 구간에서 호출되지 않는다. 다른 legacy/GBC/USB 사용과 전체 호출 그래프는 별도이며 모든 sleep이 bounded라고 쓰지 않는다. SysTick LED는 계속 실행한다.
- 초기 단위/통합 결과와 대조를 모두 보존한다. card-state-01 대조는 disk_state가 이미 DISK_CHANGED여서 잘못 통과했다. DISK_OK로 시작해 실제 갱신 효과를 확인하도록 수정한 최종03은 예상 실패한다. units02는 비승격 MinGW 실행의 WinError623 DLL 재할당 오류로 컴파일을 시작하지 못했고 범위 지정 실행으로 통과했다. 최종 timer 정지 통합을 추가하면서 단위용200000회 harness watchdog을 단위에만 적용했다. 제품 wait의 tick/poll 예산은 바꾸지 않았다. 중간01/02와 최종03/04의 실행 driver/model 차이를 구분한다. ARM Make 최초 의존성 실패/재시도와 기존 경고도 보존한다. 자동 승인 거절·새 라이선스 오류는 없다.
- 완료finalizer/044–104archive 수정 금지. 하위 모델을 실제 함수 대신 다시 사용하지 말고 현재 실행 증거의 경계를 유지한다.103 sharedfault/report.error 구분,102 차단12writes/3DSB,101 SPI TXE→BSY 순서/공유 예산 유지. 오류 뒤 SPI reset 해제·자동 IO/보고·예산 재시작 금지.

## 고정 기준

097 동일086fit RBF510856 SHA6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1, packed219453 SHA6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805.071encoder/no089terminalFF. 정확044복원169056 SHA1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b.

084 저장/재읽기/화면/044복원/메뉴/GBC,092 클록활동/TXT/복원 PASS. 부품·LED·분해·PC USB·동일 저장/클록/복원 질문을 반복하지 않는다. 이전103와102 근거는 해당 결과문서로 추적한다.

준비도4완료/7부분/1미완료·설치false. SMB3(J) mapper4·PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49 첫 목표 유지.80/96KiB진단은384KiB지원이 아니다. ROM/바이너리/사용자자료/라이선스 Git 금지.
