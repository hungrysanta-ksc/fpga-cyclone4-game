# 576 — 진단·host reset 수정과 정확한 CDC 제약

572 START 단독에 세 경계 수정과 검증한 CDC 제약을 연결했다. 단일 전체 FIT는 성공했고, 최종 정확 경로 제약 아래에서 내부 setup·hold·recovery·removal의 음수 항목은 없다. **실기 기준은 MMC558이며, 576은 조건부 개발 후보다.** FPS 개선이나 보드 전체 전기적 sign-off를 뜻하지 않는다.

## 실제 변경

- screen_status의 진단용 bus_drive를 host 2단 동기화 뒤 snapshot[31]에 넣는다. 물리 SNES OE·DIR의 즉시 차단 식은 그대로다.
- sink의 idle_ss·idle_write·host_ready는 기존 release_local의 로컬 reset 해제를 공유한다.
- 최상위 sink_rom_fault도 같은 reset 출력을 사용한다. 새 reset FSM이나 RAM을 추가하지 않는다. 고장 검출 뒤의 정상 2 host 에지 샘플 지연은 유지한다.

실제 변경 RTL은 nes_screen_status151.sv, nes_sink_bridge165.sv, fxpak_nes_screen137_top.sv 세 파일이다. source·collector·epoch·plan·65816·ARM의 바이트는 기준과 같다. 원본 bridge를 함께 실행한 시험에서 RUN 뒤 최초 host 수락은 3→5에지로, **23.808ns 늘었다.** 평상시 패킷 공급 속도를 바꾸는 수정은 아니다.

## 제약과 전체 비용

기존 cdc181은 유지했다. 빠진 첫 동기화 단에는 수신 한 주기의 유한 max-delay를 둔다. Gray에는 더 짧은 송신 주기 **5.952ns**를 적용한다. held-data는 수신 2주기 예산을 쓰되 기존 11.904ns가 더 엄격하면 그 값을 보존한다. hold 제외는 이 정확한 비동기 입력 쌍에만 적용한다.

reset 예외는 검증한 release chain의 **CLRN 핀에만** 끝난다. D/ASDATA, 첫→둘째 단, 마지막 단에서 로컬 소비자까지의 정상 경로는 계속 검사한다. 전체 clock group, raw 제어, 진단 snapshot, 임의 reset 소비자를 포괄해서 제외하지 않는다.

| 같은 정책으로 비교 | MMC558 | 572 | 576 |
|---|---:|---:|---:|
| 음수 endpoint 행, 세 코너 합계 | 471 | 24 | 0 |
| 남는 음수 setup / recovery, ns | −7.081 / −7.167 | −5.695 / −6.578 | 없음 |
| 실제 첫→둘째 단 검사 수 | 67 | 70 | 77 |
| 검사 중인 유한 데이터 쌍 | 228 | 229 | 231 |
| 정확한 reset CLRN 핀 | 42 | 46 | 58 |

행은 clock pair별 각 목적지 최악 경로이며 모든 조합 경로 수가 아니다. 576은 합성기의 동등 reset 공유가 바뀌어 물리 이름과 chain 수가 달라졌다. 고정된 이전 이름으로 첫 검증이 실패한 것을 보존하고, **새 배치의 실제 연결**을 다시 추출했다. 한 번의 FIT 뒤 STA만 재실행했으며 배치 seed 반복은 하지 않았다. FIT 당시 초기 SDC와 최종 경로 SDC의 해시를 따로 기록했다. 최종 SDC로 다시 FIT한 결과라고 주장하지 않는다.

576의 전체 최악 setup **+0.045ns**, hold **+0.140ns**, recovery **+2.364ns**, removal **+0.490ns**, 최소 펄스폭 **+2.629ns**다. 다음 동기화 단의 최소 setup/hold는 **+4.764/+0.188ns**다. 유한 데이터 예산의 최소 여유는 Gray +5.102, mailbox +5.810, ROM 주소 +5.657, 단일 비트 +1.100ns다.

576은 **15,260 LE / 14,191 조합 논리 / 8,407 FF / 51 M9K / 264,816 RAM bits**다. 572 대비 −37 LE / −4 조합 논리 / +17 FF, RAM 동일이다. 세 개의 소규모 RTL 수정과 제약에 따른 전체 배치 결과이며 삭제한 제어량을 뜻하지 않는다.

원래 제약의 raw 결과도 보존했다. 576 raw setup/hold/recovery/removal은 **−8.849/−2.408/−11.602/−0.309ns**로, 숫자만 비교하면 기존보다 나쁘다. 해당 경로를 실제 CDC/동기 reset 경계와 대조한 최종 검사가 위 표다. 예외를 더해서 raw 수치가 좋아졌다고 표현하지 않는다.

