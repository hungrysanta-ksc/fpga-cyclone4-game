# 다른 게임기 코어의 Cyclone IV 이식 참고 절차

이 문서는 FXPAK Pro GBC 작업에서 배운 **검토 순서**다. 대상 보드·칩·코어가 바뀌면 수치와 제약을 다시 측정한다. 소스의 라이선스와 실제 보드 회로를 먼저 확인한다.

## 1. 목표와 기준선

원본 프로그램 형식, CPU/PPU/APU 속도, 화면 화소·색·순서, 입력·음향·저장, reset/menu 동작을 요구로 적는다. 허용되는 화면 재표시와 허용되지 않는 source frame 손실을 구별한다. upstream commit/수정분, 대상 FPGA package, 회로 revision, MCU/renderer 버전, 도구 버전을 고정한다. 상용 ROM은 로컬 시험에만 둔다.

## 2. 물리 보드 계약

모든 핀의 방향·OE·전압·pull/drive, 양방향 bus의 turnaround와 동시 구동 방지, 외부 RAM의 tAA/tWP/setup/hold, SPI·DAC, 콘솔 CPU/DMA/refresh strobe를 회로·부품 자료와 대조한다. 추정 또는 모형 입력은 `unknown`으로 남기고 실제 보드 측정과 혼동하지 않는다. 하드웨어 무개조 조건이 있으면 관측 수단도 그 범위 안에서 설계한다.

## 3. 클록·리셋·CDC 및 메모리

producer/consumer, 도메인 주파수·관계, async assert/sync release, payload/valid/ready, backpressure, buffer 소유권·epoch, 주소/폭/endianness, read-during-write, timeout을 표로 만든다. FIFO Gray pointer와 bundled data는 첫 동기화 FF뿐 아니라 hold/skew 및 reset 중 손실을 확인한다. 외부 메모리와 M9K **블록 수**, LE·핀·PLL을 동시에 예산화한다.

## 4. 검증과 타이밍

모델/단위 → 오류 주입 → 실제 코어·MCU·표시 프로그램 통합 → 동일 후보 full-fit/STA → 제한된 실기 → 장면별 실기의 순서로 진행한다. 각 결과는 후보 ID, 소스/SDC 해시, 도구·seed, stimulus, model scope, pass/fail, evidence를 가진다. 제약 5종 slack과 미제약 경로, ignored exception, clock transfer, MTBF 계산 범위, 외부 I/O timing을 각각 판정한다. 경고를 없애려고 false path나 SDC를 임의 완화하지 않는다.

## 5. 지속 처리와 배포

프레임당 평균 바이트 외에 최장 burst/blackout, FIFO peak, 누적 backlog 기울기, source→commit→publish→display epoch와 최대 age를 측정한다. 첫 설치와 반복 설치를 분리한다. 기능 통과·constrained slack·보드 timing·실기 성공을 별도 gate로 유지한다. 실패 결과와 원래 제약을 보존하고, 좁은 진단의 rollback·세이브 보호를 정한 후에만 실기로 간다.

GBC 사례의 33.56MHz core, 84MHz SRAM, 56/56 M9K, 270ns SNES slot, 21,764바이트/프레임은 **현재 후보의 관측/가정**이다. 새 코어의 예산 입력으로 재사용하지 않는다.
