# NES247: 수신 비용 분해와 packet 내부 범위 누적

2026-10-18, PR128.60프레임 목표를 위해5775B 수신기를 계측한 뒤, 입력/STOP 확인 주기를 그대로 유지하면서 DMA 목록 추가를 묶었다. **본문은5818B(+43B), warm69 수신·검사 합계는17.23% 감소, 최악 합은13.28558→10.82605ms**다. 같은71프레임의 wire·map·DMA 목록·표시가 일치한다. 전체60fps/P2 후보는 아직 선정하지 않았다.

[검증과 비용](../analysis/maskbatch247-verification.json) · [71 frame 표](../analysis/maskbatch247-frames.csv) · [직전 그룹 수신기](nes-maskfast247-contract.ko.md).

## 먼저 실제 비용을 분해했다

`maskprofile-build01`은 계측 label만 추가했다. body.bin·32KiB 실행ROM·8KiB compact ROM 모두 `maskfast-build02`와 byte exact다. 실제71frame에서2427record를 instruction 경계로 관측했고, warm69는1915record/2607word다.

|warm mask 내부 구간|합계ms|비중|
|---|---:|---:|
|record 검증·조회표·복사 준비|145.751|34.23%|
|선택 값 복사|79.183|18.60%|
|목록용 주소 계산|44.696|10.50%|
|generic append 호출|102.704|24.12%|
|append 성공 검사|2.099|0.49%|
|입력/STOP service 호출|34.066|8.00%|
|packet 진입·record 사이·복귀 등 나머지|17.255|4.05%|

서로 겹치지 않는 구간이며 합이 mask 전체 관측 시간과 정확히 일치한다. copy에는 bit 검사·index 이동이 포함되고, prepare에는 범위 검증·receipt 기록 등이 포함된다. 순수 메모리 버스 시간만의 표가 아니다. 같은 바이너리의 별도 실행 총425.754ms와 직전425.719ms의 미세 차이도 보존한다. mailbox 공개와 PPU/HDMA 위상이 있는 실행을 완전히 같은 clock trace로 주장하지 않는다.

service를 줄이는 것보다 주소·목록35%를 줄이는 방향을 선택했다. 기존 service는 STOP을 읽고 VBlank의 pad 준비 상태를 확인하는 bounded routine이다. 매 record 확인을 생략하지 않았다.

## 범위 누적의 정확한 수명

같은 packet 안에서 엄격히 증가하는 map group의 첫 선택 word부터 마지막 선택 word까지 범위를 모은다. 이전 끝에서 다음 시작까지 gap≤96이면 합치고, gap>96 또는 packet 끝이면 기존 generic append를 호출한다. packet을 넘겨 pending span을 유지하지 않는다. packet 사이의 기존 목록 병합·section 구분·4096 길이·목록 용량 검사는 generic append가 그대로 수행한다.

DP94..97에 pending 시작/끝, DP8a..8b에 incoming 끝을 둔다. 기존 DP80..93 영역의 미사용 hole2B와 새4B를 사용하므로 실제 사용 scratch는6B 늘고 최상위 주소는97이다. end0이 empty를 나타내며, 유효 span의 끝은2..4096이어서 충돌하지 않는다. 불변 packet 검사 뒤 선택 word만 inactive WRAM에 기록한다. pending span이 남은 상태의 오류·STOP은 terminal rejection되어 display로 진행하지 않는다. 다음 정상 packet 진입은 pending end를0으로 시작한다.

입력/STOP service는 각 record 뒤 그대로 실행한다. 마지막 flush 뒤에도 기존 caller의 service 및 STOP 검사 후에만 정상 packet ACK가 나간다. manifest/cold map/pattern/raw/CGRAM coverage와 최종 display ACK 소유권은 변경하지 않았다.

## 실제 검증 결과

SELECT `maskbatch-build01/test01/fault01/lanes01/masks01/bounds01/stop01/analysis01`, `batchstorage-map01/rtl01`; profile은 `maskprofile-build01/test01/analysis01`이다. 송신기는 기존 `maskrun-host01`이다.

