# 실행 계획 / 완료 기준 — 2026-09-23

## 전체 순서

**P0 기준선·계약 감사 → P1 자원/처리량·관측 계획 → P2 근거 있는 수정 → P3 동일 후보 통합/물리 검증 → P4 실기 안정화 → P5 폴리오·미니게임·전투 → 사용자 판단 → P6 제품 정리.**

P0/P1은 완벽한 문서 작업을 무한히 하는 단계가 아니다. 다음 코드 변경과 실기 시험을 안전하게 판단할 최소한의 표·근거를 만드는 단계다. 외부 관측이 필요한 항목은 P4의 좁은 진단으로 연결하되, 그것이 전체 게임 성공 gate를 건너뛰는 것은 아니다.

현재 로직 애널라이저가 없어 실제 SNES/FXPAK Pro/SRAM 핀 파형은 측정할 수 없다. 당분간 동결 후보의 시뮬레이션·정적 검사·오류 주입을 우선하고, 각 결과에 사용한 버스/메모리 가정과 미확인 물리 계약을 기록한다. 계측 불가 항목을 통과로 승격하지 않으며, 소프트웨어에서 재현한 결함은 실기 승인 전에 별도로 해결한다.

## P0 — 먼저 할 일: 기준선/인터페이스/클록/리셋/제약

산출물: `ISOLATION-MANIFEST.json`, `INTERFACE-CLOCK-RESET.ko.md`, `TIMING-EXCEPTIONS.ko.md`, `VERIFICATION-MATRIX.json`.

1. 별도 작업 폴더에 소스와 검증 자료를 복제하고 SHA256 대조. 원본에 쓰는 실행 경로를 차단한다. upstream Git 상태/commit, 도구 버전, constraints/RTL/renderer/MCU hash를 식별한다. 과거 사본은 수정하지 않는다.
2. 인터페이스마다 producer/consumer, clock/frequency/relation, reset assert/deassert, payload/valid/ready, hold/backpressure, buffer ownership, timeout, 주소/폭/endianness, 최대 burst/blackout, 검증 근거를 기록한다.
3. 범위: GBC core/PPU→capture→encoder→page/FIFO→SNES SRAM→DMA/HDMA, MCU SPI/ROM loader, SaveRAM/PSRAM, joypad/audio/DAC, SNES reset/menu/reconfigure. 외부 핀의 direction/OE/turnaround·핀 배치·전압 설정을 실제 보드 자료와 대조한다.
4. 최신 후보의 unconstrained ports/paths, clock transfers, ignored constraints, min-pulse/recovery/removal, MTBF chain을 추적. unused/static/protocol-asynchronous/timed 별로 분류하고 예외마다 대상·근거·검증·담당 시험을 붙인다. 미확인 경로를 0개라고 보고하지 않는다.
5. reset 시험 표: cold boot, console reset, menu return, 같은 ROM 재실행, 다른 ROM 후 복귀, reset during capture/DMA/save/첫 publish, PLL unlocked, LCD on/off. 기대값은 RAM 전체 0이 아니라 유효 비트/epoch/소유권과 저장 보존을 포함한다.

종료 기준: 모든 외부/도메인 경계가 표에 있고, 타이밍 미제약·경고가 누락/합리적 예외/관측 필요로 분류됨. unknown은 해결 계획과 출하 차단 여부가 명시됨. 새 물리 시험은 bus contention/OE/쓰기 pulse 및 저장 보호의 안전 전제가 설명될 때만 제안한다.

## P1 — 자원·대역폭·지연 예산

산출물: `SYSTEM-BUDGET.ko.md`, 재현 가능한 계산/trace 분석, 부족한 관측 목록.

- M9K 56/56 및 LE 잔여531을 baseline으로 block 단위 메모리 지도 작성. ROM/cache/capture/encoder/output/save/audio별 폭×깊이·포트·read-during-write·clock을 기록.
- 원본 프레임 입력률, 각 단계 cycle, PSRAM/SRAM 서비스율, DMA/HDMA/refresh/CPU 점유, arbitration 최장 대기, FIFO 최대 누적량을 분리. 느린 consumer를 FIFO 크기만으로 무한히 해결하지 않는다.
- 첫 설치와 정상 반복 설치를 별도 모델로 유지. first-install one-shot 관측을 steady bus 모델에 일반화하지 않는다.
- 일정 길이만 실행한 pass 대신, 위상 sweep 및 누적 backlog 기울기/최대 age/epoch 순서를 계측한다. 예비 장기 시험은 최소 수백~수천 source frames 중 실행 비용에 맞게 정하고, GBC/SNES 주기 beat와 최장 burst를 덮는 이유를 함께 기록한다. 숫자 자체는 충분성 증명이 아니다.
- ‘561792 처리시간 초과’, ‘원본 frame drop’, ‘화면 재표시’를 서로 다른 지표로 기록. 기존 gate/실패는 보존한다.

종료 기준: 병목이 연산/출력 서비스/소유권/잘못된 모델 중 무엇인지 근거와 불확실성이 분리됨. 제안 변경의 LE/M9K/대역폭/지연 비용이 예산에 들어감. 모델 신뢰성 부족 시 더 많은 최적화보다 필요한 실제 경계 관측을 먼저 선택한다.

## P2 — 한 번에 하나의 수정

트랙 A: reset 후 점멸/간헐 오류 원인. 트랙 B: 정상 장면의 팔레트 표현 한계와 G13 처리량. 독립 가설로 다루고 동일 원인으로 미리 묶지 않는다.

