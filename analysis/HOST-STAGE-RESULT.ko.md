# Host stage029 및 첫 실기 묶음
2026-10-05, NES-R2-HOST-STAGE-029. Core014/CPU 기능017/자원018/SNES 에뮬레이터025 유지.

## 새로 확인한 것
027 큐→028 CDC→새 host stage를 실제 Questa에서 연결 실행했다.
큐/호스트 주기10/14ns,14/10ns,10/22ns의3조건에서 각각10항목 PASS,총28,431바이트가 원본과 exact 일치했다.
컴파일과 각 시뮬레이터 종료 요약의 Errors/Warnings는0이다. 실행 스크립트의 onerror 사용 안내는 로그에 남아 있다.
첫 실행에서 통과했으며 실패 실행을 대체하지 않았다. 기존 무료 Starter FLOAT로 실행했고 별도 smoke는 반복하지 않았다.

최대3072B를 먼저 복사하고 READY를 켠 뒤 호스트 연속 읽기에 등록된 데이터를 반환한다.
부분 publish/빈 큐, 준비 전 읽기, busy 중 설정 덮어쓰기, 조기 commit, overread,
잘못된 sequence, prefetch 중 reset, READY 상태 reset, 새 generation 복구를 검사했다.
최대 패킷은 큐 클록을 멈춘 뒤에도 local buffer에서 전량 읽혔다.
commit은 큐가 재개되어 응답할 때까지 busy를 유지했다. 준비 버퍼만으로 큐의 반납 응답까지 해결됐다고 보지 않는다.

|큐/호스트 주기 ns|split2328B start→읽기 시험 ns|resident2008B ns|3072B ns|
|---|---:|---:|---:|
|10/14|244706|211064|322799|
|14/10|244680|211040|322779|
|10/22|341836|294822|450873|

시각에는 register/status/오류 주입 확인 시간이 포함된다. 순수 prefetch 지연이나 실제 SNES DMA 기한 수치가 아니다.
바이트마다 CDC 왕복하는 prefetch 비용은 남는다. 준비 버퍼3KiB를 더해 큐와 합계9KiB이며 실제 M9K/LAB fit은 미측정이다.
정규화된 host register/data strobes까지만 연결했다. 실제 SNES 주소 공간, PHI2/버스 드라이버, IO timing, DMA master는 미연결이다.
리셋 후 오래된 RAM 값은 노출되지 않지만 RAM 자체를 지우지는 않는다.

## 지금 가능한 실기 H0
기존025에서 화소/PPU DMA를 검증한 top/bottom/fine_x 자체 SNES ROM의 바이트를 그대로 패키징했다.
기존 Mesen 증거 해시와 최종 프레임 RGB를 재검증하고 PNG 비교 화면을 생성했다. 새 Mesen 실행은 하지 않았다.
[실기 절차](../docs/nes-hardware-first-test.ko.md), [기계 판독 준비 상태](hardware-readiness.json).
로컬 묶음: analysis/local-host-stage-029/NES-H0-029.zip
ZIP SHA-256: 444f9b612dc5df087179f4b4ce01fa64f25c7823f0dba2e71214cfff26004b5c

일반 SNES ROM 메뉴 경로로 실행하며 펌웨어/FPGA 교체는 없다. NES FPGA 비트스트림은 포함하지 않는다.
4프레임 갱신 후 색 점무늬 화면이 고정된다. 소리·입력·PASS 문구는 없다.
239줄 진단 viewport 두 개는 제품 crop 정책 승인이 아니다.
지금 사용자가 이 패키지로 첫 화면 경로 실기를 시작할 수 있다. 실제 실기 결과는 아직 없다.
마지막 화면 확인만으로 중간 프레임 deadline, NES 실행이나 FPGA 버스를 입증하지 않는다.

## 다음 실행
1. H0 실기 결과를 수집하면서 H1의 실제 SNES 주소 디코더/읽기 strobe와029 준비 버퍼를 연결한다.
2. 원본 자체 패턴 생산기와 PPU DMA를 연결하고 sequence/error를 눈으로 확인할 수 있게 한다.
   동일 후보의 실제 핀/클록/IO/CDC 및 fit/STA와 로더/복귀 경로를 검사한 뒤 H1 설치 묶음을 만든다.
   H1은 자체 transport 진단이며 SMB3 전체/DMC 완료를 선행조건으로 삼지 않는다.
3. 본 NES 경로의 clock drift, joint CHR/OBJ/patch 배치, 외부 메모리, 전체 자원 및 정확도 관문은 계속 유지한다.

원시 증거: analysis/local-host-stage-029/run.028 상태6개는 baseline-status에 보존했고 기존 manifest55항목을 검증했다.
GBC C44/0.9.0,014/027/028 RTL 및 upstream 변경 없음. 전체 NES fit/실기/SMB3 성공 선언은 하지 않는다.
