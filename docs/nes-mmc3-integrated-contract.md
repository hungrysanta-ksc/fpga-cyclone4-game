# Mapper4 CPU/PPU 통합 검증 계약

SPDX-License-Identifier: MIT.

[기존 FLOAT 실행 규칙](questa-execution.md)을 사용한다. 기존 NROM driver와 테스트는 수정하지 않는다. `nes_mmc3_integrated.py`는 해시 고정된 RTL-006 driver의 adapter 생성 부분만 확장한다. MMC3를 단독 module로 정규화하여 연결하고, 기존 CPU/PPU/APU 수정은 그대로 재사용한다. IRQ는 NES의 실제 mapper_irq 경로, CE는 cart_ce, m2_inv는 cpu_ce에 연결한다.

```powershell
& $PY -B -X utf8 tools/build_nes_mmc3.py --out "$env:TEMP/nes-mmc3-rom"
& ./tools/run_nes_mmc3_integrated.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-mmc3-rtl" -Diagnostic "$env:TEMP/nes-mmc3-rom"
& $PY -B -X utf8 tools/run_nes_mmc3_reference.py --mesen $MESEN --probe "$env:TEMP/nes-mmc3-rom" --out "$env:TEMP/nes-mmc3-mesen"
& $PY -B -X utf8 tools/verify_nes_mmc3_integrated.py --run "$env:TEMP/nes-mmc3-rtl" --reference "$env:TEMP/nes-mmc3-mesen" --rom "$env:TEMP/nes-mmc3-rom"
& $PY -B -X utf8 tools/test_nes_mmc3_integrated.py --run "$env:TEMP/nes-mmc3-rtl" --reference "$env:TEMP/nes-mmc3-mesen" --rom "$env:TEMP/nes-mmc3-rom" --out "$env:TEMP/nes-mmc3-negative"
```

출력은 모두 새 ASCII 경로다. 설치 경로는 전역 AGENTS.md, Mesen 환경은 기존 로컬 설치를 사용한다. runner는 같은 원본 생성기의 ROM bytes 일치를 요구하고 verifier는 최종 ROM SHA256을 고정한다.

## 원본 ROM과 메모리

64KB PRG / 16KB CHR, mapper4 submapper0. E000 고정 bank에서 코드를 실행한다. 프레임마다 R6=0/1과 CHR R0/R1=0/2 또는 8/10으로 바꾼다. CPU가 $8000 marker를 읽어 오류를 RAM4에 누적하고, R7=3의 $A000 marker도 확인한다. NMI handler가 RAM8 flag를 올리고 main이 프레임 작업을 수행한다. IRQ latch=63, 매 프레임 reload/enable, IRQ handler가 RAM3을 증가시키고 E000으로 acknowledge한다. APU frame IRQ는 비활성화한다.

BG table=0, sprite table=1, BG만 표시하며 OAM=FF다. PPU의 dummy sprite fetch가 실제 A12를 구동한다. 16KB CHR는 사전 상주하고 ideal memory는 1 master tick 응답이다. 최소 adapter는 이 ROM 크기와 표준 Mapper4만 지원한다. PRG mask는 64KB, CHR mask는 16KB로 고정하며 generic loader/cart_top, savestate, 확장 매퍼 지원을 주장하지 않는다.

## 관측과 비교

- 140.02ms RTL 실행, 60ms 이후 연속 4프레임. 등록된 color의 cycle=x+2에서 256×240 전체를 보존한다.
- 프레임당 배경 latch 16,388건을 검사하고 화소에 쓰인 15,360건의 virtual/physical address 및 값을 좌표 oracle과 Mesen에 대조한다. RTL latch cycle 6/8 ↔ Mesen read slot 5/7 계약은 RTL-FETCH-007과 같다.
- Mesen은 frame6..9를 저장한다. 부팅 frame 번호를 같다고 가정하지 않으며 ROM counter가 같으면 우선 매칭하고, 겹치지 않는 첫 RTL frame은 같은 CHR group 참조와 비교한다. BG pixel과 fetch 의미에만 이 매칭을 사용한다.
- 각 캡처 프레임 pre-render+visible 241줄의 A12 상승은 261,269,…317 dot에서 8회씩, 총 1,928회다. IRQ 상승은 scanline62/cycle261이며 A12 상승 기록의 다음 master tick에 관측된다. 중간 짧은 A12 펄스로 IRQ가 중복되지 않아야 한다.
- CPU INC의 old/new 두 RAM write와 E000 write가 scanline62에 한 번 있어야 한다. IRQ 해제는 E000 관측 다음 master tick이다. Mesen도 같은 줄에서 같은 RAM increment와 acknowledge를 보여야 한다.
- 공통 counter3..5에서 RTL ack dot=328/330/331, Mesen=332/334/335로 **4-dot 관측 차이가 남는다**. cart_ce 버스 관측과 emulator callback의 위상, CPU interrupt latency를 아직 분리하지 않았다. 정확한 IRQ cycle equivalence를 통과 조건으로 삼거나 완료로 선언하지 않는다.
- PASS marker와 Fatal/Error 부재 외에 pixel/fetch/counter/IRQ/A12 조건을 모두 요구한다. 화소·bank 변조/절단/fetch 누락 5종과 IRQ/A12 누락·handler 변조 3종을 검사한다.

원본 upstream·COPYING·변환 diff는 ignored evidence에 남긴다. MMC3/savestate 파일 license hold를 유지한다. 상용 ROM·기존 GBC 코드·제품 패키지는 수정하지 않는다.
