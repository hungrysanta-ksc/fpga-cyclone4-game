# NES247 P1: 실제 병렬 경계와 raster 의미 투영

최신 후속은 [unused gap 수명과 실제 DMA 실행 경계](nes-gap247-contract.ko.md)다. 아래 결과와 기존 판정은 해당 단계의 근거로 보존한다.

2026-10-18, PR128. [schedule247](nes-schedule247-contract.ko.md) 다음 비교다. **전체 변환기를 그대로 FPGA로 옮기는 안은 기존 배열 배치만으로 RAM 여유를 넘는다. 반면 현재 planner가 사용하는 raster 필드만 전달하는 표현은 실제 C 출력 동일성을 통과했다.** 아직 FPGA 면적·SNES burst·새 입력 ARM 시간 여유가 결합되지 않아 P2 구현 후보를 선정하지 않았다.

[재현 도구](../tools/analyze_nes_relocation247.py) · [검증 요약](../analysis/relocation247-verification.json) · [71행 비용표](../analysis/relocation247-frames.csv). SELECT private `relocation01`; 기존 observer03/analysis06/schedule04는 보존한다.

## 실제 병렬창의 현재 연결

옛188 문서의 “미연결”은 당시 범위다. 실제240 board snapshot의 `nes_live_joint`에는 `nes_direct206`이 연결돼 있고, `nes_plan_spi200 → nes_plan_batch206 → nes_source_tile192 → nes_tile_bulk206 → aperture188/control194` 경로가 있다. ARM이 보낸 tile plan의 physical tag/row/alternate/mask/slot으로 FPGA가 CHR-ROM을 읽고 SNES planar tile을 만든다. `qualified_slot/core_safe`와 core 우선 읽기 중재, captured/live epoch, lease를 유지한다. 기존 기능을 새 작업으로 세지 않는다.

`$40:0800..0fff`는2KiB×2 immutable payload 창이다. `$00:6040..6050`은 ready/kind/length/offset/generation/token과 token consume 제어다. 두 버퍼4KiB는 이미 현재 보드 RAM에 포함된다. [control194](../src/nes/rtl/nes_bulk_control194.sv)의 kind는1bit BG/OBJ이고, `nes_sink195_bulk`도 kind>1을 거부한다. 따라서 raw/map/geometry를 기존 타입에 조용히 넣을 수 없다. section/range/version/descriptor와 consumer coverage를 함께 바꿔야 한다.

chunk consume은 그 payload buffer만 해제한다. source capture lease의 해제는 별도다. 현재 `reader_drained`, `retire_permitted`, final display ACK 후 retire 경계를 보존해야 한다. SPI→ARM→SPI로 metadata를 다시 넣는 방식은 병렬창을 사용해도 ARM→FPGA wire를 없애지 않는다.

## 변환 위치별 자원 경계

|안|없앨 수 있는 작업|남거나 새로 필요한 작업|현재 판단|
|---|---|---|---|
|ARM metadata refill→병렬창|SNES byte 읽기 방식 변경|동일 metadata의 ARM→FPGA SPI, 새 producer/descriptor|우회 전송 절약으로 계산하지 않음|
|전체 planner/allocator FPGA 이동|ARM geometry 수신·변환 및 plan/metadata SPI|exact/retained key, slot lookup, bank dirty, map/OAM/raster/raw 생성, 검사와 소유권|기존 C 배열 그대로의 포트는 RAM 부족|
|geometry 병렬→SNES planner|ARM geometry와 output SPI의 대부분|65816 변환/allocator, 코드·WRAM 배치, CPU/서비스 시간|현재3910/3936B 코드에 추가할 수 있다는 근거 없음; 시간 UNKNOWN|
|의미 raster 입력+raw 변환만 FPGA 이동|불필요한 raster 필드·raster-XOR 경로, raw pixel 입력과 raw CHR SPI 출력 일부|typed raw producer, sparse raw base/dirty, shared aperture 중재, 새 입력 decoder|구체적인 제한 후보이나 전체 여유는 아직 미입증|

현재 allocator의 배열을 변경 없이 FPGA에 옮기면 current BG exact8192 + OBJ exact512 + retained BG2048 + OBJ512 + resident/used/dirty576 + index2816 + map4096 = **18,752B**다. patch union은 BG exact와 겹치므로 중복 계산하지 않았다. geometry, OAM, CGRAM, HDMA, 제어 RAM은 오히려 제외했다. M9K의 비트 용량만 보아도 최소17개가 필요하다. 이 계산은 배열 배치를 그대로 옮기는 경우이며 재설계된 allocator의 보편적 하한이 아니다.

