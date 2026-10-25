# NES363 — NES 로컬 행 공급과 source·host 바이트 실행부 교체

source338·ARM355·359 host와 BG5·OBJ2 선행 읽기를 기준으로 실제 RTL을 교체했다. **선행 읽기의 시간 이득은 유지했지만 조합 논리는 +132개 늘었다. 회로 절감 후보로 채택하지 않는다.** 이번 교체는 핵심 바이트 실행부에 해당하며, descriptor·manifest·RLE·DMA를 지휘하는 source/host 상위 FSM 전체를 없앤 것은 아니다.

## 실제 삭제와 추가

- NES 로컬 query가 기존 의미검사를 수행하고, 640..705와 800..865의 두 66B 행 슬롯을 채운다. 각 슬롯의 generation/block/length/slot descriptor는 마지막 바이트를 host codec이 소비한 뒤에만 반환된다. per-query host 요청/응답 CDC는 생성 결과에 없다.
- source codec·base history·전송기는 84MHz host에서 동작한다. source의 FSTORE/SREAD, host의 PCAP/PUT 상태와 별도 new_byte/held 레지스터를 삭제했다. 하나의 CAPTURE/HOLD 실행 상태와 데이터 레지스터로 source 행 읽기·압축 레코드 출력·host payload 전달을 처리한다. source FETCH와 SBYTE, host PREAD는 공통 실행기 요청·완료를 기다리는 상위 상태로 남는다.
- 기존 source transport의 40bit descriptor CDC 두 개와 prepared ACK CDC, publish/sent 동기화 제어를 제거했다. host 내부의 23bit descriptor 저장은 남는다. 시작·입력 완료·최종 표시 ACK CDC와 collector 취소 완료는 명시적으로 유지한다. 두 행 descriptor CDC와 소유권 제어는 새 비용으로 포함한다.
- MASK·SHIFT와 output RLE 압축을 보존한다. source CRC와 validator CRC는 각각 유지하며, 359 독립 validator 파일은 기준과 바이트 단위로 같다. packet/header/descriptor/manifest/receipt의 상위 실행 및 RLE seed·진행 제어는 남아 있다.

## 고정 RAM 포트와 완료 경계

port A는 NES 행 쓰기, port B는 host source codec과 출력 validator가 단계별로 공유한다. 클록 mux와 추가 RAM은 없다. source scratch는 delta512..577/header768..787/mask896..904이고 행 슬롯과 겹치지 않는다. 하지만 행 슬롯은 출력 단계의 ordinary receipt512..677/H2 680..711/map receipt768..1023과 겹친다.

따라서 두 행 descriptor의 반환, 로컬 query 종료, source 전송 drain을 확인한 뒤에만 입력 ACK/DONE와 출력 lease를 넘긴다. validator의 최초 RAM 초기화는 입력 시작 이전에 끝나야 한다. STOP은 행 쓰기·공통 실행기·source 출력을 막고, collector가 취소를 적용한 뒤 남은 응답과 descriptor 반환을 확인한다. 취소 뒤 DONE 공개를 차단하며 NES plan cursor도 0으로 돌린다. plan cursor는 출력 단계에서 같은 NES 로컬 cursor를 재사용한다.

## 실제 ARM·IRQ·두 슬롯·ROM 일정

| 일정 | 프레임 | 기준 ms | 후보 ms | 차이 µs |
|---|---:|---:|---:|---:|
| 연속 | 905 | 99.270627 | 99.270718 | +0.091 |
| 연속 | 906 | 116.702145 | 116.687463 | -14.682 |
| 연속 | 907 | 12.156081 | 12.156218 | +0.137 |
| 동일 시작 위상 | 905 | 98.643135 | 98.643226 | +0.091 |
| 동일 시작 위상 | 906 | 117.983220 | 117.968629 | -14.591 |
| 동일 시작 위상 | 907 | 12.157717 | 12.157854 | +0.137 |

동일 시작 위상은 각 프레임의 시작 시각과 ROM cycle을 기준과 정확히 맞춘다. 연속 일정은 직전 완료 시간이 다음 프레임 위상에 반영된다. 서로 다른 일정의 차이를 최적화 효과로 합산하지 않는다. warm 연속 시작 ROM cycle은 5677168, 기준은 5677489다.

warm 첫 입력 블록 decode 완료는 연속 1.458202ms, 고정 1.458201ms다. ARM355 실행 이미지와 BG5·OBJ2의 실제 M4 helper는 그대로이며, 추가 helper 4,497개 명령·EA28B·112B 유효 cache·공유 SPI를 포함했다. 선행 정보는 수신 완료한 첫 source block과 이전에 commit된 ARM 상태로 만든다.

연속 hint SPI 시작/종료/fill은 1.512809/1.606142/1.693366ms, 고정은 1.512808/1.606141/5.067052ms다. 첫 ROM 허용 구간 상한까지 남은 fill 여유는 각각 33.543/1022.675µs다. 실제 foreground·모든 IRQ 지연을 보장하는 하드웨어 WCET가 아니다.

