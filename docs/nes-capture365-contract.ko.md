# NES365–366: 공통 source 시작 경계와 collector 읽기 완료 handoff

PR131 병합 `914138969246387162bf2c909159824e72a3666d`가 origin/master에 포함됨을 확인하고 `codex/nes-capture-admission-365`에서 시작했다. source338·ARM355·host359·BG5/OBJ2를 보존한다. 이 변경은 source/lease 연결과 캡처 재시작의 수정이며, 전체 보드의 공간 부족이나 지속 60fps 달성을 해결했다는 승격이 아니다.

## 구현

기능 TB의 수동 source start·현재 generation 주입·고정 source epoch 연결을 제거했다. 보드와 기능 시험 모두 [nes_native_capture365.sv](../src/fpga/nes_native_capture365.sv)를 사용한다. 실제 collector의 capture_begin에 묶인 epoch/generation이 유효하고, immutable ROM과 geometry가 확인된 뒤 한 번만 source를 시작한다. 입력 완료 뒤에야 갱신되던 표시 문맥으로 처음 source를 시작하던 PR131 오류가 없어졌다.

admission에서 저장한 source epoch/generation/serial은 **최종 표시 ACK와 drained plan retirement가 모두 끝날 때까지** 유지한다. 다음 collector 프레임의 generation이나 count가 바뀌어도 source, plan, tile, receipt, 출력 identity가 다음 프레임 문맥으로 바뀌지 않는다. SPI 입력 ACK도 현재 collector generation 대신 이 저장된 source generation을 사용한다.

독립 expected/actual 검사, MASK/SHIFT와 출력 압축, 2슬롯 저장 credit, 실제 read-event CRC/coverage, token, 최종 12B exact-read ACK 경로는 유지했다. source의 출력 바이트나 기존 ARM/65816 ABI를 바꾸지 않았다.

### collector 읽기 완료와 ARM 입력 완료를 분리

시작 오류만 수정한 NES365에서도 다음 캡처 누락이 재현됐다. warm907 입력 ACK는 약 2.84ms에 끝나는데 다음 capture_begin은 약 2.34ms에 온다. 그러나 마지막 collector query와 내부 저장은 약 1.71ms에 완료된다.

NES366은 [nes_capture_lease366.sv](../src/fpga/nes_capture_lease366.sv)로 다음 단계를 분리한다.

| 단계 | 소유권과 허용 작업 |
|---|---|
| 캡처 준비 | 실제 collector/ROM context를 검증하고 source 문맥 저장 |
| 마지막 collector 읽기 확정 | canonical base와 마지막 record 작업 데이터가 기존 FPGA RAM에 존재함을 source core가 통지. collector RAM 해제 |
| ARM 수신·입력 ACK 대기 | local source lease로 기존 RAM·압축 record를 전송. 다음 collector 캡처 허용. 출력 identity는 아직 공개하지 않음 |
| 유효한 입력 ACK | display lease와 identity 공개. 이 ACK는 진행 중인 다음 collector를 해제하지 않음 |
| 최종 표시 ACK + drained plan retirement | 해당 표시 문맥을 닫고 다음 source admission 허용. 다음 collector는 보존 |

추가 프레임 RAM이나 geometry 복사는 없다. 기존 source base RAM과 scratch/transport 저장이 해당 데이터의 소유자가 된다. 이 RAM은 다음 source 실행 때까지 보존하며, 기존 source/output phase RAM 전환은 계속 입력 ACK 뒤에 일어난다. collector RAM만 다음 캡처가 사용한다.

source의 `capture_materialized366`은 pending query가 없고 마지막 raw block 저장이 끝난 BLOCKEND, 또는 raw0의 RAWSTART에서 발생한다. 그 뒤 collector query가 한 번이라도 나오면 통합 TB가 실패한다. raw0/1/2의 실제 source core를 별도로 실행해 이 경계를 검사했다.

STOP, ROM epoch 변경, source 오류는 local/display lease를 즉시 무효화하고 재시작을 차단한다. 늦은 DONE으로 identity를 공개할 수 없다. ownership 오류가 cancel로 lease FSM을 지운 뒤 사라지는 문제도 수정해 첫 오류를 보존한다. STOP 이후 재개는 기존과 같이 quiesce/reset/cold 절차가 필요하다.

