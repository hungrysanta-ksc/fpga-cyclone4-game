# NES 실제 OAM DMA 검증 계약

SPDX-License-Identifier: MIT.

기존 RDY-014 코어를 그대로 사용한다. `pause_cpu`나 DMA state를 force하지 않는다. 자체 ROM의 CPU가 RAM 두 페이지를 채우고 `$2003` OAMADDR를 설정한 뒤 `$4014`에 source page를 써서 실제 DmaController를 시작한다. rendering, NMI, IRQ, DMC는 비활성화하고 ideal external memory를 사용한다.

## 입력과 관측

RAM0200/0300은 별도의256-byte 패턴이다. 패턴 원본은 자체 ROM E000/E100에 있으며 CPU가 indexed load/store loop로 RAM에 복사한다. 각 페이지에 OAM 시작 주소00/01/FC/FF를 적용한다. NOP(2-cycle) 또는 BIT zp(3-cycle) padding으로 두 DMA alignment를 자극하며 초기3-cycle pad로 첫 쌍까지 맞춘다. 총16개이고 각 page/start 조합에서513 및514 paused CPU cycles가 모두 있어야 한다.

각 DMA 뒤 `INC $10`을 한 번 실행한다. RAM10은0에서16까지 증가해야 하며 다음 case completion marker에서 OAM256바이트와 RTL OAMADDR를 저장한다. Mesen은 실제 `nesSpriteRam`을 read-only로 읽는다. Mesen OAMADDR 값은 이 캡처에서 직접 읽지 않으며 -1로 기록한다.

RTL은 cart_ce에서 tick/effective address/read/data/case/CPU address/CPU read/pause/DMA enable/put phase를 기록한다. 이는 cpu_ce보다2 master ticks 앞의 bus 관측이다. 한 CPU cycle은12 master ticks다. source RAM read256회와 `$2004` write256회를 빠짐없이 검사한다. put phase는 source read0/write1을 번갈아야 한다. CPU는 다음 INC opcode 주소에서 read 상태로 정지하고 DMA 종료 뒤 같은 주소부터 진행해야 한다.

Mesen read/write callback은 DMA access를 포함한다. exec callback은 opcode fetch 이전이므로 CPU 재개 시점을 exec callback만으로 판정하지 않는다. 양쪽의 `$4014` write를 기준점으로 각 DMA read/write의 상대 CPU cycle을 비교한다. DMA 종료 뒤 INC의 read/old-write/new-write가 같은 상대 cycle에 일어나는지도 확인한다. 절대 boot clock이나 CPU/PPU 위상을 같다고 가정하지 않는다.

## 데이터와 시간 조건

각 source byte i는 OAM `(start+i)&255`에 저장되어야 한다. destination 주소의 low2 bits가2인 attribute byte는 E3 mask를 적용한다. 이는 raw DMA write bus 값과 분리한다. RTL/Mesen 전체 OAM snapshots와 ROM-derived 기대값이 모두 일치해야 한다. RTL OAMADDR는256회 쓰기 후 처음 start로 돌아와야 한다.

DMA bus512 accesses에 halt/alignment1 또는2 cycles를 합쳐 CPU pause가513/514 cycles여야 한다. `$4014` write를 cycle0으로 삼으면 DMA 첫 source read는 cycle2/3, 마지막 write는513/514, CPU opcode 재개는514/515다. 이후 INC read는 pause-length+3, old-write는+4, new-write는+5다. 실제 Mesen bus도 같은 상대 cycle을 가져야 한다.

data/address/tick/pause/OAM snapshot 변조, transfer 누락 및 trace 절단7종을 거부한다. 초기 ROM처럼 한 page/start 조합에서 같은 위상만 두 번 실행되면 전체 사례에서513과514가 각각 보이더라도 coverage 실패로 처리한다.

## 재현

[FLOAT 실행 규칙](questa-execution.md)을 따른다. 변수는 기존 설치의 절대 경로이고 Out은 새 ASCII 경로다. 무료 Starter workflow를 재사용하며 별도 license smoke를 반복하지 않는다. 기존 runner의 implementation candidate014와 diagnostic candidate015를 구분한다.

```powershell
& $PY -B -X utf8 tools/build_nes_oam_dma.py --out "$env:TEMP/nes-oam-rom"
& ./tools/run_nes_rdy.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-oam-rtl" -Diagnostic "$env:TEMP/nes-oam-rom" -Testbench tests/nes-functional/oam_dma_tb.sv
& $PY -B -X utf8 tools/run_nes_oam_dma_reference.py --mesen $MESEN --probe "$env:TEMP/nes-oam-rom" --out "$env:TEMP/nes-oam-mesen"
& $PY -B -X utf8 tools/verify_nes_oam_dma.py --rom "$env:TEMP/nes-oam-rom" --rtl "$env:TEMP/nes-oam-rtl" --mesen "$env:TEMP/nes-oam-mesen" --out "$env:TEMP/nes-oam-rtl/verification.json"
```

Mesen runner는 생성기를 별도 경로에서 다시 실행하여 원본 ROM bytes 일치를 요구한다. 기존 로컬 Mesen emucap 빌드, binary/settings hash를 capture.json에 남긴다. HDL과 raw ROM/trace는 ignored 증거 경로에만 보존하며 라이선스/서버 로그는 제외한다.

이 시험은 실제 DMA 동작과 실제 Mesen runtime 비교다. DMC 경쟁, DMA 도중 interrupt, rendering 중 OAM write, RMW `$4014` trigger, source page 경계 및 모든 mapping, MMIO, 외부 memory stall/arbitration, fit/STA 및 hardware는 미검증이다. 기존014의 다른 회귀는 보존 결과이며 코어 변경이 없는 이번에 다시 실행한 것으로 표시하지 않는다.
