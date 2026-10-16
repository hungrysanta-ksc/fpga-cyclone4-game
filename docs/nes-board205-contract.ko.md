# NES205 로컬 ROM 허용 경계와 중복 타일 버퍼 제거

## 작업 의미

204 전체 보드에서 드러난 raw ROM 상태 우회와 논리 자원 부담을 함께 줄이는 후보다. 동작 클록·PSRAM 속도·SPI 주기·타일 수·화면 품질은 낮추지 않는다. 60fps 전송 경로에 필요한 배치 여유를 확보하는 작업이며 실기 성능 측정 결과는 아니다. 배포186/GBC164/세이브 SRAM과204 원본 증거는 유지한다.

## ROM 상태 경계

204의 `source_ready=!invalid&&!held&&admitted`, `source_writing=invalid`는 memory-clock raw 상태를 NES 데이터 논리까지 통과시켰다.205는 `!held&&admitted`, `held||!admitted`로 바꾼다. raw 상태는 기존 asynchronous-assert/two-edge-release 경계의 reset 입력에서 끝나고, 데이터 허용은 NES 로컬 상태를 사용한다. Gray serial/동기화/안정성 확인/소진 거부는 그대로다.

write·STOP·오류가 오면 클록이 멈췄어도 즉시 무효화하고, 다시 허용할 때는 NES 클록과 epoch 안정화가 필요하다. 현재 fixed CHR-ROM만 지원한다. local unavailable이 source_writing에 포함되므로 이 신호는 실제 메모리 쓰기 핀의 관측값이 아니다. 정확한 물리 CDC/reset 검증은 기능 시뮬레이션과 구분한다.

## 타일 저장 계약

191은 완성한 타일32B를 register 배열에 저장하고,193은 이를 다시 unpublished32B dual-clock RAM에 복사했다.205는 앞쪽 배열을1B holding register로 바꾼다. source192/cache/코어 우선 physical READ16/193 mailbox·RAM·aperture는 그대로다. 기존191의 독립 모듈 계약을 변경하지 않고 새로운205를 보드 후보에만 연결한다.

검사된 메모리 응답 또는 zero byte를 holding register에 넣고 downstream ready 때만 index를 진행한다. bulk193은 마지막 byte까지 받기 전에는 mailbox를 공개하지 않는다. 부분 타일 중 response error/address/generation 불일치, lease 해제, timeout, STOP/reset이 발생하면 공통 취소로 RAM의 소유권을 버린다. payload RAM은 지우지 않아도 공개되지 않는다. 마지막 byte가 timeout 경계에서 수락되지 않도록 out_valid/mem_request를 cycles<MAX_CYCLES로 제한한다.

**단독205의 out_valid는 완성 타일 승인이 아니다.** 부분 스트림을 저장하는193 및 source fault 취소와 짝으로 써야 한다. final tile 완료, chunk seal/consume, frame SEAL/display ACK/retire는 서로 다른 단계다.

## 필요한 검증

- epoch01: 미완료 크기/STOP 재시작/멈춘 NES clock 중 write/reload/fault/소진/reset20검사와 local admission assertion.
- test01: production direct204에205 tile을 연결한 실제 SPI2.625MHz/READ16/194 consume 경로. 보존된 C 계획3장면×3프레임1968B exact186.204 대비 각 장면381183/384357/740051사이클과 코어 read290/316/508이 동일하다. 이 합성 fixture에서는 처리량 회귀가 없지만 게임 FPS로 해석하지 않는다.
- test01/atomic: 실제205+193 RAM/mailbox/aperture에서 partial1/7/15byte 이후7종 실패21경로, 전송 대기 byte 안정성 및 회복 완료1경로로22검사. fault 전파를2NES edge 늦춰도 부분 tile mailbox/chunk가 공개되지 않는다. timeout은 counter를 경계값으로 진행시킨 시험이며 실제 대기시간 측정은 아니다.
- CPU request/PSRAM/계획/lease/최종 ACK는 fixture다. 전체 NES 게임 CPU+ARM+65816 동시 실행이나 실기 화면·사운드 시험으로 세지 않는다. 첫레벨 스크롤 실측은 아직 없다.

