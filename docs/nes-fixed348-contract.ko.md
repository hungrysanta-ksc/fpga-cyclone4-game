# NES348 — fixed-block 압축과 host·queue·plan 분리 구현

**선택 구현은 338 RTL·336 ARM을 유지한다.** A 압축과 B 공동 제어를 각각 실제로 구현했다. A는 전송량과 일반 ROM 시간을 줄였지만 제한 ROM warm 시간을 줄이지 못했고, B의 연속 일정상 작은 감소는 시작 위상 효과였다. 전체 comb는 각각46개/3개 늘었다. 두 후보를 합친 회로·시간은 측정하지 않았으며 독립 결과를 더해 결합 이득으로 주장하지 않는다.

현재 선택 기준의 **4.022994145ms 초과 /1,866comb 부족은 그대로**다. MAP·양성 일정·오류 주입 검사를 완료했다.

## A: 기존 fixed-block scan을 재사용한 nonmap 압축

338 source에347 N5v4를 연결했다. map MASK·좌우 SHIFT와 기존 block 순서를 유지하고 nonmap/raw block 전체의 repeat8/16을 기존 edge0/edge1 및 left_row/right_row로 판정한다. row_size·diff_count·history도 재사용한다. 반복 record가 기존 MASK보다 짧을 때만 선택한다.

344의 연속 record builder로 MASK/SHIFT/REPEAT 최종 출력을 통일해 기존 MASK 출력 주소 threshold/subtraction과 SHIFT byte 출력 mux를 대체했다. query·history·CRC·mask_pending RAM 쓰기는 유지한다. raw 시작에서는 재사용하는 비교 flags를 다시 초기화한다. 새 반복 비교와 선택 mux는 추가 비용으로 계상했다.

ARM은336 batching·sorted membership·full COMMIT을 유지하고 decoder만 교체했다.340/346의 OBJ-after-GEO bitmap 대응이나 추가 BG prefix를 가져오지 않았다. 실제 입력 bank가 SPI를 통과한 checkpoint에서 같은 M4가 decode/준비하며 실행 명령 비용을 계상한다. 전체 text30110→30206B(+96),BSS47404/data0/관측 stack1288은 같다.

새 RTL의905–907 source records는347의 독립 encoder와 byte 단위로 일치한다. warm907 성공 source wire는564→189B,3→1bank다.347의71프레임/348610B M4 codec 결과는 같은 decoder 코드의 선행 증거이며 이번 새 RTL을71프레임 실행한 것으로 확대하지 않는다.

## B: host·queue·plan 공동 제어 교체

source와ARM은338/336 그대로 두고 다음 경로를 교체했다.

- E1 ingress_length312 16bit를 삭제하고 SPI request_length280의 command 문맥을 공유한다. 길이·CRC·정확한 transaction 종료 검사는 SPI commit 판정에 남겼다. SS 종료 후 handoff 수명과 D4/D5/E9/EA 의미는 유지한다.
- queue·plan endpoint의 중복 SS/bit-edge 조건을 공통 byte_event/commit event로 대체했다. admission·fault·accepted/retired/consumed/retire 상태는 각각의 수명 의미대로 유지한다.
- host PUT/EXPAND와 metadata MISSUE/MWAIT/MNEXT의 목적지 실행을 공통 ISSUE/WAIT/NEXT로 교체했다. expected RAM grant 이전에는 write/cursor가 진행하지 않는다. metadata cursor와 expanded cursor 저장을 공유하되 encoded 위치·codec 검사는 남긴다.
- E9 wire 형식·CRC·길이·plan 수를 유지하면서 host ingress가 plan을 기존512B bank의32B slot에 직접 정규화한다. 첫 byte와31개 기본값을 쓰고 packed 필드를 최종 주소에 기록한다. 수신이 끝난 뒤 in-place 확장해 아직 읽지 않은 데이터를 덮어쓰지 않는다.
- NES의 shortform/가변 length register,popcount 길이 계산,빈 alt mask 순회를 삭제했다. 고정32B를 읽고 모든 필드를 검사한다. 대신 host의 hat/hlen/short/mask/alt selector/clear 진행과 seal 검사가 추가됐다. 이 이동 비용도 전체 합성에 포함한다.

