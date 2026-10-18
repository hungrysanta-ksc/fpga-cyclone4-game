# NES247 P1: 전체 bitmap 순회 스캐너의 크기·실행시간 판정

2026-10-18, PR128. [gap·DMA 경계](nes-gap247-contract.ko.md) 다음의 제한된 P1 진단이다. **수신 시 명령 생성을 post-SEAL 전체 bit 순회로 교체하면3930/3936B에는 들어가지만, 순회만53.08..53.84ms여서 이 구현은 기각한다.** 제품 적용·P2 후보 선정은 없다.

[검증 요약](../analysis/scan247-verification.json) · [71행 실행표](../analysis/scan247-frames.csv) · [진단 builder](../tools/nes_scan247.py) · [실제 재생](../tools/test_nes_scan247.py) · [독립 분석](../tools/analyze_nes_scan247.py). SELECT `scan-build02/scan-test01/scan-analysis01`. 기존 봉인 probe와 제품 소스는 수정하지 않았다.

## 실제로 교체한 경계

기존232에서 수신 후 `mark212`는 received/target-valid를 설정한 다음 source/destination 주소와 append 명령을 만든다. 진단에서는 주소 계산·append 부분을 제거했다. bitmap 기록과 중복/범위 검사, SEAL coverage는 유지했다.

coverage 성공 뒤 BG1024slot, OBJ128slot, map256granule, raw CHR128granule를 순서대로 방문한다. 기존 received bitmap의 총192byte를 재사용하며 총1536bit를 모두 순회한다. CGRAM/OAM과 raw의 HDMA/mode tail은 기존 경로로 남긴다. 네 section의 source/양 VRAM destination 표는48B다.

같은 section에서 gap≤96B, descriptor≤4096B로 합친다. source는 해당 target WRAM, destination도 같은 target VRAM이다. 명령은 기존8B 형식/최대1536개/`7E4000..6fff`에 생성한다. 명령의 미사용 마지막word는0이다. 실제 수신으로만 validity가 증가하며 gap 복사로 비트를 올리지 않는다. uploader의4192 charge, final display/ACK/retire 및 host wire 형식은 바꾸지 않았다.

8slot마다 기존 service를 호출하며 STOP 요청 시 스캐너가 실패를 반환한다. 이 반환 경로의 새 fault injection 검증은 수행하지 않았으므로 생산 STOP 승인으로 세지 않는다.

## 코드 크기와 보존한 중간 결과

|항목|byte|
|---|---:|
|기존232 body|3910|
|수신 명령 생성 제거에 따른 local 감소|271|
|새 scanner+표|283|
|coverage 이후 호출·오류 분기|8|
|진단 body|3930|
|3936B 한도까지 여유|6|

추가 persistent 상태는0B다. 기존 DP scratch와 명령 저장소를 재사용한다. 코드가 들어간다는 결과는 여유가 충분하다는 승인도, 전체 FPGA/ARM 예산 승인도 아니다.

`scan-build01`은3928B로 조립됐지만 실행 전에 destination의16bit wrap에 대한 연속 SBC borrow 문제를 발견했다. BG bank B의 끝은FFFF→0000으로 돌아가므로 gap 차감의 borrow를 length 차감으로 전달하면 시작 주소가1 어긋날 수 있다. 각 모듈러 차감 앞에 SEC를 넣은 `scan-build02`3930B를 실제 실행했다. build01의 source/result는 보존했으며 실행 PASS로 표시하지 않는다. 이2B 수정은 타이밍 최적화가 아니라 주소 정확성 수정이다.

## 실제65816와 독립 명령 비교

기존231 C host와 같은71 frame을 새 진단 ROM에 공급했다. 원래 Mesen Lua의 metadata/used pattern/map/raw/VBlank 비교를 유지했다. 별도 Python 분석기는 원래 plan·packet에서 순서가 정해진 범위를 만들어, 스캐너가 실제 기록한 source/destination/length 목록과 전부 비교했다.

- **71 commit/3077 ACK,71개 명령 목록 exact PASS.**
- DMA 명령478→418, DMA bytes133600→135072(+1472gapB).
- 기존64/71 single VBlank에서66/71로 변했다. cold2개는 다중 VBlank이고 warm69 중952/955/963은 여전히 다중 VBlank다. 전체 frame latency/FPS 개선이라는 뜻은 아니다.
- Mesen의 미초기화 읽기880건/880개 주소는 모두 독립 모델이 허용한 invalid-unused gap에 속했다. used pattern은 이전과 동일했고 경고를 삭제하거나0 초기화로 숨기지 않았다.

이 결과는 기존16B map의 실제 소비 경계다. 별도의 word-map decoder나449B semantic input, 새 FPGA source까지 실행한 결과는 아니다.

