# NES252 — HDMA 상속 내용 봉인과 제어 공유 경계

2026-10-19, PR129. [현재 계획](nes-binding252-plan.json) · [검증 집계](../analysis/binding252-verification.json) · [프레임별 전송량](../analysis/binding252-frames.csv) · [조건부 일정](../analysis/binding252-schedules.csv).

**기존에 검증한 내용의 CRC를 양 bank 합계64B 보관하는 후보가 단순 재전송보다 유리하다.** 실제 C로 ARM certificate를 생성하고 실제71프레임 패킷에서 갱신한 CRC와 비교했다. 다만 수신기와 갱신은 Python 모델이며, FPGA 논리 절약이나 전체60fps를 입증한 결과는 아니다. production227과 기존251 RTL은 변경하지 않았다.

## 이번에 확인한 누락 조건

71프레임의 기존 C 송신 패킷을 양쪽 WRAM bank에 순서대로 적용했다. 각 프레임의 HDMA 의미에 사용되는 바이트는90B였다. cold2프레임은 전부 수신하지만 **warm69프레임 모두 scroll21B만 새로 받고 나머지69B는 해당 bank에서 상속**한다. 따라서 이번 frame의 새 패킷에만 CRC를 붙이는 방식은 전체 후보의 HDMA 검사를 대체하지 못한다.

907번 프레임의 상속 offset3169를 모델에서 변조하면 새로 받은 바이트의 CRC는 그대로지만, 현재 HDMA의 CRC는 달라진다. 이는 미완성 봉인 제안의 반례이지 production에서 실제 손상이 관찰됐다는 뜻은 아니다. 기존 SNES 의미검사는 아직 제거하지 않았다.

## 세 후보의 전체 비용 비교

| 후보 | 기존 패킷 외에 warm마다 필요한 것 | 확인된 제한 |
|---|---|---|
| 기존16B granule로 필요한 표 재전송 | 데이터105B + 4패킷 framing76B = **181B** | 수신 예상 manifest도 갱신 필요 |
| active 표만 새 typed packet으로 전송 | active69B + 4개 descriptor12B + framing19B = **100B** | 새 덮어쓰기·중복 범위·소비 소유권 필요 |
| bank별 granule CRC 보관 | 추가 표 전송0B, 영속 **64B** | CRC 갱신·RAM 중재·완료 결합 RTL 필요 |

위 추가량은 certificate32B와 별개다. 251의 ARM32000cycles,추가certificate32B,phase2clock 배정을 유지하고 재전송은 직렬 비용으로 더했다. 새 패킷의 CPU 처리·추가 poll/ACK 비용은 포함하지 않았으므로 단순 재전송에 유리한 비교다. 새 packet scheduler를 실행한 결과도 아니다.

| 정책 | 빠른 setup500/명령tail 최대 | 잔여 | setup1000/명령tail 최대 |
|---|---:|---:|---:|
| 16B granule 재전송 | 16.732788ms | −0.066121ms | 17.594164ms |
| active typed 재전송 | 16.485931ms | 0.180736ms | 17.347306ms |
| CRC64B 보관 | 16.212805ms | 0.453861ms | 17.074181ms |

CRC 보관은 warm마다 추가 FPGA696clock(22MHz에서0.031636ms)을 **배정**했다. fresh scroll·certificate·CRC 목록 처리와 RAM 읽기를 직렬로 더한 값이며, 새 RTL의 실행시간/상한이 아니다. cold에서는249B/16granule 초기화까지2720clock이다. 총828개 조건을 계산했다. 비트맵 loop만 제거하는500setup에서는 CRC 보관조차16.593673ms/잔여0.072994ms에 불과하다. 따라서 이전0.485498ms 여유를 확정된 시간으로 취급하면 안 된다.

## 64B가 가능한 이유와 수명

스크롤은 기존 경로에서 매번 전부 전송되므로 bank별 과거 scroll CRC를 보관할 필요가 없다. 저장 대상은 bundle3169..3417의249B(modeA81+modeB81+enable81+길이6)다. 이를 기존 dirty 전송과 같은16B granule16개로 나누면 bank마다 CRC16 32B, 양쪽 합계64B다. 마지막 granule은9B다.

