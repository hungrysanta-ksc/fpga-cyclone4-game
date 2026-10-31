# NES507 — 오류 공개 시점을 유지한 타이밍 회복과 출력 일정 경계

실기 기준은 **MMC502 / 기존 489 SNES 소비기 / 관측 평균 10.59fps**다. [506](nes-raw506-contract.ko.md)의 정확한 raw 압축과 ARM 단일 복원을 유지한다. 새 실기 성능이나 메뉴 복귀 시험을 주장하지 않는다. 현재 결과와 입력 SHA는 [507 검증](../analysis/fault507-verification.json)에 기록한다.

## 타이밍 실패 원인과 변경

506의 최소 setup 경로는 168MHz loader `fault`에서 SPI control `error_code[2]`까지였다. 데이터 지연 7.161ns 중 배선이 6.010ns였으며, 공유 `error_hard`에서 최종 오류 코드 선택기로 가는 한 배선이 3.974ns를 차지했다. 따라서 raw 압축 계산 자체가 느려졌다고 결론 내리지 않는다. 논리 3단과 공유 배선에 대한 실제 배치 결과다.

507은 `hard9 > response7 > overlap1 > decoded_error` 우선순위를 비트별 식으로 표현한다. hard9는 같은 클록에 bit0/3을 설정하고 bit1/2를 지운다. sticky fault, reset, command 취소, STOP, 응답 소유권, status snapshot은 그대로다. 오류 코드를 뒤늦게 공개하는 파이프라인이나 새 상태 저장을 추가하지 않는다.

8192개 조합은 모든 prior code·sticky fault·hard/response/overlap/pending·decoded error를 포함한다. 실제 SPI 268회에는 CHECK→READ→response→ACK→VERIFY→START→STOP, 잘못된 응답 주소·미요청 응답·CHECK fault를 포함한다. 각 64개 serial bit 시점에 boot fault를 넣고 두 RTL의 모든 외부 출력을 매 클록 비교했다. hard9의 bit2 우선순위를 일부러 깨뜨린 mutant도 거부했다. 정상 compile/simulation은 error/warning 0이다.

처음 test01은 `loaded_bytes=1`인 fixture에 STOP offset0을 보내 기존 규칙대로 거부됐다. 올바른 offset1의 test02를 선택하고 실패 원본도 보존한다. 샌드박스의 장치 식별 제한은 기존 임시 Starter FLOAT wrapper를 승인된 실행 환경에서 사용해 해결했다. 추가 좌석이나 새 라이선스는 사용하지 않았다.

## 전체 보드 비용

506의 70개 보드 입력 중 `nes_rom_spi.sv`만 바꾸고 같은 Quartus Lite 설정으로 전체 합성·배치 1회와 STA를 실행했다. seed·SDC 예외·clock 설정을 바꾸지 않았다.

| 항목 | MMC502 | 506 | 507 |
|---|---:|---:|---:|
| fitted LE | 15,287 | 15,198 | 15,164 |
| 조합 함수 | 14,135 | 14,168 | 14,172 |
| FF | 8,399 | 8,399 | 8,394 |
| logical RAM bits / M9K | 264,816 / 51 | 동일 | 동일 |
| 관련 setup / hold | +0.353 / +0.142ns | −1.276 / +0.137ns | **+0.078 / +0.139ns** |

기존 실패 경로 자체는 +0.992ns로 회복했고, 새 최소 setup은 loader `fault`→`check_failed`다. implementation/nominal 결과가 같다. 244LE가 남지만 LE 감소를 논리 삭제량으로 해석하지 않는다. 506 대비 조합 함수는 4개 늘었다. 관련 clock 검사는 통과했으나 여유는 작으며 **전체 reset·CDC·IO 승인은 별도 미완료**다. 이 결과를 전체 보드의 모든 timing 경로 통과라고 표현하지 않는다.

ARM firmware는 506과 동일한 212,852B이며 Flash 140B가 남는다. SNES 프로그램도 동일하다. 이번 loader 변경 자체의 프레임 시간 개선은 0이며, 506의 조건부 개선을 더 크게 다시 계산하지 않는다.

## 일반 출력이 늦어지는 경계

