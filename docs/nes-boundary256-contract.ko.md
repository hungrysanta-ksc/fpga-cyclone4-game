# NES256 R0: 교체 경계와 전체 비용표

PR129는2978f04aef65987c615d62ca54576e68fc946637로 머지됐으며 origin/master 포함을 확인했다. 그 커밋에서 codex/nes-wholepath-boundary-256을 만들었다. [PR129 계획](nes-pr129-next-plan.json)의 R0를 수행한 결과다. 새 RTL/ARM/SNES 구현이나 합성을 실행한 단계가 아니다.

**결론:** 교체할 기능 경계와 비용의 출처를 고정했다. 실제 통합에 필요한 lease 전환과 DMA 완료 receipt가255에 연결되지 않았음을 코드에서 확인했다. 기존552개 조건부 일정을11개 비용 항목으로 재구성했으며 최대 오차는7.11e-15ms다. 이는 회계 검증이고 실제 전체 처리 시간 검증은 아니다. R0는 미확인 비용을 명시한 상태로 완료하며 R1/P2/60fps는 미통과다.

## 고정한 교체 경계

아래의 제거/교체는 **후속 구현의 범위**이며 이번 단계에서 회로가 제거됐다는 뜻이 아니다. 이름이 같은 과거 파일 대신 실제240 board01/255 test03 생성물을 조사했다. 특히240의 nes_sink_spi165는 단일 패킷 원본이 아니라 queue184의4패킷 구현이다.

| 기능·실제 기준 | 후속 조치와 소유자 | 보존/추가 비용 |
|---|---|---|
| native_source240의 encoder240/query235/transport235 | NES255 core+transport 경계로 교체. NES 클록에서 query·투영·source·receipt/CRC 문맥 담당 | 기존 query를 함께 남기지 않는다. source SPI의 host 클록·mailbox·SS/CRC/취소는 여전히 필요 |
| nes_native_capture201 / nes_capture_lease201 | collector와 표시 lease의 두 수명은 유지하고 core 접속 변경 | 입력 소유권→표시 lease 전환 및 epoch/generation/serial 결합 추가. collector 재사용과 출력 검사 수명을 혼동하지 않음 |
| sink bridge의 nes_sink_spi165(queue184 동작) | host 클록의 E0/E1 framing·CRC·4credit RAM 유지, head 읽기/retire 제어를 typed parser와 공동 설계해 교체 | 기존 ACK checker와 새 parser를 독립 head 소유자로 중복 연결하지 않음. READ 포트 중재·오류 보고 비용 미확인 |
| nes_sink_bus165 | SNES 버스/ROM/입력 경로 유지, typed descriptor·완료 연결 변경 | 버스 전체나 ROM을 회수로 계산하지 않음. ROM 크기는 실제 효율에 따라 결정 |
| 새 typed parser / map staging | map 범위·manifest·H2를 host 경계에서 해독하고 범위 데이터/문맥을 core에 전달 | 새 wire opcode/framing·분할, 저장 RAM/descriptor, host→NES 전달 회로는 R1에서 실제 구현·계측 필요 |
| nes_direct206의 plan_spi200/batch206 | 타일 계획·ROM reader 경로 유지, typed map 제출·완료는 기존 bulk 제어와 공유하도록 확장 | 기존 endpoint/transport 전체 제거를 가정하지 않음. tile/map 동시 사용 시 명시적 중재 |
| source_tile192 / cache192 / arbiter165 / tile205 | 타일 생성·메모리 우선순위 유지 | 타일 준비·대기·reader drain은 남는 비용이며 source255 시간에 포함됐다고 보지 않음 |
| tile_bulk206 / bulk_aperture188 / bulk_control194 |2×2KiB payload와 token 불변성 유지, map과의 사용 수명·descriptor·완료 제어 재설계 |2KiB를 임의 scratch로 사용하거나 source phase RAM과 겹쳐 무료 저장으로 보지 않음 |
|255 range sink / receipt /64B CRC /32B H2 문맥 | source NES 클록의 공유 core 유지, 실제 소비 완료로 receipt를 갱신하도록 접속 교체 | payload staging 수락과 DMA 완료를 분리. 범위 정보를 완료까지 보존할 RAM/제어·CDC 비용 미확인 |
| ARM233 RUN/planner231/window184 및 H2 C252 | N5 복원·계획·H2 생성·새 output serializer를 실제 RUN에 결합 |233의 입력은227이므로 기존1616B 여유를 새 입력 승인으로 재사용하지 않음. 새 call chain/IRQ/stack 필요 |
| SNES232/2472 검사·mark·DMA | FPGA로 이전한 검사를 실제로 제거하고 typed DMA command 실행부로 교체 | validate181 제거와 command_tail 정책은 end-to-end binding 통과 후만 인정.2472는 진단 기준 |
| final display ACK / ARM resident·dirty commit / plan retire | 순서와 별도 완료 의미 유지 | 실제 표시 성공 후 generation 확인, 최종 retire 완료 후 입력 consumed. 단순 sink_ready나 input ACK로 대체 금지 |

