# NES 현재 인계 —105 최종 파일 조합

ARM104·CF86의097 ASM·정확044 복원 조합을11개 파일의 역할과 SHA256으로 고정했다. 이름이 같은 구형 파일, 진단/복원본 혼동, 설치 승인 플래그 변조를 오프라인에서 거부한다.

**작업 의미:** 실기 디버깅 기반의 검증·배포 준비다. 같은 검증 파일 조합을 다시 선택하고 잘못된 조합을 걸러낼 수 있게 됐다. CPU/PPU/APU/mapper 배선이나 SMB3 실행 기능을 추가한 작업은 아니다.

PR54 병합93feb9f3262cf2ce01db3105602ac74ffaf497d0/head80c161525cced4640d596088c0bd01f0b108c951 포함 확인. 현재 codex/nes-final-pair-105. [105 결과](../../analysis/PAIR105-RESULT.ko.md)·[계약](../../docs/nes-pair105-contract.md)·[파일 역할](../../analysis/pair105-inputs.json)을 먼저 읽는다.

## 바로 다음 작업

1. 106에서는 외부 IO의 미측정 가정과 공통고장 제외 범위를 하나의 제한 실기 판정표로 좁히고, 허용 가능한 조건의 근거와 정상·실패 관측·종료 한도를 확정한다. 파일 조합이나 같은 fit/ARM을 다시 만들지 않는다.
2. 외부전압/부하/PCB 가정과 두클록정지lockedHIGH CE9µs 반례를 해결된 것으로 쓰지 않는다. 단일클록 조건부 보호와093 Q 이후 전파값을 무조건8µs 보호로 합산하지 않는다. 미확정 조건을 문서 서명만으로 PASS 처리하지 않는다.
3. 준비된11파일 조합은 오프라인 검토 자료다. 설치false/실기승인false/RUNfalse이며 ZIP/SD 설치 구조는 만들지 않았다. 제한실기 허용 근거와 관측절차가 완성된 뒤 별도 패키지 단계로 넘어간다.
4.104 펌웨어가094 선택파일/로그/candidate를 그대로 사용한다. 배포 파일의 SHA로 버전을 식별한다. TXT는 PREPARED_RESET_HELD까지만 저장되고 RETURN_READY_RESET_RELEASED는 UART-only다. 이전TXT를 새성공으로 해석하거나 저장만으로 메뉴 표시를 승인하지 않는다.
5. 제품 공유오류 뒤 새TXT/화면/UART 보장 없음. 전체 관측한도는 wire113/136초 하한 또는menu60초 예산과 다르다. 검은화면/0바이트만으로 원인 단정 금지. 사용자 실기는 외부이며 패키지→사용자실행→로그 반환 방식이다.
6. 최종 조합이 바뀌지 않으면 새ARM/fit/ASM/기존단위회귀를 반복하지 않는다. 이후 게임 목표는384KiB/mapper4·IRQ·CPU/PPU/APU/DMC·영상/입력/음향 및 타이틀→월드맵→1-1 플레이다. 이번 작업은 이 배선을 추가하지 않았다.

## 재사용할 증거

-105 review02:11파일 역할·크기·SHA, CF86 전체510856바이트 decode, 제품소스/바이너리8문자열. tests01 정상1/거부23. pair manifest `bba0316dc6160c107edab5a41b6ea32e11b74e3fc227f23b69e967a79dbc797a`. review01은 목록검사 추가 전 중간본. 예상 밖 시험 실패 없음.
-104 ARM182640 SHA7f0601cc24b3fc7288afd4b2531fffaf3aca0c67300c5c4d2bb9aa57d4ac1cca, ELF1eeeb57746883eb96732f30b95b5e742356a383f5a7e63a3de5c9c7529f8f45f. 실제timer/SysTick/LED/CIC/reset 호스트85/대조6/ARM분기 근거는104에서 재사용. 생산C/RTL 변경 없음.
-097 동일086fit RBF510856 SHA6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1, packed219453 SHA6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805. 받은base168440→214981 legacy EOF 패딩/원본HDL 동등성 미증명 유지.
-정확044복원169056 SHA1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b, 기존091 ZIP에서 그대로 추출. 사용자 현재SD 동일성/새복원시험은 주장하지 않는다.
-완료finalizer/044–105archive 수정 금지.103 sharedfault/report.error 구분,102 차단12writes/3DSB,101 SPI TXE→BSY/공유예산 보존.104 실제함수와TIM2/GPIO/IRQ모델 구분, 전체main/모든IRQ/MCU시간 증명 아님.

## 사용자 운영 규칙과 목표

PR 제목·본문 한국어, **작업 목표→작업 내용→작업 결과→작업 의미** 네 절을 사용한다. 작업 의미는 전체 목표 진전과 디버깅기반/배선구현/게임호환성/검증배포 중 성격을 명시한다. 새 규칙은 과거3절 지시보다 우선하고 병합PR은 고치지 않는다. 사용자만 머지한다.

084 저장/재읽기/화면/044복원/메뉴/GBC와092클록활동/TXT/복원 PASS. 부품·LED·분해·PC USB·동일 저장/클록/복원 질문을 반복하지 않는다. 준비도4완료/7부분/1미완료·설치false. SMB3(J) mapper4 PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49 첫 목표.80/96KiB합성진단은384KiB게임지원이 아니다. ROM/바이너리/미디어/라이선스/private경로 Git 금지.
