# NES247 P1: 배치 내부 정렬과 수신 시 명령 생성

2026-10-18, PR128. **기존15개·240B 계획 배치 안에서만 정렬하고 수신 시 DMA 목록을 합쳐, post-SEAL 스캔을 없앴다.** 실제71 frame의 화면·순서·명령 목록을 확인했고 SNES body3903/3936B다. 수신 검사와 최종 coverage 비용, warm3개의 다중 VBlank는 남으므로 제품/P2 후보 선정은 없다.

SELECT `order-model01/build01/host01/append01/test01/analysis02`. analysis01의 수치·raw 근거도 보존했다. analysis02는 같은 실행에 “plan당1개 bulk fixture이며 실제 FPGA 합치기와 다름”이라는 해석 제한을 추가했다. 재생을 반복한 것이 아니다. [이전 word 순회](nes-wordwalk247-contract.ko.md)의5.41..7.90ms 결과는 보존한다.

## 먼저 확인한 일정과 소유권

실제233 RUN의 `nes_native_runtime165.c`와 `nes_plan_service200.c`를 읽었다. 새 입력으로 교체한 전체 RUN을 실행했다는 뜻은 아니다.

1. COMMITTED 입력에서 resident BEGIN과 inactive target을 선택한다.
2. planner는 slot 할당 순서대로 callback을 부른다. `nes_plan200_emit`는 최대15개/240B 배치를 채우고, 꽉 차면 poll/transfer를 동기 수행한다.
3. `nes_plan200_finish`는 END까지 보낸 뒤 변환 완료와 남은 chunk를 drain한다.
4. `nes_sink231_seal`이 metadata와 SEAL을 보내고 실제 표시 ACK를 기다린다. resident/dirty commit은 그 뒤다.
5. `nes_plan200_retire`는 표시와 generation을 확인한 뒤 NES-domain retire/rearm을 수행한다. 그 후에야 `nes_native165_consumed`로 다음 입력을 받는다.

따라서 현재 RUN에 임의의 cross-frame overlap을 넣어 시간을 상쇄할 수 없다. 반면 **배치가 전송되기 전 그 내부 레코드 순서를 바꾸는 것**은 source/base/target 수명을 늘리지 않는다. allocation·physical CHR identity·row/alt·mask·generation 및 배치 경계는 보존해야 한다. END는 마지막, zero slot은 첫 배치 맨 앞이다. CRC는 정렬 뒤 계산한다.

전체 frame을 보관해 정렬하는 안은 다른 비용이다. `nes_plan191`는40B이고 최대1152 tile 계획을 그대로 저장하면46,080B다. 기존248B 배치 버퍼나233의 미검증 여유1616B에 들어간다고 주장하지 않는다. retained key에는 임의 row/alt 계획 전체가 남아 있지 않아 이를 생략해 복구할 수도 없다.

## 같은71 frame의 배치 비교

[모델 요약](../analysis/batchorder247-verification.json) · [71행](../analysis/batchorder247-frames.csv) · [분석기](../tools/analyze_nes_batchorder247.py).

observer의 실제 slot 기록과 plan 목록을 맞췄다. 이번71 frame의 쓰기는 모두 ordinary였음을 확인한 뒤 실제199 형식의 zero3B/BG7B/OBJ8B와 END3B,15개/240B 경계를 적용했다. 다른 장면에도 ordinary라고 가정하지 않는다.

|warm69|관측/모델|
|---|---:|
|tile 계획/frame|1..24|
|배치/frame|1..2|
|정렬로 이동하는 encoded bytes/frame|0..136, 합642B|
|원래 도착 순서+pattern gap의 DMA 명령 합|444|
|배치 내부 정렬+pattern gap의 DMA 명령 합|414|
|전체 주소 정렬의 DMA 명령 합|410|
|배치 정렬 최대 charge|4336|
|4192 초과 frame|952/955/963|

