# NES323 — 영역별 단위 좌표 전송과 FPGA 주소 계산 교체

319 RTL과317 metadata 선행 ARM을 기준으로 실제 구현했다. 이 문서의 최종 수치와 판정은 `analysis/units323-verification.json`에 결합한다. production227/GBC164/saveSRAM은 변경하지 않는다.

## 교체한 경계

`nes_units323.py`는 기존 ARM serializer의 section/start/span을 domain/unit_first/unit_count로 대체한다. BG/OBJ는16/32B, section3는16B, section4와 section5 앞부분은byte, section5 middle/raw는1121/3169 기준16B 단위다. raw의 마지막 end=16은3418의9B 부분 granule로 복원한다. payload 압축과 map batch 형식은 유지하며 별도 receipt 주소를 전송하지 않는다.

기존 packet 분할을 먼저 보존하고 경계를 넘는 packet만 추가 분할한다. literal은 바이트를 정확히 분리하고 RLE는 분할 위치의 패턴 위상을 보존한다. cold905/906에 각각 한 명령이 추가된다. 단위 변환은 실제 Cortex-M4 코드에서 실행하고 SPI CRC 계산 전에 적용한다. 상태 응답/IRQ/refill/2슬롯 credit 정책과 metadata 선행 발행은 그대로다. 별도 정규화 버퍼는 추가하지 않았다.

FPGA active record는 단위 좌표를 보관한다. 일반17bit start+outlen 및 receipt의1121/3169 감산/경계 분기를12bit unit end, domain별 한도, 고정 base/shift로 대체했다. SNES에 노출하는 byte descriptor는 기존 ABI로 복원하며 literal span은0을 유지한다. 원래 입력 형식을 병존시키는 fallback decoder는 없다. map/internal 명령은 기존 표현을 유지한다.

단위 좌표를 byte 주소로 복원하는 가산기/mux, raw 마지막7B 보정, section4/fresh byte 계산, 실제 bus tap의 주소·CRC 계산은 남는다. 모든 주소 계산을 삭제한 구현이 아니다. 패턴 인덱스는 하위2bit 차이로 명시했지만 원래 합성기도 폭을 줄일 수 있으므로 별도 절감으로 계산하지 않는다.

manifest expected coverage와 실제 소비 receipt/CRC는 분리한다. 새 단위 count의0·상위bit·domain별 상한을 검사하며, receipt는 실제 소비 완료 후에만 갱신한다. queue 저장 credit과 소비 완료 분리, persistent valid/CRC, source/plan RAM 포트·CDC·ROM drain, STOP·최종 ACK·VBlank를 유지한다.

## 실제 검증 경계

`probe_nes_cpu323.py`는 기존 명령을 독립적으로 분할한 입력으로 실제65816 ROM을 Mesen에서 실행한다. 71프레임 입력의546 ordinary 명령,128,041 출력byte,2회 zero DMA/2,200B가 통과했다. 새65816 코드가 아니라 같은864B 소비 ROM에 바뀐 명령 목록을 실행했다. cold905/906의 명령 수는각+1, 합산 master clocks는각+3,916/+3,924, warm907은정렬 영향+8이다. 이 isolated CPU 실행 자체는 VBlank/fullRTL 증명이 아니며, 생성된 bus trace를 실제 ARM/RTL 일정에 연결한다.

ARM 후처리 검사는 수신된 단위 형식을 독립적으로 byte 좌표로 복원한 뒤 원래 계획의 전체 주소/바이트 쓰기·tile 범위·map·manifest·sequence와 비교한다. 비교 oracle을 새로운 FPGA의 receipt 값으로 대체하지 않는다. 잘못된 domain/count와 STOP 검증은 실제 ARM/ROM/2슬롯 경로에서 주입한다.

최종 정상 일정9건과guards01 오류11건 모두 PASS다. source/plan/부분E1/부분E9 STOP, 조기 최종ACK, 독립manifest/receipt mismatch, 물리ROM 요청 중 STOP/drain, 잘못된domain/count0/상위count bit/raw 마지막granule 초과를 검사했다. 새 좌표 오류4건은 수신 후 active record를 강제로 변조하는 주입이며 SPI CRC를 새로 만든 악성 wire packet 시험은 아니다. 주입 전 정상 검사는 유지하고, 주입 후에는8+256 host clock 동안 phase/queue RAM freeze와 seal/lease/ACK 비노출을 확인했다. mismatch는fault3, 나머지는fault4다.

## 실패 보존

