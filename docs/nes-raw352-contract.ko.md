# NES352 — 표시 이력에 묶인 ARM raw 그룹 비교

기준은338 RTL·336 ARM이다. 351 reader RTL은 면적 회귀로 계속 제외한다. 이번 후보는 `nes_dirty231_material`의 raw planar 변환·비교만 변경 그룹으로 제한한다. 최종 출력 material 생성, CGRAM512B, HDMA249B, raw pixel 범위 검사, source CRC, FPGA expected/receipt/coverage, STOP·최종 ACK·VBlank는 유지한다.

## 저장 수명과 실행 경계

별도512B raw cache를 추가하지 않았다. decoder가 raw MASK record의 값을 기존 source history에 쓰기 직전에 이전 byte와 비교해32bit 변경 마스크를 만든다. 한 그룹은 각 slot의8픽셀이며 출력 planar64B에 영향을 준다. 두 slot의 같은 그룹 번호는 OR한다. 전체 source CRC가 성공하기 전에는 마스크를 사용할 수 없다. input_commit은 이력 조건을 확인해 이 마스크를 material 비교에 넘긴다. 실제 M4 decoder를71프레임 재실행해 블록별 추가 비용을 source SPI 일정에 반영했다. live output ELF에서도 같은 decoder를 실행하며 이 중복 재생 구간은 기존 방식대로 output 시간에서 제외해 이중 계산하지 않는다.

마스크 사용에는 다음 조건이 모두 필요하다.

- 입력이 PREPARED에서 COMMITTED로 정상 전환되며 receiver의 전체 CRC가 유효하다.
- source epoch가 마지막 표시 성공 epoch와 같고 serial이 정확히 다음 값이며 raw count가 같다.
- cold/raw-cold가 아니고 dirty/resident 이력이 유효하며 fault가 없다.
- 이전 dirty frame이 닫혔고 새 resident frame이 열려 있으며, 두 표시 문맥의 epoch와 순차 serial이 맞는다.

추가 필드는 decoder mask·선택한 material mask·마지막 표시 source epoch·serial·raw_count의20B다. 실제 링크된 전체BSS 증가는 기존 padding 차이까지 포함해16B다. 표시 이력은 기존 `commit285`의 dirty commit, resident commit, producer commit이 **모두 성공한 뒤** 갱신한다. 입력 완료만으로 갱신하지 않는다. reset/STOP은 이력을 무효화하고 전체 마스크로 되돌린다. 이력 불일치와 cold/raw-count 변화는 전체 비교로 fallback한다. CRC/입력 상태 오류는 기존 fail-closed 경로로 거절한다. 이미 시작된 표시가 실패하면 dirty/resident 상태 또는 다음 source serial 불일치로 이전 입력을 잘못 재사용하지 못한다.

그룹 생략은 두 bank의 stale bits를 지우지 않는다. 이전 frame에서 이미 stale이었던 destination은 그대로 남는다. 비교는 BG key 준비가 `patch` scratch를 덮기 전에 수행한다. 최종 raw 출력은 종전처럼 전체 생성한다. 이번 변경을 전체 raw 생성 제거로 계산하지 않는다.

## 실측 결과

| warm907 일정 | 338/336 기준 ms | 352 후보 ms | 변화 ms |
|---|---:|---:|---:|
|제한 ROM 연속|20.689660812|20.689660812|+0.000000000|
|동일 시작·ROM 위상|25.051199382|25.051517560|+0.000318178|
|일반 ROM 연속|13.410066350|12.246307588|-1.163758762|

warm907의 raw material 비교는134354→34586명령으로99768명령(**1.187714286ms**,CPI1/84MHz) 줄었다. input_commit은2591→2641명령이며,decoder의 블록별 비용은cold905 +20683,906 +3199,907 +2000명령이다. 이 비용과 IRQ·polling·SPI·2슬롯·staging·ROM 경쟁은 위 일정에 포함된다. `.text`는30110→30638B(+528),`.bss`는47404→47420B(+16),관측 stack은1288B로 같다. 전체BSS에는 기존 probe 저장소가 포함되어 있으며 이를새타깃할당으로계산하지 않는다.

고정 위상 첫BG 요청은7.217890000ms다. 앞선 ROM 허용 구간 종료6.089722ms에 도달하려면 아직 **1.128168000ms** 더 앞당겨야 한다. 첫ROM accept 후 비용은3.833568000ms이며3.180ms cap까지0.653568000ms가 별도로 남는다. 준비 함수의 절감이ROM대기로흡수되어제한ROM의전체프레임이줄지않았다. 연속 일정의남은4.022994145ms와이두값을서로더하거나빼지않는다.

