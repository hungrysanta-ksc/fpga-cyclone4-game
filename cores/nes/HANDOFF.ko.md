# NES 현재 인계 —133 실제 RUN 시작·종료 계약

[133 결과](../../analysis/RUN133-RESULT.ko.md) · [검증 메타](../../analysis/run133-verification.json) · [132 CDC](../../analysis/CDC132-RESULT.ko.md) · [131 회로](../../analysis/COUNTER131-RESULT.ko.md)

## 다음 작업

재사용131fit05/133test03의 RUN 기능 계약을 유지하고 실제 외부IO와 SNES 소비자 연결을 확인한다. 가상 포트와 실제 핀을 구분해 PSRAM/SPI/SNES 소유권·입출력 타이밍·소비자 관측 경로를 정리하고, 최소 RUN 상태·오류·044 복원을 확인할 실기 경로를 구현한다. 같은 초기화/전체쓰기/371CDC/배치를 무변경 반복하지 않는다.

현재 실제 top은 `nes_live_joint.sv`, 기준 배치는131fit05, 최종 기능 시험은133test03이다. IO는 해당 `live.qsf`의 실제 핀과 virtual pin을 우선 대조한다. 132의 입력83/출력227 무제약 포트 수에는 가상 포트가 포함된다. 이를 보드 핀 수로 해석하거나 전부 같은 IO delay로 덮지 않는다. 실제 SNES 소비자가 무엇을 읽고 언제 상태·오류·화면을 갱신할지 기존 구현에서 확인하고 최소 RUN 실기의 관측 경로를 구체화한다.

통과한 배치를 무변경 재실행하지 않는다. 새 결선이 필요하면 바뀐 경계만 먼저 시험하고, 실제 구현을 바꾼 시점에 자원·같은 클록 타이밍·영향받는 CDC/IO를 다시 확인한다. 외부 제품/PSRAM 검색이나 저장 진단을 다시 시작하지 않는다. 실기는 원격 SD 설치→TXT 전달 방식이며 PC 직접 연결·LED 관측·재분해를 요구하지 않는다.

## 현재 확인한 계약

- 실제131 top과CPU/PPU·ROM 서비스·로더·SPI·guard·내부 RAM·reset·transport를 함께 인스턴스화했다. 같은 클록 memory +0.041ns,14,078LE/954LAB 배치는 그대로다.
- test03 두 위상에서20 RUN·22 취소/차단·420요청/412응답 통과. 모든 RUN에서 RAM8,192주소 초기화 후 reset을 해제하고 실제 CPU가 reset vector→JMP $8000 명령/피연산자를 읽었다. 요청8개는 중간 취소됐다.
- STOP→같은 이미지 재시작, STOP→CHR16/32K 변경→재시작, 잘못된CRC·원시reset·한쪽clock정지·미검증START를 확인했다. 클록 복귀만으로 guard fault가 풀리지 않는다. 실제 START/STOP 명령은SPI 프레임으로 전달했다.
- CHR 변경은 소비자 reset 중이고 RUN 동안 유지됐다. 최소 RUN→해제372,513.658ns/CHR→해제388,718.502ns는 모델 관측값이다. 132의183설정·115제어 쌍에 대해 기능적 안정/취소 조건을 뒷받침하지만 새 STA 예외나 모든 위상·아날로그 승인을 추가하지 않는다.
- reset 체인 입력107음수행과 일반 하류6,168행은132의 구분을 유지한다. 물리 pulse/reconvergence/MTBF는 별도다. clock 정지 뒤10µs 관측을8µs 보장으로 쓰지 않는다.

## 시험 초기값과 미완료 범위

PLL은 이상적인84/168MHz 및 즉시lock 모델이다. 상용 ROM 대신 JMP 시험 이미지를 사용했고 전체 적재 바이트 수·CHECK verified는 초기값으로 넣었다. 전체쓰기/전체CHECK/MCU·SD 경로를 재시험한 결과가 아니다. BEGIN/END/START/STOP·CRC·미검증START는 실제 SPI 해석기와 로더를 거쳤다.

PPU/encoder/transport reset은 연결했지만 `arm=0`, SNES 버스 idle이다. 렌더링·실제 SNES 소비자·영상/입력/오디오/MMC3는 미검증이다. 다음 작업에서 이 경계를 반드시 표시한다. 새ARM/ASM/실기 패키지는 없다. 132 데이터371쌍/16체인과131 전체쓰기는 변경 없으므로 재사용한다.

## 재현과 실패 보존

`run_nes_run133.ps1`은 기존FLOAT wrapper/Python/Questa/새ASCII Out/Baseline을 받는다. `nes_run133.py`는 고정131입력37개를 확인하고 선언4개만 앞으로 옮긴다. 초기값·결선·절차 변경이 없음을 `top-normalization.json`과 검증기로 확인한다. `verify_nes_run133.py --evidence <frozen133>`은 인접131 증거가 필요하다.

test01은 forward declaration 컴파일 오류, test02는8RUN/위상의 초기 통과, test03는10RUN·11취소/위상 최종 통과다. 두 reset gate 제거 부정 대조는 실패해야 정상이다. 원본 로그와 실행 소스 보존. 라이선스 오류·승인 거부 없음. 124manifest 불일치는132의 격리 기록을 유지하며 이번 입력으로 사용하지 않았다.

동결265파일, manifest `83c2acf15d4730e4c207382ddc6e0b5a78252c1d6c70b14c4c59146251eb24c5`. 완료 finalizer와 archive044–133 수정 금지.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 게시

PR78 병합 확인. 한국어 제목과 작업 목표/작업 내용/작업 결과/작업 의미 네 항목, 사용자 병합. GBC152/원래NES334/과거 공개 해시 보존. ROM·바이너리·미디어·라이선스·개인 경로 Git 제외. 준비도6/5/1은 제한 진단 기준이며 게임 완성률이 아니다.
