# NES338 — 256B queue와 immutable D4 descriptor

현재 작업은 PR131의336 RTL·ARM 위에서 E1 저장 주소와 D4 응답의 중복 상태를 실제로 교체한다. ARM336,압축 source/짧은 E9 형식,metadata 선행 발행,tile 선행 생산은 유지한다. 검증 결과와 선택 상태는 `analysis/ingress338-verification.json` 및 `nes-ingress338-plan.json`에 결합한다.

## 실제 교체

E1 packet 전체를1024x8 RAM의512..767/768..1023에 그대로 저장한다. expected0..471과472..511 여유40B는 유지한다. 기존480/752 기반272B 간격,header compact/payload 재배치,ingress field permutation,opcode/prefix/base 선택과 payload 주소 덧셈을 제거했다. ingress는 `{1,accepted[0],byte_index-1}`,소비 주소는 `{1,retired[0],sn_address}`다. byte index−1과 expected/packet 포트 선택은 여전히 필요하다.

active record 로더는 원래 wire 위치 `[0,1,2,3,10,11,14,15,12,13,16..20]`를 읽는다. 작은 주소 선택과 synchronous RAM 지연은 유지하며 기존 record의 필드 의미와 순서를 바꾸지 않는다. sequence·serial·generation·길이·CRC 검사,2슬롯 fullness,저장 retire/소비 완료 분리는 유지한다. 단순히 검사 대상 byte를 생략해서 얻은 절감이 아니다.

D4는 checked prefix의 POP으로 선택한 bank descriptor와 현재 token을 직접 사용한다. snapshot_length8/CRC16/token16의40비트 복제를 제거했다. 현재 bank는 다음 검증된 POP 전까지 writer에게 반환되지 않는다. 반대 bank의 공개/재사용은 현재 descriptor를 변경하지 않는다. prefix 당시 empty였던 응답은 나중에 bank가 공개돼도 길이0을 유지해야 하므로 `snapshot_ready`와 `reading`,header CRC8은 남긴다. CDC mailbox와 source bank RAM도 유지한다. D5 input ACK는 SNES 최종 표시 ACK와 다르다.

독립 expected/CRC·coverage·receipt 검사,실제 read job drain 후 정확한 token/count ACK 공개,STOP freeze/reset 후 cold bank 재사용,display lease·최종 ACK·VBlank는 그대로다. production227/GBC164/saveSRAM에는 적용하지 않았다.

## 전체 회로 비용

한 번의 Quartus Lite whole MAP에서 실제338 queue/transport를 합성했다. 다른 입력 파일은336 whole MAP과 같다. queue는 기능 검증 RTL과 hash가 같고,transport는336부터 있던 `endmodule` 앞 빈 줄 하나만 정규화하면 완전히 같다. 원본 양쪽 hash와기존 차이도 검증한다.

|항목|336|338|차이|
|---|---:|---:|---:|
|LE|22256|22144|−112|
|조합 논리|17378|17274|−104|
|FF|9066|9018|−48|
|RAM bits|307808|307808|0|
|15408comb 대비 부족|1970|1866|−104|

queue own comb는285→225,source transport own은396→375다. whole 감소104를 이 두 블록만의 절감81과 같다고 하지 않는다. 동일 입력의 다른 hierarchy에도 합성 매핑 분배 변화가 있으며 전체 수치와 겹치지 않는 own 계상을 함께 저장한다. 제거한 opcode8+snapshot40비트와 전체 FF−48이 일치하지만 FF를 comb로 환산하지 않는다. 추가 latch/undriven은 없고 기존 cache_index141 latch는 남는다. FIT/STA 및 배치 가능성은 미검증이다.

|겹치지 않는 범위|338 comb|기존 설계 상한 유지|필요 순감소|
|---|---:|---:|---:|
|host|2161|1146|1015|
|독립 validator+aperture|1159|1160|−1|
|queue+SPI|798|600|198|
|source encoder+transport/mailbox|1747|1100|647|
|plan|459|297|162|
|범위 합계|6324|4303|2021|
|범위 밖|10950|10950|0|
|whole|17274|15253|2021|

