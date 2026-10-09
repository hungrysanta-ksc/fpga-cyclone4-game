# NES 현재 인계 —130 상태 enable 제거, 카운터 입력 타이밍 미해결

[130 결과](../../analysis/ENABLE130-RESULT.ko.md) · [검증 메타](../../analysis/enable130-verification.json)

## 바로 이어서 할 일

**130 fit01 상태 전용 attribute 후보에서 시작한다. fit02는 미채택이다.** 실제 최악 경로 `boot|check_failed → loader|remaining[3]|ena`는6단계, 데이터 지연5.926ns, setup−0.040ns다. 상세 보고서 `state130-8_slow_1200mv_85c-setup.rpt`에서 오류·주소 조건이 카운터 enable로 합쳐지는 논리를 추적하고, 공유 오류 신호의 fanout과 SPI 오류 경로까지 함께 살핀다. 구조 변경이 필요하면129의 오류 drain 대조를 사용해 영향 범위를 검증한다.

카운터 전체에 AUTO_CLOCK_ENABLE_RECOGNITION OFF를 적용한130fit02는 SPI fault→pending_body_error2에서−1.470ns로 악화됐으므로 반복하지 않는다.129fit02–05의 단독phase/counter분리·standard refit도 미채택이다. [129 결과](../../analysis/READER129-RESULT.ko.md)의 이유를 보존한다.

내부 타이밍 통과 후 새 hierarchy CDC/외부IO·실제 SNES 소비자·관측 가능한 최소 RUN과 오류 종료·독립044 복원으로 진행한다. −0.040ns도 실패이며 작은 위반이라는 이유로 패키징하지 않는다. 이전126 CDC 승인과119 실기 증거를 새 배치 승인으로 상속하지 않는다.

## 선택한 구현과 증거

- 최종 materializer는129fit01의 입력을 고정하고 loader.state 선언에만 합성 attribute를 넣는다. 제거하면 로더 동작 코드가129와 바이트 단위로 같고 다른 RTL/QSF/SDC는 동일하다. 조건·쓰기 시간·원시 취소·시간 예외는 변경하지 않았다.
- fit01 14,261LE/959LAB/5,320regs/26M9K/PLL1/물리46핀+가상264핀. NES7.805/host3.388/mem−0.040ns, raw−8.236ns. 잔여4LAB은 소비자·MMC3 여유가 아니다.
- baseline02 상태 enable4/카운터3 → fit01 상태0/카운터3. fit02는0/0이지만 전체 타이밍 악화로 제외했다. 새state130 TCL은16레지스터 동기 입력과 setup/hold를 조사한다.
- fit01 상태·카운터9,846행 setup최소−0.040/hold+0.179ns. reader219행 최소+0.950, old_direct0. owner_valid는 상수D여서 register setup0개이며 reset 승인 아님.
- 진단 reset 첫 단계 fanout1/6단계경로 최소+0.383ns. 혼합 하류1,776행 최소−4.695ns는 미해결이다. E1/E2·전체MTBF·8µs·양클록정지 CE9µs 반례도 남는다.
- READ16/168MHz, write22/64/22/22 최소125/375/125/125ns, guard21/672/startup33603 유지. 현재 진단은 고정64KiB PRG+16/32KiB CHR이며384KiB/mapper4 구현 완료가 아니다.

## 재사용한 시험과 재현

이번에는 합성 attribute만 바뀌어129기능 시험을 재사용했다. CHECK308/RUN128, 오류 쓰기87/drain86, 취소48+96, 멈춘 클록3, READY오용6, 부정 대조2는129결과다. 새Questa·gate-level동등성·전체 SPI/CPU/MCU/SNES소비자·실기 결과로 표기하지 않는다. 상태/카운터 코드가 실제로 바뀌면 해당 회귀 시험을 새로 수행한다.

`nes_enable130_fit.py --baseline <probes> --out <fresh ASCII directory> --quartus-bin <bin>`은 pinned129에 상태 attribute만 넣고 MAP/FIT/STA를 실행한다. 완료 후 `review_nes_enable130.py --out ... --quartus-bin ...`으로 실제 포트·clock/reader/reset 경로를 검사한다. `nes_enable130_baseline.py`는129 DB를 별도 복사해 읽기 전용 분석한다. fit02 재현은 해당 동결 디렉터리의 executed materializer를 사용하며 최종으로 사용하지 않는다.

`verify_nes_enable130.py --evidence <frozen130>`은 manifest/공개소스/채택 입력 재생성/attribute제거 동작동일성/포트·타이밍을 검사한다. 인접129동결자료도 필요하다. PASS는 설치 승인이 아니다. 1,773파일 manifest `511eaaa612656cd6c42448a5801f812a5b57ed4f1758a6e282bff76993f91d90`. archive044–130 및 완료 finalizer 수정 금지. 초기9레지스터 결과와16개 확장 결과 모두 보존했다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 게시

PR75 병합 확인. 한국어 제목·작업 목표/작업 내용/작업 결과/작업 의미4절, 사용자 병합. GBC152/원래NES334/과거 공개핀 보존. ROM·바이너리·미디어·라이선스·개인경로는Git제외. 이번 새ARM/ASM/실기 패키지 없음. 제한 진단6완료/5부분/1미완료는 게임 완성률이 아니다.
