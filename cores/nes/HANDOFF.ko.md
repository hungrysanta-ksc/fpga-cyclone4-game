# NES 현재 인계 —129 reader 소유권 분리, 다음은 로더 상태 enable

[129 결과](../../analysis/READER129-RESULT.ko.md) · [검증 메타](../../analysis/reader129-verification.json)

## 바로 이어서 할 일

**최종은128 이후의 reader-only129 test01/fit01이다.** 번호가 큰 fit03/04/05를 이어 쓰지 않는다. `loader|state.WRITE → loader|state.HOLD` enable 경로가−0.158ns로 남는다. 실제 경로 보고서를 분석해 enable/state 구현을 단축할 새 근거를 먼저 세운다. 단독 phase shortcut·counter 분리·standard fitter 시도는 이미 비교했고 더 나빴으므로 반복하지 않는다.

내부 타이밍 통과 후 새 hierarchy CDC/외부IO·실제 SNES 소비자·진행 관측/오류 종료/독립044 복원을 갖춘 최소 RUN 실기로 진행한다. same-clock 개선은 전체 타이밍 승인이나 전기적 안전 보증이 아니다. 이전126의372데이터쌍/10체인 승인도 상속하지 않는다.

## 선택한 후보와 구현 계약

- fit01:14,183LE/960LAB/5,320regs/26M9K/PLL1/물리46핀+가상264핀. NES9.280/host3.172/mem−0.158ns. raw−8.298ns는128보다 악화됐다. 남은3LAB을 소비자·MMC3 여유로 보지 않는다.
- reader의 owner_valid/owner_check를 local reset 해제 다음 clock에서 확정한다. 이후 check_ready/pending/address/response가 이 mode를 사용한다. 공통 reset이 없이는 mode가 바뀌지 않아야 한다. CHECK→RUN은 CHECK 종료/reset 후 START, RUN→CHECK는 STOP/reset을 거친다. 불법 변경은 기존 sticky check_failed가 차단한다.
- 내부 요청 gate는 raw_check_ready+주소범위+!check_failed다. 외부 ready의 즉각적 합법성 gate는 남아 있다. 원시 reset/취소는 FSM과 owner를 비동기로 지운다. 클록 정지 중에도 출력·응답을 취소하고, 각 로컬 클록 없이는 reset을 해제하지 않는다.
- old release_reset→주소 직접 setup 경로0개, 분리된219보고경로 최소0.808ns. 그룹은 일부 겹친다. owner_valid는 상수1을 저장해 register setup0개이며 reset 승인이 아니다. 진단 reset fanout1/6단계경로 최소0.456만 확인; 하류혼합1,776경로 최소−4.280은 미해결이다.
- 최종 loader와 SPI는128 동일 바이트다. READ16/168MHz, write22/64/22/22 최소125/375/125/125ns, guard21/672/startup33603 유지. 시간 예외나 클록 주기 완화 금지.

## 재사용할 시험과 미채택 실험

test01: RAM/loaded 상태를80/96KiB로 설정, 실제 CHECK308/RUN128, 오류 쓰기87/drain86, CHECK취소48+새CHECK/RUN취소96, 멈춘clock3, seededREADY불법6, 잘못된owner/동기식취소 부정 대조2 통과. 전체 정상 이미지 쓰기·SPI decoder·CPU 프레임은 재시험하지 않았다. 모델과 실기 증거를 혼동하지 않는다.

fit02(reader-only standard)−0.615, fit03(phase shortcut)−0.695, fit04(추가counter 분리)−0.350, fit05(동일RTL standard)−0.521ns는 모두 미채택이다. test02/diff01↔fit03, test03/diff02↔fit04는 각26,112상태대조+오류code대조가 통과했으나 최종 변경이 아니다. 로더 구조를 다시 바꾸면 이 실패한 배치 결과를 비교 기준으로 삼는다. 최종 공개 materializer는 fit01과 동일한 reader-only RTL을 생성한다.

## 동결·재현·기록 주의

2,502파일 manifest `10ff116cdb29ca1d2e35d9bd4aff7c7866cb404a57a2128be999d50480ca4c9b`. 완료 finalizer/archive044–129 수정 금지. 초기 owner_valid 경로 존재 가정으로 발생한 parser 오류와 TSV, refit 시작 metadata 보완 전 실행기, 미채택 실험도 보존했다. 새 refit 실행기는 시작 시phase를 비워야 한다. 실제 도구 종료 확인 후 review를 실행한다.

`run_nes_reader129.ps1`은 기존 FLOAT wrapper/Python/Questa와 `-Baseline <probes>`/새 ASCII `-Out`을 사용한다. `nes_reader129_fit.py`로 fresh MAP/FIT/STA 후 `review_nes_reader129.py`로 읽기 전용 clock/owner 경로를 확인한다. `verify_nes_reader129.py --evidence <frozen129>`의 PASS는 기록 무결성이며 설치 승인이 아니다. `run_nes_reader129_diff.ps1`은 이후 로더를 바꿀 때 사용하며 기본 materializer는 최종 reader-only 후보를 생성한다. 미채택 실험 재현에는 동결된 각 디렉터리의 정확한 RTL/실행기를 쓴다.

이전 root AGENTS의128 게시 줄에 있는 `-127 frozen3773`은 숫자 표식 오기다. manifest3078...과3,773파일은128이며127은별도1,171파일이다. 역사 기록을 다시 쓰지 말고 이 설명을 우선한다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 게시

PR74 병합 확인. 한국어 제목·작업 목표/작업 내용/작업 결과/작업 의미4절, 사용자가 병합한다. GBC152/원래NES334/과거 공개 핀 보존. ROM·바이너리·미디어·라이선스·개인경로는Git제외. ARM/ASM/설치 패키지·새 실기 없음. 제한 진단6완료/5부분/1미완료는 게임 완성률이 아니다.