## 같은 구현으로 시험·합성

변경한 공통 RTL 10개를 [canonical manifest](../src/fpga/nes_capture365/manifest.json)에 고정했다. 새 두 모듈과 source/host/plan의 실제 SV 본문을 Git에서 검토할 수 있다. [생성 도구](../tools/nes_capture365.py)는 이 파일들을 양쪽에 그대로 복사한다. 기능 전용 lease나 별도의 plan 구현을 사용하지 않는다.

최종 `early03`과 전체 Lite `map03`에서 공통 경계 10개가 byte-identical이다. QSF에 실제 포함된 파일 기준으로 collector·validator·queue 등을 포함한 공유 모듈 30개의 identity도 일치한다. source 시작/문맥/identity/retire와 plan의 연결 역할도 일치시켰다. PPU·SPI·메모리의 외부 구동은 각각 시험 fixture와 보드 IO이므로 전체 보드 시뮬레이션 또는 실기 타이밍 sign-off를 뜻하지 않는다. 기존 resource-only 보드 RAM 서비스 한계도 남아 있다.

선택한 `EARLY_RELEASE=1`을 기능/보드에서 모두 사용한다. `0`은 기존 입력 ACK 해제를 대조·재현하는 용도이며 제품 선택값이 아니다. 원본 controller/lease는 변경 후 공통 모듈의 inactive generate 분기와 비교 증거로만 남는다.

## 실제 연속 캡처 결과

선택: `probes/nes-capture365/early03`, `guards04`, `rawguards02`, `map03`. 905–908의 실제 collector query·수신 바이트·ARM 출력·일반 65816 버스 trace·tile ROM·receipt·최종 ACK 검사가 통과했다. 907 출력과 실제로 다른 908의 PPU 데이터를 중첩했고, 이어서 909의 capture_begin도 공급했다.

| 이전 프레임 | 내부 저장 확정 | ARM 입력 ACK | 다음 캡처 시작 | 해제 여유 |
|---|---:|---:|---:|---:|
| 907 → 908 | 1.711980ms | 2.838444ms | 2.340269ms | **0.628289ms** |
| 908 → 909 | 0.576947ms | 2.480084ms | 2.340223ms | **1.763276ms** |

시간은 각 이전 프레임의 source 시작 기준이다. 두 캡처 모두 **입력 ACK 전에** 시작했다. 이후 908의 전체 데이터·출력 검사가 통과하므로 907의 늦은 입력 ACK가 908을 지우지 않았음도 확인했다.

- 시작 수정만 적용한 대조군 `cadence01`: 2회 시도 중 1회 누락, 다음 주기에 회복.
- 최종 `early03`: **2회 시도 모두 admission, 누락 0회**. handoff 이후 query 0회.
- source/lease 제어 가드 **22개**: STOP/늦은 DONE/입력 ACK 전 seal 요구/중복 seal/다음 캡처 보호/ROM mutation/최종 ACK 순서/reader drain/generation16 wrap 통과.
- 실제 source core의 **raw0/1/2**: 마지막 query 이전 조기 해제 및 해제 이후 query가 없음을 확인.

이 fixture는 dot당 NES 4클록·262라인·45.454ns, 프레임 간격 357,368클록을 사용한다. 905/906은 초기 준비용으로 직렬 공급했고 연속 cadence는 907 이후부터다. 908 전체 캡처와 출력, 909의 시작까지의 **두 마감 검사**이며 909 전체 데이터나 71프레임 지속 실행을 검사한 것은 아니다. 실제 리전/클록의 장시간 출력 주기는 별도 검증해야 한다.

## 입력 중 ROM 경쟁과 남은 시간 문제

입력 중에도 ROM core 요청을 계속 적용했다. 기존 output 단계뿐 아니라 source 시작부터 입력 ACK까지도 ready-gated 120 NES 클록 간격·주소001234의 부하가 발생한다. **입력 요청/응답 5,736건**이 모두 완료됐고 반환 데이터 및 물리 grant의 core 우선순위를 확인했다. 실제 NES CPU 요청 trace를 연결한 부하는 아니다.