실제 코드 순서는 `planner221` → `nes_plan200_finish` → `nes_sink212_seal`이다. planner가 반환하면 map·OAM·CGRAM·HDMA 및 canonical raw가 확정된다. 다만 전송용 raw packing과 일반 packet 생성 일부는 seal 함수 안에서 이루어진다. finish는 END 발행 뒤 모든 tile 소비를 기다리며, 이후에야 일반 데이터 전송이 시작된다.

506의 같은 12개 연속 실행에 함수 진입/반환과 ROM 모형 슬롯 관측만 추가한다. linked ARM·실제 489 CPU·SPI 비용·IRQ·시작 위상·입력은 고정한다. 계측 전후 ARM 명령 수, IRQ, wire, 모든 ACK 시각과 최종 RGB가 같아야 선택한다. 계측의 SPI 구간은 함수의 포함 비용이며 ROM 대기는 그 안에서 겹친다. 이를 더해서 전체 시간으로 만들지 않는다. ROM 슬롯은 여전히 명시적 모형이며 실제 NES/PSRAM arbiter trace가 아니다.

trace01에서 12개 최종 ACK 시각·RGB·ARM 명령 수·IRQ·wire가 모두 기존506과 같았고, 함수 구간36개와 ROM 모형 read3280개를 기록했다. 첫 두 bank 초기 채우기 뒤10개에서 END→finish 반환은 평균 **8.165ms**(1.581~15.613ms), finish 반환→첫 일반 전송은 **0.289ms**였다. END→첫 일반 전송 전체는8.454ms이며, 일반 전송 시작→SEAL 시작은27.275ms였다. 이는 새 가속 결과나 순수 CPU 비용이 아니다. 기다리는 동안 공급할 수 있는 범위를 찾기 위한 기준이다. 특히 canonical 데이터 이후의 작은 준비 비용만 줄이는 작업보다 완료 소유권과 공급 일정을 함께 바꾸는 것이 우선이다.

단순히 seal 호출을 앞당기는 방법은 선택하지 않는다. `complete485`는 `bulk_pending`일 때 `window.last[0]==7`을 요구한다. 그 사이 일반 packet을 넣으면 last가 바뀌어 올바른 bulk도 실패 처리된다. 반대로 이 검사를 지우면 소비 완료의 증거가 약해진다. 또한 일반 출력을 한꺼번에 보내면 이미 준비된 두 bulk bank의 소비와 다음 ROM 공급을 늦출 수 있다.

## 다음 교체 범위와 예산

다음 후보는 **END 수락 뒤의 제한된 일반 출력 공급과 bulk 완료 소유권을 함께 교체**한다.

1. 기존 CRC·flags·accepted/retired 차이 검사를 유지하면서 bulk 제출 watermark로 완료를 추적한다. 전체 queue의 마지막 opcode를 bulk의 identity로 사용하는 의존성을 제거한다. FPGA의 packet별 독립 ACK 검사와 최종 full identity 검사를 유지한다.
2. 준비된 bulk의 제출·소비 및 plan credit을 먼저 처리한다. 한 service turn에서는 일반 packet을 최대 하나만 내보내고 SPI에 재진입하지 않는다. 전체 ordinary queue 4개와 bulk bank 2개 한도는 유지한다.
3. 일반 출력은 비활성 표시 문맥에만 쓴다. tile/ordinary 전부 소비되기 전 SEAL을 허용하지 않고, 최종 ACK 뒤에만 EA와 새 표시 identity를 허용한다. STOP은 부분 공급 상태와 tentative 인증을 무효화한다.
4. 목표 예산은 runtime 구조 추가 최대 8B, 새 global RAM 0B, Flash 순증 최대 140B, FPGA 제어/M9K 추가 0이다. 아직 측정한 구현 비용이 아니다. 함수 분할만 덧붙여 Flash를 넘기지 않도록 기존 blocking 진행 제어의 교체를 포함한다.
5. wrap·future/stale completion·중간 STOP·부분 queue·최종 ACK 반례를 통과한 뒤 실제 arbiter trace와 연속 일정에 연결한다. 첫 프레임/두 bank 초기 채우기를 분리하고 새 최종 표시 이득을 확인한다.

MMC502 설치본은 유지한다. 관련 timing 통과만으로 새 실기 FPS나 60Hz를 선언하지 않는다. 새 전달 후보를 선정할 때는 고유한 파일명을 사용하고 RESTORE 폴더를 포함하지 않는다.
