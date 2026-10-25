# NES343 — BG 공급 순서와 압축 데이터 경로 교체 예산

338 RTL·336 ARM을 유지한다. 이번 단계는 실제 코드 감사, 기록된 plan의 순서 모델, 71프레임 압축 길이·map 복원 비교다. 새 ARM 실행·RTL 시뮬레이션·Quartus 합성은 수행하지 않았다. 기존 증거 1,268파일을 재해시했다. 재현 도구는 `tools/analyze_nes_order343.py`, 결과는 `analysis/order343-verification.json`이다.

## 유지하는 실측 기준

| 항목 | 선택된 338 RTL·336 ARM |
|---|---:|
| 제한 ROM 연속 일정 warm907 | 20.689660812 ms |
| 60Hz 대비 부족 | 4.022994145 ms |
| 동일 시작·ROM 위상 warm907 | 25.051199382 ms |
| 일반 ROM 연속 일정 warm907 | 13.410066350 ms |
| whole Quartus Lite | 22,144 LE / 17,274 comb / 9,018 FF / 307,808 RAM bits |
| 조합 논리 부족 | 1,866 |

342의 shared reader는 whole −2 comb에 그쳤고 source 단순화는 압축을 잃었다. 두 후보 모두 선택하지 않았다. 이번 모델의 신규 실측 시간·면적 이득은 0이다. MAP은 FIT·STA·물리 60fps 증명이 아니며 production227/GBC164/saveSRAM을 변경하지 않는다.

## 순서 변경: 다른 slot이라는 이유만으로 안전하지 않다

실제 resident allocator는 같은 프레임에 used slot을 퇴거하지 않으며 exact-key 중복은 재발행하지 않는다. 그러나 낮은 미사용 slot은 나중에 새로 할당될 수 있다. 따라서 최저 미사용 slot을 기다리는342 방식 대신, **이미 완성된 서로 겹치지 않는 BG 목적지의 쓰기 순서 교환**을 검증할 수 있다.

허용 단위는 완전한 BG record, 우선적으로 연속 slot 묶음이다. full input COMMIT 뒤 clear0을 먼저 유지하고 BG 부분 완료 표식보다 앞에서만 이동한다. OBJ·최종 종료 경계를 넘지 않는다. bank/generation/epoch/kind와 실제 byte 범위로 비중첩을 확인한다. 부분 tile·같은 물리 목적지·변경 가능한 CHR 문맥은 교환 대상이 아니다. lease와 CHR mapping이 고정되어야 한다.

Token과 sequence는 바뀐 **실제 제출 순서**로 배정하고 packet CRC를 다시 계산한다. 예전 token을 slot과 함께 이동하지 않는다. 새 chunk의 시작 slot·길이에 맞춰 DMA descriptor를 만든다. 독립 expected는 목적지와 내용으로 유지하고 실제 read CRC·coverage로 receipt를 확정한다. plan queue가 비었다는 이유로 최종 ACK를 내지 않는다. STOP은 대기 plan과 speculative generation을 취소하고 visible bank는 VBlank·최종 검사까지 바꾸지 않는다.

기록된 완성 plan 905/906/907에서 각각81/81/5개 BG record, 합계167개를 clear 뒤로 하나씩 이동했다. symbolic 목적지 footprint는 동일했고 중복 clear는 거부했다. **새 발견 순서·ready 시각·RTL/PPU 결과를 검증한 것은 아니다.** 실제 ARM callback 이전의 준비 시각은 아직 미계측이다.

| 프레임 | 기존 전체 chunk | 단일 BG 선행 시 최대 추가 chunk |
|---|---:|---:|
|905|2|3|
|906|10|3|
|907|3|2|

실제 C와 FPGA tile producer 모두 같은 kind·다음 연속 slot·2KiB 이내에서만 합친다. 중간 slot을 먼저 보내면 기존 run을 분할한다. E9 packet 경계만으로 chunk가 닫히지는 않는다. ROM fetch가 빨라도 gap이나 BG 표식까지 staging chunk 공개가 늦을 수 있다. ROM 요청, ROM 승인, chunk seal, DMA 완료, receipt, 최종 ACK를 각각 계측해야 한다.

