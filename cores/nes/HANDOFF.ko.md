# NES 현재 인계 —131 카운터 사전 설정과 제어 입력 매핑

[131 결과](../../analysis/COUNTER131-RESULT.ko.md) · [검증 메타](../../analysis/counter131-verification.json)

## 다음 작업

**최종은 test02/fit05**다. 선택131fit05의 같은 클록 setup·hold 통과를 기준으로 새 hierarchy의 CDC/제어·reset 경로와 외부IO를 검증한다. 이후 실제 SNES 소비자와 관측 가능한 최소 RUN·044 복원으로 진행한다. 근거 없이 다섯 배치나 전체 쓰기를 반복하지 않는다.

같은 클록 setup 통과: memory +0.041ns, hold 최소+0.158ns. 원시 clock-pair -10.408ns 및 새 hierarchy CDC/외부IO·MTBF는 별도다. 시간 예외·클록 완화나 과거126 승인 상속으로 통과시키지 않는다. 최소 안정성 이후에는 진행 관측·오류 종료·독립044 복원을 갖춘 실기로 전환한다.

## 변경 계약과 시험 재사용

- 로더 카운터는 timed phase 밖에서 SETUP 값으로 사전 설정한다. 비활성remaining은 과거와 다르지만 새SETUP 진입 시부터는 동일하다. fault WRITE/HOLD drain, 명령 pause와 error priority, 원시 reset을 유지한다. 중간counter만 비교하거나 무조건 홀드를 기대하는 회귀 검사는 이 계약을 반영해야 한다.
- 상태 전이 대조26,112개는 상태0–8,64명령조합,길이0/total−1/total,remaining1/2/22/64,오류0/1이다. 도달 불가FAILED+fault0 및 임의 레지스터 손상은 제외한다. 다음 활성 카운트와 모든 핀을 검사하며 잘못된 사전 설정 부정 대조도 통과했다.
- test02는 실제80/96KiB 쓰기180,224회+오류87회, CHECK308/RUN128/drain86/cancel48+96/멈춘클록3/READY오용6을 통과했다. 추가 취소·오용 시험은 READY를 설정하는 fixture를 포함한다. 전체 SPI/CPU/MCU/SNES소비자나 실기 시험은 아니다.
- SPIindex·loaderstate/address의 enable/sync제어입력은 제거됐지만 response-data enable8개는 남는다. 합성 설정만으로 제거를 추정하지 않는다. fit05 최초검증기는0개 가정으로 실패했고 실제8개를 기록하도록 수정했다. 원본 검증기/TSV 보존. 이후attribute만 다른 후보는 정확한 정규화로 test02의 동작 소스와 대조했다. 새 기능시뮬레이션·gatelevel증명으로 과장하지 않는다.
- 14,078LE/954LAB/5320regs/26M9K/PLL1. 남은LAB을 최종 소비자·MMC3 여유로 해석하지 않는다. READ16/168MHz/write22-64-22-22 최소125/375/125/125ns/guard21-672-33603 유지.
- 바이트 수→카운터 경로0개, check_failed→counter +1.496ns. reader219경로 최소+1.089; reset체인6경로 최소+0.456,혼합하류최소-4.439ns 미해결. 원시reset/전체MTBF/E1E2/8µs/양클록정지CE9µs는 남는다.

## 재현·미채택 기록

`run_nes_counter131_diff.ps1`, `run_nes_counter131.ps1`은 기존FLOAT wrapper/Python/Questa/새ASCII `-Out`/`-Baseline <probes>`를 받는다. 1seat이므로 직렬 실행한다. `nes_counter131_fit.py --baseline <probes> --out <newASCII> --quartus-bin <bin>` 후 `review_nes_counter131.py`로 실제 포트와 타이밍을 검사한다. `verify_nes_counter131.py --evidence <frozen131>`은 인접130자료와 함께 입력 재생성·시험·배치·manifest를 확인한다.

동결 2,409파일 manifest `363d7305f110b92805c468a37138acc12341ef9fe208c659ae12a0dbf6d607ef`. 완료 finalizer/archive044–131 수정 금지. test01의87쓰기 기대값 오류와 원본 로그, 모든 중간fit을 보존했다. test02는180,311로 고친 후 전체 재실행했다. 라이선스·승인 실패 없음. 같은 의미의 전체 쓰기·배치를 무변경 반복하지 않는다. 각 중간 후보는 해당 executed materializer로만 재현하고 최종 입력과 섞지 않는다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 게시

PR76 병합 확인. 한국어 제목과 작업 목표/작업 내용/작업 결과/작업 의미4절, 사용자 병합. GBC152/원래NES334/과거 공개핀 보존. ROM·바이너리·미디어·라이선스·개인경로 Git제외. 새ARM/ASM/설치 패키지 없음. 준비도6완료/5부분/1미완료는 게임 완성률이 아니다.