warm 연속 source SPI 668B + hint28B + output 1028B, source empty poll 8회, E2 poll 18회를 청구했다. OBJ 첫 plan/tile은 8.607874/8.608329ms다. 독립 소비 순서, token, CRC, unit coverage, private RAM 쓰기 뒤 ACK 공개, 최대 2credit 및 최종 12read를 대조했다. 압축 source records와 출력 명령 바이트는 기준과 같다.

## Quartus Lite 전체 비용과 판단

| 전체 MAP | LE | 조합 논리 | FF | RAM bits |
|---|---:|---:|---:|---:|
| 기준 BG5·OBJ2 | 22733 | 17724 | 9179 | 308832 |
| NES363 | 22789 | 17856 | 9127 | 308832 |
| 차이 | +56 | +132 | -52 | +0 |

device 조합 논리 한도15408 대비 2448개 초과다. 기존 목표15253은 여유155개를 포함하므로, 필요한 순절감은 **2471 → 2603개**로 늘었다. FF 감소를 조합 논리 절감이나 배치 성공으로 해석하지 않는다. FIT/STA는 실행하지 않았다.

중복 없는 합계는 source-host 4061, 독립 checker/aperture 1182, queue/SPI 779, plan 468, 나머지 11366 = 17856comb다. source-host에는 행 producer·모든 새 CDC·공통 실행기가 포함된다. queue/SPI650 상한을 유지할 때 source-host 상한은 1587이며 각각 2474와 129개의 추가 삭제가 필요하다. 이는 합격 예산이지 달성 예측이 아니다.

세부 계층 비교는 다음과 같다. parent와 child는 더하지 않는다.

| source-host 내부 | 기준 comb | 후보 comb |
|---|---:|---:|
| source codec/query | 1348 | codec767 + local row559 |
| source transport, 하위 CDC 포함 | 400 | 330 |
| core wrapper 자체 | 21 | 289 |
| start/DONE/final CDC | 0 | 18 |
| host 자체 | 2063 | 2066 |
| 공통 바이트 실행기 | 0 | 32 |
| 합계 | 3832 | 4061 |

source codec·행 producer·host·공통 실행기의 FSM은 모두 Quartus에서 추출됐다. FSM 추출 자체가 회로 감소를 보장하지는 않는다. codec만의 감소581개 중559개는 이동한 행/query 생산기에 다시 들어간다. 추가 포트 소유권과 주소 선택 등을 포함한 wrapper 비용도 빠뜨릴 수 없다. 개별 셀의 계층 배치는 합성 최적화에 영향을 받으므로 최종 판단은 전체 합계로 한다.

상위 source/host/queue/plan 해석을 보존한 채 바이트 상태만 공유하는 범위는 필요한 삭제량에 미치지 못한다. 후속은 기존 압축의 시간 이득을 유지하면서 host 명령 ABI·descriptor/manifest 해석·queue/plan 실행 경계에서 실제 없앨 제어를 먼저 정해야 한다. 독립 검사를 제거해서 예산을 맞추지 않는다.

## 검증과 한계

window05/fixed01 각각 3프레임, 10개 실제 통합 fault 주입, aperture 회귀 및 독립 final/raw0/STOP/reset 8검사를 통과했다. query 응답 대기, 행 소비, 두 행 슬롯 점유, 입력→표시 handoff, NES plan 읽기, ROM request, private receipt, raw CRC 중 STOP과 잘못된 token/조기 최종 ACK를 포함한다. 기존 EA/cache/arbiter 68검사는 변경 없는 RTL 해시와 이전 로그에 연결해 유지했다.

window01은 생성기 치환 충돌, window02는 선언 순서, window03은 삭제된 PCAP를 참조하던 testbench, window04는 옛 portB 전용 소유권 assertion에서 중단했다. 모든 중간 결과를 보존했다. 최종 기능 소스는 window05/fixed01, 비용 소스는 map02다. 주요 생성 모듈을 대조했으며 board의 기존 tile_closed267 단순 출력 export 두 줄만 정규화했다. analysis01에서 이 차이를 잡았고, 그 외 차이는 허용하지 않는다. map01은 STOP cursor 수정을 반영하기 전의 예비 결과다.

guards01의 case27은 초기 reset에서 두 ready가 0인 구간을 실제 슬롯 점유로 잘못 잡았다. 그 PASS는 최종 근거에서 제외했다. guards02에서는 활성 프레임·SPACE 상태·두 유효 descriptor·반환 전 credit를 모두 요구하고, 실제 행과 source 바이트가 소비된 뒤 STOP했음을 별도로 확인했다. 최종 10건은 guards01의 나머지9건과 guards02의 case27이다.

실제 M4 명령 실행과 IRQ/refill/2슬롯을 사용하지만 CPI1 시간 할당 모델이다. ordinary65816 trace와 tile/display bus model을 사용하고 VBlank 제약을 유지했다. 전체 firmware foreground·모든 IRQ, 전체 65816/VBlank CPU 실행, 71프레임·실물 지속60fps·FIT/STA는 미완료다. production227/GBC164/saveSRAM은 변경하지 않았다. PR131은 자동 merge하지 않는다.

근거: [검증 JSON](../analysis/rows363-verification.json), [후속 계획](nes-rows363-plan.json), probes/nes-rows363의 원시 로그·소스·MAP.
