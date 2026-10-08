# NES 현재 인계 — RTC 종료 보호099

실제 RTC의 RSF·INITF 무한 대기를 진단 전용 시간·반복 한도로 제한했다. 단위18·실제 main/FatFS 통합12경우와 대조4개, 원본 반례 및 같은 ARM 링크를 확인했다.

PR48 병합 `4ea53133ff225c332d10cb2739b115c39892b214`를 확인했다. 현재 `codex/nes-rtc-guard-099`. [099 결과](../../analysis/RTC099-RESULT.ko.md), [재현 계약](../../docs/nes-rtc099-contract.md)을 먼저 읽는다. PR은 사용자가 병합하며 한국어 제목과 작업 목표·작업 내용·작업 결과 세 절을 유지한다.

## 다음 작업과 완료 조건

1. 099 ARM/097 이미지를 기준으로 실제 SRAM→fpga_spi→STM32 SPI 및 UART/printf/타이머/CIC/RESET 보호를 현재 main/load_rom과 연결한다. 최초 오류 이후 하위 IO 차단을 확인한 뒤 최종 파일 쌍·044 복원·외부IO/공통고장·관측 가능한 제한 실기를 확정한다.
2. RTC는 이제 실제 함수로 연결했다. 남은 SRAM/SPI/UART/printf/CIC/RESET/GBC disarm/시간·핀·카드 모델을 실제 보호로 오해하지 않는다. main은 오류 뒤에도 CFG/status 등 일부 함수를 호출하므로 하위 차단을 검사한다. 현재 main의 두 구간과 전체 load_rom을 그대로 재사용하고 상위 흐름을 새로 조립하지 않는다. 첫부팅/이후 메뉴 루프는 아직 제외다.
3. 098 메뉴 주소0xC00000 두 검사 수정 유지. 해제 후 autoboot 읽기가 있으므로 IRQ/진단 소유권은 postrelease 검사까지 유지한다.099 report-time RTC 실패는 오류16·저장0바이트·해제0회이며 TXT를 항상 남길 수는 없다. 모델 보완 없이 반복 실기 패키지를 보내지 않는다.
4. 동일097 ASM/CF86 이미지는 이미 준비됐다. 재fit/ASM은 소스/요구 변경 없으면 반복하지 않는다. 새 production C 변경 때만 ARM을 갱신하고 실제 host 소스·ELF 호출 일치를 확인한다. 외부IO 및 두 클록 정지+lockedHIGH CE9us 반례는 미해결이다.

## 완료와 고정 입력

- 099 RTC 수정은 `stm32f4xx/rtc.c`, `nes_diag_runtime.h`의 추가 오류17, VERSION 세 파일만이다. 진단 비활성 GBC/일반 RTC 동작은 보존했다. 로컬100tick/100,000poll 및 기존 공유 예산을 검사하며 오류/예산 초기화나 재시도를 하지 않는다. INITF 실패 후 INIT 해제/WPR lock만 허용한다.
- 최종 unit05=18, main04=9, fat32-96-01=3, negative-poll/time/cleanup/fault01=4, negative-baseline01=원본 비종료 반례. ARM01 181200바이트 SHA a37e782bc168e36a9147881e828452ac2d1fa81b3a0a027df68391cdfd23c67a, ELF64ba4a49e67e66045ba0efbc27394662d55461558469dca54251b32b3006b58f. VERSION CF86-RTC099, 표식/보고 파일/세션094 유지. compile-only/설치false.
- RTC와 FatFS 파일 시간도 실제 함수가 실행된다. 레지스터·BITBAND·시간은 모델이며 물리 MCU/MMIO 고장 종료 보장이나 WCET가 아니다. 보고서 공유 한도는 로컬RTC 한도보다 먼저 끝날 수 있고 오류16이 정상적인 실패 결과다. 최초 오류 이후 SD명령/에지/CF86프레임/구성바이트가 늘지 않는 것을 확인했다.
- 097 고정086 fit ASM RBF510856 SHA6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1, packed219453 SHA6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805.071encoder/no089terminalFF. 사용자base의 legacyEOFpadding/HDL출처 미증명 유지. 정확한044복원169056 SHA1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b.
- private `probes/nes-rtc099/evidence`와 공개 `analysis/rtc099-verification.json`/verifier가 최신 근거다. 완료한 finalizer 재실행/044–099 archive 수정 금지. 초기 COFF/ABI/모델 기대값/주입 위치 실패, Make 의존성 재시도, checker CRLF 실패를 보존했다. 초기 실패 일부 driver snapshot 부재도 결과 문서에 명시했다. 공개 driver의 마지막 baseline 옵션 추가는 이전 정상 시험 경로를 바꾸지 않았다.

## 실기·제품 목표

084 저장/재읽기/화면/044복원/메뉴/GBC,092 클록 활동/TXT/복원 PASS를 유지한다. 추가 부품·LED·분해·PC USB·이미 받은 파일 질문을 반복하지 않는다. 외부 실기는 사용자가 패키지를 실행하고 로그를 보내는 방식이다.

준비도4완료/7부분/1미완료·설치false. 전체 코어 자원/DMC/IRQ/영상/입력/음향과 SMB3 실행은 별개다. 첫 게임 Super Mario Bros3(J), mapper4, PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49.80/96KiB 진단을384KiB 지원으로 쓰지 않는다. ROM/바이너리/사용자 자료/라이선스는 Git에 넣지 않는다.