매 실험에 가설, 단일 변경, 불변 조건, 기대 지표, 실패 시 해석, 비용 한도를 먼저 적는다. 다음 순서로 검증한다.

1. 모델/단위: exact RGB555, palette table, FIFO overflow/underflow, one-request/one-response, page ownership, fence/drain/publish.
2. 오류 주입: 잘못된 epoch, busy 중 교체, 늦은 응답, reset/lock/LCD 변화, 불완전 DMA 등. 오류를 실제로 검출하는지 확인.
3. 동일 trace·동일 seed/위상/부하로 baseline 비교. 변경한 소스 범위와 constraint diff 기록.
4. 개선 없거나 자원/타이밍 비용이 예산을 넘는 변경은 미채택. 2~3개 비개선 국소 변형 후에는 구조/모델 검토로 돌아간다. seed 탐색만으로 근본 해결을 주장하지 않는다.

UVM 전체 도입은 필수 아님. 현재 Python/Questa testbench와 assertions/scoreboard에 coverage 항목을 추가한다. formal은 사용 가능한 도구가 있고 FIFO/handshake 같은 작은 불변 조건에 이득이 있을 때만 도입한다.

## P3 — 같은 후보에 대한 통합 및 FPGA 검증

검증 행렬의 각 결과는 `candidate_id, source_hashes, constraint_hashes, tools, stimulus, model_scope, pass/fail, evidence`를 가진다.

필수 항목:

- 실제 GBC CPU/PPU와 ROM/저장 데이터 경계, double speed/DMA, MCU command와 SaveRAM 회귀.
- 실제 SNES renderer의 DMA/HDMA 및 버스 중재 연결. 이상적인 ROM bank로 대체한 시험은 별도 표시.
- 부하/위상·장기 epoch 순서·backlog·지연, reset/LCD/최초 fault context 회귀.
- 동일 source/SDC의 full-fit, 핀/전압/메모리 inference, setup/hold/recovery/removal/minpulse, unconstrained/ignored constraints/CDC 판정표. 해당 장치에서 생성된 corner 범위를 명시.
- tight slack은 주요 경로·배치 민감도 검토. 여러 seed 통과는 참고 자료이며 누락된 제약/외부 타이밍을 대체하지 않는다.
- simulation pass, constrained-slack pass, constraint coverage, CDC/reset review, board timing, hardware functional pass를 별도 값으로 저장. 하나의 timing_pass를 출하 gate로 사용하지 않는다.

종료 기준: 기능·자원·타이밍·CDC/리셋·자산 보호 gate가 같은 후보에서 닫히거나, 제한된 실기 진단에 필요한 미결 항목만 명시적으로 남음. 완제품 승인과 제한된 진단 승인을 구별한다.

## P4 — 통제된 실기 재시험

사용자에게 후보ID/복사 파일/경로/rollback/세이브 백업/기대 화면/중단 조건을 짧게 안내한다. 원본 SD 폴더를 자동 덮어쓰지 않는다.

- cold boot와 warm reset 동일 ROM/동일 정상 세이브/동일 입력 경로 A/B. 첫 목표 각10회는 재현성 확인용 제안이며 통계적 무결함 증명이 아니다.
- 점멸, fault, audio continuity, controller, epoch/first fault context를 기록. fault 뒤 reset 전에 확보한 정보와 reset 뒤 덤프를 구별.
- save 교차 로드 3방향은 관련 변경 후 회귀만 수행. 이미 해결된 SaveRAM을 다시 설계하지 않는다.
- 실패하면 다음 한 가지 관측을 얻을 수 있는 진단으로 좁힌다. 불특정 full-game 재시험을 반복 요청하지 않는다.

## P5 — 게임 장면 및 최종 방향 판단

진행 순서: 기존 도비/론 대화·집 떠나기 → 메뉴/폴리오 마기 상세 → 지역/화면 전환 → 미니게임 → 전투 → 저장 후 재시작과 장시간 재현.

정상 에뮬레이터 기준 화면/입력과 색·화소·순서·오디오/입력 지연을 대조하되 CRT 촬영상의 scan band를 디지털 화소 오류로 판정하지 않는다. 각각의 기능을 사용자가 실제 확인하기 전에는 완료로 표시하지 않는다.

이후 사용자가 확장 지속/중단/열화판을 결정한다. 현재 단계에서 ‘후기 게임이므로 불가능’ 또는 ‘모든 게임 무열화 가능’으로 결론내리지 않는다.

## P6 — 재현 가능한 결과물

필수 소스/빌드 명령/tool versions/해시/지원 대상/설치·rollback·제한사항을 정리하고 깨끗한 작업 폴더에서 재빌드한다. FPGA core+firmware+SNES 보조 프로그램을 제품 단위로 묶는다. 원본 상용 ROM/사용자 세이브/라이선스는 배포하지 않는다. 원래 SGB/SNES 경로의 회귀도 확인한다.

## 보고 규칙

매 작업 결과는 ‘무엇이 바뀜 / 어떤 범위가 검증됨 / 무엇이 아직 모름 / 다음 gate’ 네 항목으로 요약한다. 전체 진행률을 임의로 추정하지 않는다. build 실행 성공, 테스트 통과, 실기 통과를 구분한다. 라이선스는 실제 오류가 발생한 경우에만 blocker로 다시 올린다.
