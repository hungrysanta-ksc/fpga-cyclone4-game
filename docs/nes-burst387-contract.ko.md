# NES386–387: 부분·열·전체 DMA의 실제 CPU 비용

375 RTL·377 ARM과 383의 WRAM 선행 보관을 유지하고, SNES가 받은 map 범위로 sparse/column/dense DMA를 선택하는 실제65816 후보386을 구현했다. 독립 expected/CRC/coverage, 저장 receipt와 PPU 완료의 구분, STOP·최종 ACK·VBlank를 유지한다. 새 FPGA 회로 절감은0이며 기존2,255comb 부족은 그대로다.

## 실제 구현

원본 map을 bank별 WRAM image에 저장하며 기존16B job record에도 범위를 남긴다. 작은 변경(7범위 이하·128B 이하)은 sparse 정책으로 처리한다. 그 외에는 두 개의32×32 screen을 구분해64열의 min/max row를 계산한다. `1280clocks/job+8clocks/byte`의 DMA 예산으로 sparse/column/dense를 비교한다. **이는 전송 선택용 예산이며 CPU·SPI 전체 비용의 최적해가 아니다.**

column을 선택하면 유효한 target-bank image에서 변경 사이의 빈 셀까지 모아 연속 WRAM buffer를 만들고 VMAIN=$81로 전송한다. sparse/tile/dense는 VMAIN=$80이다. 실제 주소 증가와 최종 VRAM bytes를 CPU 시험에서 확인했다. [SNESdev VMAIN](https://snes.nesdev.org/wiki/PPU_registers), [큰 map의 열 갱신](https://snes.nesdev.org/wiki/Scrolling_a_large_map).

기존385 예산표는 두 screen의 같은 열을 하나로 합친 계산이었다. 실제 구현은 `(screen,column,row)`로 분리한다. 예를 들어908은 예산표의1열·80B가 아니라 **2열·32B**다. min/max 저장도64B가 아니라128B가 필요하다. 과거 예산은 측정값이 아니며 새 결과로 대체한다.

선택 후 불필요한 map record를 VBlank 전에 압축한다. 초기 native05는 삭제된 record를 VBlank 중에 순회하여915의 표시가 다음 창으로 넘어갔다. 최종 native08은 실행할 job만 남겨 이 숨은 비용을 제거했다. 각 job의 실제 PPU DMA가 끝난 뒤에만 표시와 최종 ACK를 실행한다.

## CPU·메모리 비용

|항목|383|386|
|---|---:|---:|
|실행 ROM fragment|2,168B|3,290B|
|SNES payload/job/cache WRAM|20,480B|24,705B|
|추가 live DP 변수|기준|30B|
|새 FPGA 절감|0|0|

추가 WRAM4,225B는 column pack4KiB($7EE000..EFFF), min/max128B($7EF000..F07F), cache validity1B($7EF080)다. 기존 tile8KiB/jobs4KiB/map images8KiB와 수명이 겹쳐 별도 공간으로 계산한다. ordinary WRAM·view·기존 DP·stack은 별도이며 전체 resident firmware의 RAM 배치를 승인하지 않는다.

현재 보드의 sink ROM slot은4KiB다. fragment가 들어가는 것과 dispatcher/ordinary/NMI/음성·입력/복구를 포함한 프로그램이 들어가는 것은 다르다.4KiB를 목표의 하드 한도로 삼지 않는다. 확장이 필요하면 실제 ROM decode·M9K 비용을 합산해야 한다. 이 ROM은 보드에 설치하지 않았다.

CPU는 현재 bank의 cache validity bit가0이면 PPU 전송 전에 거절한다. STOP/용량 실패는 두 bank bit를 모두 지우고 forced blank·HDMA off·최종 ACK 차단으로 끝난다. **cold 초기화나 정상 복구 구현은 아니다.** warm 시험은 이전 target-bank WRAM 및 VRAM map/OAM, valid bits, HDMA terminator를 명시적으로 준비한다. live epoch/generation별 cache 초기화·STOP 후 재구축은 미완료다.

## 실제 native 검증

native08은907..916의10warm+STOP1개를 통과했다. 받은 모든 payload를 먼저 저장하고, 현재 H2의 scroll·bank를 적용하며, 전체 map4096B·변경 tile·OAM544B를 독립 expected와 비교했다. 실제 PPU data port write와 최종 ACK가 같은 VBlank에 있어야 한다.

guards03의11case는 첫 저장 뒤STOP, 모두 저장 뒤STOP, PPU job2개 뒤STOP, tile8193B,257번째job, CGRAM512B, palette 추가, 전체map, 양screen의 열 사이 빈 셀, invalid cache, column gather 중STOP을 확인한다. 모든 STOP/용량/invalid-cache 사례는 최종 ACK를 차단하고 cache bits를 지웠다.

palette/전체map/columnholes는 synthetic 출력 ABI 시험이며 추가 ARM/NES 프레임이 아니다. 이전383이 거절하던907+512B palette 사례는 sparse DMA로 같은 VBlank 안에서 완료한다. 이것이 일반 palette·MMC5 부하나 cold 준비 시간의 승인은 아니다. CGRAM-only의 map/OAM은 prior PPU fixture다.

PPU tail은 짧아지지만 CPU 준비 비용이 늘었다. 아래 시간은 Mesen CPU master clocks×46,561ps의 관측 allocation이며 실기 WCET가 아니다.

|frame|선택|383 준비|386 준비|383 PPU/표시 tail|386 tail|
|---|---|---:|---:|---:|---:|
|907|sparse|0.303391ms|1.243924ms|2.214441ms|0.953849ms|
|908|column|0.294731ms|6.059449ms|2.133984ms|0.629970ms|
|914|column|0.296594ms|10.593838ms|2.151863ms|1.250070ms|
|915|column|0.280204ms|12.509637ms|2.146835ms|1.294675ms|

각 map 범위의 job 저장에도 추가 CPU 시간이 든다. 이 비용이 기존 대기 시간에 들어가는지는 실제 연속 일정으로 판정한다.

profile01은 동일 ROM에 수동 PC marker만 추가했다.907/908/915의 모든 bus event/hash가 native08과 같아 CPU 시각이 변하지 않았음을 확인했다.915의 준비 시간은 초기화·범위 재해석,64열 비용 계산,job 압축,column buffer 구성에 쓰인다. ARM의 기존 범위 정보 활용,변경 열의 증분 기록,기존 대기와의 겹침을 추가wire·credit·IRQ 비용과 함께 비교한다.

## 같은 시작 시각의 실제 ARM·SPI·IRQ·ROM 일정

joint03은 이전384 joint04와 **생성된 testbench 전체 hash가 같다.** M4 load image와 보드 공유RTL31개도 같다. ROM_WINDOW=1,46,561ps master allocation,위상0,907의 고정 capture cycle5,371,247과 다음 capture 기한을 유지한다. native386의 source 저장·사전 준비·PPU tail 관측값만 service 파일로 교체한다.325 ordinary WRAM 및381 view head는 보수적으로 유지하여 하나로 컴파일한 전체 resident CPU와 구분한다.

|항목|384|387|
|---|---:|---:|
|907 표시 ready|277.697742ms|278.254825ms|
|907 최종 표시|282.738367ms|281.476126ms|
|907 source 시작→완료|18.488559ms|17.226290ms|
|908 표시 ready|304.949735ms|297.510545ms|
|908 최종 표시|315.936861ms|314.433267ms|
|908 source 시작→완료|35.047559ms|33.543965ms|
|표시 VBlank index|16/18|16/18|
|첫 capture 누락|911|911|

907 ready는 저장 제어 증가로0.557083ms 늦어졌지만, VBlank 대기 안에 준비가 들어갔고 표시가1.262241ms 빨라졌다. 최종 retire까지 포함한 완료는1.262269ms 빨라졌다.908 완료는1.503594ms 빨라졌다. **905..908 배출4개,908/909/910 capture 승인,911 owned1/release0/fault0 실패라는 최종 판정은 그대로다.** 지속60fps로 선택하지 않는다.

907이 먼저 끝나면서908의 첫 hint fill은282.681539ms에 완료되어 첫 ROM 허용 구간에 들어왔다. 이전 실행에는 해당 구간의 hint fill이 없었다. 남은 약61.6µs는 관측값이며 mapper/WCET 예산으로 전용하지 않는다. 첫 BG plan은298.283013→288.200414ms로 앞당겨지고908 ready도7.439190ms 빨라졌다.

하지만908의 view head 후 시각은297.616978ms,ROM phase316,720이다. 실제 native cutoff246행까지 남은18,824clocks는 **0.876464ms**다. 여기에6.059449ms 준비를 넣어 다음 VBlank18로 밀렸다. 다음 실험의 사전 준비 목표는 이 조건에서 **0.8ms 이하**로 잡는다. source receipt 시간·ARM·SPI 일정이 바뀌면 이 목표도 다시 검증해야 하며, 준비 시간을 임의로0으로 놓은 성공 수치를 만들지 않는다.

387의907/908 VBlank service는0.954251/0.630381ms다. 남은 VBlank1.394036/1.715726ms와 달리, 전체 source 처리에는17.226290/33.543965ms가 든다. 이 allocation의 한 frame은16.639411ms,명목60Hz는16.666667ms이므로 두 목표 모두 아직 만족하지 못한다. PPU 창 안의 여유와 연속 프레임의 여유를 구분한다.

초기 joint01은 중복 cadence 변환으로 준비 단계에서 실패했다. joint02는 고정 시작 옵션이 빠진 것을 확인해 실행을 중단하고 비교에서 제외했다. 임시 script의 중복 BOM 오류도 보존했다. 최종 joint03만 같은 시작/위상 비교에 사용한다. native01/02의 비ASCII Lua 경로 실패,native03의 prior VRAM fixture 누락,native05의 VBlank 순회 실패와 수정 전 native04/06/07도 보존한다.

## 다음 구조와 예산

먼저 표시 후 사전 준비6.059ms를0.8ms 이하로 줄이는 **실제 제어 삭제 범위**를 비교한다. 받은 범위를 다시 해석하고 모든 열을 순회하는 대신, 저장 중에 변경 열 목록·범위를 증분 기록하여 같은 정보를 재사용하는 안과 ARM의 기존 map 범위에서 compact job을 만들어 기존 ordinary WRAM 명령으로 공급하는 안이다.

전자는 추가 source 저장/receipt 지연이 shared SPI의2슬롯·ARM IRQ와 겹치는지 측정해야 한다. 후자는 실제 M4 생성·추가 byte·queue credit·SNES 수신과 목적지/coverage 검사를 합산해야 한다. 둘 다 독립 source 검사·cache 소유권·STOP·최종 ACK를 유지하고, 새 parser/문맥이 생기면 FPGA 전체 비용에 넣는다. 현재 구현·측정된 시간이나 회로 절감은 없다.

동시에 기존 source/host/queue/plan/receipt 본체의2,410comb 순삭제 예산을 유지한다. 계산 위치를 옮겨 시간을 줄였더라도 회로가 들어가지 않으면 실기 후보가 아니다. 이 두 조건을 함께 만족시키기 어렵다면 ROM 중재·렌더 표현·역할 분담·하드웨어 범위를 다시 비교한다.

## 공통의 한계와 회로 gate

FPGA의 독립 expected/CRC/coverage는 실제로 읽은 source의 저장을 검사한다. SNES 내부의 미전송 cache word나 실제 PPU memory를 하드웨어에서 검사했다고 주장하지 않는다. native PPU 비교와 FPGA receipt의 의미를 구분한다.

공유RTL31개와 M4 load image는375/377과 같다. Quartus Lite375의22,390LE/17,663comb/8,985FF/300,640bits를 상속하며 새MAP/FIT/STA를 실행하지 않았다.2,255comb 부족,155여유 포함 순삭제2,410,제어pool3,582→1,172이하 예산은 그대로다. 새 SNES ROM을 포함한 전체 구현 비용은 미확정이다.

MMC4/5는376 gate 그대로 미구현·여유 미승인이다. 단일 DMA 단축을 mapper 예산으로 삼지 않는다. cold/STOP 정상복구·전체resident CPU·71/heavy7·여러위상·live core/mapper·전체pixel·WCET·whole FIT/STA·실기60fps는 미완료다. production227/GBC164/saveSRAM을 유지하고 자동merge/구매하지 않는다.

근거는 `analysis/burst387-verification.json`, raw는 `../probes/nes-burst386/`다.
