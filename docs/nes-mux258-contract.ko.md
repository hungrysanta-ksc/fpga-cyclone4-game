# NES258 — 일반/typed head 중재와 tile/map staging 공유

2026-10-19, PR130 `codex/nes-wholepath-boundary-256`. NES257의 입력→표시 lease 전환과 한 map DMA 경로를 확장했다. 동일한 직렬 소유 일정에서 staging RAM을 공유하면 **240LE·171FF·32,768bits(4KiB)**가 줄고 검증된 처리 기록은 같다. 전체 보드의 490LE/40LAB 부족 해결이나 60fps 달성 판정은 아니다.

[계획](nes-mux258-plan.json) · [기계 검증](../analysis/mux258-verification.json) · [부모 경계](nes-boundary256-contract.ko.md)

## 실제 교체 경계

`nes_mux258`은 기존 queue184에서 유래한 queue의 단일 head를 읽는다. op1..8은 SNES 일반 packet 읽기/ACK 검사에, op9는 typed map parser에 소유권을 준다. 일반 ACK 검사 동안 SNES의 packet 읽기를 닫아 ACK 검사기와 RAM 읽기 포트를 공유한다. ACK 성공의 `ack_done` 또는 typed staging seal 뒤의 parser retire 중 하나만 같은 head를 반환한다. 일반 ACK 검사기는 합성에서 살아 있다. 257의 일반 ACK 입력을 묶어 제거한 MAP과 증분 면적을 비교하지 않는다.

실제 `nes_tile_bulk206`에서 aperture만 밖으로 꺼낸 `nes_tile_producer258`을 사용한다. tile 입력의 32B CDC RAM, descriptor, 연속 slot 묶기, chunk seal 및 소비 대기는 유지한다. 원래 tile 생산자가 요구하던 2×2KiB aperture를 typed map과 공유한다. `NONE/TILE/MAP` 소유권에 따라 begin/put/seal/read/consume을 중재한다. TILE은 end seal과 모든 chunk 소비까지, MAP은 전체 순차 DMA 읽기와 token 확인 및 core receipt 완료까지 RAM을 보유한다. map 선점 시 tile 입력은 실제206의 보류 경로에서 대기한다.

SHARED=0 기준군은 **같은 중재·같은 직렬 일정**에 tile/map aperture만 각각 둔다. SHARED=1은 하나를 공유한다. 독립 aperture를 동시에 생산하는 더 빠른 일정의 성능까지 비교한 것은 아니다. RAM 공유로 얻는 비용 차이를 분리하는 대조군이다.

출력 MAP top에는 queue/ACK/parser, tile206 producer, aperture, CDC mailbox, token·읽기·receipt·최종 ACK 제어가 포함된다. source257/core/collector/display lease 및 upstream tile192/ROM arbiter는 포함하지 않는다. 실제 CPU 연결 시험에는 source/core/collector/display lease를 함께 사용하지만 그 회로를 이 MAP에 더해 전체 면적을 산출하지 않는다.

## bank·token·취소 규칙

- 일반/typed 모두 bank, generation16, serial32, packet sequence16을 확인한다. 다음 identity는 이전 표시 ACK 또는 공통 STOP 전에는 받아들이지 않는다.
- 모든 tile/map chunk는 한32bit allocator에서 성공한 begin 때 token을 받는다. typed packet은 OPEN 때 allocator와 일치하는 token을 제시해야 한다. 앞으로 ARM serializer의 token 할당/조회 연결이 필요하다.
- STOP은 진행 중 queue·tile CDC·staging·receipt·최종 ACK를 취소하지만 이미 할당한 token과 마지막 admitted serial은 되돌리지 않는다. FFFFFFFF token과 serial 역행/래핑은 거부한다. 보드 reset만 namespace를 초기화하며, 그 전후 실제 버스의 quiesce는 시스템 계약에 남는다.
- 완료된 순차 aperture 읽기 수가 chunk 길이와 같고, 4B token을 모두 쓴 뒤 A5 consume을 보내야 소비한다. map staging seal/queue retire, DMA consume/receipt, 최종 표시 ACK는 서로 다르다.
- map receipt 뒤에도 최종 map token을 유지한다. map 뒤 tile이 소비된 경우에도 최종 ACK는 마지막 map token으로 확인한다. 이 범위는 적어도 한 map receipt가 있는 표시이며 tile-only 최종 표시 프로토콜을 새로 정의하지 않는다.
- map은 이 진단 범위에서 최대64B이다. 일반 패킷의 의미 해석은 기존 SNES 소비자 책임이다. 여기서 실행한 일반 패킷은 op2/16B header/무payload이므로 일반 명령 전체 렌더링 검증으로 확대하지 않는다.

## 검증 결과

