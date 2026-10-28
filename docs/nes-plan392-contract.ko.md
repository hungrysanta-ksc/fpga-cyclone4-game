# NES390–392: ARM compact 계획과 실제 65816 수신·DMA

## 작업 목표

388–389의 첫 capture 누락911과 comb2255 부족을 함께 줄일 수 있는지 실제 경계에서 비교한다. ARM이 map 실행 범위를 결정하고 SNES는 수신·검사·DMA를 맡는다.375 RTL·377 ARM의 source/hint/IRQ·2슬롯·독립 expected/CRC/coverage를 기준으로 유지하고 새로운 전송·검사 비용을 더한다. 이 문서는390–392 후보의 결과이며 production227/GBC164/saveSRAM을 바꾸지 않는다.

## 구현한 경계

390은 실제 M4의 `map_byte327` target-bank bitmap에서 sparse/column/dense 계획을 만든다. 첫 map 발행 직전에 생산·전송하므로 ARM 준비와 queue 대기는 모두 임계 구간에 포함된다. 미래 geometry나 oracle을 생산기에 공급하지 않는다. 기록된 map으로 실행한 component와 live M4가 보낸 payload가 같아야 한다.

16B header는 magic/version/mode,bank,generation,serial,실제 source range 수와 word 수다. sparse는 최대7개의 start/span word 좌표, column은 두32×32 screen의64개 min/max 쌍, dense는 전체 map 실행이다. 이번10warm payload는44/144B, 추가 E1은 header·CRC 포함63/163B다. 매 warm에 실제 storage credit과 receipt를 소비하는 패킷 하나가 추가된다. 범위 정보가 compact하다는 뜻이며 최종12B DMA job 자체를 그대로 전송하는 형식은 아니다.

기존 ordinary section5의3418B는 HDMA와 독립 검사가 소유한다. 빈 공간으로 간주하지 않고 **literal opcode2/section6,start0,length16..144**를 추가했다. 목적지는7F7500/F500이며 기존2슬롯 queue·staging aperture·read handshake·token·storage receipt를 재사용한다. FPGA는 PUT 중 magic/version/bank/generation/serial을 현재 identity에 묶는다. metadata는 기존 canonical expected 데이터에 섞지 않는다.

ARM은 별도209B SPI buffer를 사용한다. 기존 `metadata317`는 선행 manifest와 map scratch가 아직 소유하므로 공유하지 않는다. 추가 BSS248B는209B buffer와32B planner state,4B sent flag 및 정렬이다. component의16byte 단위 처리 함수를 처음에는 finish 호출 안에서 끝까지 실행한다. IRQ와 실제 send317/credit 응답 비용을 제거하거나 무료 overlap으로 세지 않는다.

391의 실제65816은 section6를 WRAM에 저장한 뒤 header·mode·길이를 검사한다. 각 실제 map DMA의 bank/generation을 계획에 묶고 sparse 좌표·span 또는 column bounds coverage를 대조한다. 실제 range/word 합계도 sealed view 뒤에 다시 맞춘다. dense와 column의 빈 셀에는 명시적으로 유효한 prior-bank cache가 필요하다. 계획에 빠진 변경 word,길이/세대 오류,plan 미수신은 PPU/최종 ACK 전에 거절한다.

일반3/4뿐 아니라 **일반5의 실제 수신과 WRAM DMA**도 새 CPU에 연결했다. 기존 zero-tail descriptor는2B를 읽은 뒤 ROM zero에서1100B를 실제 DMA로 채운다. 두 byte만 읽고 채우기 비용을 생략하지 않는다. 전체3418B HDMA WRAM을 독립 expected와 비교한다. 이전 zero terminator fixture를 canonical 이미지에 덮어쓰던 부분은 제거하고 올바른 prior-bank HDMA 전체를 초기 fixture로 사용한다.

tile spool·12B job·map cache·column gather·budget·VBlank admission과 표시 suffix를 유지한다. 이전 SNES의 dirty-column 추적과 전략 비용 계산은 사라졌지만, column payload64개 순회와 WRAM gather,실제 job 구성은 여전히 표시 전에 실행된다. 따라서 이것은 SNES 준비 전체를 삭제한 구현이 아니다.

STOP은 공통 invalidator로 두 cache bit를 지우고 forced blank·HDMA off·최종 ACK 차단을 수행한다. source receipt는 **WRAM 저장 완료**, 최종 ACK는 실제 PPU DMA와 현재 H2 표시가 같은 VBlank에서 끝난 뒤다. DMA 예산·cutoff·512clock reserve·고정 capture 기한은 완화하지 않는다.

## 검증과 전체 비용