실제907 E1 op7은23 wireB다. 추가 chunk당 최소70.095238µs의 명령 wire 점유가 생긴다. warm +2는140.190476µs, cold +3은210.285714µs이며 ARM·SPI gap·SNES setup·IRQ/poll·receipt·staging 경쟁은 별도다. 이를 프레임 시간이나 ROM 이전 여유에서 무조건 빼는 것도 부정확하다.

첫 구현은 프레임당 **준비된 연속 run 하나**의 이동으로 제한한다. 추가 chunk0을 우선하고 +1은 전체 일정 이득이 실측될 때만 허용한다. warm82..86 전체 run이 언제 준비되는지는 아직 모르므로 선행 가능성을 보장하지 않는다. BG 부분 완료에 새로운 전체 DMA drain barrier를 추가하지 않는다. 기존 부분 완료와 프레임 종료 의미를 유지한다.

## SHIFT 보존만으로는 충분하지 않다

SHIFT는 유지하고 map MASK를 byte run으로 바꾸며 nonmap340 압축을 유지한 길이 모델을 비교했다. 71개 map을 독립 복원했지만 새 ABI의 count/CRC/ARM/RTL은 구현하지 않았다. trailer 길이만 고정하여 계산한 **길이 모델**이다.

| 71프레임 성공 전송 wire | 합계 |
|---|---:|
|338 기준|52,113 B|
|기존 실제340 codec|32,236 B|
|343 SHIFT+run 길이 모델|40,916 B|

343 모델은11프레임(909/922/925/931/938/941/954/957/963/970/973)에서 회귀한다. 최대954의 +896B는 wire만2.730667ms다. 프레임 시간 회귀로 측정한 값은 아니다. 따라서 MASK 제거를 요구했던341 예산은 수정한다. **map MASK·SHIFT 효율을 함께 보존**한다.

후보 A는 wire-identical338 contiguous record builder다. 기존 phase RAM 안에 header/mask 위치를 예약하고 바뀐 값을 최종 record 위치에 쓴다. SHIFT는4B record로 만든다. 공통 출력기는 record_base+read_cursor만 순회한다. 삭제 대상은 MASK 출력 주소 threshold/subtraction, MASK/SHIFT 출력 byte mux, 재배치 scratch 순회다. SHIFT 비교·history·cold/edge 검사, mask 계산, query·CRC·port 지연은 유지한다.

기록된338/340 최대 record는76B이므로128B 예약은 기존512B phase 할당 안에서 산술상 가능하다. 실제 수명 충돌·read/write 포트·M9K packing 증명은 남는다. mask와 value 동시 갱신을 무료로 취급하지 않는다. 직렬화 뒤 확정되는 CRC trailer는 별도2B select를 유지하거나 RAM patch/read 비용을 계상해야 한다. A는 wire564B를 그대로 유지하므로 제한 ROM 이전 창을 혼자 해결하지 못한다.

후보 B는 A에340의 bounded nonmap 반복 압축을 결합하되, 독립 encoder/출력기를 추가하지 않는 방식이다. 하나의 build cursor/length·최종 record buffer·순차 출력기를 사용한다. 실제340의 warm206B는 참고치일 뿐 새 회로·일정 예측이 아니다. 형식별 판단·seed·region 제어는 여전히 필요하다. 먼저 A로 byte 동일성과 실제 삭제를 분리 검증한 뒤 B를 평가한다. 16bit 포트로 scan 시간이 자동 반감된다고 가정하지 않는다.

## host와 source의 실제 삭제 경계

