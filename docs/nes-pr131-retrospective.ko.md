# PR131 회고: 최적화 성과와 실기 60fps 사이에 남은 경계

검토일: 2026-10-25. 구현 기준은 `6674e57c68695b67b02ee36b57fd6868ae2f9831`, PR130 병합 기준은 `d7a96c5652d7c511d061ae5035277027c14ec597`이다. PR131의 NES299–364를 검토했다. 이번 변경은 회고·재현 검사·후속 계획이며 새로운 최적화나 제품 승격이 아니다.

## 판단

ARM이 화면을 계획하고, FPGA가 압축 스트림·소비 추적·독립 검사를 처리하고, SNES가 DMA·표시를 수행하는 역할 분담은 계속 검증할 가치가 있다. 실제로 ARM 중간 변환과 FPGA 중복 순회를 제거한 개선이 있었다. 그러나 현재 자료로 이 구성이 기존 보드에서 지속 60fps를 달성할 수 있다고 확정할 수 없다.

**진행 방식은 수정해야 한다.** 합성용 보드 연결과 기능 테스트 연결이 다르고, 다음 캡처를 놓치지 않는 연속 일정도 검증하지 않았다. 작은 제어 통합을 반복한 뒤 더 큰 ABI 교체를 바로 다음 목표로 정한 것은 실기 통합의 병목보다 최적화를 앞세운 순서였다. PR130 회고에서 경계했던 실험 반복이 PR131에서도 이어졌다.

다음 목표는 “조합 논리 2,471개 삭제”만이 아니라, **같은 구현으로 캡처→전송→소비→표시→다음 캡처를 검증할 수 있는 후보를 만들고 실제 마감을 확인하는 것**이어야 한다. 843개라는 새 실행기 예산은 남는 공간의 산술값이며, 구현 가능성을 입증한 수치가 아니다.

## 실제로 얻은 개선

아래는 기존 전체 Quartus Lite MAP 기록의 비교다. 기능 시험용 작은 모듈 면적을 전체에서 뺀 값이 아니다. 다만 MAP은 배치·배선 FIT 및 STA 통과를 뜻하지 않는다.

| 구성 | 전체 조합 논리 | PR130 대비 | 장치 15,408개 대비 부족 | RAM bits |
|---|---:|---:|---:|---:|
| PR130 끝, NES298 | 17,683 | 기준 | 2,275 | 307,808 |
| NES338 | 17,274 | −409 | 1,866 | 307,808 |
| NES359 host 유지, 선행 읽기 추가 전 | 17,213 | **−470** | **1,805** | 307,808 |
| source338·ARM355·host359 + BG5·OBJ2 | 17,724 | **+41** | **2,316** | 308,832 |

최소 면적 구성은 처음 부족했던 2,275개 중 약 20.7%를 줄였다. 하지만 빠른 구성은 여기에 선행 읽기의 511개·1,024bit가 추가된다. 서로 다른 구성의 최소 면적과 최소 시간을 하나의 성과로 합칠 수 없다. 새 ABI364는 실제 삭제 0개, 새 전체 면적 미측정이다.

유지할 가치가 큰 변경은 다음과 같다.

- **NES325 단일 확장:** FPGA에서 압축을 한 번 풀고 SNES 소비·독립 검사에 연결했다. byte 주소 복원과 중복 RLE 해석을 줄였다. 별도 실제 65816 검증은 해당 소비 경로의 증거이며 전체 펌웨어 실행의 증거는 아니다.
- **NES336 read-event 통합:** 실제 read event가 CRC·coverage·RAM 진행을 소유한다. host receipt 범위와 validator의 중복 순회를 없애 전체 조합 논리 271개를 줄였다. 독립 expected와 실제 소비의 분리는 유지했다.
- **NES338 queue 정렬·D4 재사용:** 256B 정렬과 불변 bank descriptor 재사용으로 추가 104개를 줄였다. 시간 이득은 없지만 실제 회로 삭제다.
- **NES359 host 실행기:** 추가 61개를 줄였다. 반대로 NES363의 source/host 공동 byte 실행기는 132개 증가하여 채택하지 않았다.
- **ARM352·354·355:** 변경 raw 그룹만 처리하고 compact geometry/raster의 복사·재해석을 줄였다. 기록된 normal-service warm907 계열은 13.410066→12.007265ms, 약 1.403ms 개선됐다. 이는 제한 ROM의 최악 시간이나 PR130부터의 동일 위상 비교가 아니다.
- **BG5·OBJ2 선행 읽기:** 실제 수신한 첫 블록과 이전에 확정된 ARM 이력으로 tag를 만든다. 미래 프레임 정답을 주는 방식은 제거했다. 고정 시작 위상 warm907은 25.051563→12.157717ms로 개선됐다. 연속 fixture에서는 20.689706→12.156081ms지만 시작 위상도 달라져 효과를 구분해야 한다.