- ARM component10frame 및 독립 sparse/column/dense30벡터 통과. component9791..13886명령,관측 stack52B. 이는 hardware cycles/full firmware WCET가 아니다.
- 실제65816 native10warm907..916+STOP 통과. 전체 map VRAM·변경 tile·OAM·HDMA WRAM·현재 H2 view와 같은 VBlank의 PPU/최종 ACK를 확인했다.
- 별도 native guard19case: 잘못된 magic/version/bank/generation/length,range/word 수,좌표·span·column 누락/역전,map 경계,plan 누락/중복,STOP,상위32bit token 및 dense 실행을 확인했다. 실패는 양 bank 무효화·forced blank·HDMA off·no final ACK다.
- 합성에 사용한 RTL에서 admission/PUT identity 판단을 그대로 추출해518회 검사했다. 이 unit 시험을 integrated fault/RAM-freeze 시험으로 부르지 않는다. 원래 데이터의 independent expected/CRC/coverage 경로는 보존하고 live 실행의 실제 read→unit→receipt 공개도 대조한다.

|자원|388–389 기준|390–392 후보|차이|
|---|---:|---:|---:|
|실제 M4 text|35982B|36570B|+588B|
|실제 M4 BSS|48476B|48724B|+248B|
|65816 fragment|3274B|3543B|+269B|
|SNES payload/job/cache 예약|24769B|23841B|−928B|
|보수적 추가 DP 예약|37B|52B|+15B|
|whole Lite LE|22390|22471|+81|
|whole Lite comb|17663|17744|+81|
|whole Lite FF|8985|8985|0|
|whole Lite RAM bits|300640|300640|0|

native component 보고의23697B는 active plan buffer144B만 포함한 값이다. 양 bank의7500/F500을 모두 예약하는 전체 표에는 다른 bank144B를 더한23841B를 쓴다. 원래 map coordinate1024B·bounds128B·dirty list64B를 없애고 plan288B를 더했다. CGRAM/OAM/HDMA 기존 영역·fullresident stack은 이 fragment 표 밖의 기존 비용이며 무료로 회수하지 않는다.

새 SNES fragment는 기존4KiB slot 크기 이내지만 아직 보드 `sink-program.hex`에 설치하지 않았다. whole MAP은 새 ingress를 포함한 **FPGA 제어 전체 비용**이며 새 cold/warm resident 프로그램과 ROM decode까지 완성한 FIT 결과가 아니다. 따라서 comb2336 부족은 확정된 하한이고 fullresident/mapper 증분은 미확정이다.4KiB를 하드 목표로 삼지 않는다.

|native frame|388 source control|391 source control,일반5 포함|388 표시 전 준비|391 표시 전 준비|
|---|---:|---:|---:|---:|
|907|2.603505ms|4.031717ms|0.788185ms|0.857467ms|
|908|5.933268ms|6.719870ms|0.786136ms|2.587395ms|
|914|10.094704ms|10.537592ms|3.614158ms|4.683850ms|
|915|13.856554ms|14.268712ms|3.825172ms|4.831728ms|

새 source control에는 추가 plan·실제 ordinary5 소비가 포함되므로 기존의 tile/map/ordinary3/4만과 동일한 부분 합계라고 부르지 않는다. 영역별 비용을 검증 JSON에 따로 기록한다.914/915 native 값은 연속 출력 완료를 뜻하지 않는다.

고정907 capture cycle5371247·ROM_WINDOW1·master46561ps·위상0과 원래 후속 capture 기한을 유지했다. 보드와 functional의 공유RTL31개 hash가 같고,907/908 모두 기준과 동일한 source 시작 시각·ROM cycle이다.

|연속 일정|388–389 기준|390–392 후보|
|---|---:|---:|
|907 ready|277.776498ms|278.786636ms|
|907 source→완료|17.226057ms|17.226011ms|
|908 ready|297.967444ms|298.562216ms|
|908 source→완료|33.542615ms|33.543825ms|
|표시 VBlank index|16/18|16/18|
|첫 capture 누락|911|911|

905~908 완료,capture908/909/910 승인 후911 owned1/initialized1/release0/fault0으로 실패했다.907 완료46ns 차이는 이득으로 세지 않으며908은1.210µs 늦다. 두 warm 완료 사이 간격은32.957272ms로 지속60fps가 아니다. ready는 각각1.010138/0.594772ms 늦어졌다.

|추가 실제 비용|907|908|
|---|---:|---:|
|전체 ARM 명령 증가|20073|22552|
|전체 SPI byte 증가|133B|219B|
|그 중 plan E1|63B|163B|
|추가 E2 응답/전송|5회/70B|4회/56B|
|E0 회수 변화|0|0|
|WFI 요청 기준→후보|14→15|20→23|
|할당 exception cycles 기준→후보|600→696|720→192|

