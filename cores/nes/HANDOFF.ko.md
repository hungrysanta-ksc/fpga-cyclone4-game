# NES 현재 인계 —107 보드 근거와 고장 종료 설계

공개 회로도의 세대 불일치와 MCU·FPGA의 공통 HSE 의존성을 확인했다. 현재 NMI 벡터는 미처리 예외 루프를 가리킨다. 전기적 근거 확보와 고장 차단 구현에 필요한 항목을 분리했다.

작업 의미: 실기 디버깅 기반의 설계 검토다. 잘못된 회로도나 MCU 타이머를 독립 보호 근거로 사용하는 경로를 배제했다. 코어 배선·게임 기능·새 실기 성공을 추가한 작업은 아니다.

PR56 병합3578defda4d5ed7104b1aaf765afe57fd675b854, 이전 head43db374de95b0218661b66e0a0f0253d60b066f6 포함을 확인했다. 현재 codex/nes-board-evidence-107. [107 결과](../../analysis/BOARD107-RESULT.ko.md)와 [후속 계약](../../docs/nes-board107-actions.ko.md)을 먼저 읽는다.

## 다음 행동

다음은 진단 세션에 한정한 CSS/NMI 고장 종료 경로의 구현·호스트/ARM 검증이다. 정상 GBC 경로와 공유 fault를 보존하고, HSI 전환 후 SD/UART/메뉴 복구를 시도하지 않도록 한다. 이 기능의 고장 범위와 nCONFIG→패드 비활성→CE HIGH 지연을 분리해 기록한다. E1의 보드 전압·부하·배선 근거와 E2의 8µs 상한은 별도 미결이며, CSS 추가만으로 시험을 승인하지 않는다.

- 공개 upstream cf7e21d7 KiCad192개 blob은 Pro Rev.D 회로도가 아니다. 특히 RevD 폴더는2011년 시트 Rev C다. 같은 revision 글자를 근거로 전원/풀업을 가져오지 않는다.
-104 SYSCLK=HSE PLL, MCO1 PA8=HSE. TIM2는 별도 발진기 아님. clock_init에 CSS enable 없음; 실제 부트 후 CSS 상태 측정은 아님. NMI/미처리 예외는 같은0x0800c60e 루프. CSS를 켜기만 하는 수정 금지.
-086 fit03 QSF/board.pin의 CLKIN M2, CE G16/J16, SNES_SYSCLK A9는 설정·배치 근거이며 배선/전압/지연 실측 아님. PA1 PROG_B→nCONFIG는 후보이며 high-Z→CE HIGH 시간을 생략하지 않는다.
- E1/E2는 미결, installable/trial/start=false. 두 클록 정지 lockedHIGH CE9µs 반례 유지. [106 판정](../../docs/nes-trial106-decision.json)과 [관측 초안](../../docs/nes-trial106-observation.ko.md)은 현재에도 유효하다.600초는 사람이 기다리는 한도이며 펌웨어/8µs/SD완료 보장 아님.

## 재사용할 근거

-107은 소스·심볼·핀·Git 객체 조사.14입력,192blob. 최초 checkout 줄바꿈 비교 실패 보존, Git 객체 원본 비교로 완료. 새 제품C/RTL/ARM/fit/STA/ASM/Questa/실기/설치 패키지 없음. 완료107 audit/finalizer 및044–107 archive 재작성 금지.
-105 pair11역할, 정상1/거부23, manifest bba0316dc6160c107edab5a41b6ea32e11b74e3fc227f23b69e967a79dbc797a. 새 소스가 바뀐 역할만 이후 갱신한다.
-104 ARM182640 SHA7f0601cc24b3fc7288afd4b2531fffaf3aca0c67300c5c4d2bb9aa57d4ac1cca, ELF1eeeb57746883eb96732f30b95b5e742356a383f5a7e63a3de5c9c7529f8f45f.103 sharedfault와report.error 구분/102차단12writes·3DSB/101TXE→BSY·공유예산 보존. NMI에서 기존 observer를 무검토 호출하지 않는다.
-097 동일086fit RBF510856 SHA6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1, packed219453 SHA6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805. 정확044복원169056 SHA1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b. 받은base legacy EOF/HDL동등성 미증명 유지.
- 제품104는094 표식/TXT candidate 유지. 저장TXT는PREPARED_RESET_HELD, released는UARTonly. 새TXT/메뉴/복원은 따로 판정. 오류뒤 추가IO·보고 강제·자동 재시도 금지.

## 사용자 규칙과 전체 목표

한국어 PR 제목, 작업 목표→작업 내용→작업 결과→작업 의미 네 절. 사용자가 머지한다. 실기는 외부에서 패키지→실행→로그 반환. 알려진 부품/LED/분해/PC USB/성공한 저장·클록 질문 반복 금지.

084저장/메뉴/GBC·092클록/TXT/복원PASS 유지. 준비도4완료/7부분/1미완료. 첫 게임 SMB3(J) mapper4 PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49.80/96KiB 진단은384KiB 게임지원 아님. ROM/바이너리/미디어/라이선스/private경로 Git 금지.
