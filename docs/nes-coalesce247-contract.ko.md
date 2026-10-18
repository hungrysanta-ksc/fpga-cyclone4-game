# NES247 P1: 범위 마스크 크기와 기존 타일 묶음의 수신 비용

2026-10-18, PR128. **범위 마스크 두 안은 ROM 한도 초과로 기각했다. 기존193 타일 묶음 규칙을 반영한 재생에서는71 frame이 일치했지만, warm 수신 검사 시간은 여전히3.08..11.59ms다.** 이 검사 시간 합계의 약80.9%가 map에서 발생한다. 새 제품/P2 후보는 선정하지 않았다.

SELECT `range16-build01`, `range8-build01`의 크기 결과와 `coalesce-host01/guards01/test01/analysis04`. analysis01은 잘못된 동일-clocks 가정으로 실패했다. analysis02는 수정한 전체 시간,03은 section 분류,04는 같은 분류의 CSV 열 순서를 고정한 결과다. SNES 재생은 test01 한 번이며 분석 중간본을 모두 보존했다.

[공개 검증](../analysis/coalesce247-verification.json) · [71 frame 비교](../analysis/coalesce247-frames.csv) · [이전 배치 정렬](nes-batchorder247-contract.ko.md).

## 범위 마스크의 크기 판정

[builder](../tools/nes_rangemark247.py)는 각 bit를 처리하던 루프 대신 시작/끝 prefix mask를 조합해8 또는16bit씩 received/target-valid bitmap을 검사·갱신하는 진단을 생성한다. 이전 입력 정렬·범위 검사와 SEAL coverage, append 경계를 남긴 상태로 body를 측정했다.

|안|body|3936B 한도 대비|판정|
|---|---:|---:|---|
|기존 수신 시 append|3903|33B 여유|기존 기능 검증 유지|
|16bit mask|3971|35B 초과|현재 크기에서 기각|
|8bit mask|3950|14B 초과|현재 크기에서 기각|

3936B는4KiB에서 boot96B와 footer64B를 뺀 용량이다. builder가 만든8KiB 진단 이미지가 현재 FPGA4KiB 경로에 들어간다는 뜻이 아니다. 두 mask 안은 **기능·중복/부분실패·STOP·실행시간을 시험하지 않았다**. 의도한 의미 보존을 검증 완료로 표시하지 않는다. ROM 확대 또는 opcode 몇 개 절약을 자동 채택하지 않았고71 frame 재생에는 기존3903B 바이너리만 사용했다.

## 기존193의 payload 묶음 규칙

[실제 RTL](../src/nes/rtl/nes_tile_bulk193.sv)의 `append_ok`와 CHECK/SEAL 규칙을 읽었다. 같은 generation·kind·연속 slot이고 합≤2048B이면 한 chunk에 이어 붙인다. kind/slot 불연속 또는 용량 초과 시 이전 chunk를 닫으며 END가 마지막 chunk를 닫는다. **15개 encoded-plan 배치의 끝은 tile chunk의 끝이 아니다.** generation 불일치는 정상적인 새 chunk로 수용하지 않는다.

[host fixture](../tools/prepare_nes_coalesce247.py)는 이 payload 분할을 구현한다. 앞선 타일별 fixture의 `slot*n` 오프셋 계산은 타일 길이에서만 맞으므로, 묶음에는 `slot*(kind?32:16)`을 사용한다. encoded-plan 정렬·allocation·변환된 tile bytes·배치 경계는 그대로다. 최대2048B 및15개 변환 tile 보관은 PC 재생용이며 ARM에 추가하는 상태가 아니다.

[C 경계 검사](../tools/test_nes_coalesce247.py)4사례/11chunk/6352B PASS:130 BG tile의2048+32B 분리,128 OBJ tile의2048+2048B, 불연속·역순·kind 변경, END/빈 flush/다음 generation. 배치15개에서 chunk를 끊지 않으며 각 byte를 독립 기대값과 대조했다. 실제 FPGA CDC·두 buffer·backpressure·STOP·token 고갈 검사는 아니다.

## 같은71 frame의 실제65816 결과

기존 [재생기](../tools/test_nes_batchorder247.py)와3903B 소비기를 사용했다. [분석기](../tools/analyze_nes_coalesce247.py)는 원래 개별 tile request를 묶음 payload와 독립적으로 대조하고, 모든 request descriptor·연속 token·순서·DMA 목록을 확인한다.

