# NES502 — raw 행 소유권 축소와 실제 소비 비용

[검증 원장](../analysis/capture502-verification.json) · [PR139](progress/pr-139.md) · [A1–A4 계획](nes-audit499-plan.json).

**필요 없는 세 번째 raw 행을 제거하면서 실제493 ARM·65816의 결과를 보존했다.** 이는 제한된 고정 장면의 정확성·비용 검증이다. 실기 선택은 MMC493/9.57fps이며502 전달본이나 실기 가속 결과는 아직 없다.

## 변경과 유지 경계

501은 visible 구간에서 렌더링을 재개해도 다음 행을 raw로 지정했다.502는 dot1..257 전환을 현재 행에, 다음 행의 fetch 구간인 dot257 이후 전환을 다음 행에 귀속한다. dot0 전환은 line-edge 회전 전이므로 다음 행에만 귀속해 이전 행을 뒤늦게 오염시키지 않는다. 실기493의70개 보드 입력 중 planes/frame 두 파일을 교체하며, frame 파일은501과 byte 동일하다.

2행 상한을 새로 만들지 않았다. 떨어진 두 번의 전환은 실제4행을 보존하고, 기존7행 저장 용량을 넘기면 계속 거부한다. 실제 ROM 주소·DATA·byte/plane lane, raw pixel/행 identity/세대/완료 통지, native high 누락, STOP 및 조기 query 검사를 유지했다. FPGA 메모리 배치, source codec, ARM·65816 바이너리, 메뉴/base/GBC/save 경로는 바꾸지 않았다.

## 기능 검증

- `equivalence01`: 기존27조건 모두 통과.501 대비10조건에서 raw3→2, 합계10행 감소. 나머지 행의 native 이벤트 개수·순서·64bit 내용이 일치한다.
- `boundary02`: visible 끝/HBlank/prefetch 시작·끝/dot0/정당한4행의6조건 통과. 총33조건에서 raw15,360픽셀과 native241,956이벤트를 비교했다. raw 관측기는 같은 실제PPU의 별도 post-CE 관측기다.
- `guards01`: 주소·DATA·lane·ROM fault·pixel 누락·행/세대·완료 통지·용량·STOP·native high 누락 등12반례를 거부했다. 조기 및 다른 세대 query도 차단했다.
- `export501-02`/`export502-02`: 같은 `f620-addr1-d3` PPU 입력을 실제 collector와493 source exporter에 연결했다. raw3/2행의 실제 query와96bit record를 추출했다. source release와 PREPARED 응답은 시험용이며 실시간 ARM과 연결한 공통 클록은 아니다.
- `arm01`: 실제493 firmware/ELF로 record 수신·단일 복원·planner·resident·serializer를 실행했다. canonical geometry/raw와 독립 복원한 map/CGRAM/OAM/HDMA를 비교하고, compact 변환이 만료된 BG scratch 밖을 변경하지 않는지 검사했다.
- `cpu01`/`cpu02`: 같은 실제493 65816 코드에 실제 ARM 패킷과 계획을 공급했다. 기존496의 연속·동일 section/generation·최대2048B bulk 묶음을 적용해257plan을3chunk로 처리했다. 타일 순서·주소·bytes는 독립 재구성으로 일치한다. 두 시작 위상 모두 DMA·독립 검사·VBlank·최종ACK를 통과하고501/502의256×239 최종 RGB가 byte 동일했다. 화면에는9색이 있어 단색 비교가 아니다.

## 실제 ARM·전송 비용

아래는 게임 평균이 아닌 **같은 한 cold fixture** 비교다. source의96bit record를 기존 variable-width ABI로 packetize하고, 수신 SPI/ACK endpoint를 모델링했다. 실제 공유 SPI 설정70/73, IRQ·ROM 대기·전체 RUN 시간은 포함하지 않는다.

| 항목 | 501 | 502 | 차이 |
|---|---:|---:|---:|
| raw 행 | 3 | 2 | −1 |
| source record / packet | 358 / 18 | 332 / 17 | −26 / −1 |
| source payload | 4,293B | 3,982B | −311B |
| 수신 callback SPI 합계 | 4,675B | 4,345B | −330B |
| 수신 ARM 명령 수 | 376,825 | 349,445 | −27,380 |
| planner ARM 명령 수 | 1,221,895 | 1,188,079 | −33,816 |
| serializer ARM 명령 수 | 224,085 | 115,056 | −109,029 |
| HDMA section body | 2,316B | 652B | −1,664B |
| ordinary+manifest E1 | 7,647B | 5,850B | −1,797B |
| BEGIN/bulk 포함 모델 E1 | 7,747B | 5,950B | −1,797B |
| 65816 VRAM DMA | 14,352B | 12,752B | −1,600B |