선택 `test07`: 공유/분리 각각 정상 경로와16개 guard(34회 독립 실행). 정상 경로는 4credit를 먼저 채운 일반→map→일반→map head 순서, 두 비연속 tile chunk, bank0→1→0 재사용, 총288B 소비,4 map receipt,2 일반 ACK,3 최종 표시 ACK를 검사한다. 두 구성의 이벤트 CSV가 byte exact다.

16개 guard는 잘못된/재사용/중복 token, 부분 DMA consume, typed head에 일반 ACK 쓰기, 잘못된 일반 ACK sequence, map PUT 중 취소, DMA 중 취소, 일반 ACK 검사 중 취소, tile CDC 부분 입력 취소, token/serial 끝값, 조기 identity, map→tile 역방향 중재, 두 tile bank가 seal된 상태의 부분 읽기 취소를 포함한다. 상세 case별 의미는 JSON에 있다. 고정 클록 위상 시뮬레이션이며 CDC 위상 전수 검사나 STA가 아니다.

선택 `coupled05/reference02`: 실제 frame905 collector/query/source/SPI(4398B canonical,5597B source payload)와257 receipt/H2 core에258을 연결했다. 실제65816이 일반 header를 읽고 ACK한 뒤 **tile16B와 map64B를 DMA**한다. Mesen VRAM의 두 영역을 fixture와 비교하고, token consume→map receipt→seal→VBlank BG1SC/표시→최종 ACK/lease retire까지 통과했다. CPU/PPU 상태 주입 없이 실제 코드446B를32KiB 진단 ROM에서 실행했다. 공유/분리 ROM·CPU 버스·RTL 이벤트 기록은 동일하다.

tile16B는 기존 C stream fixture에서 공급했다. upstream tile192/ROM arbiter는 연결하지 않았다. 나머지90개 범위/8224B와 H2/manifest는255 fixture다. ARM 실제 serializer, 전체 일반 명령/메타데이터 전송 및 전체 픽셀 비교는 아직 아니다.

## 같은 경계의 비용표

| 측정 | 분리 aperture | 공유 aperture | 공유−분리 |
|---|---:|---:|---:|
| MAP LE | 3559 | 3319 | −240 |
| 조합 함수 | 2177 | 2062 | −115 |
| FF | 1922 | 1751 | −171 |
| RAM bits | 73984 | 41216 | −32768 |
| 정상 test07 host ticks | 137315 | 137315 | 0 |
| 정상 map의 tile 대기 ticks | 2282 | 2282 | 0 |
| 일반 ACK 검사 ticks,2회 합계 | 36 | 36 | 0 |
| 실제 CPU 마지막 map DMA 시작→consume master clocks | 880 | 880 | 0 |

MAP `map-separate02/map-shared02`는 같은9개 RTL hash를 `test06`에 묶어 실행했고,16guard를 추가한 `test07` 및 최종 CPU 실행의 RTL과도 같다. Quartus Lite25.1std.0 Build1129, EP4CE15F17C8, top/옵션 동일, SHARED만 다르다. owner/state/ns/tile state가 FSM으로 추출된다. 공유판 RAM은 aperture4096×8,queue1024×8,tile_store32×8로 추론됐다. 이 비트 수를 배치된 M9K 수나 전체 회로 여유로 환산하지 않는다. 기존206 async_reg 경고와 상수 range 상위 비트 경고를 보존한다. FIT/STA는 실행하지 않았다.

test07의100MHz host 기준 총1.37315ms에는 시험대의 의도적인 일반 head 대기612.10us, map의 tile 대기22.82us, 고정 버스 서비스가 포함된다. receipt 응답은8NES-cycle 시험 endpoint다. 이 숫자를 실측 프레임 지연이나 기존 조건부 비용표에 더할 새로운 독립 항으로 쓰지 않는다.

실제65816 기록은 일반 ACK publish2564, tile 읽기3100..3220/consume3564, map DMA 시작4338/읽기4372..4916/consume5218, 최종 ACK307324 master clocks다. map 읽기는 대부분8clock 간격이며 한48clock 간격을 포함한다. 최종 ACK는 진단 코드의 VBlank 대기를 포함한다. RTL↔Mesen RPC는 버스200ns active+200ns release, zero receipt/seal poll 때 RTL100us 진행이다. CPU와 RTL에 공통 물리 시간축이 없으므로 두 시각을 합산하거나 FPS로 환산하지 않는다. **현재 확보한 이득은 같은 직렬 처리에서의 회로/RAM 절약이며 속도 향상은 관측되지 않았다.**

## 라이선스와 재현 실패

