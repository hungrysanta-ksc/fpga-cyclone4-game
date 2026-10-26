# NES383–385: SNES WRAM 보관과 PPU 완료를 분리한 후보

375 RTL·377 ARM을 유지하고 SNES 소비 방식 후보를 구현했다. payload를 WRAM에 먼저 보관해 FPGA의 저장 공간을 반환하고, 준비된 작업들을 VBlank에서 DMA한 뒤 최종 ACK한다. map은 이전 target bank의 WRAM 이미지를 갱신한 다음4KiB를 한 번에 DMA하고, OAM도544B로 묶는다.

**실제65816의10warm 단일 프레임 시험은 통과했지만 연속 일정은 아직 실패한다.** 첫 실패가910→911로 늦춰지고907 표시 준비가21.602105ms 빨라졌다. 전체 회로 부족2,255comb는 그대로다. 현재 후보를 실기용으로 선택하거나 지속60fps라고 판정하지 않는다.

## 구현과 소유권

383은 실제65816 프로그램2,168B다. $6040..$604b의 typed descriptor와 $6060..$6068의 ordinary descriptor를 읽어 payload를 WRAM으로 복사한다. typed tile은 append-only buffer, map은 bank별4KiB 이미지, CGRAM/OAM은 기존 bank별 WRAM 영역에 저장한다. 작은 FPGA staging을 VBlank까지 붙잡지 않는다.

|SNES 영역|크기|역할|
|---|---:|---|
|$7E8000..$7E9FFF|8KiB|tile payload spool|
|$7EA000..$7EAFFF|4KiB|16B job record,최대256개|
|$7EC000..$7EDFFF|8KiB|두 bank map 이미지|

합계20KiB이며 DP·view·stack 제어 공간은 별도다. 기존 SNES 코드가 사용하는 $7E2000을 피했다. **전체 resident firmware의 WRAM 배치를 승인한 것은 아니다.** ordinary325의 WRAM/HDMA 처리와 실제 dispatcher·frame reset·음성/입력/NMI 및 WRIO shadow를 하나의 프로그램으로 연결해야 한다.

source read CRC/coverage·token receipt는 이제 **WRAM 저장 완료**를 뜻한다. 실제 PPU 완료와 같다고 세지 않는다. native CPU는 모든 source 저장 뒤 PPU job을 실행하고, 그 완료 후에만 최종 token/ACK를 보낸다. FPGA의 독립 source expected/CRC/coverage는 유지한다. FPGA가 보지 못하는 SNES WRAM의 이전 map 값까지 새로 검사했다고 주장하지 않는다.

## 실제 CPU와 검증 범위

native07은907~916 각 프레임의 실제 source read payload/descriptor를 공급한다. 각 프레임의 H2 view도 실제 ARM op15와 certificate에서 재구성했다. 다음을 실제 Mesen65816에서 확인했다.

- 모든 source byte를 읽고 해당 token으로 저장 receipt를 보낸 뒤 PPU 전송을 시작한다.
- 최종4KiB VRAM map·tile 범위·OAM544B가 독립 expected와 같다.
- 실제 PPU data write와 최종 ACK가 같은 VBlank 안에 있다.
- 실제 현재 view의 네 scroll byte를 PPU에 쓴다.

10개 모두 통과했다. 첫907은 source record13개를 PPU job5개로 바꾸고, 첫 PPU trigger→최종 ACK는46,484master clocks다. 위상0/46,561ps allocation으로 약2.164342ms이며 refresh/alignment도 기록된 CPU 시간에 포함된다. 표본은mask0x18/raw2다. 다른 mask/raw count·시작 위상이나 실기 WCET 보장은 아니다.

