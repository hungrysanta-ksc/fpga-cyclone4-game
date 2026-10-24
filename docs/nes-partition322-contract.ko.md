# NES322 — 319 기준 ARM/FPGA 역할과 descriptor 형식 재검토

319를 비교 기준으로 유지한다. 321의 실행기 통합은 실제 전체 MAP에서266comb 증가했고 제한 ROM 시간도 그대로였다. 따라서 다음 후보는 상태 번호나 반환 제어 공유가 아니라 **전송 descriptor의 표현과 주소 datapath를 함께 교체**하는 것이다. 이번 결과는 기존 실제 ARM 전송9건(3프레임×제한/정상/고정 위상)의 재분석이며 새 ARM 실행·RTL·Quartus 합성 결과가 아니다.

## 실제 전송으로 비교한 후보

`tools/analyze_nes_partition322.py`가 실제 E1 길이와 각 batch의 descriptor/payload 끝 위치를 검사하고, 입력 해시와 결과를 `analysis/partition322-verification.json`에 저장한다. 고정/정상/제한 일정의 아래 개수는 동일하다. 바이트는 E1 명령·16B header·2B CRC를 포함하며 응답 polling·CS 시간은 포함하지 않는다.

| 후보 비용 | cold905 | cold906 | warm907 |
|---|---:|---:|---:|
| 현재 manifest wire bytes / 패킷 |397 /4|397 /4|106 /2|
| requirements190B+map256B를 dense로 재포장 |503 /3|503 /3|503 /3|
| 증가 wire bytes |106|106|397|
| ordinary/tile descriptor 수 |31|39|9|
| 기존 descriptor에 receipt first/end 4B 추가 |124B|156B|36B|
| section5의1121/3169 경계 횡단 수 |1|1|0|
| map batch / 범위 수 |22 /64|22 /64|1 /7|

dense는 payload240B 상한으로 map을2패킷에 재포장하는 가정이다. 실제 ARM은 cold에서 map3패킷을 사용하므로 패킷 수는 줄지만 바이트는 증가한다. 새로운 분할의 ARM 준비·IRQ·credit 대기는 측정하지 않았다. warm에서는 특히397B와 추가 패킷의 비용을 감수하고 RLE decoder만 없애는 방향이 불리하다. wire 차이를 SPI 비트율R로 환산한 순수 직렬 시간은 `8×증가B/R`이며 이것을 프레임 증가 시간으로 바로 더할 수 없다. ROM 대기와 겹치는 부분, DMA/plan과 경쟁하는 부분이 다르다.

receipt 필드를 추가하고 FPGA에서 원래 주소로 다시 계산하면 datapath가 삭제되지 않는다. 반대로 ARM 제공 receipt만 믿으면 잘못된 DMA 주소를 정상 receipt로 위장할 수 있다. 이 방식은 제외한다. source 전체를 ARM으로 이동하는 대안도 source+plan 전량2,235comb보다 부족분2,416이 크므로 단독 해결책이 아니며, source 데이터의 입력 SPI·planner 비용을 무료로 둘 수 없다.

## 우선 실험할 형식: 영역별 단위 좌표로 기존 필드를 대체

wire에 별도 receipt 주소를 추가하지 않는다. 기존 section/start/span을 domain/unit_first/unit_count로 바꾸고 payload 압축과 batch를 유지한다. 기존 형식과 새 형식을 동시에 지원하는 합성 결과를 절감으로 평가하지 않는다.

| domain | ARM에서 결정할 표현 | FPGA에 남길 독립 관계 |
|---|---|---|
| BG/OBJ tile |16/32B 단위 first/count|domain 상한, count≠0, 실제 staging/SNES 소비 주소·바이트 수와 단위 좌표 일치|
| section3 |16B 단위 first/count|512B 범위, 실제 소비·coverage와 대응|
| section4 및 fresh scroll/고정 앞부분 |영역 분리와 byte 좌표|정확한 byte 길이·fresh scroll 전체 포함 조건·실제 소비 CRC|
| section5 middle/raw tail |1121/3169 기준16B 단위와 마지막 유효 길이|domain별 고정 base+shift, 마지막3418 경계의9B 부분 granule 허용을 독립 확인|
| map batch |기존3B 범위 형식 유지 우선|짝수/count≤64/범위·순서·packet 끝·token 검사를 유지|

ARM이 영역 분할·단위 변환·패턴 위상 보존을 담당한다. 특히 경계를 나눈 RLE4/RLE2는 새 조각의 패턴 시작 위상을 바르게 회전해야 하며 literal은 원본 바이트를 정확히 분할해야 한다. cold에서 관측한 경계 횡단1건은 무조건0비용으로 처리할 수 없다. 별도 E1으로 나누면 최소 header/command/CRC19B와 반복 pattern payload, 새로운 token/credit 및 DMA setup이 붙는다. 한 packet 안의 복수 record로 유지하면 신규 record decoder와 길이 검사를 회로에 청구한다. 둘을 실제 M4 일정으로 비교하기 전에는 추가0B를 달성했다고 주장하지 않는다. warm의0B/0추가패킷은 설계 제약이다.