| 프레임 | source 시작 → 최종 ACK | 16.667ms 대비 초과 |
|---|---:|---:|
| 905 초기 준비 | 99.273422ms | 82.606755ms |
| 906 초기 준비 | 116.690214ms | 100.023547ms |
| 907 warm | **12.155968ms** | 0 |
| 908 실제 다음 warm | **20.651275ms** | **3.984608ms** |

907의 처리 시간은 동일한 시작·ROM 위상의 시작 수정 대조군과 같다. handoff는 처리 시간을 줄인 것이 아니라 collector를 제때 재사용하게 만든 변경이다. 908은 입력 ACK 뒤 출력에 18.171191ms가 걸려 표시 예산을 넘었다. 따라서 캡처 두 번을 놓치지 않았다는 사실을 지속 60fps 달성으로 합칠 수 없다.

현재 harness의 causal BG5/OBJ2 hint는 907에만 생성한다. 908에는 새 hint가 없어 이 수치를 일반적인 per-frame hint 구현의 성능으로 해석해서도 안 된다. 다음에는 실제 ARM foreground에서 매 프레임의 수신 정보·확정 이력으로 hint를 공급하는 경로와 후반 ROM 대기를 연결해야 한다. 미래 plan oracle을 hint 입력으로 주거나 907의 좋은 결과만 재사용하지 않는다.

## 전체 Quartus Lite 비용

| 전체 구성 | LE | 조합 논리 | FF | RAM bits |
|---|---:|---:|---:|---:|
| 기존 빠른 362 | 22,733 | 17,724 | 9,179 | 308,832 |
| 시작 수정 365 | 22,774 | 17,733 | 9,216 | 308,832 |
| 최종 handoff·오류 보존 366 | 22,817 | **17,776** | **9,217** | **308,832** |

기존 빠른 구성 대비 **+52comb/+38FF/추가 RAM 0**이다. 정확성과 캡처 마감을 위한 비용이며 면적 절감으로 보고하지 않는다. 장치의 조합 논리 15,408개보다 **2,368개 부족**, 155개 예비분을 포함한 목표까지 **2,523개 삭제**가 필요하다. 기존 843개 실행기 예산은 재계산해야 하며 새 전체 삭제 경계를 아직 확정하지 않았다.

MAP만 실행했다. 전체 FIT·STA·새 CDC/외부 IO sign-off·bitstream/실기 구동은 없다. Quartus Lite를 사용했고 Standard 평가나 구매를 시도하지 않았다.

## 보존한 검사와 검증 한계

independent validator·실제 read-event CRC/coverage·저장 credit/소비 완료 분리·12B exact reads/token/final ACK 본문은 변경하지 않았다. 새 제어는 input ACK 전 identity 공개나 plan retirement 선행을 허용하지 않는다. 기존 SNES VBlank 표시 코드를 변경하지 않았다.

출력 ARM은 실제 M4 명령을 실행해 live RTL status/IRQ/SPI에 반응한다. source ARM 비용은 exact 수신 바이트에 대한 측정된 M4 처리 비용이며 source foreground 전체와 IRQ preemption의 실기 WCET는 아니다. 일반 65816 명령은 기존 실제 버스 trace를 재생하지만 map DMA·최종 표시 ACK는 버스 모델이다. **VBlank를 포함한 전체 65816 실행을 이번 일정에 새로 결합한 검증은 남아 있다.** 이 한계를 생략한 실기 FPS 주장은 하지 않는다.

첫 시험의 생성/선언 오류와 합성용 tile_closed 포트 차이, 908 oracle 파일 누락은 원시 로그로 보존했다. `guards03`이 찾아낸 ownership 오류 보고 소실은 실제 제어 수정으로 해결했고, `guards04`와 `early03/map03`을 최종 선택했다. 중간 성공을 최종 소스로 대체해 기록하지 않았다. 라이선스/서버 로그 및 게임 데이터는 Git에 포함하지 않는다. production227·GBC164·saveSRAM은 변경하지 않았다.

다음 단계는 매 프레임 causal hint와 실제 ARM/SNES 서비스를 넣은 더 긴 연속 일정, heavy7/71 및 위상 변화 검증이다. 이 일정으로 지켜야 할 소유권/RAM 비용을 확정한 뒤 전체 회로 삭제 범위를 재검토한다. [검증 JSON](../analysis/capture365-verification.json), [후속 계획](nes-capture365-plan.json), [재계산 도구](../tools/analyze_nes_capture365.py).
