# NES 현재 인계 —108 CSS/NMI 종료 구현

진단 세션에 한정한 CSS/NMI 고장 종료 경로를 구현했다. HSE 고장 시 직접 RESET·nCONFIG·SPI를 정리하고 복귀하지 않으며, 정상 종료 때 CSS를 해제한다. 실제 C 호스트63건/보호 제거 대조4건과 최종 ARM 벡터·종료 경로 검증을 통과했다.

작업 의미: 실기 디버깅 기반의 고장 종료 기능 구현이다. 이전 미처리 NMI 루프에 없던 진단 소유권·고장 고정·직접 출력 차단을 추가했다. 게임 실행 배선이나 SMB3 호환성을 구현한 것은 아니다.

PR57 병합e3b0f4853698995dcb8b8327d933a643a9d28951, head3f1dbfac 포함 확인. 현재codex/nes-css-nmi-108. [108 결과](../../analysis/CSS108-RESULT.ko.md), [계약](../../docs/nes-css108-contract.md)을 먼저 읽는다.

## 다음 행동

다음은108을 기존104/097의 전체 SD·FatFS·main/menu 호스트 경로에 연결하는 통합 회귀다. 진입 거부·정상 반환·복구 중 고장·정상 종료 경계의 실제 CSS 연결을 검증하고, 모델 핀과 실제 PA0/PA1/PA4 매핑 차이를 명시적으로 해결한다. 108 ARM을105 파일 조합에 반영하는 것은 이 회귀 후 한 번만 한다. E1 전기적 범위와 E2 감지부터 CE HIGH까지의 최악 지연/고장 범위 판단은 여전히 별도다.

- 새 CSS begin은 USB IRQ/RESET/CF86/diag begin 뒤 첫 f_open 전에 호출된다. 기존 CSSON이나 CSSF를 인수·clear하지 않고 거부한다. 정상 leave가 먼저 CSS end를 검사하며 fault일 때 observer/IRQ 복구로 넘어가지 않는다.
- NMI에서 일반 nes_return_fail/observer/printf/SD/timer 호출 금지. fault108은 volatile32bit; nes_return_failed OR에 연결, reset/leave로 해제 안 됨. 정상 종료 후 claimed 이력은 남겨 늦은 CSSF NMI도 차단한다. 비활성 non-CSS는 원래 loop. RESET은 방향 제어/기존type보존이며 open-drain을 가정하지 않는다.
- units04 실제C63건, negative4, arm-check04. 최종ARM183220 SHA394c1c442b6d767b5d41f891151eed12e82954b624a0b53a346dad8dc948692c; ELF98d53c9e64f98d815983eb9b9ec5765fe8862389b85cef01e7e68f0f27829db3. VERSION CF86-CSS108. 실제vector0x08018d31→NMI0x08018d30; stop15store명령(조건부fault1+MMIO14)/0calls/DSB3/ISB2. 실행시간 보장 아님.
- 실제GPIO/CSS/NVIC는 모델, 전체 instruction preemption/CPU버스정지/전원고장 미검증.104/097 native 전체세션에108CSS를 붙인 실행은 아직 없다. 기존104 전체native PASS를108전체PASS로 쓰지 않는다.
- E1/E2/실기/설치false. high-Z는CE HIGH보장아님. 양클록정지 lockedHIGH CE9µs 반례 유지. [107 후속 근거](../../docs/nes-board107-actions.ko.md)와 [106 관측 초안](../../docs/nes-trial106-observation.ko.md)을 사용한다.600초 관측은사람의한도.
-105 pair는104 ARM의역사적11역할조합.097ASM/086fit/정확044복원 재사용. 같은FPGA를다시빌드하지않는다. 제품094marker/TXTcandidate 유지; PREPARED_RESET_HELD는release아님. NMI뒤새TXT·자동메뉴반환을약속하지않는다.
- 실패보존: units01DLL623, 자동승인검토timeout1회재시도성공(안전거부아님), units02과다경계case122, 초기ARMchecker괄호/CR/공백, Make초기dependency/retry. 완료108finalizer/archive044–108재작성금지. 공개CSS파일/host/checker 해시는108metadata로고정.

## 사용자 규칙과 전체 목표

한국어 PR 제목, 작업 목표→작업 내용→작업 결과→작업 의미 네 절. 사용자가 머지한다. 실기는 외부에서 패키지→실행→로그 반환. 알려진 부품/LED/분해/PC USB/성공한 저장·클록 질문 반복 금지.

084저장/메뉴/GBC·092클록/TXT/복원PASS 유지. 준비도4완료/7부분/1미완료. 첫 게임 SMB3(J) mapper4 PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49.80/96KiB 진단은384KiB 게임지원 아님. ROM/바이너리/미디어/라이선스/private경로 Git 금지.