**삭제 대상으로 확인할 식**은 host의 `decode_end305` 일반17bit start+outlen, receipt 변환의1121/3169 감산 및 분기, `tap_pos-startpos` 패턴 위상 계산, 반복 section 경계/alignment classification이다. 새 domain별 좁은 count/end 검사와 base+shift 주소 생성으로 대체한다. 단순 배선 shift도 원래부터 거의 무료일 수 있어 삭제 식 개수를 LUT 절감으로 환산하지 않는다. section4/fresh의 byte adder, packet cursor/length check, raw 마지막 부분 granule 로직은 남는다. 모든17bit adder가 사라진다는 주장은 하지 않는다.

validator는 ARM record를 기대값으로 그대로 재사용하지 않는다. 독립 manifest expected coverage와 실제 소비 byte/address 증거를 비교하고 receipt/persistent valid/CRC/first fault를 유지한다. 실행 주소와 receipt가 같은 canonical 좌표에서 나오더라도 기대 coverage·실제 bus 관측은 분리한다. 잘못된 domain/unit/count, 같은 receipt를 가리키는 다른 DMA 주소, 마지막9B 초과, RLE 위상 오류를 반드시 거부해야 한다. 주소 선택 하나를 공유한다는 이유로 RAM 포트나 CDC가 없어지지 않는다.

## 시간과 전체 회로의 통과 예산

현재319 전체 Lite MAP은22,618LE /17,824comb /9,022FF /307,808bits이며 부족분2,416comb다. 모든 교체 경계6,700comb를 대상으로 해도4,284 이하가 필요하다. host+validator3,492만 바꾸면1,076까지 줄여야 한다. 이번 형식 변경이 그69.2%를 줄인다는 근거는 없다. 새 후보의 예상 comb는 **미정**이며, 독립 검사·새 domain decode·split/dispatch를 포함한 전체 MAP으로 판정한다.321의266comb 증가는 채택하지 않는다.

제한 ROM907은17.119885468ms, 부족0.453218801ms다. 마지막 consume 이후0.236063ms 전부를 없애도0.217155801ms는 앞에서 더 줄여야 한다.321의 warm RAM/queue 읽기 관측29.117184µs도 제거 가능한 critical path가 아니며453µs 해결 근거로 사용할 수 없다. 따라서 descriptor 단위 변환은 우선 **회로 절감 가설**이고, 시간은 실제 DMA/plan 공급 공백을 별도로 줄여야 한다.

metadata op15 선행 발행을 유지하고, ARM 변환 작업은 DMA refill/plan credit/IRQ보다 낮은 우선순위의 중단 가능한 준비로 둔다. BG 요청을 앞당겨도 ROM 허용창 수락이 같으면 이득은0이다. 동일 source 시작·ROM cycle A/B와 연속 제한/정상 A/B를 모두 요구한다. 초기 cold부터 최종 ACK까지 비교하고 새 바이트/응답/2슬롯 대기·ARM instructions/exception cycles/stack을 실제로 청구한다. `gain_DMA_supply + gain_terminal - exposed_ARM - exposed_SPI - added_credit_wait`는 중복 없는 critical-path 구간으로만 계산한다. 아직 각 gain은 측정되지 않았다.

다음 최소 실험은 (1)실제 ARM serializer에서 domain 단위 형식과 cold split 두 방식 생성, 원래 DMA byte/address/manifest와 round-trip 비교, (2)319 host의 해당 계산을 삭제한 decoder 및 실제65816 소비 어댑터 연결, (3)같은 일정에서 ARM/IRQ/SPI/2슬롯/ROM replay와 전체 Lite MAP이다. 단순 Python round-trip만으로 실제 소비 검증을 대신하지 않는다. 시간≤16.666667ms와 comb≤15,408의 공동 목표를 유지하되 최소 비교에서 둘 중 하나라도 회귀하면 확장하지 않는다. 새 형식만으로 목표에 부족하면 ROM 요청 공급·데이터 전송 역할까지 재검토하며 FSM 공유 반복으로 돌아가지 않는다.

저장 credit≠소비 완료, STOP의 pending write 취소·ROM drain, token/bank 재사용, 최종12회 display 읽기/token ACK·VBlank·독립 CRC/coverage는 모두 유지한다. source/plan 물리 RAM port와 persistent 데이터 수명도 그대로 비용에 포함한다. 새 회로/시간 개선, full71/fullRUN, FIT/STA 또는 실물60fps를 이번 검토로 승인하지 않는다. production227/GBC164/saveSRAM 변경 없음.