실제decoder71프레임/348610B복원 및77사례,실제M4snapshot65사례,세일정의9관측/3고유프레임이PASS다. 독립expected/실제read·private receipt·publish 순서와최종ACK/VBlank 검사,2슬롯credit을유지했다. 새RTL이없으므로기존 338 RTL 오류 주입 검증은hash가같은기존증거로유지하며이번에다시실행했다고세지않는다. ARM후보352의준비비용개선은보존하지만제한ROM60fps달성또는회로절감을승인한것은아니다.

## 검증과 시간의 해석

`probe_nes_raw352.py`는338 RTL에 후보 M4 ELF를 연결한다. 제한 ROM 연속 일정, 동일 시작 시각·동일 ROM 위상, 일반 ROM 연속 일정을 분리한다. source SPI/decoder 재생, 실제 M4 명령, IRQ, E1/E9,2슬롯 credit, tile ROM, staging 및 기존65816 ordinary trace를 포함한다. source 입력과 출력 packet 내용·순서, read→private receipt→publish 순서를 기존 결과와 대조한다.

`check_nes_raw352.py`는 실제 실행의 input_commit 직전 RAM snapshot을 같은 M4 ELF로 다시 실행한다. 최적화 마스크와 강제 전체 fallback의 dirty/resident/video/input 결과를 byte 단위로 대조한다. cold/raw-cold·이력 불일치·STOP·CRC 실패·중복 commit·미발행 commit을 검사하고, 모든32그룹 및 다중 그룹의 합성 변경으로 그룹 주소 산술을 검사한다. 합성 변경은 CRC 입장 검증의 증거로 사용하지 않는다.

측정 결과는 `analysis/raw352-verification.json`을 따른다. 실제 M4 명령에 CPI1/84MHz를 적용한 일정 모델이며 full firmware RUN, 물리 WCET, 전체65816/whole-pixel, FIT/STA 또는 물리60fps 증명이 아니다. 시작 위상 변화로 얻은 연속 일정 차이를 ARM 자체 절감으로 부르지 않는다.

## 더 넓은 FPGA 교체 범위와 예산

338 RTL이 byte 동일하므로 기존 whole Quartus Lite MAP을 재사용한다. **22144LE /17274comb /9018FF /307808RAMbits**, 장치15408comb 대비1866개 부족은 이번 ARM 변경으로 줄지 않는다.155comb 여유까지 두는15253cap에는 **2021comb 순삭제**가 필요하다. 동일 RTL의 MAP/FIT를 다시 돌리지 않는다.

다음 표의 cap은 구현 착수 여부를 판단할 목표 예산이며 합성 예측이나 이미 확보한 절감이 아니다. inclusive parent/child 수치를 더하지 않고 기존 own-cost를 사용한다.

| 범위 | 현재comb | 목표cap | 필요한 순삭제 |
|---|---:|---:|---:|
| source 실행 + host 실행 |3908|2035|1873|
| queue + SPI |798|650|148|
| 동시 plan 공급 경로 유지 |459|459|0|
| 독립 validator + aperture 유지 |1159|1159|0|
| 그 밖의 보드 회로 유지 |10950|10950|0|
| 전체 |17274|15253|2021|

핵심 후보는 source 단계와 output 단계의 **실행 문맥·주소 진행·반환 대기·완료 분기**를 공유 RAM의 phase record와 하나의 실행 경계로 바꾸는 것이다. 기존 두 FSM 옆에 공통 reader를 추가하는 방식으로 계산하지 않는다. source 쪽 MASK/SHIFT scan·record 출력 cursor와 host 쪽 descriptor/RLE/manifest 소비 cursor 중 수명이 겹치지 않는 저장·주소 선택을 실제로 지워야 한다. source용 실행 제어와 host용 실행 제어 합계3908에서47.9%를 줄여야 하므로 아직 타당성이 입증되지 않은 큰 목표다.

