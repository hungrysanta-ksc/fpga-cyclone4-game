# NES241: 제어 ROM 후보 기각 — NES240을 기준으로 유지

## 작업 의미

60fps 증분 입력 회로의 FPGA 자원 부족을 해결하기 위한 설계 선택 검증이다. NES240의490LE·40LAB 부족을 줄이려 했으나 **상태 전환/RAM 제어만 ROM으로 옮기는 이번 후보는 자원이 더 커져 기각**한다. 기능 동일성을 자원 개선이나 실기60fps 성공으로 취급하지 않는다. 다음 구현 기준은240이며 생산판은227이다.

## 구현한 후보

128×32bit ROM 한 word에 true/false 다음PC 각7bit,predicate6bit,RAM command5bit,interface flag7bit를 둔다. 실제58개 상태,30개 predicate,17개 RAM command와9개 복합 return resolver가 있다. 다음PC로 ROM을 읽는 edge에 PC도 함께 갱신하여 synchronous read의 추가 실행 bubble을 없앤다. reset은PC0/IDLE word를 읽고,abort/lease/early ACK/fault의 기존 우선순위는 유지한다.

이전 데이터 경로의 branch annotation은 no-op task로 남겨 전사 검토를 가능하게 했지만 실제 PC를 쓰는 곳은 next_pc 한 곳뿐이다. 테스트 runner가 단일 PC driver를 정적으로 검사한다. 기존 넓은 데이터 레지스터·연산과 해당 update case는 유지한 **control-only 후보**이며,완전한 microcoded shared datapath 구현이 아니다.

RAM read/write routing과 외부 ready/valid를 ROM instruction으로 구동한다. base RAM 두 bank,직접 송신 view,CRC/serial/epoch 폭,독립 query offset 검사,raw 경계와오류 규약을 유지한다. 새 clock domain이나 새로운 SDC 예외는 없다.

## 검증과 실패 이력

- guards01: lease_ok 선언 순서로 compile 실패. 라이선스 문제가 아니다.
- guards02: 버전명 전사 중240B literal 조건을241로 잘못 바꾼4곳이 있었고 reference 비교가 frame1에서 PC 불일치를 잡았다. wire 규약은240B로 복원했다.
- guards03:24정상+17경계41검사,7개 view stall,기존240과1,278,508cycle의 PC/interface/byte 일치.
- guards04: RAM 주소·write enable·write data 비교와58개 상태 coverage를 추가해 통과했다. 그러나 다음 MAP가 LH0/LH1/LH2의 잔여 PC driver3개를 발견했다. 같은 값을 쓰는 다중 driver는 이 simulation만으로 검출되지 않음을 확인했다.
- board01: 그 다중 driver 때문에 elaboration 실패. 자원 부족의 증거로 사용하지 않는다. FIT는 실행되지 않았다.
- guards05: 잔여 driver 제거와 정적 단일 driver/literal 한도 검사를 추가한 최종 source다. **1,278,508cycle/58states의 RAM·PC·interface·byte 일치,24정상+17경계41검사,7view stall**을 통과했다. 정상 완료마다 base5741B도 비교했다.
- board02: 최종 source의 MAP가 완료됐고 FIT를 한 번 실행했다. 아래 자원 결과를 얻었다.

정상/경계 자료는240과 같은seed237·24입력이다. shift양방향,raster 반복/희소/0,literal240B/gap,patch0..7,serial/epoch/offset,lease/abort/ACK/raw오류와 cold replay를 포함한다. 큰 serial은 lifetime counter seed 시험이다. 참조240도 동일하게 seed한다. 모든 자료와 중간 실패 source를 보존한다.

자원 판정을 먼저 수행했고 최종 후보가 악화되어 **241의 실제collector→SPI→C 스크롤71프레임 통합 시험은 실행하지 않았다.** 해당 runner는 준비돼 있지만 실행 결과는 없다. 기존240의71프레임 결과는 이전 baseline 근거이며241의 신규 실험으로 재표기하지 않는다. 새 frame 시간/FPS/ARM/65816/실기 검증도 없다.

