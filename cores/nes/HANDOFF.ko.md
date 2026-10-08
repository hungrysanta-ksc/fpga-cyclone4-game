# NES 현재 인계 —106 실기 조건 분석

CF86의 외부 지연 예산을 원시3168경로에서 재계산하고, 최소 조건이 CE 비활성 간격임을 확인했다. 실기 미결 조건을 외부 전기적 범위와 공통고장 처리 두 항목으로 좁히고 관측·종료 절차를 구체화했다.

작업 의미: 실기 디버깅 기반의 진입 조건 분석이다. 필요한 외부 근거의 수치와 관측 판정 기준이 명확해졌다. 새로운 코어 배선·게임 기능·실기 PASS를 추가한 작업은 아니다.

PR55 병합4558aedab3feedc79e553756fe60486009c0dbed/head0314bdf6127fcc8348231af6ecafe9286492df2b 포함. 현재codex/nes-trial-conditions-106. [106 결과](../../analysis/TRIAL106-RESULT.ko.md), [관측 초안](../../docs/nes-trial106-observation.ko.md), [판정 상태](../../docs/nes-trial106-decision.json), [계약](../../docs/nes-trial106-contract.md)을 먼저 읽는다.

## 다음 행동

107은 반복 분석 대신 미결 E1/E2를 닫는 근거 확보 또는 설계 변경을 선택한다. 먼저 기존 보드 설계·핀/전원 자료에서 전기적 상한을 확보할 수 있는지 조사하고, 없으면 필요한 측정과 공통고장 대안을 구체적으로 보고한다. 조건이 열린 상태에서 또 패키지 준비 PR을 반복하지 않는다.

- E1: 실제VDD/VDDQ/부하/PCB 범위. 계산상최소는CE HIGH(tCPH5), 외부예산109.565ns.20ns leg+5ns→64.565ns, 동일leg52.282ns→+1ps/52.283ns→−1ps. 이경계로 물리승인하지말것. 보호범위의실측/설계근거는현재없다.
- E2: 두클록정지/lockedHIGH CE9µs 반례. 독립차단설계 또는 제한시험 고장범위의 명시적 판단 필요.093 Q 이후23.699ns/092활동은해결증거아님. EBLL에T계열읽기tCEM예외적용금지.
- 관측은정의됐지만시험승인은아님. 선택후600초는사람의대기종료한도, MCU WCET/8µs차단/SD저장완료보장아님. 전체wire113/136초하한과menu60초예산을혼동하지않는다.
- 제품104는094표식/TXTcandidate 유지. 저장TXT는PREPARED_RESET_HELD, released는UARTonly. 새TXT·메뉴화면·복원관측을분리한다. 오래된TXT/0바이트/검은화면으로원인단정금지. 오류뒤추가IO/자동보고강제금지.

## 고정 자료

-106 envelope01:086원시3168경로/3corner,20/60ns전체JSON동일재현,4경계시나리오+4잘못된가정거부. 새RTL/C/ARM/fit/STA/ASM/Questa/실기/설치패키지없음. 공식PDF직접403/공식검색색인으로tCEM범위교차확인,기존판본자료보존. 실패한회로실험없음.
-105 pair11역할/정상1·거부23,manifest bba0316dc6160c107edab5a41b6ea32e11b74e3fc227f23b69e967a79dbc797a 재사용. installable/trial/start=false. 다음에도 동일조합을 다시조립/빌드하지않는다.
-104 ARM182640 SHA7f0601cc24b3fc7288afd4b2531fffaf3aca0c67300c5c4d2bb9aa57d4ac1cca. ELF1eeeb57746883eb96732f30b95b5e742356a383f5a7e63a3de5c9c7529f8f45f. 실제timer/SysTick/LED/CIC/reset호스트85/대조6/ARM분기 근거는104에서재사용; IRQ/GPIO/시간모델과실물을구분.
-097 동일086fit RBF510856 SHA6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1/packed219453 SHA6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805. 정확044복원169056 SHA1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b. 받은base legacy EOF/HDL동등성미증명 유지.
- 완료finalizer/044–106archive수정금지.103 sharedfault/report.error,102차단12writes/3DSB,101TXE→BSY/공유예산보존. 새보호검증없이예산/오류를초기화하지않는다.

## 사용자 규칙

PR제목/본문한국어, 작업 목표→작업 내용→작업 결과→작업 의미 네절. 의미에는전체목표진전과디버깅기반/배선구현/호환성/검증배포를명시. 사용자가머지한다. 실기외부·패키지→사용자실행→로그반환. 이미확정한부품/LED/분해/PC USB/성공한저장·클록질문반복금지.

084저장/메뉴/GBC·092클록/TXT/복원PASS 유지. 준비도4완료/7부분/1미완료,설치false. SMB3(J) mapper4 PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49 첫목표.80/96KiB진단은384KiB게임지원아님.ROM/바이너리/미디어/라이선스/private경로Git금지.