240은54/56M9K다. source base6+scratch1+SPI1을 모두 없애고, plan batch1 및 sink SPI1까지 회수한다고 **낙관적으로 가정**해도 추가 여유는12개다. 실제로 제어/소비 경계를 바꾸지 않고 이 모두를 회수할 수 있다는 승인은 없다. 따라서17개 배열을 그대로 넣는 안은 중단한다. 기존 병렬창4개를 또 회수하거나 새 필요량에서 빼지 않는다. LE/LAB를 MAP 경계 수치로 단순 차감하여 배치 가능성을 주장하지 않는다.

## raster 의미 투영: 유효성을 검사한 뒤 작은 표현으로 전달

현재 planner가 사용하는 normal raster는 coarseX/NT-X, fineX, palette epoch와 display mask다. raw row는 raw flag와 slot 번호를 사용한다. 나머지 scroll_v/scroll_t/pattern 정보는 이미 physical map/tag와 row/alternate geometry에 반영되어 이 **현재 변환 경로**의 출력에는 직접 쓰이지 않는다. NES 코어에서 필요 없는 정보라는 뜻은 아니다.

|원본 필드|투영16bit row|
|---|---|
|bits0..4 및10: coarseX/NT-X|bits0..5|
|bits30..32: fineX|bits6..8|
|bits44..48: palette epoch|원본 epoch가 palettes(1 또는2) 미만인지 검사 후 bit9|
|bit49: raw row|bit10|
|bits50..52: raw slot|bits11..13; normal은0|
|bits36..43: display mask|normal 전체가 같은18/1E인지 검사 후 frame당1B|

bits14..15는0이다. raw row는 원본 low49bits=0/upper53bits=0/slot 순서·count를 먼저 확인하고 투영에서도 normal용 필드를0으로 둔다. 정상 raster의 upper49bits, epoch 범위, mask 일관성을 검사하기 전에 버리면 손상 증거를 지울 수 있다. 원래 counts/row/map/exception/physical tag 검증은 별도로 유지한다. 새 wire version과4398B 주소/범위 규칙이 필요하며 기존5741B decoder와 호환되는 새 제품 형식으로 선언하지 않았다.

raster1792B가448B+mask1B가 되어 canonical geometry는5741→4398B다. warm69에서 raster 영역의 바뀐 byte 합은30340→20720이다. 이는 wire나 실행시간 자체가 아니다.

### 실제 C 비교

Python이 각 frame의449B 표현을 직렬화하고, 독립 C decoder가 이를 복원해 **candidate input의 raster만** 바꿨다. 참조 `reference203`의 원래 raster와 source 검증은 그대로다. 원래231/227 planner·resident·dirty·sink를 사용했다.

- 71프레임, **4,066,624 참조 비교 PASS**.
- metadata/packets/plans213파일 byte exact, 이전에 기록한 원본 geometry/raw142파일도 exact: 합355파일. geometry dump는 투영 전 원본이므로 이를 투영된5741B의 byte 동일성으로 표현하지 않는다.
- cost.csv, map247.csv, slot247.csv도 exact. 현재 화면 의미와 slot 결정이 동일하다.
- C decoder10개 경계 검증과 원본 손상5개 투영 전 거부 검증 PASS. 잘못된 mode/길이/reserved/epoch/raw 필드·순서·count 등을 포함한다. CRC/CDC/serial/ACK 새 binding 검증은 아니다.

## 같은 프레임의 SPI 및 SNES 비용

4398B 의미 geometry에 row shift66B를 유지하고 나머지는 기존 literal span 규칙을 적용했다. 기존 raster-XOR 표현은 사용하지 않는다. 크기 모델의 header20/geometry END10/RAW END6, whole-record248B 블록과19B 제어 비용은 그대로다. 이것은 새 스트림 decoder 구현이 아니라, 실제 C 출력 동일성으로 뒷받침한 입력 표현의 **wire 모델**이다. 새 FPGA의 cycle/면적을240에서 가져오지 않았다.

|warm69 조합|ready4 최대B|ready1 최대B|SPI 예산5468.75B 초과|SNES4192 초과|
|---|---:|---:|---:|---|
|원본 raster+shift+16B map (schedule04)|6340|6520|3|952/955/963|
|의미 raster+shift+16B map|5141|5321|0|952/955/963|
|의미 raster+shift+word map|4601|4741|0|952/955|
|의미 raster+shift+16B map+FPGA sparse raw 제거 상한|4426|4546|0|952/955/963|
|의미 raster+shift+word map+FPGA sparse raw 제거 상한|3866|3966|0|952/955|

앞 두 의미 조합의 source 전송은 각각 같은 것이며 차이는 output map이다. 16B map의 ready1 여유는147.75B뿐이다. word map은 ARM retained state448B를 추가하며 새 RUN/IRQ는 여전히 미승인이다. SNES 수치는 schedule04의 주소순·유효gap 조건을 유지한다. 전체 pipeline의 시간 상한은 아직 UNKNOWN이다.