삽입의 최대 비교 수는 배치당105, 이동 쓰기의 보수적 상한은3360B와 같은 양의 읽기다. 새 레코드 복사량은 별도로 배치당≤240B다. 전 프레임 역순 목록의4.58MB 이동 상한을 이 배치 단위 제한으로 피한다. 이는 cycle 상한이나 무료 작업이라는 뜻이 아니다.

모델의 backward insertion 비교 횟수와 실제 C helper의 forward insertion 비교 횟수는 같다고 보고하지 않는다. 정렬 순서·레코드 이동량·105 상한은 공통이다. 기존 순서를 유지할 경우 END 때문에 달라지는 마지막 배치도 보존했다.

## 실제 C append 검사

[helper·SNES builder](../tools/nes_batchorder247.py)와 [C 검사기](../tools/test_nes_orderappend247.py)를 사용했다. 내부 helper는 **이미196/199 encoder가 검증한** 레코드만 받으며 raw packet decoder로 공개하지 않는다.

기존 `nes_plan_service200.c`의 `append`에서 마지막 memcpy를 in-place insertion으로 교체한 private source를 실행했다. 이미 존재하는 `encoded[32]`를 사용하며 persistent 상태 추가는0B다. 별도의16개 포인터 배열이나 frame 계획 저장소는 없다.

원본 append와 변경 append의 배치별 레코드를 독립 Python 비교기로 대조했다. 실제 flush CRC16/CRC8,15개 경계,240B 경계, END 마지막, 구조체 양끝 canary를 확인했다. 네 사례는 reverse15 ordinary,0..8 alternate가 있는 full16..32B와 short 혼합, 정확히240B로 END가 다음 배치가 되는 경우,15개 직후의 후속 레코드다. 원래 배치 경계와 모든 레코드 byte가 보존됐다. **ARM binary 전체 RUN/IRQ나 CPU 시간 검사는 아니다.**

## 수신 시 합치기와 실제65816

기존232 append는 metadata에만 gap≤96B를 허용했다. 진단에서는 이 조건을 pattern에도 허용한다. 다른 length/중복/범위/target 검사, 같은 section 및≤4096B 제한은 유지했다. 역순 범위는 기존대로 새 descriptor를 만든다. 정렬되지 않은 배치 경계 때문에 생기는 추가 descriptor도 허용한다.

이미 검증한 SEAL의 used⊆valid 조건을 사용하므로 used pattern gap은 실제 유효한 target bytes여야 한다. invalid-unused gap은 표시에서 참조하지 않으며 DMA가 validity를 올리지 않는다. **모든 payload 수신 및 coverage 성공 전에 DMA하지 않는다.** 이것이 수신 시 목록 생성과 수신 중 VRAM 업로드의 차이다.

[실행 검증](../analysis/order247-verification.json) · [71행 시간표](../analysis/order247-frames.csv) · [재생기](../tools/test_nes_batchorder247.py) · [독립 분석기](../tools/analyze_nes_order247.py).

- body **3903/3936B**, 여유33B. post-SEAL 스캐너 없음.
- 실제71 commit/3077 ACK, **71개 계획 순서와 전체 DMA 목록 exact PASS**.
- DMA426회/134,944B. word 순회 대비8회 늘고128B 줄었다. 배치 경계를 넘어서는 정렬은 하지 않은 결과다.
- 66/71 single VBlank. cold2개와 warm952/955/963은 다중 VBlank다.4192 정책은 그대로다.
- 미초기화 읽기752건/752주소는 모두 pattern gap 주소다. 실제 used pattern/map/raw/metadata는 기존 Lua와 C 참조 비교를 통과했다.

재생의 private C fixture는 최대15개의 **변환 완료 pixel**을 PC 메모리에 잠시 두고 실제 helper 순서대로 보낸다. 이것은 ARM에 추가하는 메모리가 아니다. 제안 ARM 변경은 기존 encoded 배치 내부 정렬뿐이다. fixture는 각 계획마다1개의 bulk를 보내 총598개다. 실제 FPGA의2048B 합치기·token 경계를 실행한 것은 아니며, 실제 합치기는 mark 호출 수를 줄일 수 있다. 따라서 아래 시간을 물리 실행의 하한으로 삼지 않는다.