가드와 실제 M4 실행, SPI 응답·2슬롯 credit·STOP·최종 ACK를 묶어 비용을 확인한 점도 성과다. 하지만 많은 가드의 통과가 아래의 미검증 연결을 대신하지는 않는다.

## 이번 회고에서 확인한 핵심 문제

### 1. 합성용 source/lease 연결은 기능 테스트와 다르며 시작 오류가 재현된다

`probes/nes-execute362/objmap01/nes_live_joint.sv`는 첫 줄부터 RAM 서비스가 resource-only인 wrapper라고 명시한다. 이 wrapper의 source 시작은 `export_permitted && start_ready && !source_started`이며, source에는 `captured_epoch204`와 `captured_gen204`가 전달된다.

그러나 실제 `nes_capture_lease201`은 이 출력들을 **source 입력 완료 후 export_release 시점**에 표시 문맥으로 갱신한다. 첫 캡처가 준비되어도 그 전에는 둘 다 0이다. 실제 source core는 epoch 0을 거부한다. 또한 시작 식에 캡처 준비 조건이 없어 캡처 전 시작도 가능하고, `source_started`는 표시 lease가 없으면 계속 지워진다. 이는 입력 소유권과 표시 소유권을 별개로 다뤄야 할 문제다.

이번에 원본 source core·lease 모듈을 변경하지 않고 wrapper 식을 가져온 Questa 검사를 실행했다.

| 검사 | 결과 |
|---|---|
| 원래 시작 식, 캡처 없음 | source fault 1 재현 |
| 캡처 준비 gate만 추가, 첫 유효 캡처 | 이전 표시 epoch/generation=0 때문에 source fault 1 재현 |
| 현재 캡처 epoch/generation과 준비 gate를 주는 대조군 | source admission 성공, query generation=1 |

최종 join02는 3개 검사 모두 예상 결과와 일치하고 오류·경고 0이다. 대조군은 collector query 데이터·STOP drain·전체 보드를 검사하지 않으므로 완성된 수정안이 아니다. join01의 미연결 출력 경고도 원본 로그로 보존했다.

기존 기능 TB는 현재 generation과 고정 epoch 1을 직접 전달하고 캡처 완료 후 수동으로 시작한다. 따라서 그 PASS로 위 보드 연결을 검증했다고 볼 수 없다. **실기에서 재현한 고장이 아니라, 자원 산정 wrapper의 시작 경계를 원본 모듈로 재현한 결과**다. production227의 새 회귀라고 주장하지 않는다.

근거: `nes_live_joint.sv:299–329`, `nes_capture_lease201.sv`, `nes_native_frame201.sv:30–32`, 기능 TB `joint266_tb.sv:141,958–990`. 재현 도구는 [probe_nes_pr131_join.py](../tools/probe_nes_pr131_join.py), 입력 해시와 결과는 [회고 분석](../analysis/pr131-retrospective.json)에 고정했다.

### 2. “입력 시작부터 표시까지 12.16ms”는 다음 프레임을 놓치지 않는다는 증거가 아니다

최신 기능 TB는 한 프레임의 PPU 자극을 모두 공급하고 source를 시작한 다음, output_frame과 최종 ACK까지 끝나야 다음 PPU 프레임을 공급한다. `start319→frame_done`에는 앞선 캡처 시간이 들어 있지 않다. 허용된 캡처/표시 중첩도 실제로 실행하지 않는다.

더 구체적인 마감 문제가 있다. 현재 collector는 `scanline=7,dot=257`에 시작하고, 이전 캡처의 `owned`가 남아 있으면 새로 시작하지 않는다. 캡처의 fetch 종료는 `232,1`이며 source 입력 완료까지 이전 캡처를 소유한다. 현재 fixture의 262라인·dot당 NES 4클록·45.454ns 조건에서는 종료 지점부터 다음 시작까지 최대 여유가 다음과 같다.

`(262×341 − (232×341+1) + (7×341+257)) × 4 = 51,492클록 = 2.340517ms`