전체 MAP/FIT/STA와 새 CDC inventory는 `analysis/board205-verification.json`에 기록한다. 타이밍 예외와 클록 조건은 이번 후보에서 바꾸지 않는다. 원본 raw report를 보존하고 합성 예상 LE, 실제 fitted LE/LAB, STA 도구 종료, 실제 slack 승인을 각각 구분한다. 아직 설치 가능한 짝패키지가 아니다.

## 전체 보드 결과

source01→mapfit01은 한 번의 전체 MAP/FIT다. Fitter 내부 자동 라우팅 재시도는 있었지만 별도 seed 변경/재실행은 없다. 합성 예상18,790 LE, 실제 배치15,182 LE/8,337 FF/961 LAB/47 M9K.204보다128 LE/249 FF/2 LAB 줄었고 메모리 블록은 동일하다. LE226개/LAB2개 여유이며 mapper 확장 여유가 충분하다는 뜻은 아니다. tile 단독은926 ALUT/299 FF→681 ALUT/51 FF로 줄었다. 전체 fitted 절약량과 모듈별 synthesis 절약량을 혼동하지 않는다.

timing01은 같은 DB에서 기존 SDC와 nominal 조건의3corner를 확인했다. 관련 클록 최저 setup−0.739ns/hold+0.148ns로 **전체 타이밍 미통과**다. 이전 check_next→reader.check_response_address 경로는+0.240ns로 개선됐다. 현재 실패는 loaded_bytes[2]→count_complete,9논리단/6.586ns, 그중 배선4.426ns(67%)다. paths02에서 상세 추출했으며 단순히 clock을 느리게 하거나 경로를 제외하지 않았다.

204의 loader.release_reset→export.pack_count raw 우회는3corner 모두 더 이상 경로가 없다. inventory02의 content_lifetime 관련 setup/hold64행은 Gray32비트→각 epoch_meta뿐이며 raw loader 상태의 데이터 우회가 없다. recovery/removal은 별도로152쌍씩 남겨두었다. 이것은 async reset 해제의 전기적 승인까지 끝났다는 의미가 아니다.

새 경계의 실제 첫 단계44개(Gray32+control12)는 각각 두 번째 단계 하나만 구동한다. 전체 cross-clock 목록18,582행을 관련 PLL/Gray/control/held payload/cancel·other/reset/기존 경로로 분류했다. inventory는 기본 STA corner의 목록이며, held-data/Gray 데이터 지연과 reset/cancel의 **전체 corner budget/예외 범위 검증은 미완료**다. broad false_path나 clock-group 예외는 추가하지 않았다.

timing01 안의 첫 topology 추출은 `get_fanouts`에 node ID를 전달해0행이었다. inventory02에서 실제 register collection을 전달하고 빈 결과를 오류로 처리한 뒤44개 연결을 확인했다. 이전 raw 로그는 보존한다. epoch 실행 직후 다음 wrapper의 임시 FLOAT port 종료가 잠시 지연되어 첫 시작 요청은 거부됐지만, 다른 서버를 종료하지 않고 종료 확인 후 test01을 실행했다. 새 라이선스·전역 설정 변경은 없다.

## 다음 작업

205 로컬 상태 경계와 단일 byte stream을 유지한다. 먼저 분류된 새 held-data/cancel/reset 경계를 정확한 프로토콜과 연결해 CDC bounds를 닫는다.9단 완료 판정과 source-count fanout/기존 terminal predicate 재사용 가능성, 작은 캐시·상태 저장을 RAM으로 옮길 때의 자원/포트/추가 cycle을 함께 검토한다. 기존 loader만 반복 미세 수정하거나 seed를 바꾸는 FIT 루프로 돌아가지 않는다. 부분 타일 공개 금지와16.67ms 전송 목표를 그대로 유지한다.

새 구조 근거와 최소 결합 검증 후 전체FIT/STA/IO, actual board→C→SNES 짝 검증으로 간다. 통과한 뒤에만 첫 레벨 연속스크롤 실기판을 만든다. 이번에는 새 ARM/ASM/ZIP/실기 재시험 요청이 없다.