관측 패킷은 해당 granule을 모두 쓰거나 전혀 쓰지 않았으며 부분 granule은 없었다. consumed된 granule에서만 CRC를 갱신하고, 전송되지 않은 granule은 검증된 bank의 CRC를 상속한다. 초기화 여부는 기존 raw validity의 해당16bits를 재사용하는 설계안이다. 공통 STOP/fault/raw0에서는 양 bank validity를 무효화하며 다음 raw 사용은 필요한 granule 재수신을 요구한다. 메모리 내용 자체를 reset하지 않아도 되지만, stale CRC를 유효하게 읽으면 안 된다.

251의1024×8 RAM에 대한 다음 **배치안**은 다음과 같다. 아직 RTL에 반영하거나 합성하지 않았다.

| 영역 | 주소 | 수명 |
|---|---|---|
| 두 bank 기존 validity | 0..331 | display까지 영속 |
| 두 bank HDMA granule CRC | 332..395 | validity에 종속된 영속 상태 |
| 현재 frame received | 396..561 | 출력 검사 동안만 |
| 현재 frame map receipt | 562..817 | 출력 검사 동안만 |
| source scratch | 512..1023 | 입력 source 동안만 |

영속396B와 출력 임시422B 합계818B다. source는396B 영속 영역을 건드리지 않는다. 출력 단계에서는 source가 멈춰 있어 임시 영역과 겹쳐도 된다. certificate의32B 보관, decoder/CRC 레지스터, 포트 중재 비용은 이818B 산술에 숨겨 넣지 않았다. 초기 clear는 최대818주소가 될 수 있으나 per-frame 임시 clear는422B 그대로다.

첫 기본 비교 `test01`은 모든 HDMA 바이트에 과거 CRC를 보관하는344B 예를 넣었지만, 이미 fresh인 scroll을 제외하지 않은 과대 배치였다. `test02/03`은 raw-tail만64B로 좁혔다. 이는 M9K를 새로 회수한 측정이나 모든 설계에 대한 최소 저장량 증명은 아니다.

## ARM certificate와 검증 범위

[C 구현](../tools/nes_hdmabind252.c)은251 의미검사를 통과한 immutable 후보에서32B certificate를 만든다.

| 바이트 | 내용 |
|---|---|
| 0..3 | H2,version(fresh1/shadow2),target bank |
| 4..11 | epoch32,frame serial32 |
| 12..18 | generation16,scroll length16,세 table length8 |
| 19..21 | mask,raw count,reserved0 |
| 22..25 | 내용 CRC16,논리적으로 포함하는 바이트 수16 |
| 26..31 | target bank의 display base serial32,certificate CRC16 |

수신 측은 **admitted context**와 모든 identity를 대조해야 한다. base serial은 source input commit serial과 혼동하지 않는다. fresh version은 active 바이트를 정확한 offset/순서로 전부 소비했을 때만 승인한다. shadow version은 fresh scroll 뒤에 target bank의16개 CRC를 고정 순서의32B 목록으로 이어 CRC를 계산한다. ARM은 현재 후보249B를 같은16개 granule로 나누어 같은 값을 만든다. context는 certificate CRC로 함께 보호한다. CRC16은 기존 source와 같은0x1021 다항식을 쓰는 오류 검출이며 암호학적 인증이나 충돌 없는 동일성 증명은 아니다.

기록71프레임에서 C certificate와 두 Python 수신 정책이 일치했다. fresh 정책9372개 거부 검사,shadow 정책2769개 거부 검사,별도 granule 갱신·stale 거부·양 bank 무효화10검사를 통과했다. 마지막9B granule과 서로 다른 표의 padding 변경도 포함한다. warm 기록에는 raw-tail 갱신 자체가 없으므로 이 별도 검사를 생략하지 않았다. normal 모드와 generation16 wrap도 확인했다. 이것은 실제 FPGA packet parser/STOP/CDC나 SNES 소비 실행 시험은 아니다.