범위 밖은336의10973에서23개 줄었으나 원본 입력 변경에 따른 전역 매핑 차이이며 새 삭제 블록으로 주장하지 않는다.132comb 여유를 위한 산술 상한은4326이지만 기존4303 설계 상한을 유지하면155comb 여유다. 외부23개 감소를 예산 완화에 쓰지 않으면 외부가336 값으로 돌아가도132개 여유를 보존한다. 어느 쪽도 달성 예측은 아니다. queue/SPI798+source transport/mailbox399+plan459를 모두 무료로 만드는 불가능한 가정도1656개뿐이라 현재1866개 부족에서210개가 남는다. host/source encoder의 decode·주소·데이터 경로까지 교체 범위에 들어가야 한다.

## 시간과 source·첫 BG 공급

실제 ARM336/IRQ·공유 SPI·2슬롯·staging/ROM 경합·독립 검사·표시 완료까지905–907의9개 일정을 실행했다. 세 조건 모두336/337과 전체 event timeline,ARM 호출/전송/응답,source cycles 및 실행 ELF image가 같다.338에서 새로 얻은 시간 절감은0이다.

|모델 일정|905 ms|906 ms|warm907 ms|336 대비|
|---|---:|---:|---:|---:|
|동일 시작·ROM cycle|98.617271124|117.966993470|25.051199382|0|
|제한 ROM 연속|99.244763594|116.712281254|20.689660812|0|
|일반 ROM 연속|74.552332634|50.829799126|13.410066350|0|

제한 ROM warm은60Hz까지4.022994145ms 부족하다. 첫 ROM 허용 후3.833795ms는3.180ms 예산보다0.653795ms 크다. 고정 시작과연속 일정은 다른 ROM 위상이며 서로의 시간을 절감량으로 빼지 않는다.905/906 cold 비용도 위 표와근거에 포함하며 warm 결과로 덮지 않는다. ARM text30110/BSS47404/data0/관측stack1288은 그대로다. 일반 ROM의 한 warm 결과가 예산 안이라는 사실은 제한 ROM 또는 실물 지속60fps의 증명이 아니다.

제한 연속 warm907은 source511payloadB/3blocks와 실제668wireB를 사용한다.8개 empty poll을 제외하고도 성공 D4/D5의 최소564B가 필요하다. 실제 첫 source 공개는 시작455.517µs 뒤다.8개 poll은 모두 그 전에 끝나므로 poll 점유380.952µs를 frame 이득으로 빼지 않는다. source input과첫 BG 공개시점은 이번 RTL 변경에서 움직이지 않는다.

현재 시작·전송 형식·input commit barrier에서 처리 비용을 모두0으로 해도 input ACK 하한1.746666667ms가 앞선 ROM 구간까지의1.728002082ms보다18.664585µs 늦다. 첫 E9 46B까지 포함하면166.855061µs가 부족하다. 거래 간격과 첫 E9를 고정하면55wireB 상당을 줄여야 하는 낙관적 하한이며,실제 source 공개/ARM 준비 비용은 아직 더해져야 한다. 이는 다른 시작 위상이나 새로운 protocol의 불가능 증명이 아니다.

동일 시작·ROM 위상의 경우에는 input wire 하한 뒤4.343055285ms의 여지가 있지만 실제 요청을2.291427048ms 앞당겨야 앞선 구간 끝에 도달한다. 제한 연속에서는6.650692918ms가 필요하다. 요청 시각만 빨라져도 같은 닫힌 ROM 구간에 걸리면 완료 시각은 개선되지 않는다. ROM 허용 구간 종료 도달도 필요 조건일 뿐,slot/core 경쟁과 나머지 DMA/표시 완료를 보장하지 않는다.

실제 ARM top-level 준비267357instructions/3.182821429ms 뒤에도 BG step·SPI·IRQ/응답이 남는다. input 완료→첫 ROM 요청은 제한 연속5.712ms다. source decoder는 이미 nibble CRC를 사용한다. 다음 후보는 geometry/BG 준비를 source 대기와 겹치거나 첫 완성 BG plan을 먼저 발행하는 것이다. 현재 batch sorting/15plan·240B 제한,partial BG 완료 표식과 credit/IRQ 우선을 유지해야 하며 split에 따른 추가 E9·CRC·ARM 비용도 계상한다. 실제 새 ARM 일정으로 검증하기 전 이 비용을 시간 절감으로 인정하지 않는다.