source255와 출력 queue는 클록이 다르다. 공유 core를 host 클록으로 옮기거나 모든 클록을 합치는 안은 이번 범위에 포함하지 않는다. source는 NES 클록에 두고, host parser와 core 사이에 유효한 문맥/범위/완료 전달이 필요하다는 경계를 고정한다. 기존 mailbox 재사용 가능성은 수명·폭·동시 사용을 입증한 뒤 비용표에 반영한다.

## 실제 코드에서 드러난 연결 조건

255 core의 lease_ok는 frame_owned && geometry_valid && generation==frame_generation이다. WAITACK에서 done을 내고 V_IDLE로 전환한 뒤에도 이를 요구한다.240 보드에서는 source done을 export_release204에 연결하고, capture_lease201은 export_release로 collector를 해제하면서 waiting_display의 별도 lease를 세운다. 따라서255를 단순 치환하면 출력 단계가 이미 해제된 collector 소유권에 매달리게 된다. 이는 코드 접속상 불일치의 정적 발견이며 새 통합 시뮬레이션 결과가 아니다.

R1에서는 입력 단계의 collector identity와 출력 단계의 captured display lease를 명시적으로 전환해야 한다. epoch/generation/serial은 admission 문맥에 결합하고 STOP·세대/epoch 변경·lease 상실은 즉시 취소한다. owned를 상수로 강제하거나 collector를 무조건 오래 붙잡는 방식은 다음 프레임 capture 중첩을 바꾸므로 해결로 간주하지 않는다.

또한255의 sink_valid/ready는 바이트가 모델 RAM에 수락됐다는 뜻이다. 실제 DMA 완료와 같지 않다. 후속 인터페이스는 다음 세 소유권을 분리한다.

1. **패킷 slot:** CRC가 확인된4개 큐의 head 하나만 parser 또는 SNES가 읽는다. typed packet은 모든 내용과 identity를 수명 보장된 staging에 옮겼을 때만 parser 완료로 credit 반환이 가능하다. 일반 packet은 기존 검증된 SNES ACK로 반환한다. 둘의 완료를 중재하는 단일 retire 소유자를 둔다. 내부 parser 완료를 SNES 표시 ACK로 위장하지 않는다.
2. **DMA chunk/range:** staging 완료 후 descriptor/token으로 불변 데이터를 게시한다. 실제 SNES가 해당 범위를 DMA하고 token을 consume한 뒤에만 그 범위의 receipt를 확정한다. chunk를 재사용하기 전 필요한 범위·bank·identity를 보존한다. 정확한 descriptor 인코딩과 저장 비용은 R1 미확인 항목이다.
3. **프레임 표시 lease:** 모든 필요한 범위/metadata/H2 검사가 끝나도 final display ACK까지 유지한다. ARM의 resident/dirty commit 및 최종 NES retire는 기존 표시 성공 순서를 지킨다.

map/manifest를 앞선 미퇴역 packet 너머로 읽지 않는다. source phase RAM의0..395는 영속 validity/CRC,396..817은 출력 receipt/map,832..863은 H2 문맥,512..1023은 입력 scratch다. 입력 scratch와 출력 임시 상태는 겹치므로 같은 core에서 두 단계를 동시에 실행하지 않는다. 기존 collector의 다음 프레임 capture와는 별개이며 그 중첩은 R1에서 검증한다.

## 회로 비용표의 기준

| 기존240 전체 MAP 내부 계층 | comb | FF | memory bits | 처리 방침 |
|---|---:|---:|---:|---|
| native_source240 전체 |2092|974|57344|255로 교체할 비교 경계 |
| direct_path 전체 |2503|1670|41216|타일 경로 유지, bulk/완료 일부 재설계 |
| sink bridge 전체 |748|580|40960|queue/bus를 포함한 부모 |
| ↳ queue endpoint |679|424|8192|framing/RAM 유지, head/retire 변경 |
| ↳ SNES bus |66|149|32768|버스·program ROM 유지 |
| direct_path 내부 bulk |465|512|33024|typed map 공유 시 중재 추가 |
| direct_path 내부 control |100|174|0|descriptor/token 확장·공유 |

이 표의 값은 **이전 MAP의 inclusive 계층**이며 부모와 자식을 합산하지 않는다. LE 절약이나 FIT 회수 수치가 아니다.255 standalone3362LE/3055comb/985FF/49152bits는 다른 합성 경계이므로 이 표에서 빼지 않는다. 전체240은15898LE/1003LAB/54M9K를 요구해15408LE/963LAB/56M9K 장치에서490LE·40LAB 부족했다. 새 parser·staging·CDC·lease·완료 제어의 비용과 전체 배치는 미확인이다. 논리 회수 입증은 여전히0이며 새 whole-FIT 없이는 회로 여유를 승인하지 않는다.

## 전체 시간 비용표

기존255의 warm69×setup2×검사정책2×회계정책2=552행을 그대로 재구성했다. 기존250 일정에서 modeled source wire+prepare와 receipt/validate를 제거하고 실제255 경계 측정과 후속 배정 항목으로 교체한 과정을 역산했다. source 측정에 이미 들어간 SPI polling과 wait를 다시 더하지 않는다.

