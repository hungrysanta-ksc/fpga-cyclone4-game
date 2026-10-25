# NES342 실제 ARM BG frontier·host reader 공유·단일 source 삭제 후보

## 판정과 경계

선택 구현은 **338 RTL·336 ARM 유지**다. frontier를 실제 M4에 연결하고338 RTL에서 출력 순서와 일정을 분리 검증했다. 별도 host 후보는 source338을 유지하며 공통 queue reader·주소 진행 저장을 교체했다. source 후보는 MASK/SHIFT를 제거한 단일 run 생성기를 구현했으나71개 실제 M4 decoder 전송에서 큰 회귀가 나와 전체 RTL 일정 전에 제외했다. source의 whole MAP은 진단 결과이며 동작 동등성 증명이 아니다.

## 실제 ARM frontier

기존 used bitmap을 읽고 가장 낮은 미사용 BG slot을 유지한다. 한 번에 최대8개 검사하며, 정렬된 pending prefix의 key가 이 경계보다 작을 때만 한 프레임에 한 번 공개한다. clear만 있으면 공개하지 않는다. 기존 batch의 byte/plan 용량을 예약하므로 후속15plan/240B·OBJ 정렬 경계를 보존한다. 첫 prefix는 실제 prefill·SPI·credit 경로로 전달한다. COMMITTED 이전 공개 금지, STOP/fault 취소와 generation별 초기화는 유지한다.

warm907의 첫 pending plan은slot82..86이다. 실제 실행에서 frontier는 처음1→3으로 진행하고 마지막까지 **8에 머물렀다**. 총28회 호출/35개 bit 검사로 prefix0회였다. slot8이 미사용인 이상 후속 더 낮은 slot 가능성을 배제할 수 없으므로 발행하지 않은 것이 맞다. warm 첫 E9는46B 그대로다. 함수비용3092명령=36.809524µs(CPI1/84MHz)이며 IRQ 비용은 실제 일정에 따로 포함된다. 첫 ROM 요청은 기준보다42.272µs 늦었지만 제한/고정 위상에서는 같은 허용 구간을 기다려 총 시간이 같았다.

cold905/906에서는 clear+slot1/2의25B prefix가 발행됐다. 341의18B 가정과 다르며 이것을 강제로18B로 만들지 않았다. 제한905 첫 BG 요청은2.187610ms 빨라졌지만 실제 accept는 같았다. OBJ 첫 요청은65.011061→80.476102ms로 늦어졌고, 첫 accept는79.979927→80.476284ms였다. 실제 ROM 허용 뒤 tail이1.551754ms 늘었다. 첫 요청만의 개선으로 전체 이득을 주장하지 않는다. 정확한 E1 material/DMA·plan 순서는 유지된다.

M4 text30586B(기준+476),data4B(+4),BSS47412B(+8),관측stack1288B(동일)다. 새 상태는 frontier/prefix/check 계수12B이며 마지막 계수는 계측용이다. 검사 비용을 제거한 가상 결과로 실제 일정을 대체하지 않는다.

| 일정 |905 ms|906 ms|907 ms|warm338 대비|
|---|---:|---:|---:|---:|
|동일 시작·ROM 위상|100.169025230|117.966993470|25.051199382|+0.000000000ms|
|제한 ROM 연속|100.796517700|115.160527148|20.689660812|+0.000000000ms|
|정상 ROM 연속|74.787875262|51.007615174|13.452338570|+0.042272220ms|
|host교체+제한 연속|100.796517700|115.160527148|20.689660812|+0.000000000ms|

고정 위상 warm에서 첫 frontier 검사는 source 시작6.294800429ms 뒤, 마지막 검사는8.190621952ms 뒤, 첫 E9 전송은8.274348ms 뒤였다. 첫 ROM 요청은8.423421ms 뒤다. 따라서 frontier 조건을 해결하는 것 외에 첫 검사 전 준비 비용도 줄여야 한다. 선행 prefix 확정 시각은 이 warm에서 존재하지 않는다.

연속906의 감소가905 증가와 상쇄되는 경우는 시작 위상 효과다. 고정 시작·ROM cycle을 별도로 유지해 비교한다. 시간은 기존CPI1/84MHz·IRQ 모델이며 D4 입력 비용은 기존 측정 재생, tile/map은 C/DMA bus 모델, ordinary는 기존536B65816 trace다. 전체 firmware RUN·전체65816 polling/dispatch·물리 WCET는 아니다.

## host 교체

338 source·독립 validator는 유지한다. host의 별도 batch cursor를 parser_address로 대체하고, metadata run_left는 기존 byte counter at을 사용한다. metadata manifest_byte/zero 진행은 상호 배타적인 DMA expanded/zero 저장을 사용한다. MREAD/MCAP를 PREAD/PCAP로 합쳐 실제 queue read 포트의 중복 상태·선택을 제거했다.

모든 실행 제어를 없앤 것은 아니다. metadata MNEXT/MISSUE/MWAIT와 DMA PUT/EXPAND의 destination 수락 경로는 남는다. expected RAM·staging 소유권과 실제 read CRC/coverage·private receipt job·drain 후 token ACK는 별도다. 남아 있는 이 진행·주소 선택 비용을 새 공통 실행기로 이미 삭제했다고 세지 않는다.

hostwindow02의905..907은 frontier-only window01과 **전체 이벤트 CSV·ARM 전송/명령·source cycles가 정확히 같다**. 실제 읽기 주소16+index와 encoded 길이를 검사해 본문을 한 번만 소비하는 것을 확인했다. 고정/정상 일정9개는338 RTL에서의 frontier 검증이며 host 교체 자체는 제한 연속3개에서만 실행했다. 두 범위를 합쳐9개 host 실행으로 주장하지 않는다.

