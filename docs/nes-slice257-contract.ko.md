# NES257: 입력 lease 전환과 한 map 범위의 실제 DMA 완료

PR130의 R1 첫 범위를 구현했다. **frame905의 bank0 map 32단어(64B)**에서 실제 collector/source/SPI → 표시 lease → E1 packet/queue/parser → staging → Mesen의 실제65816 DMA → receipt → seal → VBlank의 표시 레지스터 갱신 → 최종 ACK 연결이 통과했다. 전체 R1·보드·60fps 승인은 아니다. 선택 결과는 `probes/nes-slice257/test06`, `map03`, `analysis01`이다.

## 실제로 연결한 부분

기존255를 생성 기반으로 쓰는 `nes_slice257.py`가 입력 단계에서는 collector의 owned/geometry/generation을, 입력 done 이후에는 capture_lease201의 display lease/epoch/generation을 검사한다. done 한 사이클은 기존 입력 identity를 유지해 lease가 등록되는 경계를 건넌다. 실제 capture_lease201의 export_release가 collector를 해제하며 owned를 상수로 강제하지 않았다. 선택 범위 진입 시 `owned==0`, `waiting_display==1`, `lease_valid==1`을 검사했다. 다음 collector capture와의 중첩은 이번에 실행하지 않았다.

입력은 실제 frame201/query/projector/core/transport를 실행한다. canonical4398B를 검사했고, 출력된 source SPI5597B는 이전249의 독립 기대 fixture와 바이트 단위로 같았다. 실제 ARM serializer를 새로 실행한 것은 아니다. 기존 C 결과 fixture에서 선택 범위의 데이터를 읽어 테스트벤치가 실제 SPI 신호로 전송한다.

`nes_range257.sv`는 host 클록에서 queue184 기반4slot 큐의 CRC 확인된 head를 읽고 op/bank/serial/generation/sequence/범위/길이/token을 검사한다. 16B header,4B token,64B 값에 E1 opcode와 CRC2B를 더한87B wire packet을 사용했다. 범위 상한은32단어이며 일반 프로토콜 확정안이 아닌 제한 진단 포맷이다.

queue의 읽기 포트와 retire는 이 범위에서 parser 하나가 소유한다. 모든 값이 기존 bulk_aperture188의 불변 chunk에 게시된 뒤 별도 parser_retire로 packet credit을 반환한다. 이때 receipt는 그대로다. 일반 SNES ACK 입력은 이 시험에서0으로 연결돼 있으며 **일반/typed packet의 head 중재는 아직 결합하지 않았다.** 두 경로의 retire를 같은 ACK로 위장하지 않았다.

180B 본문의 진단용65816 프로그램이 실제 `$420B` DMA를 실행한다. Lua는 CPU/PPU 상태를 주입하지 않고 외부 버스 read를 RTL에 요청하고 CPU write를 RTL로 전달한다. 실제 CPU가 `$40:0800..083f`를 읽고 VRAM `$8000..803f`에 쓴64B가 원본과 같음을 확인했다. adapter는 완료된 read 주소가 순서대로64개 모두 관측됐는지 검사하며, 읽기 없이 token만 쓰면 취소한다. 이 계수는 외부 버스 읽기를 확인하는 것이며 FPGA가 SNES 내부 PPU write 자체를 관측한다는 뜻은 아니다. PPU 결과는 Mesen에서 별도로 검사한다.

DMA 뒤 CPU가 token과 consume을 쓰면 host→NES mailbox가 범위 정보를 전달한다. core는 선택 범위의 receipt를 갱신하고 반대 방향 mailbox로 확인한다. 그때 aperture를 해제한다. 남은90범위/8224B와 manifest/H2/CRC는 기존255 fixture 경로로 검증한다. 전체 seal 후 CPU가 VBlank를 기다려 BG1SC/화면 밝기 레지스터를 쓰고, 별도 final ACK token을 보낸다. 최종 mailbox가 core와 표시 lease를 퇴역시킨다. **한 범위의 VRAM 및 표시 레지스터 전환 검사이며 완성된 게임 화면의 픽셀 검증은 아니다.**

## 실행과 취소 결과

| 사건 | NES 테스트벤치 tick |
|---|---:|
| 입력 done |738361|
| staging 게시 |760957|
| DMA 완료 범위 수락 |761897|
| receipt 확인 |761910|
| 전체 seal |789509|
| SNES 최종 표시 ACK |790709|

staging 게시 시 queue accepted/retired가 각각1임을 확인했고 receipt는 변경되지 않았다. 실제 DMA consume 이전에도 receipt 불변성을 검사했다. 최종 receipt754B, CRC 상태64B, H2 문맥32B는 기존 기대 결과와 같았다.