전송 전 CHR2048→384B 차이가 이번 장면에서는 실제 HDMA body1664B 감소로 이어졌다. packet7개도 줄어 E1 절감은1797B다. source와 출력의 절감 합계는2127B지만, 이를 전체 프레임 단축으로 치환하지 않는다. ARM 명령 수는 하드웨어 cycle/ms가 아니다. ARM Flash/static RAM 추가는0이며, 전체 실제 stack/IRQ 최대치는 새로 증명하지 않았다.

## 시작 위상과 표시 시각

각 행은501/502를 **같은 시작 master clock**에 놓고 비교한 것이다.2.625Mbps E1와4credit을 모델링하며, 실제ARM/source/IRQ/ROM은 이65816 클록에서 실행하지 않는다. 두 시작 위상 사이의 차이를 최적화 이득으로 합산하지 않는다.

| 시작 master clock | 최종 준비 단축 | 최종 ACK 단축 |
|---|---:|---:|
| 3,000,000 | 4,396clock ≈0.20468ms | 4,370clock ≈0.20347ms |
| 3,085,909 | 361,390clock ≈16.82662ms | 361,356clock ≈16.82504ms |

전송·DMA를 줄여도 같은 VBlank를 기다리면 최종 표시 이득이 작다. 다른 위상에서는 다음 VBlank로 넘어가던 대기가 사라진다. 이는 새 실기 FPS나 지속60fps 증명이 아니다. 단일 cold 장면이며, continuous frame·실제 공유 SPI/refill/IRQ/입력 중 ROM 경쟁은 미측정이다. 실기 STOP·메뉴 복귀도 이번 후보에서 다시 확인한 것은 아니다. 변경하지 않은493 경로의 기존 증거와 새로운 collector STOP 검증을 구분한다.

## Quartus Lite 전체 비용

| 항목 | 501 | 502 | 차이 |
|---|---:|---:|---:|
| LE | 15,308 | 15,287 | −21; 잔여121 |
| 조합 논리 | 14,133 | 14,135 | +2 |
| FF | 8,399 | 8,399 | 0 |
| 논리 RAM bit | 264,816 | 264,816 | 0 |
| M9K | 51 | 51 | 0; 잔여5 |
| 관련 setup/hold | +0.077/+0.145ns | +0.353/+0.142ns | implementation/nominal 모두 양수 |

493 대비 +15LE/+57comb/+7FF/+16RAMbit다. LE 감소를 제어 삭제 성과로 해석하지 않는다. 같은 seed·SDC로 한 번 전체 build했고, 관련 경로를 확인했다. 전체 reset/CDC/외부 IO sign-off가 아니다.

## 재현과 다음 순서

`test_nes_capture502.py`의 일반/`--boundary`/`--guards`가33+12조건을 만들고, `test_nes_capture502_export.py --prior`가501 비교 source를 만든다. `test_nes_capture502_pipeline.py arm/cpu`는 실제493 바이너리와 record hash를 확인한다. `prepare_nes_capture502_board.py`는493 보드70입력을 검증해 두 파일만 overlay하며 `analyze_nes_capture502.py`가 원장과 같은 source/로그/전체 비용을 재대조한다. Questa는 기존 FLOAT 한 좌석을 순차 사용했다.

`export501-01`은 시험용 producer를 wire 선언보다 먼저 배치한 컴파일 실패였다. 선언 순서만 고친02 두 실행을 선택했다. 제품RTL 변경이나 license 문제가 아니다. `boundary01`/`export502-01`은 준비만 했으므로 성공 증거가 아니다. 원시 입력·실행 로그·산출물은 작업공간 `probes/nes-capture502/evidence`에 보존하고 manifest를 기록한다. 비공개 보존본은 clone에 포함되지 않는다. `archive01.json`에710파일/17,413,169B를 고정했고, `reproduction01.json`은 최종 generator로5개 선택 fixture의 입력·testbench manifest가 동일하게 재생성됨을 확인한다.

제한된 수집·실제 소비 gate는 통과했지만 A1의 실기 확인은 남았다. **다음 작업은502 수정만 분리한 고유 파일명 전달본과493 복구본 준비 → 같은 장면의 수집 거부·표시 간격·메뉴 확인 → A2 전체 전송·DMA 예산 갱신** 순서다. 실기 확인을 대신해 같은 bounded 시험/FIT를 반복하지 않는다. 실기493 기준은 유지하며, 아직 선정하지 않은498·status/FSM 미세 최적화를 섞지 않는다. A2에는 실제 공유SPI/IRQ/ROM과 따로 계측한 VBlank 비용을 넣는다.