- fixed01: SNES byte descriptor의 span에 raw unit count가 노출되어 CPU trace가006066 불일치를 검출했다. byte ABI 복원을 수정했다. board01은 이 중간 소스의 진단용 MAP으로 채택하지 않는다.
- fixed02: 경계 분할을 기존 packet 분할보다 먼저 적용해 뒤쪽 명령 크기가 달라졌고 CPU trace가006064 불일치를 검출했다. 기존 분할 후 경계 분할로 순서를 수정했다.
- fixed03: 실제 cold 소비 뒤 ARM 후처리 검사가 구형 byte 형식을 그대로 가정해 실패했다. 독립 형식 복원을 추가하고 기존 canonical 비교는 유지했다. 대기 중인 해당 테스트 프로세스만 정리했다. 라이선스 오류가 아니다.

최종 비교는 동일 source 시작/ROM cycle의 fixed04, 연속 제한window01/정상normal01, 수정 RTL의 전체 Lite board02를 사용한다. 정상/제한 일정의 시작 위상 이동은 고정 위상 결과와 구분한다. 전체71 ARM/fullRUN/live65816/fullpixels/FIT/STA/실물60fps를 주장하지 않는다.

## 전체 비용과 판정

| 항목 |319|323|변화|
|---|---:|---:|---:|
|전체 Lite LE|22,618|22,612|−6|
|전체 comb|17,824|17,813|−11|
|전체 FF|9,022|9,022|0|
|RAM bits|307,808|307,808|0|
|comb 부족|2,416|2,405|−11|
|ARM text|28,986B|29,478B|+492B|
|ARM BSS|47,348B|47,348B|0|
|관측 ARM stack|1,304B|1,360B|+56B|
|정상 연속907|14.763186476ms|14.763595562ms|+0.000409086ms|
|제한 연속907|17.119885468ms|16.888479154ms|−0.231406314ms, 위상 영향|

ARM text/BSS는 테스트 executable 전체이며 물리 firmware SRAM 배치 증명이 아니다. 시간은 실제 M4 명령의 CPI1/84MHz 모델과 IRQ/exception 비용을 포함한다. 새 IP로 인한 물리 clock/Fmax 변화는 MAP으로 입증하지 않는다.

동일 시작/ROM 위상의905/906/907 완료 시각은각+0.229634/+0.231633/+0.000273ms다. ARM 명령 수는각+5,769/+5,716/+305, SPI는각+47/+47/0B다. cold의47B는 E1 한 번19B와 E2 두 번28B다. 순수 header 증가19B만 비용으로 보면 응답/credit 비용을 누락한다. 정상 연속cold905/906의 duration 회귀는각0.171634304/0.170725224ms이며,907 절대 완료는0.342769ms 늦다.

제한 연속907은 시작이263.146933→263.378567ms로0.231634ms 늦어졌다. 첫 BG backend 수락은274.905042ms로 동일하고 마지막 완료는280.266864→280.267091ms로0.000227ms 늦다. 따라서 duration 감소0.231406314ms는 앞선cold 지연으로 ROM 대기를 덜 포함한 결과이며 실제 공급/실행 단축으로 인정하지 않는다. 관측 duration의 잔여0.221812487ms와 원래 동일 위상 개선 목표0.453218801ms를 혼동하지 않는다.

제한warm의op15 release는 첫BG보다1.986154ms 빨라 metadata 선행 정책을 유지한다. 정상ROM에서는 첫BG가op15보다 먼저 올 수 있으므로 모든 일정에서 BG보다 빠르다는 주장은 하지 않는다. 3프레임 duration 합의 변화는고정+0.461539916ms, 제한연속+0.000227270ms, 정상연속+0.342768614ms다. 제한warm만 떼어낸 apparent gain을 전체 일정 개선으로 세지 않는다. SysTick/EXTI는고정36/79, 제한28/81, 정상19/75이며 응답/IRQ 증가도 실제 실행 비용에 포함됐다.

host 자체 comb는2,485→2,461(−24)이나 validator mapping은+3, 그 외 mapping 변화가 일부 상쇄해 전체−11이다. 독립 검증기 코드와 저장체를 제거한 결과가 아니다. 목표2,416 중11개만 줄었고, ARM 코드/stack 및cold 시간은 증가했다. **323은 미채택,319 비교 기준과0.453219ms/2,416comb 예산을 유지한다.**323의 실제2405comb 부족은 실험 결과로 보존하되 production 기준으로 승격하지 않는다.

다음 단계는 같은 단위 형식의 필드/상태 번호 미세 조정이 아니다. host/validator의 byte-domain 소비 ABI를 유지한 채 ARM에 단위 변환만 추가하면 복원·독립 검사 비용이 남는다는 결과를 반영해, 전체 소비/검증 인터페이스와 데이터 흐름을 다시 평가해야 한다. 미입증 절감치를2,405개에 임의 배분하거나 FIT/seed 반복으로 이 실험을 구제하지 않는다.
