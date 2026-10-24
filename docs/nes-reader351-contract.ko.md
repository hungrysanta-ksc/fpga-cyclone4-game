# NES351 — skip-header/common RAM reader 실제 교체 결과

**351 후보는 면적 회귀로 채택하지 않고338 RTL·336 ARM을 유지한다.** queue 필드 로더와 host RAM 발행/응답 경로를 실제로 교체했지만 전체 Quartus Lite MAP은17,274→17,295comb(+21),시간은 동일했다. remaining4.022994145ms와1,866comb 부족을 함께 줄이지 못했다. 새 후보의 부족은1,887comb다. 이 결과를 숨기기 위해 seed/FIT/상태 번호를 바꾼 재합성을 하지 않았다.

## 실제 구현과 제거 목록

`tools/nes_reader351.py`는338 생성 결과에서 두 제품 모듈만 바꾼다.

| 경계 | 없앤 것 | 대체·유지한 것 |
|---|---|---|
| queue header loader | `field338`,load_enable/load_at,record_valid/record_at/record_byte,192bit record wire interface | 원본2×256B slot 유지;head bank만 host에 공개 |
| RAM 주소 | queue의 header-specific 주소 선택,queue expected-select/address 입력 | host `ram_address351`가 packet/expected 주소를 선택;물리 region mux 자체는 유지 |
| header | 논리 field index→물리 주소 변환/반환 adapter | parser physical cursor `0..3→10..끝`,5bit 반환주소와pending flag;같은10/14/15fields,1byte/clock pipeline 유지 |
| packet read | 별도 DREAD/DCAP·MCAP 상태와 소비 경로별 RAM 발행/반환 연결 | 공통 PREAD/PCAP,2bit consumer kind로ordinary/descriptor/metadata dispatch |
| 진행 | 분산된 parser 증가 구문의 소유권 | 공통 `advance_packet351`;task 추출 자체를 별도 ALU 절감으로 계산하지 않음 |
| final scan | 변경 없음 | final MREAD/seal wait,독립expected 주소·446byte capture 및validator 유지 |

`read_packet351(kind)`는 해당 consumer로1clock RAM 응답을 귀속시킨다. header는 별도 pipeline이므로 일반 PREAD/PCAP의2clock/byte 처리량으로 떨어뜨리지 않았다. header packet_seq2/3 재검사,op/section/range/encoded/end 조건,실제 consume 뒤 token/left 갱신은 유지했다. HLOAD/HCHECK라는 경계 상태는 남으며 queue 전용 loader가 제거된 것이다.

incoming port A는 그대로다. queue RAM의 expected write는 host의 주소를 받지만 `address<472`,reset/fault/enable gate를 독립적으로 남겼다. accepted/retired/consumed는 서로 다른 사건이다. active121bit,batch end cursor,encoded/expanded progress,원본압축·MASK·SHIFT·tile 선행 생산,CDC·SPI response·plan transport는 유지했다. header/record의 wire 삭제를 저장소 절감으로 세지 않는다.

## 기능·포트·일정 검증

SELECT `window01/fixed01/normal01`, `map01`, `guards01`, `analysis-final01`;최종 판정과 hash는 `analysis/reader351-verification.json`이다.9관측은905..907의3unique frames다. 새71-frame proof가 아니다. 기존2351pins를재해시했고최종2648pins를보관했다. 9fault/STOP guard와aperture 및raw0/final8cases가모두PASS다.

검증기는 제품 RTL 변경이 `nes_mux260.sv`/`nes_queue260.sv` 두 개뿐임을 검사한다. ARM PT_LOAD와 실행 결과·SPI transfer 내용,source bytes/cycles,65816 ordinary bus trace 및기존 `joint-events.csv` **전체가 baseline과 동일**해야 통과한다. frame 종료 시각만 비교하지 않는다.

새 header capture는 주소12/13과14/15의 순서가 바뀌므로 committed head별 최종 주소→값 map으로 대조한다. header pipeline clock 수도 같아야 한다. 나머지 모든 host capture는 **timestamp/address/data의 순서까지 동일**하다. expected write와 독립 final capture 역시 timestamp/address/data가 같고,각 frame446개의독립 capture를 확인한다. actual RAM의 이전clock data와 현재 반환값을 테스트벤치에서 직접 비교한다.

| warm907 |338/336|351 candidate|차이 |
|---|---:|---:|---:|
|제한 ROM 연속|20.689660812ms|20.689660812ms|0|
|동일 시작/ROM 위상|25.051199382ms|25.051199382ms|0|
|정상 ROM 연속|13.410066350ms|13.410066350ms|0|

cold905/906도각모드의source/ARM/출력타임라인이같다. 따라서 이번 후보에는 앞 프레임 변화로warm 시작 위상만 이동한 효과도 없다. 최대2slot credit,실제 read→CRC/coverage/private receipt→token publication,최종ACK·12read·VBlank 계약도 기존 검사와 함께 실행했다.

guard는 E1 수신 중STOP(3),expanded staging 중STOP(8),expected 저장 중STOP(11),독립expected 최종순회 중STOP(12),map/requirements 주소overflow(15/16),소비 후wrong token(18),header response 중STOP(30),descriptor response 중STOP(31)을 사용한다. 새header/공통PCAP에 맞춰trigger만변경하고 RAMfreeze 및fault 후seal/lease/staged/ACK/retire 공개 차단 검사를 유지한다. aperture와raw0/final검사도같이실행한다. 최종guardPASS는증거JSON을따른다.