## 실제 자원 판정

동일224 보드에서240과 같은 source 범위를 교체했다. 같은216개 retired SDC 행을 제거한 파일은240과 byte-exact다. 첫 MAP elaboration 실패를 고친 뒤 완료 MAP1회/FIT1회이며 seed 탐색이나 clock 완화는 없다. 기존 loader state/IO 경고도 보존한다.

| 항목 |240 baseline|241 기각 후보|
|---|---:|---:|
| encoder 조합/FF |1399/409|1650/356|
| source 계층 조합/FF |2092/974|2360/921|
| 전체 조합/FF |14966/8577|15270/8524|
| MAP 추정LE |19809|20105|
| 실패한 FIT의 LE 요구량 |15898|16218|
| 실패한 FIT의 LAB 요구량 |1003|1022|
| M9K 요구량 |54|55|
| 논리 memory bit |311904|315744|

제어 ROM은 선언128×32에서 상수 bit 제거 후128×30,3840bit·1M9K로 추론됐다. 실제 요구 블록 수로 확인한 값이며 단순 용량 산술이 아니다. 그러나 encoder 조합은251개 늘었고 FF는53개 줄었으며 전체 FIT 요구LE는320개 늘었다. control word/PC 저장 절감이 주변 decode·branch·기존 data update 논리 비용을 상쇄하지 못했다는 것이 결과에 부합하는 해석이다. 각 하위 원인의 개별 기여는 분리 측정하지 않았다.

FIT는 Error170012:1022LAB/963으로 실패했다. LE도16218/15408이며 **810LE·59LAB 부족**하다. mapper/timing 여유는 별도다. LUT-only7694/register-only948/LUT+register7576이며 RAM 위치는Unassigned다. 배치·타이밍·전기적 승인이 아니다.

## 수정된 다음 계획

1. **240을 유지**한다.241 PC/control ROM을 더 작게 조정하거나 FIT seed를 반복하지 않는다. 기존 상태기계를 binary PC로 바꾸고 분기표만 ROM으로 옮기는 방법은 채택하지 않는다.
2. 다음 후보는 데이터 저장과 연산 자체의 공유 여부부터 판단한다. 240의 실제 스크롤 자료에서 필요한 byte 연산,넓은 값의 비교·증가,live register와RAM port 사용을 정리하여 memory-backed operand와 좁은 공용 ALU가 기존 병렬 datapath를 얼마나 대체하는지 계산한다. decoder만 추가하고 넓은 data mux를 그대로 두는 후보는 제외한다.
3. MCU 입력 serial/epoch는 start 직후 바뀔 수 있다. 이를 RAM에 옮기더라도 승인 시점의 snapshot과32bit 규약을 보존해야 한다. 추가로 입력을 여러 cycle 유지하라고 가정해서는 안 된다. 독립 offset 검사,reset/abort/ACK 우선순위,공개 중 immutable view,ROM/CHR-RAM lifetime과save SRAM 경계도 유지한다.
4. microinstruction의 실제 word 폭·M9K port 배치·조회 지연과 frame별 cycle 상한을 먼저 작성한다. 240의54/56M9K 여유를 모두 사용해도 된다는 승인이 아니다. 준비 시간과 공유 SPI/SNES 전체16.67ms 예산 및 향후 mapper 여유를 함께 평가한다. 아직 shared ALU/operand RAM의 자원·속도 이득은 증명하지 않았다.
5. 가능한 후보만 최소 reference/cancel 검증→자원 preflight→같은 첫 레벨71프레임 통합 검증으로 이어간다. 해당후보가 자원상 악화되면 긴 통합 시험과 실기판 생성은 하지 않는다.

새 입력 전체 ARM RUN/IRQ,host/NES 최초 오류 보존,최종 source lease/displayACK/retire,새 CDC/IO/STA,232의5개 VBlank 초과 burst도 여전히 남아 있다. 생산227/GBC164/save SRAM,ROM과 기존 봉인 자료는 변경하지 않는다. 새 firmware/ZIP이나 동일227/044 실기 재시험 요청은 없다.