아래는 frame970, setup500, command_tail, transfer_covered_conditional의 분해다. 합계는 기존15.995909ms와 같으며 **새 성능 측정값이 아니다**.

| 비용 | ms | 근거/한계 |
|---|---:|---|
| source/query/SPI/input ACK |6.276409|255 RTL fixture의 경과 시간. ARM 서비스·capture 이전은 제외 |
| 출력 SPI wire/control |5.909333|1939B,2.625MHz 모델. 추가 H2 배정은 다음 행과 별도 |
| SPI와 겹치고 남은 서비스 대기 |0.896153|기존 event model의 critical-path 차액. 전체 CPU 작업 합계가 아님 |
| display sample |1.865507|기존 SNES 표본 재사용. VBlank 대기 제외·WCET 아님 |
| parser 배정 |0.380364|출력 byte당8 FPGA cycles 가정 |
| 최종 고정 배정 |0.093122|2000 SNES master clocks 가정 |
| phase handoff 배정 |0.000091|251에서 유지한2 FPGA cycles 가정 |
| ARM 배정 |0.380952|84MHz의32000cycles 가정 |
| 추가 H2 wire 배정 |0.097524|32B 가정. 기존SEAL/typed trailer32B와 별도 항목이며 실제 framing에서 확인 필요 |
| receipt/CRC/context, stream 제외 |0.096455|255 fixture에서 공급·stall stream 구간을 뺀 값. 실제 parser/DMA와 결합 미확인 |
| **조건부 합계 / 미확인 비용용 잔여** |**15.995909 /0.670758**|잔여는 확보된 실행 여유가 아님 |

setup1000이면 frame970의 서비스 대기가 약0.861376ms 증가해16.857285ms가 된다.256cycle/range 등의 시험 공급 시간을 추가 예약하는 별도 회계는 같은500 조건에서16.548909ms다. 실제 상·하한으로 해석하지 않는다. SNES validate181 약0.652..0.654ms 제거는 여전히 조건부이며, 남겨야 한다면 해당 비용을 다시 계산해야 한다.

| 시작 검사 프레임 |500/command_tail 조건부 ms|미확인 비용용 잔여 ms|
|---|---:|---:|
|952|14.664839|2.001828|
|954|15.855268|0.811399|
|955|14.584492|2.082175|
|962|15.576690|1.089976|
|963|14.841570|1.825097|
|968|13.667268|2.999398|
|970|15.995909|0.670758|

## 미확인 비용과 R1 시작점

| ID | 담당 | 반드시 확인할 비용 |
|---|---|---|
|U1|ARM|N5 복원·계획·H2 생성·serializer·RUN/IRQ 시간과 전체 메모리/스택 |
|U2|FPGA host|실제 출력 parser·head READ 중재·typed retire·CRC 서비스 |
|U3|클록 간 경계|host→NES descriptor/data/completion 전달과 collector→display lease 전환 |
|U4|FPGA/SNES|staging 수락→DMA 완료/token→receipt 연결, bank/display serial 이력 |
|U5|FPGA|map staging·descriptor 저장과 tile aperture 공유 RAM/제어·대기 |
|U6|SNES|실제 typed setup·일반 payload 복사/DMA·dispatch·poll 비용 |
|U7|전체|VBlank·capture/game 실행 중첩·audio/input 서비스·최종 retire 대기 |
|U8|ARM/FPGA/SNES|tail CRC·fresh scroll·OAM·H2 전송/coverage와 최종 검사 제거 조건 |

JSON에서 이 항목의 시간·LE는 null이다. 모델 잔여와 합쳐 실제 비용을 알았다고 하지 않는다. R1 첫 구현은 **입력 export 뒤 lease 전환과 한 범위의 실제 packet→staging→SNES DMA→token/receipt→final ACK 경로**로 한정한다. 일반4credit queue와 타일 경로를 보존하면서 head/retire 소유자를 하나로 만드는 접속을 먼저 검증한다. 그 경로의 코드·계측이 생긴 후 위7개 프레임으로 확장한다. 명백한 초과가 나오면 이전 [중단 기준](nes-pr129-retrospective.ko.md)에 따라 구조를 재평가한다.

## 재현과 보존

`tools/analyze_nes_boundary256.py --out <새 디렉터리>`는 기존 private probe 자료를 필요로 한다. ROM·fixture bytes를 공개하지 않으며 source anchor/해시·552행 회계·이전 MAP 계층만 공개한다. 선택 결과는 probes/nes-boundary256/analysis01이다. 이번 단계의 새 하드웨어 실행은 없고 source 연결 문제도 정적 검토 결과다. 기존255 자료, production227/GBC164/saveSRAM은 변경하지 않았다.

[실행 계획](nes-boundary256-plan.json) · [검증·근거](../analysis/boundary256-verification.json) · [552행 비용표](../analysis/boundary256-costs.csv) · [이전 MAP 계층](../analysis/boundary256-area.csv)