BG5·OBJ2 warm907의 실제 기록상 source 입력 시작→완료는 고정 위상과 연속 fixture 모두 **2.838466ms**다. 캡처 뒤 drain·시작 대기를 제외하고도 위 상한보다 **0.497949ms 길다**. 같은 cadence에 그대로 연결한다면 다음 capture_begin을 놓칠 가능성을 먼저 해결해야 한다. 현재 지연된 stimulus 루프는 이 상황을 만들어 주지 않는다.

이는 기존 모델에 대한 정적 마감 감사다. 자유 실행 PPU/collector 실험이나 실기 프레임 손실 측정은 아직 아니다. 실제 NES/SNES 클록·위상·capture trigger를 연결해 확인해야 한다. 또한 fixture의 캡처 시간을 12.16ms에 단순히 더해 실기 FPS를 계산해서도 안 된다. 입력을 더 일찍 끝내거나 안전한 immutable handoff/추가 저장으로 collector를 제때 해제하는 구조가 필요할 수 있으며, 그 RAM·포트·회로 비용을 함께 계산해야 한다.

### 3. 가장 중요한 선행 읽기 구간에 NES core의 ROM 경쟁이 빠져 있다

기능 TB의 ROM core 요청은 `active263 && core_ready267 && romcycle267%120==3`이다. `active263`은 source 입력 뒤의 output_frame에서 켜진다. 따라서 **source 입력 도중의 hint fill에는 이 core 경쟁 요청이 0**이다. arbiter 우선순위 검사가 별도로 있다는 사실과, 이 일정에서 실제 core 부하가 계속 적용된다는 것은 다르다.

빠른 연속 fixture에서 hint fill은 1.682957ms, 첫 허용 ROM 구간 상한은 1.712318ms로 여유가 **29.361µs**에 불과하다. 실제 M4 helper 4,497 instructions·EA 28B·캐시 112B/물리 저장 128B 비용은 들어 있지만, 전체 펌웨어의 source 수신/선행 읽기 foreground loop·IRQ 최악 지연·캡처 중 NES core 요청을 모두 묶은 보장은 없다. 이 여유를 일반적인 60fps 여유로 해석할 수 없다.

### 4. 넓은 동작 범위와 실기용 산출물이 아직 없다

빠른 최종 일정의 주요 표본은 905·906·907이다. 71프레임 decoder/geometry 검증은 71프레임 전체 capture/display 실행과 다르다. 905/906 cold 구성은 약 99/117ms이므로 부팅·로딩 정책과 gameplay 중 STOP/무효화 후 cold 복귀 정책을 분리해야 한다. gameplay에서 발생하는 누락·반복 표시를 startup 비용으로 감출 수 없다.

신규 구성의 전체 FIT/STA, 새 CDC/외부 IO 경계 검토, 같은 버전의 FPGA·ARM·65816 산출물을 올린 실기 구동은 없다. 기존 board/CDC SDC를 복사한 사실만으로 새 경계의 타이밍이 보장되지 않는다. 전용 generated RTL과 ARM 코드는 실제 실험 구현이지만, master 대비 제품 실행 코드로 승격된 상태는 아니다. production227·GBC164·saveSRAM은 유지됐다.

## 왜 지금 큰 ABI 교체부터 시작하면 안 되는가

NES364의 보존 영역은 source 1,769 + checker/aperture 1,250 + 나머지 11,391 = 14,410개다. host/queue/SPI/plan 3,314개를 843개 이하로 바꿔야 155개 예비분을 남긴 15,253개가 된다. **74.6% 삭제**가 필요한 셈이다. 기존 queue/SPI/plan만 1,251개여서 host만 줄여서는 불가능하다.

이 계산은 유용한 거절 기준이다. 하지만 새 실행기의 RAM 포트·CDC·credit·STOP·독립 검사·최종 ACK까지 포함해 843개에 들어간다는 증거는 없다. 변환기만 실행한 ABI364 시간도 새 receiver의 실제 시간이 아니다. 기존 serializer와 기존 FPGA 패킷을 유지하고 helper 및 양의 전송 비용을 더한 진단이며 새 fragment credit/status CPU 대기는 미검증이다.

따라서 새 ABI를 즉시 구현하기 전에 같은 보드 연결의 정확성과 캡처 마감을 먼저 확보해야 한다. 그 결과 capture handoff RAM이나 새 source 공급이 필요하면 지금의 고정 영역·삭제 예산 자체가 달라진다. 반대로 필요한 제품 기능과 진단용 자원 wrapper를 구분하면 더 넓은 실제 삭제 범위를 찾을 수도 있다. 독립 검사를 없애거나 비용을 다른 블록에 숨기는 절감은 인정하지 않는다.