342는 PREAD/PCAP reader와 저장을 공유했지만 ordinary PUT/EXPAND 및 metadata MNEXT/MISSUE/MWAIT 목적지 진행은 남았다. 다음 host 후보는 checked active record에서 destination class/base/span/encoded_end/seed_width를 사용하여 **accepted-byte 진행 하나**로 literal/repeat2/repeat4/zero와 metadata dense/RLE를 실행한다. 공통 ISSUE/WAIT/ADVANCE에서 cursor·remaining을 갱신하고 기존 두 목적지 진행 경로를 삭제한다. 이미 존재하는 active record를 다시 신규 절감으로 세지 않는다.

Staging backpressure, expected RAM write latency, H2 prefix 처리는 sink adapter 비용으로 남긴다. validator의 독립 cursor·실제 read CRC/coverage·private job·최종 scan을 producer 진행으로 대체하지 않는다. host와 validator는 host_clk지만 source encoder는 NES clk다. 전역 단일 실행기나 CDC 제거를 무료로 가정할 수 없다. 2슬롯 저장 credit은 실제 소비·receipt와 계속 분리한다.

## 회로 예산: 실측 예측이 아닌 채택 상한

| 동일 경계 comb |338 현재|상한|필요 감소|
|---|---:|---:|---:|
|host|2161|1146|1015|
|validator/aperture|1159|1160|-1|
|queue/SPI|798|600|198|
|source|1747|1100|647|
|plan|459|297|162|
|교체 범위|6324|4303|2021|
|외부 유지|10950|10950|0|
|whole|17274|15253|2021|

whole 상한은155 comb 여유를 목표로 한다. source transport/mailbox399를 유지하면 encoder 상한701이다. 338 encoder1348 대비647, 340 encoder1668 대비967 감소가 필요하며 **달성 근거는 아직 없다**. queue/SPI·plan360 감소도 무료가 아니다. 이 두 블록이 그대로면 다른 상한을 만족해도 whole15613으로205 부족하다. 레지스터 감소나 부모·자식 MAP 수치 중복 합산을 회로 여유로 보고하지 않는다.

## 시간 예산과 다음 검증

기준 wire에18B prefix만 더해도 이전 ROM 창을81.522µs 놓치고46B는166.855µs 놓친다. 따라서 BG 순서만 바꾸어 해결된다고 볼 수 없다. 조건부206B·1bank 전송에 대한 비전송 작업 허용치는 prefix18/25/46B에서 각각1.025526/1.004193/0.940193ms다. 기존1ms 예산은46B에서59.807µs 초과한다.

초기 채택 상한을 비전송0.900ms(source0.350/decode0.100/첫BG준비0.250/refill0.100/IRQ·poll·CDC0.100)로 둔다. 46B 조건에서40.193µs만 남는다. 이는 전망이 아닌 실패 판정 기준이다. 기존 scan 약0.446ms와342 첫 검사6.294800ms 때문에 실현성은 미확정이며 종이 예산을 낮추는 것으로 해결하지 않는다. post-ROM 상한3.180ms 안에 추가 chunk·DMA·receipt를 포함한다. 제한 연속 일정에서 이전 ROM 창 확보에 해당하는3.369199ms와 tail0.653795ms를 함께 줄여야 한다.

다음 실행은 callback/run-ready부터 ROM 승인·chunk seal·DMA/receipt까지 계측한다. 338/336 동일 시작·ROM 위상 비교와905→906→907 연속 일정, 일반/제한 ROM을 분리한다. cold·11개 wire 회귀 프레임·중복slot·used hit·세대재사용·2slot full·STOP 각단계·BG완료후늦은BG·최종ACK 조기요청·VBlank를 검사한다. 의도적으로 순서를 바꾸므로 기존 E1 바이트 순서 동일성 대신 독립 목적지 내용/coverage·token binding·최종 표시를 비교하되 검사를 약화하지 않는다.

기능·일정 근거를 확보한 후보만 동일 경계 whole Quartus Lite 한 번으로 평가한다. 새 시간과 회로 비용이 함께 개선되지 않으면338/336을 유지한다. FIT/STA·full firmware RUN·물리 지속60fps는 이번 단계의 완료 주장에 포함하지 않는다.