ARM 객체는 기존 의미검사300B에 새 두 certificate 경로608B를 더해908B text이며 data/bss는0B다. 함수별 stack은 prepare48B,shadow48B,semantic36B,CRC12B다. shadow→prepare→semantic의 알려진 경로는132B이며 전체 RUN/IRQ bound가 아니다. 객체에는 `memset` 외부 호출도 있고 caller가32B certificate를 제공해야 한다. 참조 shadow 함수는 prepare가 만든 fresh digest를 다시 계산하므로 중복 작업도 현재 코드의 비용에 포함된다. 이를 최적화했다고 보고하지 않는다. MCU cycle/fullRUN은 여전히 미측정이며32000cycles 배정을 재승인하지 않았다.

## 실제 source·전송 제어에서 공유할 수 있는 것

실제240 board의 `nes_source240`,query235,SPI235,`nes_direct206`,capture 연결을 검토했다. 다음 비용을 RAM phase flag 하나로 제거할 수는 없다.

| 경계 | 실제 유지할 조건 | 공유 후보와 이번 결론 |
|---|---|---|
| query→encoder | immutable generation,응답 hit,독립 offset,fetch 시점 raster 검증 | query cursor와 encoder byte 처리를 합칠 후보는 가능하지만4398B projection의 실제 질의 변환도 함께 구현해야 한다. 검증을 빼거나 reader217comb를 전부 회수한다고 계산하지 않는다. |
| encoder→source SPI | source stream CRC와248B block CRC는 같은 바이트에서 서로 다른 상태를 갱신 | 다항식은 같아 연산기를 시간 분할할 수 있지만 현재byte-ready/backpressure가 바뀐다. 두 CRC 상태 중 하나를 없앨 수는 없다. |
| SPI host 제어 | D0 status,D1 읽기,D2 pop,D3 input ACK,token과부분 SS 검사 | NES clock와host clock의 mailbox/두 bank 수명을 보존해야 한다. 입력 ACK만으로 모든 전송 상태가 idle이라고 가정하지 않는다. |
| 출력 receipt/HDMA CRC | 실제 소비된 granule,dirty coverage,bank fingerprint,certificate | 입력 source 뒤에 연산기 재사용 가능성이 있으나 출력 receipt RAM 쓰기와 CRC read/write의 일정 및 consume CDC 비용이 추가된다. |
| capture 최종 해제 | input release 뒤에도reader-drained/final retire 경로 유지 | typed consume나D2/D3를display ACK로 대체하지 않는다. 기존direct206 소유권/첫 fault를 함께 연결해야 한다. |

source query의64비트 held 값은 object8B 응답을 바이트로 내보내는 역할도 하므로 phase 공유만으로 전부 사라지지 않는다. 251 parent244comb는 계층 이동 비용을 포함하며 순수 제거 대상이 아니다. 이번에 합성으로 입증한 논리 절약은0이다. 기존251의1539LE 및 full240의490LE/40LAB 부족은 그대로 남는다.

## 판단과 다음 경계

단순 재전송은 시간상 불리하고 compact 재전송도 새 소비 제어에 쓸 여유가 작다. **raw-tail CRC64B를 같은 RAM에 넣고, query/encoder/transport/receipt의 기존 제어를 실제로 없애는 통합 후보**를 다음 검증 대상으로 삼는다. 아직 P2 제품 구현을 선택한 것은 아니다.

다음 시험은 실제 query/projector→source byte→SPI block과 출력 consume→granule CRC→certificate를 같은 소유권 안에서 연결해야 한다. 부분 패킷·중복 granule·잘못된 identity·raw0 복귀·STOP·최종 display retire를 포함하고, 삭제한 기존 제어와 추가한 상태를 같은 합성 경계에서 비교한다. 전체ARM/IRQ·SNES 남은 DMA/dispatch·poll/gap/VBlank·952/955·mapper·CDC/IO/STA 비용을 포함한 공동 여유 전에는 full FIT/설치 FW/실기로 넘어가지 않는다.

재현 도구는 [분석기](../tools/analyze_nes_binding252.py)이며 선택 자료는 private `probes/nes-joint252/test03`이다. test01/02 중간 결과도 보존했다. 실제 ROM·packet·compiler log·disassembly는 private archive에만 있다. 새 MAP/FIT/Questa/SNES 실행은 없으며 production227/unplaced240/rejected241·246·2472/GBC164/saveSRAM/5886B 진단 이미지는 그대로다.