최대 storage credit은2다. SPI 수치는 seal 전 transfer JSON의 부분 합계가 아니라 finish267까지 포함한 worker 전체 합계를 사용했다. byte 증가는 plan만이 아니라 추가 E2까지 포함한다. RPC의 foreground/IRQ 명령 delay와 exception allocation도 실제 일정에 모두 부과했다.908의 exception 감소는 관측된 coalescing/위상 결과이며 WCET 여유로 세지 않는다. 완료된4frame까지 관측 M4 stack1280B이며,기존12frame의1288B와 비교해 stack을 회수했다고 주장하지 않는다.

908 view 뒤 phase는326533→339307로 늦어져 native cutoff246행의335544보다 **3763clocks,0.175209ms 늦다.** 새 표시 전 준비2.587395ms를0으로 가정해도 이 conservative cutoff를 이미 넘었다. 표시 직전 루프 절감만이 아니라 source/전송/ready를 앞당기는 변경이 필요하다.

연속 시험은 실제 M4·SPI·IRQ·2슬롯·ROM 경합과,측정한 native per-record CPU control/PPU service를 연결한다. 따로 실행한65816의 모든 source byte가 live RTL staging과 일치해야 한다. 기존 ordinary325 trace는 cold905/906만 유지하고 warm3/4/5/6은 새 native service를 쓴다.381 view head는 보수적으로 유지한다. 이것을 하나의 fullresident CPU lockstep이나 실기 WCET로 확대하지 않는다.

초기 연결 실패도 보존한다. joint01은 testbench의8bit bank 비교에서 unary NOT 확장 오류로907 descriptor를 거절했다. joint02는 새 패킷을 제외한 legacy 비교에서 sequence gap 정규화를 빠뜨려 worker가 중단됐다. 수정 후 실제 전체 wire sequence를 먼저 검사하고,기존 semantic comparator에 넣는 사본만 연속 번호로 바꾼다. 실제907 기록을 수정 검증기로 먼저 통과시킨 뒤 같은 조건의 full 실행을 수행한다. joint03은 실제907 PPU/ACK 뒤 사용하지 않은 legacy trace의 EOF 집계에서 멈췄다. 새 native 일반 명령마다 대응하는 옛 trace 한 건의 집계만 진행하고,추가 metadata는 옛 trace를 소비하지 않도록 바꿔 기존 EOF guard도 유지한다. 원래 packet/transfer·credit·응답 통계는 삭제하거나 정규화하지 않는다.

## 판정과 후속 범위

현재 **bounds 기반 compact 계획+새 ordinary 어댑터를 시간/회로 성공안으로 채택하지 않는다.** ARM 이전 자체가 불가능하다는 결론도 아니다. 남은64열 순회·gather·job 구성과 추가 수신·검사 비용을 포함하면 역할 이전만으로 시간이 줄어들지 않는다는 결과다. 기존 source/host/queue/plan/receipt 본체를 남긴 채 section6를 더해 comb도81개 늘었다. cold가 기존6066/67 PPU 주소 export를 사용하므로 그 제어의 삭제 절감도0이다.

현재 comb2336 부족에155예비를 더하면 **2491개 순삭제**가 필요하다. 새81comb를 유지한다면 기존3582 control의 상한은1091이며,resident ROM/context/mapper 증분이 생기면 더 낮아진다. 단독 FSM/seed/FIT 반복으로 이 예산을 충당했다고 부르지 않는다.

다음 구조 비교는 ARM이 정한 최종 DMA job과 source payload의 실제 저장 순서를 공통 ABI로 연결하여 SNES job 재구성·64열 순회·late gather를 함께 없애는 범위로 한정한다. column 단위 payload를 ARM에서 준비하면 증가한 byte/ARM 준비와 줄어든 range·receipt·gather를 같은 일정으로 비교해야 한다. 동시에 이 ABI가 **기존 FPGA descriptor/header/address/queue-plan 실행 제어를 대체**해야 한다. 별도 어댑터를 하나 더하는 후보는 area 성공으로 간주하지 않는다. 구체적 삭제 목록과2491+증분 예산을 먼저 맞춘다.

첫 map 강제 발행으로 경계를 분리한 현재 live 생산기는 변경 map이 없는 warm의 발행 경로를 아직 완성하지 않았다. component의 empty plan 통과를 이 경로의 성공으로 세지 않는다. 그런 frame은 plan 미수신 시 fail closed하며,선택 전 empty/cold/STOP 후 정상회복도 연결해야 한다.

375/377 검증 기준과376 mapper gate를 보존한다. MMC4/5 여유는 승인하지 않는다.71/heavy7·다중 위상·capture/표시 전체 연속성·cold/STOP 후 정상회복·fullresident CPU/IO/audio·whole FIT/STA·실기60fps는 여전히 미완료이며 자동merge/구매하지 않는다. 근거는 `analysis/plan392-verification.json`,raw는 `../probes/nes-plan390/`에 보존한다.