현재 warm907 source blocks는237/246/28B다. geometry 확정용 GEO10B는 마지막 block의 첫 부분이며 그 뒤는 raw record와END 합계18B뿐이다. 현재 producer는GEO 뒤에서 자동 flush하지 않는다. 단순히GEO에서 flush하면3→4blocks,추가 D4 overhead15B와거래 간격8µs로 SPI 점유가53.714286µs 증가하는 모델이다. 새 ARM prefix/CRC·polling·source 공개 시각은 이 수치 밖이다. 이는 실행한 새 일정이 아니며 frame 회귀 수치도 아니다. 마지막18B만 분리하는 것으로 수ms의 준비 중첩이 확보된다고 가정하지 않는다. geometry를 충분히 일찍 만들려면 원래68block 순회/필드 순서 또는 ARM의 검증된 입력 소비 경계까지 함께 바꿔야 한다. 첫 BG batch의 조기 발행은GEO 분할과 별도로 비교한다.

## 검증 범위와 다음 경계

선택한 증거는 `window03/fixed01/normal01`, `unit01`, `guards01`, `board01`이다.

- 9개 양성 일정에서 source·ARM·SPI 응답·plan/actual read·private receipt·최종 ACK/display 사건이336/337과 정확히 일치한다. 독립 metadata8570B/receipt754B/hash64B 비교와2슬롯 제한을 유지한다.
- 실제 구/신 queue RTL miter1428조합에서 모든 normal/typed/batch 허용 길이×양쪽 bank의 원본 byte·active record·payload가 같다. expected RAM 경계,full2slots,storage retire와consume 분리,identity 오류를 확인했다.
- 실제 D4 구/신 RTL과mailbox로 empty 응답 도중 공개,반대 bank 재사용,POP token,wrong generation/token,부분 SS,STOP 및D5를 비교했다. unit은SPI shifter를 우회한 link 입력이고CRC 입력은 고정 fixture이며,전체 공유 SPI/CRC는 위9개 통합 일정에서 검증한다. unit의42개 경고는 사용하지 않는 출력 포트 미연결뿐이다.
- 통합 fault13건:3/5/6/7/9/10/17/18/19/20/21/22/23. E1 중간STOP,조기 최종ACK,독립 검사 불일치,ROM 요청 중STOP,private RMW/CRC STOP,wrong token,누락 read,duplicate unit,범위 overflow,완료 공개 전 최종 검사 등을 포함한다. 오류 뒤RAM freeze와완료 미공개를 확인한다. 별도 aperture와raw0/최종 검사·private STOP/reset도 통과했다.
- `window01` 선언 순서 컴파일 실패,`window02` 구 queue 관측기 참조 실패,샌드박스 DLL 실행 실패와정상 compile02,whole transport의기존 빈 줄 차이를 엄격hash비교가 잡은analysis-partial01을 보존했다. 빈 줄 차이는336에도 있음을 확인하고그한줄만 정규화했으며,기능/회로 입력의 다른 차이는 허용하지 않는다.


회로는132comb 여유까지1998개가 더 필요하다. 작은 상태·주소 교체만으로 이 부족을 해소할 근거는 없다. 다음 비교는 source 공개/압축 전송·query/collector와 ARM 준비 경계,host의 descriptor 실행을 함께 묶어 실제 삭제할 decode/주소·데이터 경로를 정한다. 공통 SPI receiver,source/plan cursor,plan CRC와 이미 정렬된 source/plan RAM 주소는 재차 절감으로 계상하지 않는다. 새 CDC·RAM 포트 중재·취소 상태도 전체 예산에 넣는다.

시간은 actual M4 instruction/CPI1/84MHz 모델과 기존 source decoder 계측 재생,IRQ24cycle/PB8 foreground checkpoint를 포함한다. 기존325의536B ordinary65816 trace를 재사용하며 tile/map은 DMA 허용 상태의 C/버스 모델이다. 전체65816 polling/dispatch,새71 fullRUN,물리 ARM WCET,whole FIT/STA와 실물 지속60fps를 증명하지 않는다. 초기 compile/관측기 실패와 모든 원시 결과를 보존한다.