## 숨기지 않고 측정한 수신 비용

각 `mark212` 진입→복귀와 SEAL의 `coverage212` 진입→복귀를 Mesen master clock으로 계측했다. mark에는 **기존 bitmap 범위/중복 검사와 새 append 모두** 들어 있다. payload 복사·codec, packet CRC, ARM 정렬 시간은 이 구간 밖이다. 이전 mark 시간을 측정하지 않았으므로 이를 전부 새 비용 또는 절감분으로 부르지 않는다.

|warm69/frame|실측|
|---|---:|
|mark 호출|21..63|
|mark 합|80,720..312,076 clocks =3.75839..14.53052ms|
|coverage|38,510..38,584 clocks =1.79306..1.79650ms|
|post-SEAL 순회|없음|

의미449B raster+rowshift+batched16 wire 모델에 같은 frame의 mark+coverage를 직렬로 더한 조건부 값은 최대31.96280ms,49/69개가16.67ms를 넘는다. 다른 CPU/복사/DMA/대기 비용은 빠져 있다. 이 수치는 기존 wordwalk의 “wire+scan만”과 포함 경계가 다르므로31.96 대23.48을 성능 악화로 비교하면 안 된다. 새로 관측한 비용을 빠뜨리지 않기 위한 표다. 실제 파이프라인 전체 불가능 증명도 아니다.

## 판정과 다음 경계

배치 제한 정렬과 수신 시 목록 생성은 기능·코드 크기 진단을 통과했다. post-SEAL 스캔을 없애도 수신 검사와 coverage 비용은 남는다. 추가 seed나 삽입 opcode 조정으로 P2를 승인하지 않는다.

다음은 **실제 범위 단위 bitmap 검증/갱신**의 경계를 본다. 현재 수신 경로는 각 단위를 bit로 풀어 검사한다. contiguous range의 시작·끝 mask 및 중간 word를 다루는 구조가 중복 거부·target validity·partial failure·STOP을 유지하면서 비용을 줄이는지 먼저 비교한다. 실제 FPGA coalescing에 따른 호출 감소와 per-unit 비용 감소를 분리해야 한다. 최종 coverage를 제거하거나 packet 수신 ACK를 표시 완료로 대체하지 않는다.

동시에3개 VBlank burst와 의미 source의 전체LE/LAB/mapper 여유, 새 입력 ARM RUN/IRQ 및 final displayACK→commit→retire를 묶은 후보는 여전히 미선정이다. SNES 한 부분의 통과로 FIT/실기 단계로 넘어가지 않는다. 생산227·미배치240·기각241/246·GBC164·save SRAM 및 과거 자료를 보존했다.

## 재현

```text
python tools/analyze_nes_batchorder247.py --observer <observer03> --prior <analysis06/result.json> --walk <walk-analysis01/result.json> --relocation analysis/relocation247-frames.csv --out <new-model>
python tools/nes_batchorder247.py --out <new-client>
python tools/prepare_nes_batchorder247.py --out <new-host> --gcc <existing-MinGW-gcc>
python tools/test_nes_orderappend247.py --out <new-append-test> --gcc <existing-MinGW-gcc>
python tools/test_nes_batchorder247.py --out <new-test> --client <new-client> --host <new-host> --rom <private-SMB3-J-ROM>
python tools/analyze_nes_order247.py --model <new-model/result.json> --build <new-client> --host <new-host> --test <new-test> --append <new-append-test> --out <new-analysis>
```

원본 ROM·pixel·trace·바이너리·raw 로그는 private에 둔다. 공개 파일은 도구·수치·문서이며 기존 완료 probe를 덮어쓰지 않는다.