DMA의 $420B write 직후 첫 opcode fetch를 완료 증거로 쓰지 않았다. CPU가 pause하기 전 그 fetch가 먼저 일어나므로 NOP 뒤 marker와 실제 PPU data write를 확인했다. 907의4KiB map job은 trigger marker→done marker33,920clocks로, 순수 byte 하한32,768 외의 guard·DMA 시작·refresh·fence 비용도 들어간다. [SNES timing](https://snes.nesdev.org/wiki/Timing).

**이전 target-bank map/OAM WRAM 이미지를 독립 prior-frame 값으로 미리 넣었다.** cold 부팅에서 이 이미지를 만드는 것과 STOP 뒤 정상 복구·bank 유효성은 아직 없다. HDMA terminator도 명시적 fixture다. 전체 pixel·전체 resident CPU·HDMA upload 증명과 구분한다. 초기 native06은 기존266의 고정 scroll view를 사용했다. 최종 native07과 joint04의 현재 view binding을 기능 판정에 사용한다. 두 native 실행의 instruction/event 시각은 같아도 데이터 binding은 구분한다.

guards04는 실제 같은 ROM에서7case를 확인한다. 첫 저장 뒤STOP,모두 저장한 뒤STOP,PPU job2개 뒤STOP은 HDMA off/forced blank로 무효화하고 최종ACK를 보내지 않는다. tile8193B와257번째job은 WRAM 용량 한도에서 거절한다. 별도 CGRAM512B 전송도 실제 PPU data port의512바이트를 확인했다. CGRAM-only case의 이전 VRAM/OAM도 명시적 fixture이며 실제 FPGA 최종 ACK 경계 시험은 아니다.

마지막 `densepalettebudget`은 기존907 크기 구성에 출력 ABI의 길이·종류가 허용하는512B palette 갱신을 더한 synthetic case다. 추가 ARM/NES 생산 프레임을 실행한 결과는 아니다. 모든 source 저장 뒤 VBlank 예산에서 거절하고 PPU/최종 ACK를 실행하지 않는다. 이는 안전한 admission 동작을 확인하지만 **지원해야 할 palette 갱신 크기를 현재 dense 전략으로 처리하지 못한다는 반례**다. 일반 palette 변경이나 MMC4/5 확장 여유가 확보됐다는 뜻이 아니다.

## 실제 ARM·SPI·IRQ·ROM 연속 일정

384는383의 기록된 CPU source service와 PPU service를 실제377 ARM·375 RTL 경로에 연결한다. source descriptor 경계/위치/길이/모든 byte가 native profile과 같아야 계속한다. 실제 source를 profile 데이터로 대신 공급하지 않는다. recorded PPU tail은 해당 현재 payload의 WRAM 저장·독립 검사·seal 뒤에만 실행한다.

typed 소비에는 실제 native source service의 관측 control 비용을 부과한다. ordinary3/4는 기존325의 byte replay를 유지하면서 총시간이383 저장 비용보다 짧으면 보정한다. ordinary5 WRAM은325 경로다. 381 view head도 유지하므로 **하나로 컴파일된 전체 resident 소비기를 실행한 시간은 아니다.** 고정 profile/단일 위상의 실제 CPU service allocation이며 일반 WCET는 아니다.

최종 joint04는 같은 capture cycle 기한·ROM 위상0·공유 SPI·IRQ·2슬롯을 사용한다. 결과는905~908 배출4,다음 capture908/909/910 승인,**911에서 owned1/release0/fault0으로 실패**다. 909는 다음 입력 생성까지이며 출력 완료로 세지 않는다.

|항목|382: VBlank마다 staging 유지|384: WRAM 선행 보관|
|---|---:|---:|
|907 source 시작|264.333059ms|동일|
|907 표시 ready|299.299847ms|277.697742ms|
|907 표시 전환|910 실패 때까지 미완료|VBlank16,282.738367ms|
|907 source 시작→프레임 완료|실패 전 미완료|18.488559ms|
|908 source 시작→프레임 완료|미완료|35.047559ms|
|첫 실패 capture|910|911|

907 ready는21.602105ms 앞당겼지만907/908 표시는 VBlank16/18로 한 번 건너뛴다. 907의 서비스 뒤 남은 VBlank는 약131.814µs다. 이전195µs 계산 여유처럼 이 값도 mapper 예산으로 전용하지 않는다.

908 입력은281.563796ms에 물리적으로 확정되어 있다. 그러나 현재 ARM은907 최종표시·retire 후 수신을 시작한다. 그 사이 첫 ROM 허용창을 놓치고908 ready가304.949735ms까지 밀린다. 버퍼만 늘리거나 source 저장 receipt를 빨리 반환하는 것으로 ARM/hint 일정까지 해결되지는 않는다.

cancel02는 실제 M4/RTL에서907의 source 저장과12view read가 끝난 뒤 STOP을 주입한다. PPU replay/최종ACK를 차단하고 validator+queue+source shadow를256host clocks 동안 동결한다. 전체 view read36에는 cold905/906의24회가 포함된다. STOP 때문에 ARM worker가 종료하는 것은 이 negative case의 예상 결과이며 positive 실행에서는 같은 오류를 계속 실패로 처리한다.

## ARM 선행 수신의 실제 메모리 경계

385는 실제 precommit3 RAM에서 다음908의 N5 두 block을 M4 `block286`으로 해석했다.17,877instructions이며 SPI/IRQ 비용을 포함한 시간으로 환산하지 않는다. 전체 geometry/raw가 기준과 같고 input/video/resident/dirty/certificate/output/seal7개 객체는 바뀌지 않는다. 쓰기 객체는 receiver/history와 두 source mask다.

하지만 실제 postdisplay3의 닫힌 resident/dirty 객체를 합쳐 수명을 시험하면 `publish352`가 **표시3을 receiver4의 이력으로 공개**한다. 실제 RAM 두 snapshot을 조합한 의도적인 lifetime 반례이며 live 동시 일정은 아니다. 현재 commit의 epoch/serial/raw_count를 수신 문맥과 분리해야 한다.

이를 위한 `publish385` C 수정 후보도 실제 M4로 검증했다. 기존 current resident의 epoch/serial과 current input의patch_count를 재사용한다. 새16B 복사본 없이 source STOP/error·현재 metadata의 세대/상태를 검사한다. next receiver phase0/1/2와 raw count 변경,실제STOP286 및 metadata 불일치의16case가 통과했다. 기존 함수100B/30instructions 대비 후보188B/58instructions이며 **추가 정적 RAM0B지만 함수 stack은0→20B**다. 전체 stack 여유나 실행시간이 개선됐다고 계산하지 않는다.

이 후보는 별도 flash page에서 실제 baseline RAM 심볼을 사용하는 component 시험이다. 선택한377 ARM 이미지와 live scheduler를 바꾸지 않았다. 호출은 현행처럼 현재 최종 ACK/retire를 확인한 뒤여야 하며,next planner의 expand/BEGIN은 그 뒤에만 허용해야 한다. 예비 RX 상태24B에 이 방식을 연결하는 안과 frozen commit16B+RX24B=40B를 두는 안을 비교한다. 새 ISR/전체 SPI 일정·instruction 단위 STOP race·복구 검증은 아직 없다.

ARM `source_hint367`은 resident.open 동안 hint를 막는다. FPGA `nes_hint361.host_owner`도 display lease가 켜져 있으면 새 host hint를 거절한다. 현재 입력과 이전 표시의 hint generation을 독립적으로 받는 경계도 없다. 따라서 단순히 다음 수신을 호출하거나 이 guard를 삭제하지 않는다. 다음 입력의 CRC·hint·cache 소유권,현재 plan의 ROM drain·generation,STOP 무효화를 공동으로 교체해야 한다. FPGA 추가 비용은 null이다.

## 다음 후보: source 수신 확대와 SNES burst 선택을 비교

먼저 SNES에서 모든 map을4KiB로 DMA하는 대신 기존 sparse 범위·열 방향 span·dense 중 선택하는 방식을 실제로 비교한다. ARM/FPGA의 새 동시 hint 문맥 없이 최종 ACK를 앞당겨 다음 ROM 창을 확보할 가능성을 검토한다. 기존 packed 전송과 독립 검사는 유지한다.

열 전송은 VMAIN의32word 증가 기능을 후보로 삼는다. source column 데이터를 연속 WRAM에 모으는 비용까지 포함해야 한다. [PPU 레지스터](https://snes.nesdev.org/wiki/PPU_registers).

아래는 실제 read 위치에서 계산한 구조 예산이다. `1280clocks/job+8clocks/byte`는 native 후보의 예산 계수이며 **새 구현의 측정 시간이 아니다.** 열의 빈 셀은 유효한 bank 이미지에서 채워야 하며 gather·설정·추가 RAM·CPU 시간을 따로 측정해야 한다.

|frame|원본 map 범위/byte|열 span 수/byte|sparse 예산 clocks|dense 예산|column 예산|
|---|---:|---:|---:|---:|---:|
|907|7/40|12/40|9,280|34,048|15,680|
|908|16/32|1/80|20,736|34,048|1,920|
|909|32/92|2/160|41,696|34,048|3,840|
|914|28/82|13/166|36,496|34,048|17,968|
|915|41/128|14/172|53,504|34,048|19,296|

907에는 기존 sparse,908/909에는 열 span을 고르는 이유가 다르다. column pack4KiB+dirty bounds64B+작업 상태16B의추가4,176B는 예비 상한이며 아직 할당하지 않았다. 변경된 byte만 처리한다는 이유로 기존 cached map 값의 유효성이나 gather 시간을 무료로 세지 않는다. 이 후보가 먼저 같은 ROM 창을 확보할 수 있는지, ARM RX24B+publication/stack 비용과 새 FPGA hint 문맥이 필요한지 전체 비용으로 결정한다.

## 회로와 보드 gate

모든 공유 RTL31개와 M4 PT_LOAD는375 wholeMAP/377 기준과 같다. 기존 Quartus Lite22,390LE/17,663comb/8,985FF/300,640bits를 상속한다. **새 FPGA 절감0,부족2,255comb/155여유 포함순삭제2,410 그대로**다. controller3,582→1,172 이하는 mapper·새 context 증분 전의 상한 예산이며 FIT 보장이 아니다.

실제 보드의 sink client ROM은4KiB slot이다.2,168B native fragment가 그 안에 들어간다는 것과 전체 dispatcher/ordinary/IRQ/복구 프로그램이 들어간다는 것은 다르다. 4KiB를 목표의 하드 한도로 삼지 않는다. 확장이 필요하면 ROM 주소 decode와 M9K 증가도 전체 Lite 비용에 넣는다. 이번에는 새 ROM을 보드에 설치하지 않았고 MAP/FIT을 반복하지 않았다.

새 공통 ingress/실행 제어를 설계할 때는 source 소비와 PPU commit을 분리한 이 역할을 기준으로 header/descriptor/queue/plan 주소·완료 제어를 실제 삭제해야 한다. 독립 checker·codec·namespace·STOP·read capture는 보존한다. 이를 순삭제2,410과 mapper 여유까지 맞출 수 없다면 ROM 중재·렌더링 표현·역할 분담·하드웨어 범위를 다시 비교한다.

MMC4/5는376 gate 그대로다. fullmap 전략도 palette 추가에서 한계가 드러났으므로4.8ms 계산 개선이나 단일 DMA 창을 확장 승인으로 사용하지 않는다. live core/mapper·71/heavy7·여러 위상·전체 resident/WCET·cold/STOP 정상회복·FIT/STA/실기60fps는 미완료다. production227/GBC164/saveSRAM을 유지하며 자동 merge/구매하지 않는다.

근거는 `analysis/spool385-verification.json`, raw는 `../probes/nes-spool383/`다. native01분기거리/native02예산/native03VBlank경계,초기CGRAM prior-state fixture 실패,joint01준비/joint02선언순서/cancel01worker 종료 경합과 joint03 고정scroll binding을 보존한다. 수정된 최종 native07/guards04/joint04/cancel02만 각 최종 기능 판정에 사용한다.