## 제안하는 다음 순서와 중단 기준

1. **하나의 재현 가능한 통합 후보:** source338·ARM355·host359와 BG5·OBJ2의 코드/ABI/clock/port/소유권 목록을 고정한다. 기능 시험과 자원 합성이 같은 top·admission 연결을 사용하게 한다. 현재 캡처 문맥과 표시 문맥, 입력 시작 latch, STOP drain, STOP 뒤 DONE 차단을 먼저 검증한다. 원본 조각의 직접 구동으로 보드 연결을 우회하지 않는다.
2. **지속 캡처·표시 일정:** PPU 프레임을 표시 완료와 무관하게 공급하고 capture N+1과 output N을 실제로 겹친다. 입력·출력 전 구간의 NES ROM 요청, ARM source 수신·hint·IRQ, SNES DMA/poll/VBlank/최종 ACK를 포함한다. 먼저 다음 capture_begin 및 실제 표시 cadence를 확인한 뒤 heavy 952/954/955/962/963/968/970과 71프레임으로 넓힌다. frame ID 누락·중복, queue 적체, capture 재시작 지연, 표시 간격, 처리 지연을 별도 기록한다.
3. **검증된 일정에 맞춘 큰 구조 변경 한 건:** 유지할 기능 전체와 실제 삭제할 RTL을 고정하고, source/host뿐 아니라 보존 11,391개의 경계도 감사한다. 새 전송은 실제 ARM serializer와 새 receiver를 직접 연결한다. 동일 위상/위상 변화 모두에서 일정과 전체 Lite 비용을 확인한다. 작은 FSM·opcode·seed 변경 반복을 다음 단계로 삼지 않는다. 시간 또는 전체 공간이 안 맞으면 역할·표현·하드웨어 적합성을 재검토한다. 자동 구매나 Standard 전환은 하지 않는다.
4. **실기 진입:** 같은 후보의 전체 FIT·STA·CDC·외부 IO 검증을 통과한 뒤 FPGA/ARM/SNES 버전을 묶어 부팅한다. 이후 연속 스크롤·음성·입력·메뉴·STOP/재시작·saveSRAM을 포함해 frame ID와 출력 cadence를 실측한다. 16.667ms는 설계 예산이며 실제 리전/클록의 표시 주기에 마감을 맞춘다. 장시간 시험의 반복/누락 횟수와 최악 지연을 보고한다.

과대 면적 후보로도 1–2의 시뮬레이션은 가능하다. 그러나 보드에 들어가지 않는 bitstream을 실기 단계로 넘길 수는 없다. 반대로 면적만 줄어도 캡처/표시 마감이 틀리면 60fps 후보가 아니다. 두 조건을 같은 구현에서 만족시켜야 한다.

PR131은 연구 결과와 실패 원인을 정리한 체크포인트로 마감하는 것이 적절하다. “60fps/실기 준비 완료”로 승격하지 않는다. 병합은 사용자가 결정한다. 후속 계획은 [nes-pr131-next-plan.json](nes-pr131-next-plan.json)에 제안 상태로 기록했으며 새 구현은 이번 회고에 포함하지 않았다.

## 이번 검증과 증거 범위

- 기존 전체 MAP·ARM·일정 기록을 다시 읽고 수치와 24개 입력 SHA-256을 재계산했다. [analyze_nes_pr131.py](../tools/analyze_nes_pr131.py) → [analysis/pr131-retrospective.json](../analysis/pr131-retrospective.json).
- 승인된 Questa Starter FLOAT wrapper로 실제 원본 lease/core를 실행했다. `probes/nes-pr131-review/join02`의 3개 검사와 원시 로그를 보존했다. 라이선스·서버 로그는 Git에 넣지 않았다.
- join01의 출력 미연결 경고와 최초 분석기의 공백 의존 검색 실패는 보존했고, join02/analysis02에서 보정했다. 제품 RTL 수정이나 새로운 성능·MAP/FIT/STA 실행은 하지 않았다.
- 초기 PR131은 구현 기준에서 66 commits/548 changed files였다. 변경량은 진행 증거일 뿐 60fps 준비도의 척도가 아니다. 위 한계는 과거 component PASS를 취소하는 것이 아니라, 그 PASS가 덮지 않은 실기 경계를 명시한다.