마지막 plan CHECK에서 mailbox를 반환하는 경계와 tile_done까지 decoded fields를 보유하는 방식은 유지한다. RAM을 live로 읽으면서 bank만 조기 재사용하는 변경은 하지 않았다. normalized 길이는 mailbox로 전달하고 원래 wire 길이는 host seal 검사에 사용한다. STOP은 clear·payload write·pending publish를 취소한다. byte당256host cycle의 실제 driver에서 초기화·정규화 수락을 검사했다.

347의40B gap checked-header 후보는 적용하지 않았다. active-record HLOAD/HCHECK와 동시 incoming/active header 소유권은 남아 있다. 이를 완전히 삭제한 단일 FSM이나1,374comb 회수로 표현하지 않는다.

## 실제 전체 일정

|일정|프레임|338 기준 ms|A 압축 ms|B 공동 제어 ms|
|---|---:|---:|---:|---:|
|제한 ROM 연속|905|99.244763594|84.796118798|99.265672434|
|제한 ROM 연속|906|116.712281254|114.916120990|116.700872300|
|제한 ROM 연속|907|20.689660812|20.691024432|20.685479044|
|동일 시작·ROM 위상|905|98.617271124|84.168626328|98.638179964|
|동일 시작·ROM 위상|906|117.966993470|117.966993470|117.977038804|
|동일 시작·ROM 위상|907|25.051199382|25.051199382|25.056517500|
|일반 ROM 연속|905|74.552332634|65.013628918|74.557605298|
|일반 ROM 연속|906|50.829799126|50.170943396|50.835071790|
|일반 ROM 연속|907|13.410066350|12.113127368|13.415384468|

M4 명령 실행과 SPI·IRQ·2슬롯·staging·ROM 경쟁을 포함한6일정/18관측이며 고유 기록 프레임은3개다. 동일 위상 일정은 각 프레임의 시작 시각과 ROM cycle을338 기준과 일치시켜 비교했다. cold와 warm을 합쳐 평균 FPS로 판단하지 않는다.

A의 고정 warm907 첫 ROM 요청은8.381149→7.085119ms로1.296030ms 빨라졌다. 하지만 이전 허용창 종료6.089722ms보다 **0.995397ms 늦어** 동일한21.217995ms 허용 시각을 기다렸다. 전체25.051199382ms와 ROM 후3.833249ms는 그대로다.347의 wire+decoder 직렬 proxy1.375738ms를 전체 실측 이득으로 차감하지 않는다. 일반 ROM warm의1.296938982ms 개선은 확인됐지만 제한 ROM 개선과 구분한다.

B의 제한 연속 warm은4.182µs 작지만 시작이9.500µs 늦었다. 같은 시작·ROM 위상과 일반 ROM에서는 모두 **5.318µs 느리다**. 고정 위상 첫 요청도8.386058ms로4.909µs 늦어졌다. 첫 clear(3B)와 BG(7B)를 각각32B로 읽으면54B가 추가되고,READ/CAPTURE 2NES클록씩108클록(약4.909µs)이 늘어난다. 관측된 첫 요청 지연과 일치한다. 내부 plan read와 진행 응답 비용을 제외하면 얻을 수 있는 잘못된 절감이다. 실제 warm 출력 SPI는1091→1105B로14B 응답이 추가됐다.

## 전체 Quartus Lite 비용

|whole MAP|338|A 압축|B 공동 제어|
|---|---:|---:|---:|
|LE|22144|22186|22133|
|comb|17274|17320|17277|
|FF|9018|9021|8994|
|RAM bits|307808|307808|307808|
|15408 대비comb 부족|1866|1912|1869|

A source encoder own comb는1348→1394다. flags/seed를 재사용해도 반복 선택·출력 제어가 늘었다. B의 겹치지 않는 own 비용은 host2161→2132(−29),queue225→199(−26),SPI573→599(+26),plan transport348→371(+23),endpoint88동일이다. mailbox 등 하위 비용과 범위 밖 매핑 변화까지 포함하면 전체+3이다. parent inclusive 값과 child 값을 중복 합산하지 않는다.

B의FF−24에는 정규화 길이가 plan 수로 결정되면서 합성에서 줄어든 mailbox의 중복 길이 저장도 포함된다. CDC/mailbox 자체를 없앤 것은 아니다. FF−24/LE−11을 comb 부족 해결로 해석하지 않는다. RAM도 늘지 않았지만 이는 FIT/LAB/M9K 배치·STA 통과를 의미하지 않는다.

