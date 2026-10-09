# NES 현재 인계 —128 명령·로더 개선, 다음은 reader reset 경로

[128 결과](../../analysis/COMMAND128-RESULT.ko.md) · [검증 메타](../../analysis/command128-verification.json)

## 바로 이어서 할 일

**동결128 fit07의 `loader|release_reset[1] → reader|check_response_address[8]` 경로를 줄인다.** 168MHz setup은−0.446ns로 아직 실패한다. 명령 판정과 로더 구조 개선으로127의−2.647ns에서 줄었지만 실기 패키지 승인으로 해석하지 않는다. 먼저 reader reset/enable fanout과 조합 경로를 확인하고, 원시 오류의 즉시 취소를 약화시키지 않는 변경을 선택한다. 영향받는 reset·CHECK/RUN 소유권 경계만 시험한 뒤 새 fit/STA를 실행한다.

fit07은14,147LE/955LAB/5,318regs/26M9K/PLL1,46물리핀+264가상핀이다. 같은 클록 NES9.027/host1.028/mem−0.446ns,raw−6.953ns. 남은8LAB은 최종 소비자·MMC3 여유가 아니다. 새 진단 reset 첫 단계 fanout1과6단계경로 최소0.384ns만 확인했다. 하류1,776혼합경로의−4.482ns를 승인하지 않았다. 이전126의372데이터쌍/10제어체인 승인도 상속하지 않는다. blanket false path나 근거 없는 multicycle 금지.

## 구현 계약과 재사용할 시험

- SPI 종료 시 검증하고 다음 메모리 클록에 반영한다. hard fault가 queued START보다 우선한다. raw reset은 pending을 즉시 취소하고 멈춘 클록에서는 reset 해제가 불가능해야 한다. 새 프레임 겹침은 오류다.
- CHECK/순차 ACK/FINISH 후 verified가 설정된 START만 RUN에 연결한다. ACK 하위8비트 carry와 기존3비교 선행 레지스터는 프레임 간 안정화 계약을 갖는다. final test06: 두 SPI속도에서각166검사/18오류,512ACK와3개 큰 주소 경계,4개 취소 경계. 전체80/96KiB decoder replay는 아니다.
- CHECK response의 조합 gate는 제거했지만 reader 등록값은 취소 reset으로 지워진다. 중복 CHECK command gate 대신 sticky check_failed를 유지한다. 불법 BEGIN이 내부 RECEIVE를 만들더라도 이후 DATA와 외부 RUN을 차단해야 한다. 내부 오류 상태 전체 동등성은 주장하지 않는다.
- final boot05: 두 이미지180,224+오류87바이트 쓰기, CHECK308/RUN128, drain86위치, CHECK취소48위치, seededREADY불법6사례. 실제 loader/boot/reader와70ns RAM모델이며 CPU전체세션은 아니다. 직접 post-fault DATA 부정 대조를 두 번째 BEGIN보다 먼저 해야 누락된 gate가 다른 오류에 가려지지 않는다.
- final diff02: 실제127/128 한 클록 전이26,112조건. count0/total−1/total,remaining1/2/22/64,모드/명령/오류 조합. 도달 불가능한 FAILED+fault0와 임의 레지스터 손상은 범위 밖이다. 오류코드 변경 부정 대조도 통과했다.
- READ16/168MHz와 쓰기22/64/22/22(최소125/375/125/125ns), guard21/672/startup33603을 유지한다. 두 클록 정지 반례는 남는다. 기존119 full80/BASE/ENTRY/부품·storage·clock 시험을 이유 없이 반복하지 않는다.

## 실패 기록·동결·재현

3,773파일 manifest `3078ead176dd6b070b71b032b9c75a1e584b03f94784f9cdeb41bf5c8c0905eb`. final은 test06/boot05/diff02/fit07이다. test02 선언순서, test04 시험watchdog, diff01 도달불가능상태, fit02 조기audit, fit05/boot04 복사누락 발견 후 의도적중단을 모두 보존했다. 새 로더의 공개/boot/fit 해시는 일치한다. fit06 −0.413ns에서 fit07 −0.446ns로 최악값이 조금 나빠졌으며, 병목은 주소 carry에서 reset 해제로 이동했다. 완료 finalizer나 archive044–128 수정 금지.

`run_nes_command128.ps1`, `run_nes_command128_boot.ps1`, `run_nes_command128_diff.ps1`는 기존 FLOAT wrapper·Python·Questa 경로와 `-Baseline <probes>`/새 ASCII `-Out`을 사용한다. 한 seat이므로 직렬 실행한다. `nes_command128_fit.py --baseline <probes> --out <newASCII> --quartus-bin <bin64>` 후 **모든 phase 종료를 확인하고** `review_nes_command128.py --out <same> --quartus-bin <bin64>`를 실행한다. `verify_nes_command128.py --evidence <frozen128>`는 기록·해시 확인이며 타이밍/실기 승인 PASS가 아니다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 게시

PR73 병합 확인. 한국어 제목과 작업 목표/작업 내용/작업 결과/작업 의미4절, 사용자가 병합한다. GBC152/원래NES334/모든 공개 핀 보존. ROM·바이너리·미디어·라이선스·개인경로 Git 제외. 다음 목표는 위 reader reset 경로 개선→새 CDC/IO→SNES 소비자→관측 가능한 최소 RUN+044 복원이다. 이번에는 ARM/ASM/패키지/실기를 추가하지 않았다.