이번 일정은 실제 M4 instruction 실행과CPI1/84MHz·IRQ allocation,기존65816 ordinary trace와C map/tile consumer의 결합이다. full firmware RUN/실물 ARM WCET/full65816/전체pixel/FIT/STA/실물60fps를 뜻하지 않는다.

## Quartus Lite 전체 비용

| 항목 |338|351|증감 |
|---|---:|---:|---:|
|LE|22144|22170|+26|
|comb|17274|17295|+21|
|FF|9018|9023|+5|
|RAM bits|307808|307808|0|
|device15408 대비comb 부족|1866|1887|+21|
|여유155를 둔cap15253까지필요삭제|2021|2042|+21|

own-entity 비용은queue225→192(−33),host2161→2226(+65),둘의합2386→2418(+32)이다. 다른 entity mapping의합계변화−11을포함한whole은+21이다. 수정하지않은source/validator/다른보드블록의 mapping 변화도따로기록하며 이를별도최적화로주장하지않는다. parent-inclusive와child를더하지않는다.

host FSM은정상추출됐다. 따라서 이번실패를FSM미추출문제로돌리지않는다. 저장했던주소변환을없앤대신header반환tag/pending과consumer-kind decode·제어fanout이생겼고,실제host비용증가가queue절감을넘었다. 어느식이몇LUT를차지하는지는독립실험없이단정하지않는다.

MAP입력은실행한RTL과비교한다. 기존transport 생성기의module끝blank line1개차이는정확히그차이만정규화했다. extra timing-output 제거는기존whole-wrapper의명시적차이만허용한다. 새로운undriven신호는없고기존cache_index141 latch경고만유지됐다. 한 번의wholeLite MAP이며FIT/STA는실행하지않았다.

## 첫 BG ARM 준비 비용 계측

336 ARM은수정하지않고함수진입/복귀를관측했다. nested cost를상위start비용에다시더하지않는다.

| frame |dirty begin instructions|dirty material instructions|start286 instructions|
|---|---:|---:|---:|
|905|481|105093|126331|
|906|44|134161|138643|
|907|44|134354|138836|

warm dirty-material만 **1.599452381ms**다. 상위start286은1.652809524ms이며,top-level wrapper begin_step286의138843instructions와는호출경계7instructions차이다. 초기전체준비267357instructions/3.182821429ms 및첫 BG전전체440125instructions/5.239583333ms(연속기준)에이미포함된다. 함수watch의호스트실행시간은타깃시간으로더하지않는다.

고정ROM위상에서는첫요청8.381149ms를이전창끝6.089722ms까지당기려면2.291427ms가필요하다. dirty-material전체가무료라는불가능한가정에서도 **0.691974619ms**가남는다. 실제로는palette·HDMA·유효성검사등유지비용이있다. ROM accept후3.833249→3.180ms에필요한0.653249ms도별도다. 두비용을연속전체4.023ms와단순합산/차감하지않는다.

### 변경된 raw 그룹만 비교할 수 있는가

source MASK 기록을실제dense raw512B oracle과재구성대조하고,8픽셀그룹이출력planar64B에미치는범위를모델로확인했다.

|frame|MASK에담긴raw 변경픽셀|영향받는8픽셀그룹|대응planar범위|
|---|---:|---:|---:|
|905|512|32|2048B|
|906|6|1(group1)|64B|
|907|3|1(group1)|64B|

기존`nes_dirty231_material`은512B CGRAM과2048B raw tile,249B table을준비해이전표시material과비교한다. 현재raw tile부분은변경된범위와무관하게2048B전체를재생성한다. 906/907의group1만재생성한Python모델은전체변환과동일했고그밖의그룹은이전값과동일했다. 이것은**의존범위모델**이며최적화된ARM실행이나시간절감측정이아니다. 모델의dense배열을새타깃RAM으로할당할계획도아니다.

다음ARM후보는source raw MASK에서32bit group dirty 집합을보존해기존material 비교의변환범위를줄이는방식이다. 단순히raw record가작다는이유로이전표시기준을신뢰하지않는다. 입력history epoch/serial·raw count와마지막displayACK의기준이일치해야하며,cold/STOP/입력commit실패/표시실패/기준불일치에서는전체재생성또는무효화로돌아가야한다. 두destination bank의기존stale bits는그대로보존한다. source CRC·raw pixel범위·독립FPGA receipt/CRC/coverage를줄이지않는다.

이전표시material은BG key준비가scratch를덮기전에비교해야한다. 따라서전체비교를BG뒤로단순이동하는안은제외한다. group-mask생성·보관·검사·fallback·실제변환비용을M4에서계측하고,필요하면입력중immutable 준비를겹치는시간도별도검증한다. 새generation관리나shadow복사비용을무료로두지않는다. 31/32그룹을건너뛸가능성이31/32 instruction절감을뜻하지않는다.

## 다음 판정 기준

351 reader는정상동작을입증해도면적회귀로선택하지않는다.338/336 기준으로ARM raw-group 후보를먼저분리검증하고,동시에FPGA 전체2021comb삭제를설명할더넓은소유권/실행경계를다시예산화한다. 이번header/주소/tag배치만조금씩바꾸는반복실험을전체부족해법으로추진하지않는다. 새구조는삭제되는기존제어와추가되는owner/tag/check/port비용을함께제시해야한다.

생성기초기3회의문자열anchor assertion은각generator01..03 디렉터리와audit에보존했고generator04가최종PASS다. 분석첫시도의transport hash mismatch도blank line원인을기록해보존했다. 이들은라이선스오류나기능실패가아니다. 승인된Starter FLOAT와Quartus Lite만사용했다. Production227/GBC164/saveSRAM은변경하지않으며자동merge하지않는다.