raw 제거 상한은 current frame의 raw pixel 입력과 **raw CHR에 완전히 속한 E1 packet만** 제거하고 source 블록 수·ready poll 수를 다시 센 것이다. BEGIN/SEAL, mode/HDMA/CGRAM, 계획/최종 retire 제어는 제거하지 않았다. 새 병렬 descriptor/제어 비용은 **UNKNOWN**,0으로 확정한 것이 아니다. frame954에서는 raw pixel512B, raw CHR payload80B/3packet이 해당한다. 추가 병렬 제어·변환·consumer 비용을 넣기 전의 낙관적 residual이다.

## raw만 옮길 때도 sparse와 수명을 보존해야 한다

단순히 collector의512 pixel byte를 읽어2048B raw CHR 전체를 매번 보내면, 기존232 command 순서의 모델에서 **67/69 warm frame이4192를 초과**한다. raw data가 병렬로 이동해도 VRAM 대역폭은 늘지 않는다. frame952는6752,954는6208,955는6336charge다. 따라서 이 경로는 기존 sparse raw 갱신을 보존하는 변환기여야 한다.

제한 후보의 상태는 last raw material2048B와 양 target stale bitmap16B×2다. 현재 source base를4398B용4096+512 bank로 줄여6→5M9K가 되고 raw base가2M9K라면54−1+2=**55/56**이다. 이 값은 RAM 용량 산술일 뿐이다. dirty32B/control/포트 배치·새 producer와 기존 encoder의 LE/LAB 절감·mapper 여유는 입증되지 않았다. 2048B aperture payload와 last raw base는 서로 수명이 달라 같은 RAM으로 공짜로 겹칠 수 없다.

소유권 요구는 다음과 같다.

1. 단일 capture generation/epoch를 semantic geometry와 raw 변환이 함께 참조한다. collector query 포트 중재는 둘 모두 drain되기 전에 다음 capture로 바뀌면 안 된다.
2. 기존 tile chunk를 먼저 처리한 뒤 새 typed raw chunk를 같은 aperture에 넣는 단순 직렬 스케줄부터 비용을 계산한다. 기존 tile END를 전체 END로 취급할 수 없다. old BG/OBJ consumer가 raw를 잘못 해석하지 않도록 paired version·section/range 검사가 필요하다.
3. raw last-material 비교 결과는 두 target에 stale을 누적한다. target stale clear는 transport consume이 아니라 해당 target의 최종 display ACK에서만 가능하다. raw 없는 frame의 양 bank 무효화 규칙도 유지한다.
4. STOP/epoch/first-fault는 source speculative base와 raw pending/base-valid, target display 후보를 함께 무효화한다. 열린 chunk나 늦은 token ACK가 새 세대의 ownership을 해제하면 안 된다. 기존 final ACK→retire→consumed와 core 우선 CHR 읽기 여유를 유지한다.

## 결정·다음 검증

전체 allocator의 그대로 이식과 full raw 재전송은 위 구체적 범위에서 배제한다. **의미 raster+row shift는 실제 출력 보존과 SPI 시나리오를 통과한 제한 후보**로 남긴다. raw sparse 재배치는 추가 제어·area·SNES 코드 비용을 넣기 전 상한 비교이며 아직 채택하지 않았다. 단일 sequencer, 새 RTL/FIT, 새 설치물은 선택하지 않았다.

P1 다음 검증은 잔여952/955의 VRAM 비용을 실제 안전 조건으로 더 줄일 수 있는지다. schedule04의 “gap이 target-valid여야 함”보다 넓은 조건을 쓰려면 **그 frame에서 unused임을 SEAL로 증명하고 이후 사용 때 반드시 실제 write를 요구하는 수명**이 필요하다. 초기화/추가 상태·코드 비용 없이 가능하다고 가정하지 않는다. 동시에 command-list 생성·DMA 실행의 교체 범위와 보수적 실행시간을 잡아야 한다. 단지4192 gate를 낮추거나 gap 데이터를 임의로 유효 처리하지 않는다.

이 SNES 경계와 의미 raster source의 전체 LE/LAB/1M9K 여유, 새 입력 ARM RUN/IRQ를 함께 만족한 후보만 P2로 보낸다. 새 heavy scene/장기 실기·mapper 확장 여유는 여전히 별도다. 생산227·240미배치·기각241/246·GBC164·save SRAM을 보존한다.

## 재현

```text
python tools/analyze_nes_relocation247.py --out <new-private-directory> --rom <private-SMB3-J-ROM> --gcc <existing-gcc.exe>
```

private observer03 및 기존 봉인 probe가 필요하다. relocation01은 새 실패 없이 PASS, compiler/run raw log와 generated host를 private에 보존했다. 이 호스트의 MinGW가 기본 sandbox에서 시작되지 않는 기존 제한 때문에 승인된 외부 실행으로 호스트 C 검증만 수행했다. 새 product RTL/C/65816 변경이나 Questa/FIT/ARM/SNES/실기 실행은 없다.
