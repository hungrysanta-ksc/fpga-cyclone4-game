# NES 현재 인계 —112 단계 로그 개선판 결과 대기

111의1분 이상 로딩/리셋 미복귀/전원 재투입 메뉴 정상/로그 없음 관측을 반영했다.112는 단계 로그를 추가한80KiB 개선판이며 실행 패키지와044 복원이 준비됐다. 새 실기 결과를 기다린다.

PR61 head `8f43431c21f1698c30e65aba1b990e207c48c5f5` 기준, 확인 시점 open/unmerged다. 현재 `codex/nes-progress-log-112`. [112 결과](../../analysis/CHECKPOINT112-RESULT.ko.md) · [실기 안내](../../docs/nes-checkpoint112-instructions.ko.md).

## 다음 행동

112 패키지로80KiB 1회 실행, 중간 리셋 없이 최대600초 관측 후 nes-progress-112.txt와nes-verify-last-094.txt 또는 없음/0바이트, 실제메뉴/시간/044복원 후메뉴·GBC를 받는다. 영상 불필요. 마지막 기록을 기준으로 다음 최소 실험을 정한다.

- 사용자111 관측은600초 미만 중단으로 영구 멈춤을 확정하지 않는다. 전원 재투입 메뉴 정상과044 복원/GBC 성공은 다르다. 실제 소스113초는 통신 대기 하한이며 SD/구성 등 추가,600초는 사람의 관측 한도다. 호스트174초 등은 보드 ETA로 쓰지 않는다.
-112 ZIP588448바이트 SHA `91a9c9cb9d1ec084be7725b3d2a7c80176c5eddb1d6f0b947d4375a2072b0889`,12항목. `01-TRIAL-SD-ROOT`와`02-RESTORE044-SD-ROOT`를 분리 적용. 표식 `NES VERIFY 094 80.nh1`은0바이트 정상. 새 ARM `CF86-LOG112`184452바이트 SHA `ac778c02d7561f2813c0930a8fecd3af67b4ca886455a214b068a3fbbb40fb16`.097CF86/base/menu/자체80KiB/정확044는109 역할 해시 유지.
- `nes-progress-112.txt`는512바이트 순차 append,각write/sync/close,정상80에서33기록. 시작/완료와적재·비교16KiB,elapsed_ms. MENU_PREPARED와094 PREPARED 모두 실제RESET해제/화면 증명 아님. CS유휴/전경 단계 경계에서만로그; observer/ISR/NMI 쓰기없음. CSS/공유고장 뒤 SD/FPGA 추가IO금지. 체크포인트창은 원래IO시작시각/남은polls복구,60초예산 연장안함. SD전원차단 원자성 보장없음.
- 최종시험: host03 24개, budget01 1개, readback01/readback96-01 실제FatFS파일재열기. FAT16/32 제품명령1814/1943,시험기 추가읽기36/39 별도. readback96은회귀전용,96실기승인 아님. 변경C·헤더6개 ARM/host같음,벡터08018f95→NMI08018f94/기존stop15stores0calls 확인. 실제MCU 실행/WCET 아님.
- 초기arm01중복문자열 준비실패/host01DLL623/arm-check01키오류/Make의존성첫재시도 보존. 새FPGA/RTL/fit/STA/ASM/Questa 없음. 현재 ARM 생성기+기존100builder의obj-nes-100명은 역사적 명명. CSS108원본/최초GBC·NES 소스와 archive044–112/완료finalizer 수정금지.
- 사용자111 제한시험승인과이번개선판직접요청을 적용했다. 이미승인된범위 재질문안함. 전체NES/게임RUN/E1E2/8µs 미완료,양클록정지lockedHIGH CE9µs 반례유지. 같은패키지반복 대신실제마지막단계에 맞춘수정.

## 실기 우선 개발 원칙

최소 보호 동작과 검증된 파일 조합, 관측 방법, 종료·독립 복원 경로가 준비되면 제한 실기에서 데이터를 얻는 것을 우선한다. 남은 불확실성을 실제로 판별할 수 있는 시험을 먼저 정하고, 실기만으로 해결할 수 있는 항목을 같은 문서·모형 검사로 반복해서 미루지 않는다. 이는 모든 전기 조건의 입증을 생략한다는 의미가 아니다. 기존 승인 범위는 재승인을 요구하지 않으며, 고장 주입·전압 변경·노출 확대 등 범위가 달라질 때만 필요한 판단을 추가한다.

## 사용자 규칙과 전체 목표

한국어 PR 제목, 작업 목표→작업 내용→작업 결과→작업 의미 네 절. 사용자가 머지한다. 실기는 외부에서 패키지→실행→로그 반환. 알려진 부품/LED/분해/PC USB/성공한 저장·클록 질문 반복 금지.

084저장/메뉴/GBC·092클록/TXT/복원PASS 유지. 준비도4완료/7부분/1미완료. 첫 게임 SMB3(J) mapper4 PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49.80/96KiB 진단은384KiB 게임지원 아님. ROM/바이너리/미디어/라이선스/private경로 Git 금지.