특히 현재 encoder는`clk`,host/validator는`host_clk`,transport는양쪽 clock을 사용한다. 따라서 두 FSM의 register 이름을 합치는 변경은 성립하지 않는다. 공통 실행기를 host clock으로 옮기는 후보라면 source query 요청/응답과 collector RAM의 동기 경계를 새로 연결해야 하고,기존 transport CDC 중 실제 없어진 부분만 절감으로 인정한다. query 왕복 지연·backpressure가 source 입력 완료를 늦추면 ARM 준비 절감과 함께 전체 일정에서 다시 평가한다. 이 clock-domain 이동 비용을2035cap 밖에 숨기지 않는다.

반드시 유지할 경계는 다음과 같다.

구체적 삭제 검토 대상은 encoder의`block_id/row_i/rec_i/build_i`와host의`cursor/parser_address/at/run_left313/manifest_byte313`가 만드는 실행별 주소·종료 비교,source FETCH/FSTORE/REQUEST/SREAD 반환 분기와host PREAD/PCAP/DREAD/DCAP/MREAD/MCAP 반환 분기다. 단,source `cursor`와query prefetch의 동시 사용,host batch 끝 주소와현재 payload 주소는 한 register로 합칠 수 있다고 가정하지 않는다. `epoch/base_serial`,token,bank valid,실제 read_count/tap coverage는 유지 문맥이다. HDL에 선언만 남아 합성에서 이미 제거된 register는 절감량0으로 취급한다. 공유 context를 RAM에 넣는다면 기존 phase RAM의 주소·포트·수명을 먼저 확정해야 하며,새 RAM 용량이나추가 read/write clock을 무료로 두지 않는다.

- source의 collector/input lease 종료 후 output 실행 문맥으로 전환한다. source 준비와 display lease의 lifetime을 같다고 가정하지 않는다.
- plan 공급·tile ROM 응답은 host 출력과 동시에 진행된다.459comb를 유지 예산으로 두며, source와 host가 phase를 나눌 수 있다는 이유로 plan도 같은 단일 FSM에 직렬화하지 않는다.
- SPI bit/CRC 수신과 host RAM 소비는 동시에 발생한다. 기존 두 RAM 포트와2슬롯 저장 credit/실제 consume 완료를 유지한다. queue+SPI 절감148도 새로운 CDC/owner/reply snapshot 비용을 포함한 순절감이어야 한다.
- independent expected와 실제 read CRC/coverage는 공통 성공 비트로 합치지 않는다. validator/aperture1159는 이번 목표에서 삭제하지 않는다.
- STOP은 pending RAM 응답, source 진행, active packet과 private receipt를 모두 취소해야 한다. 마지막 read/receipt는 최종 표시 ACK·VBlank와 구분한다.

다음 구현 전에는 실제 clock별 source→host 전환과 plan/SPI 동시성을 표로 묶고, 삭제할 레지스터·FSM 분기·주소 mux와 추가 phase owner/CDC/RAM 명령 비용을 같은 경계로 확정해야 한다.2035cap을 설명할 구체적인 삭제 목록이 나오지 않으면 이 예산을 달성 가능하다고 주장하지 않고 역할 분담을 다시 검토한다. header tag/state/seed만 바꾸는 반복 합성으로2021개를 확보하려 하지 않는다.

Production227/GBC164/saveSRAM은 변경하지 않는다. 자동 merge하지 않는다.

## 폐기한 첫 후보와 실패 기록

처음에는 input_commit 직전의 `input285.raw_pixels`를 이전 raw 비교 저장소로 쓰려 했다. 그러나 이 배열은 `required[2048]`와 union이며 geometry 준비에서 이미 덮인다. 제한 ROM 첫 실행은 출력 검사를 통과했지만 모든 그룹을 처리해 시간 이득이 없었다. 이를 `rejected-input-alias01`과 `window01`에 보존했다. `fixed01`은 수정 전 후보의 진행 중 실행을 의도적으로 중단했고, 새 후보는 `window02/fixed02/normal02`로 분리했다. 이 중단은 FLOAT entitlement 문제가 아니다.

build01은 초기 source 준비 누락,build02는 sandbox DLL 로딩 오류,build03은 잘못된 초기 builder,build04는 commit289 suffix를 빠뜨린 generator anchor 오류였다. build05는 폐기 후보,build06은 수정 후보의 성공 빌드다. 생성물과 남아 있는 원본 로그를 보존하고 초기 wrapper 예외 유형은failure-audit.json에 기록했다. 첫 분석의 source cycles 동일 assertion도 연속 위상에 따른1clock 차이를 드러냈으므로 삭제 가능한 비용으로 숨기지 않고 실제 source 시간을 사용한다.