최종 MAP은 실제 일정에 사용한 source/queue/SPI/plan RTL hash와 연결했다. 보드 host의 tile_closed267 관측 포트 차이는 기존 방법으로만 정규화해 비교한다. 신규 undriven/latch는 없고 기존 cache_index141 latch는 유지된다. Standard나 FIT/STA 반복은 하지 않았다.

## 검사와 판정 범위

- 각 양성 일정의 source byte/CRC,336 E1/E9 packet·batch 순서,독립 actual-read unit→private receipt→정확한 token 공개를 재검증했다. max credit은2다. 기존 최종 ACK·display lease·VBlank 조건도 유지한다.
- A 인공4프레임:MASK,좌SHIFT,우SHIFT,repeat8/16,unchanged,stall,SHIFT/REPEAT build STOP PASS.
- B 기록196plan+256alt mask의512plan=708개:구·신 출력 필드 exact,dual clock,소비 stall,256host cycle ingress,clear 중 STOP PASS. 잘못된kind/tag/slot/format,잘린payload,trailing byte,alt 길이 오류8종도 구·신 모두 거부했다.
- 실제 M4:BG seal만으로 실행/commit 불가,STOP 취소,raw copy 시 sorted membership 유지,누락 membership 거부4건 PASS.
- 실제 통합 오류 주입은 B12건/A3건,합계15회 PASS. plan read·E1/E9 부분 수신·ROM/expected RAM/private CRC 중 STOP,이른 최종ACK,독립 불일치,잘못된token,조기 최종scan,공유 E1 길이 오류를 검사했다. aperture/raw0·private STOP/reset 검사도 통과했다.

기존 expected 저장과 실제 SNES read CRC·coverage·private job·최종 scan을 producer progress로 대체하지 않았다. 저장 credit과 소비 완료는 별도이며 각 클록의 CDC/lease/generation/token 수명을 유지한다.

시간은 CPI1/84MHz·IRQ 할당 모델이다. 기존325의 ordinary65816 bus trace와 C map/tile 소비 모델을 재사용했다. 전체 firmware RUN,실물 ARM WCET,전체65816 실행·화면,physical60fps,FIT/STA 증명은 아니다.

초기 한글 경로 Questa DB 오류,plan 선언 순서,unit fixture의 최종 END 누락,추가 STOP bench 선언 순서 오류를 보존했다. 최종 END 누락은 구·신 모두 정상 거부한 fixture 오류였다. 같은 Quartus 비용이었던 intermediate map-control01 대신 최종 Questa와 hash가 맞는 map-control02를 사용한다. 추가 E1 길이 오류(29)는51B transaction의15번째byte에서 주입한 뒤100µs만 기다려 종료 전에 실패했다. 남은 wire 하한109.714µs를 확인하고29만1ms 제한·SS 종료 확인으로 재실행해 통과했다. guards01 원래 suite 실패와11개 완료 사례를 구분해 보존했고,guards02와의TB차이가29에만 적용됨을 분석에서 확인했다. 라이선스 오류는 없었다.

## 다음 경계

A는 이전 ROM 창까지 첫 요청을0.995397ms 더 앞당겨야 하며,이는 필요조건이지 전체 시간의 확정 상한은 아니다. ROM 후3.180ms 예산까지도0.653249ms가 더 필요하다. 전체 comb15,253 상한까지는 A2,067개/B2,024개 순감소가 필요하며 달성 전망이 아니다. 이번처럼 endpoint·계산 위치만 옮기는 후보를 결합해 이 부족이 해결됐다고 가정하지 않는다.

새 후보는 아직 남은 active-record/header 실행과 공유 RAM 포트 경계를 실제로 삭제할 수 있는지 먼저 제시해야 한다. 그에 따른 admission·불변 header·검사·port stall 비용을 포함한 근거가 없으면 추가 구현이나 FIT 반복으로 진행하지 않는다. production227/GBC164/saveSRAM은 변경하지 않으며 자동 merge는 하지 않는다.

증거: `analysis/fixed348-verification.json`; 재현: `tools/analyze_nes_fixed348.py`; 원본 로그/RTL/ELF: `probes/nes-fixed348/`.

최종 분석은 기준466개 증거를 재해시하고 총2197개 pin을 고정했다. 개발계획은 지정5필드만 변경했다.