## 단일 source 후보의 실패

N5v4 공통 region run 경로를 구현했다. map MASK 저장·출력 재순회, SHIFT 검출·edge/history, mask 쓰기 pending arbitration과 별도 주소 선택을 제거했다. 기존64B literal scratch와 repeat8/raster repeat16 생성, 영역별 query/base cursor, source CRC·bank 전송은 남는다. map을 같은 run 경로에 넣기 위해 offset을12bit로 확장했다. input/output RAM의 물리 포트나 CDC를 공짜 통합하지 않았다.

실제 Cortex-M4 decoder71프레임348610B를 정확 복원했고16개 잘못된 입력·sticky failure/cold recovery를 거부/복구했다. 하지만 성공 source wire는 **52113→104017B**로 늘었다. cold9053039B/906332B/warm907206B만 보면 좋아 보이지만21프레임 회귀, 최대960의3379B는 wire만10.297905ms 추가다. 단순한71개 합계나 첫3프레임으로 전체60fps를 판정하면 안 된다.

추가 wire가 곧 같은 크기의 frame 회귀라는 뜻은 아니며, 이 후보의 모든 프레임60fps 불가능성을 증명한 것도 아니다. 기존 상한에 맞지 않는 큰 전송 회귀 때문에 통합 우선순위에서 제외했다.

따라서 이 source 후보는 전체 ARM·IRQ·2슬롯·ROM 일정에 채택하지 않았다. 전체 RTL 동작 검증·STOP/최종 ACK 증거를 이 후보로 전이하지 않는다. 아래 비용은 올바른12bit offset 소스의 whole synthesis 진단이다. map SHIFT를 포기하는 후보는 다음 구현으로 확대하지 않는다. 복잡한 압축 경로를 삭제했어도 region/run/address mux 비용이 절감분을 소비했다.

## Quartus Lite 전체 비용

| whole MAP |338|host 교체|단일source+host(진단)|
|---|---:|---:|---:|
|LE|22144|22142|22139|
|comb|17274|17272|17304|
|FF|9018|8989|8934|
|RAM bits|307808|307808|307808|
|15408comb 대비 부족|1866|1864|1896|

host는 whole−2comb/−29FF, source+host는+30comb/−84FF다. parent/child 포함 값을 더해 절감으로 과장하지 않는다. host 자체2161은 host-only 결과에서도2161이며 source 자체는1348→1351의 전역 매핑 변화가 있다. source+host source 자체1380/host2160도 전체와 구분한다. 현재2021comb 순감소 목표에 접근했다고 볼 수 없다. RAM 절감도 없다.

sourcehostmap01은 map 영역이2048byte를 넘는데 기존11bit offset을 남긴 오류가 있어 제외했다.12bit로 수정한02만 비교에 사용한다. 실패01과 샌드박스 DLL 오류로 컴파일 전에 중단한codec01은 보존한다. 동일 입력의 seed/FIT 반복은 하지 않았다. 새 undriven/latch는 없고 기존 cache_index141 latch는 유지된다. source state와 host state/owner/tap_state는 두 최종 MAP에서 모두 FSM으로 추출됐다. 이번 비용 실패를 FSM 추출 실패로 설명하지 않는다. FIT/STA는 하지 않았다.

## 안전 검사와 증거 범위

실제 M4 frontier guard8건은 낮은 빈slot,8검사 분할,임의slot12 발행,예약 용량,중복 공개 금지,STOP,PREPARED/fault 공개 금지,clear-only를 검사했다. 이 guard의 prefill만 stub이며 실제 SPI/credit은 통합 일정에서 검사한다. 입력/native9880B와 resident6016B layout을 실제 ELF API로 확인했다.

통합12개 일정(338 RTL frontier9 + host교체3), RTL 오류 주입8건(1/3/5/6/7/18/20/23), 별도 aperture/final-raw0가 통과했다. 실제 read 완료 unit과 독립 validator unit, private RAM write 뒤 정확한 token/count 공개,2슬롯 credit,최종 ACK·VBlank 경계를 비교했다. hostwindow01은 MREAD가 PREAD의 별칭이 된 것을 반영하지 못한 상태명 기반 관측기 실패다. 실제 읽기 주소/수량 검사로 교체한02를 사용하며01은 보존한다. guards01은 삭제한 manifest_byte313을 참조해 elaboration에서 중단했다. 실제 공유 expanded325[8:0]를 관측한guards02만 최종 판정에 사용한다. 이 검증은 source338에 대한 것이며 제외된 단일 source RTL로 전이하지 않는다.

production227/GBC164/saveSRAM은 그대로다. 새 후보의 물리60fps·fullRUN·전체65816·FIT/STA는 미검증이다.

## 다음 판단

341의 낮은 미사용 slot 경계는 안전하지만 일반 warm을 앞당길 충분조건이 아니었다. 같은 정렬을 고집한 채 bitmap scan만 더 빠르게 만드는 작업은 우선하지 않는다. 다음은 서로 다른 slot 쓰기의 순서 교환을 허용할 수 있는지 실제 SNES DMA·staging·receipt·BG 완료 조건으로 별도 증명하거나, 낮은 slot의 향후 사용 여부를 확정하는 비용을 측정해야 한다. parser에 단조성 검사가 없다는 이유만으로 순서 변경을 허용하지 않는다.

source는 map SHIFT의 효과를 보존하면서 공통 record emitter·scratch/address 경로를 교체해야 한다. host는 이번에 남은 두 destination 진행 경로를 함께 없애야 하며, 독립 expected/actual 검사를 공유 완료 카운터로 대체해서는 안 된다. 부분 FF 감소나 first-request 시각을 전체 비용의 성공으로 취급하지 않는다. 이번 후보를 채택하거나 자동 merge하지 않는다.