`license01`에서 설치된 Quartus Standard를 다시 실행했다. `Error292037`로30일 평가 기간 만료를 재확인했으며 합성 전 실패다. 라이선스 파일/전역 설정은 바꾸지 않았다. 설치된 Lite는 두 MAP을 정상 완료했고, Questa는 승인된 임시 FLOAT 경로로 모든 시험을 실행했다. Standard 오류를 Questa entitlement 부족으로 해석하지 않는다.

초기 `map-*-01`은 중첩 generate의 inline genvar 문법이 Quartus에서 거부된 실패다. genvar를 module scope로 옮기고 동일 기능을 test06/07로 확인한 뒤 map02 두 구성을 실행했다. 자원 부족이나 라이선스 오류가 아니었다. test01 경로 오류/test02 예약어 compile 실패, 중간 성공 및 모든 실패를 보존했다.

`coupled03`은 DMA/receipt 뒤 RPC140부터 Lua 반환/trace가 누락되고 잘못된 최종 token이 거부된 실패다. 당시 콜백 오류 로그는 없으므로 원인을 사후 확정하지 않는다. 새 `timeout01`에서 같은 receipt RPC에2.5초 host 지연을 주입해 **Maximum execution time (1 seconds) exceeded**를 기록했다. Mesen의 [기본 제한](https://github.com/SourMesen/Mesen2/blob/master/UI/Config/Debugger/ScriptWindowConfig.cs)과 [콜백 오류 시 반환값을 적용하지 않는 처리](https://github.com/SourMesen/Mesen2/blob/master/Core/Debugger/ScriptingContext.cpp)는 관측 증상과 일치한다.

258 검증 도구에 프로세스 한정 Lua timeout90초와 RPC 오류 파일/실패 중단을 추가했다. 최종 두 구성 모두 같은2.5초 지연을 넣고 PASS했고 에뮬레이션 기록은 동일했다. 이 설정은 벽시계의 검증 도구 대기 허용치이며 SNES/FPGA 실행 시간 변경이 아니다. 전역 Mesen 설정이나257의 역사적 도구는 변경하지 않았다.

## 다음 판정

이 후보는 공유 RAM/중재의 제한 경계에서 유지한다. P2 제품 구현 선택은 유보한다. 다음에는 ARM 계획·serializer가 tile token 배정과 일반/typed queue credit를 실제로 다루도록 연결하고, tail/scroll/OAM/H2와 일반 payload 소비를 같은 경로로 확장해야 한다. source와 output의 공유 SPI 일정, tile192/ROM arbiter의 경쟁을 포함한 heavy7(952/954/955/962/963/968/970) 시간표와 전체 RUN/IRQ·회로 경계를 먼저 완성한다. 그 동일 구성의 whole FIT/STA/CDC/IO/71프레임 검증으로 넘어간다. 240의490LE/40LAB 부족 해결, mapper 여유, 다음 capture 중첩, raw0 전환, 실기60fps는 여전히 열려 있다. production227/GBC164/saveSRAM은 그대로다.

## 재현 자료

공개 파일은 RTL/generator/testbench/분석기 및 payload 없는 결과와 hash다. 기존240/249/255의 비공개 fixture 경로가 필요하다. ROM·타일·map bytes와 전체 raw log는 `probes/nes-mux258/`에 남긴다. 선택 분석은 `analysis02`이며 `analysis01`은 최종 쌍 비교만,02는 timeout 보강 전 coupled04와의 CPU/event 동일성도 검사한다.

Questa 작업은 기존 `probe_float.ps1 -RunOnly -AfterSmokeScript <absolute job.ps1> -QuestaBin <bin>` 안에서 아래 도구를 호출한다. `--out`은 새 ASCII 경로여야 한다. MAP은 FLOAT 밖에서 실행해도 된다.

```text
python tools/probe_nes_mux258.py --guards --out <new-unit> --questa-bin <bin>
python tools/probe_nes_mux258_coupled.py --rpc-delay-ms 2500 --out <new-shared-cpu> --questa-bin <bin>
python tools/probe_nes_mux258_coupled.py --separate --rpc-delay-ms 2500 --out <new-reference-cpu> --questa-bin <bin>
python tools/probe_nes_mux258.py --map-test <passed-unit> --shared 0 --out <new-map-reference>
python tools/probe_nes_mux258.py --map-test <passed-unit> --shared 1 --out <new-map-shared>
python tools/analyze_nes_mux258.py --out <new-analysis>
```

분석기는 계획에 적힌 보존된 선택 경로를 재검사한다. 새 시험 경로로 선택을 바꿀 때는 원본 실행을 보존하고 명시적으로 갱신한다. timeout 음성 시험은 `--script-timeout 1 --rpc-delay-ms 2500`이며 실패가 정상 기대값이다. 이 실패를 기능 PASS에 합치지 않는다.
