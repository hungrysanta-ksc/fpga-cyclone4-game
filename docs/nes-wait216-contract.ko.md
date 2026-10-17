# NES216 정상 대기와 타일 실행 watchdog 구분

## 작업 의미

스테이지 선택에서 종료되는215 실기 오류와 동일한 응답을 실제 C와 FPGA 전송 경로에서 재현하고, 정상적인 대기를 실패로 처리하는 타일 watchdog을 수정한다. 프레임 큐와 변경 타일 재사용을 유지하는 동작 수정이며, 관측 로그를 더 만드는 작업이 아니다. 별도 SRAM, 프레임 RAM, 전송 확인 절차를 추가하지 않는다. 이 수정 자체를60fps 개선으로 주장하지 않는다.

## 재현 범위와 결과

실제215 C plan service와 선택207의 SPI200→batch206→lease201→source192/cache/READ16→bulk206→SNES descriptor/aperture를 사용한다. 첫 E9 뒤 MCU가 계산하거나 소비를 늦추는 상황을 명시적 NES clock 대기로 만든다. metadata/ROM contents와 SNES 소비·최종 표시 ACK는 fixture다. 실제 게임 CPU, 실제65816 실행, 전기적 타이밍을 포함하지 않는다.

| 조건 | 기존판 | 수정판 |
|---|---|---|
| 소비 지연500,000 NES cycles (fixture 약22.73ms) | 3frame/57plans/55chunks/1072B 정확히 완료 | 중복 실행 안 함 |
| 소비 지연1,200,000 cycles (약54.54ms) | EMIT/index0/out_ready0에서 제한 초과 | 같은 입력 정확히 완료, 3retire |
| ROM 승인 지연1,200,000 cycles | FETCH/index0/mem_ready0에서 제한 초과 | 같은 입력 정확히 완료, 3retire |

실제 선택된 제한은1,048,576 cycles다. 단독 모듈 기본4096이 아니다. fixture22MHz에서는 약47.66ms, 실기21.477MHz에서는 약48.82ms에 해당한다. 기존판의 최초 오류는 tile watchdog이며 arbiter/lease/denied/SPI/batch/bulk/consume/command 오류가 선행하지 않았다. 이후 실제 C가 받은20B는 두 실기와 정확히 같다.

```
00 d7 04 80 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 7f
```

이로써 **동일 증상을 만드는 정상 대기 오판 결함**을 재현했다. 실기에는 내부 최초 오류 기록이 없으므로215 실기 고장의 유일한 원인으로 확정하지 않는다. 수정판의 실제 스테이지 선택·첫 레벨로 확인해야 한다.

## 변경 계약

`nes_tile205.sv`의 실행 counter 증가 조건을 변경하고, 종료값까지 표현 가능한 폭으로 줄인다. 선택216의 제한1,048,576에는21bit가 필요하며 기존32bit보다11FF 적다. 상한값 자체는 유지한다.

- FETCH에서 일반 ROM byte를 요청했으나 `mem_ready=0`이면 아직 승인을 받지 못한 대기이므로 계산하지 않는다.
- EMIT에서 `out_ready=0`이면 불변 byte를 소비자가 가져갈 때까지 유지하는 대기이므로 계산하지 않는다.
- WAIT는 승인된 읽기의 응답을 기다리는 실행 구간으로 계속 계산한다. 응답이 사라지면 기존 제한에서 실패한다.
- 제한 값, CRC/주소/세대 검증, source lease, STOP/reset, fault 전파, 부분 타일 공개 금지와 final display ACK는 그대로다.

대기 중 상위 frame/session 취소와 소유권 상실은 여전히 즉시 작용한다. 무기한 소비 정체를 타일의 실행 오류로 판단하지 않으며, 제품의 기존60초 RUN deadline·poll/step guard와 COMMON STOP이 세션 종료를 소유한다. 향후 무제한 플레이는 별도 취소/진행 정체 정책이 필요하며, 이번 변경으로 해결됐다고 간주하지 않는다.

## 보호 및 회귀 검증

신규9조건을 외부/내부 계획 모드 각각 검사: 제한보다 긴 ROM 승인 대기·7byte 진행 뒤 출력 대기의 안정성/회복, 실제 미응답 timeout(강제 counter 주입 없음), reader error/주소/세대 오류, 대기 중 lease/STOP/reset 취소, 새 실행 복구. 기존205 부분 tile RAM 공개/late fault/STOP/reset22조건도 통과한다. guards01은 회귀 harness의 reset 모듈 의존성 누락, guards02는32bit 후보, guards03이21bit 선택 결과다. 제품 RTL 오류와 구분한다.

하드웨어 전에는 전체 FIT·관련 clock 타이밍·CDC/reset/I/O 경계와 paired ROM/ARM 검사를 마쳐야 한다. 기존207 source90파일 중 변경은 `nes_tile205.sv` 하나이며 seed/clock/SDC/pin은 그대로다. 결과와 선택 archive는 [검증 기록](../analysis/wait216-verification.json)을 따른다. 이전215 패키지·GBC164·세이브 SRAM은 유지한다.

## 배포 전 남은 조건

**기능 수정은 통과했지만 타이밍 미달로 미채택이며 새 ZIP은 없다.**

- source01(32bit): 전체 FIT 통과, 엄격한 setup -0.153ns. 기존 loader phase→loaded_bytes 경로.
- source02(21bit): 전체 FIT15,168LE/8,349FF/960LAB/47M9K 통과.240LE/3LAB/9M9K 여유. nominal/strict setup -0.320ns, hold +0.149ns.
- 정확한 실패는168MHz `control.load_valid → loader.error_code[1].ena`:5LUT, 데이터6.179ns 중배선3.975ns(64%). 변경한 tile counter에서 출발하는 보고 경로는 setup +36.322ns다. 타일 watchdog 기능 오류와 로더 경로의 배치 후 타이밍 실패를 혼동하지 않는다.
- 기존 기준으로 CDC4,392행/첫단계45개 단일fanout, 미분류 신규 데이터0. held6.597ns/Gray6.812ns, epoch96reg reset 검사 통과. 조건부 I/O는PSRAM +2.345ns/SNES85.802ns/SPI166.065ns 및 payload reset 통과. 전체 전기적 signoff는 아니다.
- ARM은215에서216의파일명/표시식별자3파일만 변경.207536B/static27868/RUN32096/IRQ508/margin4952 동일. budget/plan schema215 유지. check01은 sandbox Win623, check02 통과. 새FPGA와 짝지은 ASM·ROM 바이트 확인 전이므로 빌드된FW 단독 설치 금지.

다음 작업은 보고된 로더 오류코드 enable 경로의 공유/우선순위 조합을 정확히 보존하며 짧게 만드는 것이다. 타일 대기 수정과21bit 폭은 유지하고, 단독 loader microFIT·seed 반복·clock/SDC 완화는 하지 않는다. 논리 변경이 필요하면 기존 명령충돌/STOP 쓰기드레인/상태별 오류코드 검증을 적용하고 전체보드 타이밍을 통과한 뒤 현재212 SNES ROM/ASM과216 ARM을 짝짓는다. 이후 사용자에게216 한 번의 스테이지 선택→첫레벨 스크롤 시험을 요청한다. 같은215/044/추가영상은 지금 요청하지 않는다.