-71 display commits/1100 ACK, C reference4,066,624 checks. 독립 encoder/map290,816B 및71개 command 목록이 직전 수신기와 일치한다.
-426DMA/132,270B,178 bulk chunks/12,944B, 최대DMA1312B/목록13개가 같다. warm multi-VBlank952/955도 같다.
- normal71의2427record마다 service가 한 번씩 실행됐다. warm1915회는 유지하고 generic span flush는1915→213회, cold 포함2427→253회다. 독립 parser가 각 packet의 flush 시작/끝 전체를 기존 gap 규칙으로 재구성해 실제 관측값과 일치시켰다.
- 기존12오류·STOP+24전개 검사 위치,255 nonzero mask 전체/1024word/비선택 포함map4096B를 새 바이너리에서 통과했다.
- 추가 양성 시험은 gap96 병합/gap98 분리/최종4096 endpoint를 실제 CPU로 확인했다. 명령은 start30,length100;start228,length2;start4094,length2이다. 추가2STOP은 pending span 및 packet-final flush 시점을 겨냥해 이전 표시 보존·terminal rejection을 확인했다. 총38개 오류·STOP 조건이며 양성 span 경계와255mask 시험은 별도다.
- 정상 replay의752개 미초기화 읽기는 독립 oracle이 허용한 미사용 pattern gap에 한정됐다.

같은 packet 안의 연속 group service 복귀 간 최대 관측 간격은0.292216→0.285232ms다. packet 진입 전후·다른 command·전송·host/ARM을 포함한 **전역 STOP 응답 한도는 아니다.** 실제 service 횟수 유지와 변경된 pending 경계 시험을 근거로 삼는다.

## 성능과 저장 비용

|warm69|직전5775B|현재5818B|
|---|---:|---:|
|mask 합계ms|425.719|329.031|
|mask 최대ms|11.32351|8.86398|
|map+manifest+coverage 최대ms|13.28558|10.82605|
|위 세 항목 합계ms|561.102|464.414|
|조건부 wire+측정routine 최대ms|27.32937|25.16299|
|조건부16.67ms 초과 frame|45/69|27/69|

mask 합계는22.71% 감소했고 이번 비교에서 mask 회귀 frame은 없다. manifest와 coverage의 clock 합은 이전과 정확히 같다. 현재 세 항목 합은3.51264..10.82605ms, 조건부 wire+routine 합은12.37598..25.16299ms다. 아직 source/ARM/나머지 dispatch·copy·대기·DMA/display를 모두 포함하지 않으며 실제FPS나 모든 겹침 일정의 불가능 증명이 아니다.

새 프로그램도6KiB(4096+2048) ROM으로 standalone MAP했다.249LE/97comb/158FF/49,152bits로 배열 형상이 같고 본문 여유166B다. 직접8KiB 비교와 실제 bus RTL33,029reads+4raw 경계도 통과했다. ROM write 기본0 경고6개를 보존했다. 새 whole-board FIT/STA는 없다.

240은54/56M9K에 LE/LAB 부족으로 미배치다. 프로그램4→6M9K를 대입한56/56은 용량 산술이며 mapper/source 여유가 아니다.6KiB/166B도 절대 제한이 아니다. 생산227/GBC164/save SRAM과 기존 실패·검증 자료는 보존했다. PC 송신기의 별도 이전map4096B/stale512B는 ARM 할당 승인이 아니다.

## 다음 비교

입력/STOP 확인을 줄이지 않고 주소·목록 반복을 크게 줄였다. 다음은 남은 record 준비·선택 값 복사의 CPU 비용과 추가 wire 비용을 함께 비교한다. 기존 mask의 sparse/dense 처리와 packet 단위 연속 범위 수신(DMA 가능한 경계 포함)을 같은 map/은행/manifest 자료에서 비교하고, 기존 range·bulk 기능과 중복되지 않는 차이를 먼저 명시한다. 불변 mailbox·수신 범위·취소·display 소유권 및 전체 code/M9K·ARM 비용까지 근거가 있는 경우에만 새 수신 형식을 구현한다. 단독 opcode/seed/크기 미세 조정 반복은 하지 않는다.

952 순서와955 최소4198>4192 DMA charge, source449/rowshift 전체 면적·mapper, 새 입력 ARM RUN/IRQ, host/NES firstfault·CDC/IO·최종 display lease/retire는 여전히 열려 있다. 전체60fps·새설치물·실기 승인은 하지 않는다.