- 타일 chunk **598→178**, payload **12,944B exact**. warm69는416→166chunk.
- 71 commit/2657 ACK,426 DMA/134,944B.71개의 계획 순서·DMA 목록 exact PASS. 기존 C4,066,624 참조 비교와 used pattern/map/raw/metadata 확인도 통과했다.
- 66/71 single VBlank. cold2개와 warm952/955/963은 여전히 다중 VBlank다.4192 정책을 바꾸지 않았다.
- 미초기화752주소는 모두 기존 pattern gap 범위다. 전송량·화면 일치로 미검증 STOP/오류 경계를 승인하지 않는다.

|warm69/frame|이전 개별 tile|193 묶음 규칙 fixture|
|---|---:|---:|
|mark 호출|21..63, 합2681|16..52, 합2431|
|mark master clocks|80,720..312,076|66,184..248,988|
|mark 시간|3.75839..14.53052ms|3.08158..11.59309ms|
|coverage 시간|1.79306..1.79650ms|1.79315..1.79641ms|

mark 합계12,121,936→11,180,076 clocks, **약7.77% 감소**다. 프레임별 차이는−240..75,530 clocks이므로 모든 frame이 엄격하게 빨라졌다고 주장하지 않는다. 같은 coverage 코드도 frame별 master clock이−58..+72 달랐다. 최초 분석의 동일-clocks assert는 잘못된 가정이었으며 실행 실패나 화면 오류가 아니었다. 이 차이의 구체적인 하드웨어 원인을 별도 관측 없이 확정하지 않는다.

## 남은 수신 검사의 위치

정상 성공 request 순서와 유일한 `mark212` 호출 경계를 대응시켰다. op2/4/5/7/8마다 한 번임을 모든 frame의 호출 수·합계로 확인했다. 오류 trace에 이 대응을 일반화하지 않는다.

|section|warm 호출 합|warm mark clocks 합|
|---|---:|---:|
|map|1779|9,044,730|
|pattern|166|1,067,096|
|raw/HDMA|279|991,838|
|OAM|207|76,412|
|CGRAM|0|0|

map이 mark 합계의 약80.9%다. 이는 payload 복사·packet CRC·ARM/source·DMA·display를 포함한 전체 시간의80.9%가 아니다. 현재 `dirty_span231`은 이미 인접 dirty16B를 최대15개/240B까지 합친다. 같은 기능을 새 제안으로 세지 않는다.

같은 의미449B+rowshift+16B-map wire 모델을 고정하고 mark+coverage만 바꾼 조건부 직렬 값은 최대28.44578ms,47/69 frame이16.67ms 초과다. 이전31.96280ms/49개보다 줄었지만 source/ARM/복사/대기/DMA/표시가 빠진 제한된 비교이며, 실제 full pipeline의 가능/불가능 또는 FPS 판정이 아니다.

## 다음 비교 경계

타일 묶음은 기존193 기능이다. 이번 결과는 재생 fixture의 과도한 호출 수를 바로잡은 것이며 새 FPGA 성능 개선으로 보고하지 않는다. 범위 마스크3971/3950B를 opcode·seed 반복으로 줄이지 않는다.

다음은 map의 **의미 word/row 표현과 수신 검증·갱신을 함께** 비교한다. 기존 인접 dirty 묶음을 반복하지 말고, 실제 map 변경 원인·16B 과전송·SPI·ARM 상태·SNES 코드 크기/검사·3개 VBlank burst를 같은 frame으로 계산한다. 순서/중복 거부·target별 validity·partial failure·STOP·최종 coverage를 생략하거나 receive ACK를 displayACK로 대체할 수 없다. 단순 검사 제거, ROM 확대, mapper/ARM 여유 없는 부분 성공은 P2로 보내지 않는다.

의미449B/rowshift source 전체LE/LAB/mapper 여유, 새 입력 ARM RUN/IRQ, host/NES firstfault, final displayACK→commit→lease/retire는 계속 OPEN이다. 생산227·미배치240·기각241/246·GBC164·save SRAM 및 과거 근거를 보존했다.

## 재현

```text
python tools/nes_rangemark247.py --out <range16> --word-bits 16
python tools/nes_rangemark247.py --out <range8> --word-bits 8
python tools/prepare_nes_coalesce247.py --out <host> --gcc <existing-MinGW>
python tools/test_nes_coalesce247.py --out <guards> --gcc <existing-MinGW>
python tools/test_nes_batchorder247.py --out <test> --client <order-build01> --host <host> --rom <private-SMB3-J-ROM>
python tools/analyze_nes_coalesce247.py --model <order-model01/result.json> --build <order-build01> --host <host> --test <test> --append <order-append01> --individual <order-test01> --individual-analysis <order-analysis02/result.json> --range16 <range16> --range8 <range8> --guards <guards> --out <analysis>
```

빌드·실행 로그와 바이너리·게임 payload는 private에 둔다. 공개 파일은 도구·수치·문서다.
