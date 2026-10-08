# NES 현재 인계 —109 CSS 통합과 파일 조합

ARM108의 실제 CSS 진입·고장·해제 경로를 SD/FatFS·설정 전송·메뉴 복구 호스트 세션에 연결했다. 통합38건과 보호 제거 대조4건을 통과했고, ARM108/기존CF86/정확044복원11역할 조합을 새로 고정했다.

작업 의미: 실기 디버깅 기반의 통합 검증과 배포 준비다. 독립 시험에 머물렀던 고장 종료를 기존 전체 진단 흐름과 결합하고 파일 혼합을 검출한다. NES 코어 배선·게임 호환성 구현은 아니다.

PR58 병합33b19045929e3bdd316926b7f333da75f7bbe230, head3870d87f 포함 확인. 현재codex/nes-css-integration-109. [109 결과](../../analysis/CSS109-RESULT.ko.md)와 [계약](../../docs/nes-css109-contract.md)을 먼저 읽는다.

## 다음 행동

다음은 변경된 고장 경로를 기준으로 E1 전기적 조건과 E2 고장 범위·차단 지연의 미확인 항목을 판정하는 것이다. 근거가 없는 상한을 만들지 말고, 보장 가능한 범위와 제한 실기에서 제외할 고장·데이터 손실·수동 복원 조건을 구체적으로 구분한다. 그 판단 전에는 설치·실기 시작을 승인하지 않는다. 같은 통합 시험·ARM/FPGA 빌드·파일 조합을 변화 없이 반복하지 않는다.

-108 actual CSS5개 입력을104 전체 진단 host 흐름에 연결. 최종 normal02 20/fat32-96-01 3/fault03 15/negative4 PASS. 전체 MCU main/부팅/ARM instruction interleaving·물리 시간은 아님. main 메뉴 두 구간/load_rom 및 실제 lower C 경계를 보존.
- 실제 autoconf PA1 nCONFIG/PB8 READY 대조. 이전 PA6/PA5 모델 교정, MISO는PB4만 갱신. PA1출력/HSE/GPIO clock 등 부팅 상태 모델 전제, 진입 거부3개 별도검사. fault01 productprintf 억제와fault02 APB2RSTR 초기전제 실패,normal01중간PASS 보존.
-108 펌웨어 그대로183220 SHA394c1c442b6d767b5d41f891151eed12e82954b624a0b53a346dad8dc948692c. VERSION CF86-CSS108,ELF98d53c9e64f98d815983eb9b9ec5765fe8862389b85cef01e7e68f0f27829db3. 새ARM/RTL/fit/ASM/Questa/실기 없음.
- 새11역할 pair109 manifest 788dca6e5546456340ef03579b91a46a0496724a899432df389d48f0c69aae69,pair01/정상1+거부23.097ASM/086fit/정확044복원 재사용.105pair는104 ARM의 역사적 조합으로 보존. 같은조합 재포장PR 금지.
- NMI12지점은 실제C 종료/기록된 후속IO 없음 검증. 모델13CSSwrites와ARM15store명령 구분. fault는legacyreset으로 지워지지 않으며 nCONFIG LOW로 설정을 잃는다. UART/SD/시간/일반observer를 NMI에서 호출하지 않는다. 정상해제 후 claimed 유지.
- E1/E2/8µs/install/trial/start=false. 양클록정지lockedHIGH CE9µs반례 미해결. [107 근거목록](../../docs/nes-board107-actions.ko.md)/[106 판단](../../docs/nes-trial106-decision.json) 재사용하되106의105pair참조를현재109와구분.600초는사람의관측한도.
-094 표식/TXT 유지,PREPARED_RESET_HELD는release증명아님. NMI후새TXT·자동메뉴반환 약속금지. 완료109finalizer/archive044–109재작성금지. no approvalreview rejection.

## 사용자 규칙과 전체 목표

한국어 PR 제목, 작업 목표→작업 내용→작업 결과→작업 의미 네 절. 사용자가 머지한다. 실기는 외부에서 패키지→실행→로그 반환. 알려진 부품/LED/분해/PC USB/성공한 저장·클록 질문 반복 금지.

084저장/메뉴/GBC·092클록/TXT/복원PASS 유지. 준비도4완료/7부분/1미완료. 첫 게임 SMB3(J) mapper4 PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49.80/96KiB 진단은384KiB 게임지원 아님. ROM/바이너리/미디어/라이선스/private경로 Git 금지.