## 시간 결과: 순회가 이미 단일 frame 예산을 넘는다

`scan247` 진입부터 해당 호출의 return 직후까지 master clock을 측정했다. 외부 mailbox/VBlank 대기 루틴은 이 구간에 없다. service와 그 구간의 메모리 refresh/HDMA 영향은 포함한다. 실행기에서 읽은 clock rate는21,477,270Hz다.

|범위|측정값|
|---|---:|
|warm69 scanner|1,140,110..1,156,306 master clocks|
|같은 값의 ms 환산|53.08449..53.83859ms|
|16.66667ms 초과|69/69|
|frame당 service 진입|192회|
|각 frame의 최대 service 간격|7440..9322 master clocks|
|관측 최대 service 간격|0.43404ms|

**관측된 가장 빠른 warm 실행도 단일 frame 시간보다 길다.** 최악 실행시간을 입증할 때까지 후보를 유지할 이유가 없으므로 기각한다. 측정 최대를 WCET로 둔갑시키지 않는다. 전체bit scan을 같은 구조로 미세 조정하거나 더 많은 seed로 재시험하지 않는다.

## VBlank 시간과 charge를 연결할 수 있는 범위

이번 실행은 overscan=false, screenInterlace=false였다. [Mesen PPU 원본](https://github.com/SourMesen/Mesen2/blob/master/Core/SNES/SnesPpu.cpp)의 `UpdateNmiScanline`과 `ProcessEndOfScanline`에 따르면 해당 NTSC 모드의 VBlank는225..261이고, 보통 line1364clock/일부 frame의 line240은1360clock이다. 따라서 명목 VBlank 전체는**50,464..50,468 master clocks**다. 이는 raw 시간 창이며 DMA payload 한도나 새 dispatch 정책이 아니다.

각 event의 scanline/hClock을 기록했다. 동일 blank에서 마지막 transfer→final return의 master-clock 차이는 scanline/hClock 차이와 일치했고 short-line 차이4clock도 허용해 검사했다. final return 시점의 남은 명목 창을 보수적으로 계산하면10,588..42,268clock이다. 그 뒤 RTS/ACK/retire, 다른 시작 위상 및 서비스 경로를 포함한 여유가 아니다. 특히 charge가 부족하여 이미 새 blank로 넘어간 frame의 이 잔여를 이전 blank의 여유로 옮길 수 없다.

4192 정책은 그대로 두었다. 이 수치나 DMA01의 관측 최대를 이용해 예산을 임의로 늘리지 않았다. 향후 dispatch 변경은 fresh-VBlank 진입 지연, 모든 DMA setup/refresh, final mode/HDMA/pad 경로 및 최종 표시까지의 상한이 필요하다.

## 판정과 다음 경계

`per-bit full scan`은 **기각**한다. unused gap의 안전성, 주소순 합치기 자체, 모든 bitmap 기반 설계를 기각한 것은 아니다. 새 코드가6B밖에 남지 않고 scanner만53ms이므로 현재 형태의 제품 통합·FPGA FIT·새 실기를 진행하지 않는다.

다음 P1은 빈192byte를 매번1536bit로 풀지 않는 구조와 수신 시 bounded 명령 생성의 비용을 먼저 비교한다. nonzero bitmap word/block만 다루는 방식 또는 이미 수신한 범위로 정렬된 목록을 만드는 방식의 최악 방문 수·코드 교체량·service 간격을 실제 쓰기 분포와 연결한다. 현 구조의 opcode/counter 조정은 제외한다. 목록 생성 시점을 옮길 경우 snapshot/SEAL coverage·target ownership·STOP의 수명도 함께 지켜야 한다.

동시에449B 의미 raster+rowshift 전용 source의 전체 LE/LAB/mapper 여유와 새 입력 ARM RUN/IRQ를 충족해야 한다. source/SPI/ARM/SNES를 묶은 한 후보의 여유가 없으면 P2를 시작하지 않는다. 생산227·미배치240·기각241/246·GBC164·save SRAM과 과거 근거는 보존한다.

## 재현

```text
python tools/nes_scan247.py --out <new-private-build>
python tools/test_nes_scan247.py --out <new-private-test> --client <private-build> --rom <private-SMB3-J-ROM>
python tools/analyze_nes_scan247.py --build <private-build> --test <private-test> --prior <analysis06/result.json> --observer <observer03> --out <new-private-analysis>
```

진단 ROM과 원본 게임은 공개하지 않는다. build01/02·test01·analysis01, generated code/labels, raw 경고·계측·명령 목록은 private에 보존한다. 변경된 실제65816 경계의 동작·시간을 확인했으며 FPGA/ARM 변경이나 물리 FPS 시험은 하지 않았다.