## 동작과 일정

단일 Starter FLOAT 좌석으로 순서대로 시험했다.

- 각 위상에서 실제 SPI73 snapshot 32회, raw와 동기화 값이 다른 캡처 10회, 클록 정지·기존 transaction 유지 상태를 포함한 재시작 64회 통과.
- 실제 pad의 공통 reset·ACK·8비트 입력 전달, 원본 bridge 대비 최초 수락 3→5에지 확인.
- 실제 핀 mux 128조합, 각 위상 49 pin sample, STOP·부분 토큰·잘못된 ACK·정상 최종 ACK·두 슬롯 재사용 통과.
- 각 위상 실제 loader SPI 1,429,799 cycle, live START 거부 512회, 클록 고장 여섯 경우와 slot event 160개 통과.

기존 ARM·SPI·IRQ·ROM 도착 기록을 실제 65816에 두 위상으로 다시 재생했다. 각 53화면, 9,464/9,462개 이벤트와 arrivals/window/bank 기록은 573 재생과 정확히 같다.

| 표시 일정 | 위상 1 | 위상 2 |
|---|---:|---:|
| 952·957 표시 간격 | 각각 5 VBlank | 각각 5 VBlank |
| 952·957 최종 VBlank 대기 | 각각 0회 | 각각 0회 |
| 밀집 구간 평균 | 83.157135ms | 83.120854ms |
| 마지막 ACK master clock | 87,545,284 | 88,254,606 |

RTL과 고정 도착 기록의 65816 재생은 별도 실행이다. 새 전체 다중 클록 연속 공동 실행, 메뉴 복귀 실기, 실기 FPS를 새로 측정한 것은 아니다. ARM·메뉴 복귀 프로그램은 바뀌지 않았다.

## 남은 gate와 다음 순서

1. **168MHz load_end→remaining[0]의 +0.045ns 여유**를 검토한다. 이전 572 관련 setup +0.286ns보다 작아졌다. 경로의 실제 START/적재 의미와 수정 범위를 먼저 확정하며 seed나 epoch 배치 반복은 하지 않는다.
2. 미제약 외부 IO는 input 54 / output 57 ports로 남는다. 이 내부 STA 통과를 외부 버스 검증 완료로 확장하지 않는다. PSRAM 70ns·왕복 PCB 각 2ns 가정의 최소 읽기 예산은 +3.213ns이며 실제 부품·보드 측정값이 아니다.
3. 새 전달 여부는 이 범위와 기존 제한 실기 기준을 명시해 판단한다. STOP·두 슬롯·독립 검사·최종 ACK·VBlank를 유지한다. 파일명 갱신, RESTORE 제외, 사용자 SD 설치 후 로그 반환 절차를 따른다.
4. 실기는 MMC558과 같은 동선의 완료 [5,40) / [40,55), 합계 [5,55)로 비교한다. 현재 MMC558 14.01fps·5–55초 13.72fps를 새로운 측정 없이 갱신하지 않는다.

## 재현과 증거

[검증 JSON](../analysis/cdc576-verification.json)에 원본·최종 SDC, SOF, RTL, 원시 로그와 표시 기록의 해시를 고정했다. prepare_nes_cdc576.py는 MMC558 보드에서 572를 재생성한 뒤 세 파일을 수정한다. inventory_nes_cdc576.tcl은 원래 제약의 실제 교차 경로를 열거하며 nes_cdc576.py가 정확한 제약과 연결 검증 Tcl을 만든다. 초기 배치의 initial576.sdc와 최종 cdc576.sdc는 별도 보존한다.

선택 자료는 Temp nes-cdc576-board01, test05, bus01, start01, replay1/2와 probes/nes-cdc576/{558,572,576}-selected다. 첫 wrapper job은 경로 quoting 때문에 시험을 실행하지 못했다. test01은 watchdog 상수 폭 때문에 compile 실패했고, test02의 sink ROM 누락 경고를 고친 test03부터 실제 ROM을 사용했다. test04는 pad, test05는 원본 bridge 대조를 추가했다. 첫 routed 검증의 이전 reset 별칭 불일치도 보존했다. 라이선스 파일·서버 로그는 증거 묶음과 Git에 넣지 않는다.

선택/실패 원시 자료와 도구 301파일을 probes/nes-cdc576/archive01/evidence.zip에 보관하고 전체 바이트를 재검증했다. ZIP SHA256은 8b40405cd831dce93e26ad0e4e0757e6a095755ea124fd784c5667cc3f384676이다.