9개 오류 시험이 모두 통과했다: 읽기 없는 consume,64B 읽은 후 틀린 token, DMA/receipt/seal 전 final ACK,8B 읽은 뒤 STOP, 입력 완료 후 display generation 불일치, receipt 뒤 중복 consume, E1 CRC 오류, packet generation 오류, packet bank 오류. 각각 ACK/retired/seal/staging/표시 lease가 닫혔고 이후1024B 공유 RAM이 더 이상 바뀌지 않았다.

guard5는 처음에 실제 접속 누락을 찾았다. core generation 오류가 source를 정지시켜도 capture_lease201의 waiting_display가 남았다. 최종 접속에서는 core fault도 공통 STOP에 포함해 해결했다. 이 연결은 생성된 통합 테스트벤치에서 검증했으며 배포 보드 top을 교체하지 않았다.

## 시간의 의미

Mesen의 master clock에서 DMA 시작1130, 첫 읽기1164, 마지막 읽기1668, consume2010, final ACK307316이었다.64번의 DMA 읽기는8 master clocks 간격이다. DMA 시작→consume880 master clocks에는 시작/마무리와 token 작업이 포함된다. NES 쪽 범위 수락→receipt 확인은 이 fixture에서13ticks다.

두 시뮬레이터는 파일 RPC로 **인과 순서**를 연결했다. host 버스는 요청마다200ns 유지+200ns 해제하며, receipt/seal poll이0이면 RTL을100us 전진한다. CPU와 RTL의 시계는 물리적으로 동기화되지 않았다. 따라서 위 tick 차이들을 합산해 전체 지연·WCET·FPS로 사용할 수 없고, 기존256의 조건부15.995909ms나 잔여0.670758ms를 새 실측으로 대체하지 않는다. 전체 ARM/실제 SPI 공유·IO 타이밍/VBlank 일정 비용은 계속 미확인이다.

## 실제 합성 범위와 비용

테스트와 동일한5개 RTL의 해시를 확인해 range adapter 경계만 한 번 MAP했다. Standard 평가판이 만료돼 map01/02는 합성 시작 전에 실패했다. 설치된 **Quartus25.1std Lite Build1129**로 map03의 실제 합성을 완료했다. Questa FLOAT 라이선스는 정상이며 별개다.

| MAP 항목 | 결과 |
|---|---:|
| 전체 range 경계 LE / comb / FF |1947 /1068 /1098|
| memory bits |40960|
| 부모 자체 comb / FF |481 /460|
| 네 mailbox 합계 comb / FF |25 /174|
| queue comb / FF / bits |428 /212 /8192|
| aperture comb / FF / bits |134 /252 /32768|

queue1024×8과 aperture4096×8은 M9K RAM으로 추론됐다. parser state와 NES receipt state 모두 FSM으로 추출됐다. 이 표의 부모 자체 수치와 inclusive 전체를 중복 합산하지 않는다. source/core/capture lease는 이 MAP 밖에 있고, 일반 ACK 입력을 묶은 결과 해당 checker가 제거됐다.64B 제한으로 일부 counter도 상수화됐다. 따라서 기존240 sink/direct 부모와 빼서 절약을 주장하거나1947LE를 순수 추가 비용으로 계산할 수 없다. 기존 전체490LE/40LAB 부족은 해결되지 않았다.

`async_reg` 인식 경고(기존 mailbox206 포함), reset-loop index j의 latch 경고와 count 상위6bit 상수 경고를 보존했다. 새 FIT·배치·CDC/IO STA는 없으며 물리 타이밍을 승인하지 않았다. 실 제품에는 queue의 일반 ACK/head 중재, tile/map aperture 공유와 기존 제어 제거를 함께 묶은 동일 경계 비교가 필요하다.

## 보존과 다음 경계

test01 선언/문법 오류,02 Tcl 숫자 진법 오류·CPU timeout,03 정상 PASS,04 final RPC 응답의 비원자적 게시 경쟁,05 guard5 lease 오류를 모두 보존했다.06이 최종 정상+9guard 결과다. ROM과 원본 fixture는 private probe에만 보관하며 공개 분석에는 해시와 수치만 넣었다. production227/GBC164/saveSRAM과 기존255 증거는 변경하지 않았다.

다음 단계는 동일 경로를 bank/token 재사용과 일반/typed head 중재 및 tile/map aperture 공유에 확장하는 것이다. 이어서 실제 ARM 계획·serializer와 tail/scroll/OAM/H2까지 연결해 heavy952/954/955/962/963/968/970,71프레임 및 전체 RUN/IRQ/보드 비용을 판정한다. 첫64B 성공을 전체 R1 완료로 올리지 않는다.

[계획](nes-slice257-plan.json) · [수치와 출처](../analysis/slice257-verification.json) · [이전 전체 비용표](nes-boundary256-contract.ko.md)
