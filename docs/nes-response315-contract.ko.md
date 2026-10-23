# NES315 SPI 응답·queue 공통 실행 경로 교체

NES315 snapshot byte selector·queue host load 통합: whole Lite 22664LE/17870comb/9040FF/307808bits;314 대비 comb-94,부족2462. 제한907 16.906343ms/314 대비+0.000727,정상14.746505. 시간·면적 동시 목표 미달/production 미채택.

## 실제 삭제·유지 경계

- snapshot의 응답 출력용/CRC8용 두 가변 byte 선택기를 하나로 합쳤다. byte_event에서는 다음 응답 byte를8bit 레지스터에 미리 저장하고, 나머지 cycle에는 같은 선택기로 snapshot CRC8을 진행한다. 요청 CRC의 기존 우선순위는 유지한다. 첫 응답 byte는 command 시점의 live status에서 직접 고정한다.
- 200bit immutable snapshot은 전송 중 상태 변화와 progress IRQ 비교를 위해 유지한다. snapshot 자체, CRC8 상태/cursor, serializer를 없앴다고 계산하지 않는다. SS·partial-byte abort·reset 시 reply 수명을 종료한다.
- queue의24B zero clear, 별도 record load 상태·cursor·loaded 플래그와 mirror 제어를 삭제했다. 공통 host의 기존 at와 HLOAD/HCHECK가 ordinary10B/typed14B/batch15B만 직접 읽는다. 저장 완료 packet_ready와 active record 준비를 구분한다.
- opcode를 읽을 때 active token/count 기본값을 설정한다. 따라서 RAM을 지우지 않아도 ordinary가 이전 typed/batch slot 내용을 상속하지 않는다. payload와 필요한 canonical header만 RAM에 쓴다.
- empty/full은 최대2개 outstanding이라는 기존 불변식을 이용해 accepted/retired 하위2bit로 판별한다. 외부16bit counter, sequence 고갈 검사, 저장 retire와 실제 소비 완료 분리는 유지한다. used 관측식은 fixture용이며 합성 제어 fanout은 없다.

독립 manifest/coverage/CRC 의미 검사와 실제 receipt·STOP/RAM freeze·최종 ACK 순서는 그대로다. 공통 host FSM 추출도 유지된다. 수신 parser 전체나 validator 전체를 삭제한 변경은 아니다.

## 전체 일정·응답 비용

|ROM|frame|전체 ms|314 대비 ms|307 대비 ms|ARM 명령|SPI B|
|---|---:|---:|---:|---:|---:|---:|
|normal|905|80.074721|-0.001636|+1.581663|2241306|10168|
|normal|906|56.467050|-0.002500|+1.514391|1626145|10766|
|normal|907|14.746505|-0.000909|+0.389814|698910|1123|
|restricted|905|104.635790|-0.001500|+0.981034|2247180|10294|
|restricted|906|116.932415|-0.000182|+0.030681|1634451|10948|
|restricted|907|16.906343|+0.000727|-0.710582|700873|1165|

|ROM|frame|E0 횟수/B|E2 횟수/B|E9 횟수/B|
|---|---:|---:|---:|---:|
|normal|905|3/78|42/588|10/736|
|normal|906|11/286|59/826|9/712|
|normal|907|4/104|24/336|4/92|
|restricted|905|3/78|51/714|10/736|
|restricted|906|11/286|72/1008|9/712|
|restricted|907|4/104|27/378|4/92|

실제 M4 명령과 IRQ/refill,2슬롯·응답 비용,공유 SPI와 고정 ROM 허용 구간/core 경쟁을 같은 일정에 포함했다. ARM PT_LOAD는312/313과 동일하고313에서 측정한 ordinary65816 bus trace를 재사용했다. CPU/ARM guard를 새로 실행한 것으로 세지 않는다.

제한907은16.906343ms로60fps까지0.239676ms 부족하다. 314 대비 시작 시각은-0.001681ms, 완료 시각은-0.000954ms, 첫 BG 이후 tail은-0.000954ms다. 제한3프레임 합계 변화는-0.000955ms, 정상 합계는-0.005045ms다. 새14/15/10B 읽기의 국소 cycle 절감을 전체 프레임 시간 절감으로 자동 환산하지 않는다.

307 대비 제한3프레임 합계는+0.301133ms다. 907의 기존 단축에는 프레임 시작 위상 이동 효과가 있으므로307보다 실제 전체 처리량이 좋아졌다고 표현하지 않는다.

## Quartus Lite 전체 비용

|항목|314|315|차이|
|---|---:|---:|---:|
|LE|22758|22664|-94|
|comb|17964|17870|-94|
|FF|9043|9040|-3|
|RAM bits|307808|307808|+0|

조합 논리 부족분은2556→2462개(15408 기준)다. 전체 MAP 결과이며 parent/child를 중복 합산하지 않는다. FIT/STA는 실행하지 않았다. 기존 cache_index141 외 새 control latch/undriven 경고는 없다.

|영역 own 값|comb 변화|FF 변화|
|---|---:|---:|
|nes_validator278:validator|-3|+0|
|nes_output260:flow|+61|+2|
|nes_queue260:queue|-63|-13|
|nes_spi270:spi_front270|-119|+8|

## 검증과 한계

SELECT board01/window01/normal01/guards01/early01/queue02/spi01/reply01. raw logs/RTL/ELF는 probes/nes-response315에 보존하고 analysis의 hash로 결합한다.

queue01은 추가 fixture의 ready 신호 선언 순서로 vlog에서 실패했다. RTL 변경 없이 fixture의 always 블록 위치를 고친 queue02가 통과했으며 최초 실패도 보존했다. 라이선스 문제가 아니다.

- 동일 RTL 정상·제한905..907: metadata/receipt/CRC/display/finalACK·최대2credit 확인.
- 오류 주입12건+정상 대조: 독립 범위/manifest 검사, STOP/RAM freeze, 조기 consume/최종ACK, token/namespace, RLE, 미지원 opcode.
- queue14건: 두 슬롯·최대240B payload·CRC/identity/length·credit/counter wrap/STOP. typed/batch 뒤 ordinary에서 token/count가0이고 idle command 중 clear 쓰기가 없음을 추가 확인.
- 실제 SPI15경계: E1/E9 integrity/CRC domain/STOP/2credit, shared seal 수명, EA 이후 요청 재사용.
- 314 serializer와315를 같은 SPI pin으로 구동: 두 속도,41 transfers,16 partial-byte abort에서 전 cycle link/IRQ/progress mode 대조. 응답 중 live status를 바꿔 immutable snapshot을 확인했다. 물리 최대 SPI 주파수 시험은 아니다.
- early manifest를 BEGIN 직후에 넣어 후속 DMA·독립 coverage·최종 완료를 검사했다. 실제 ARM 일정 이득으로 세지 않는다.
- plan RTL은314와 byte/hash 동일.314의48개 dual-clock plan 검사 증거를 재사용하며 새 실행으로 세지 않는다.

시간은 CPI1/84MHz 모델로 실제 하드웨어 WCET가 아니다. ordinary CPU trace 결합 외 tile/map·VBlank/최종 표시 service 모델을 유지한다. full live65816/whole71/fullRUN/FITSTA/실물60fps는 미검증이다. production227/GBC164/saveSRAM은 변경하지 않았다.

307/314 비교 기준과 production227 유지. 남은 immutable snapshot·CRC/ingress cursor, host/validator의 주소·완료 경계를 전체 예산으로 재검토하되 독립 coverage·STOP·최종ACK는 유지한다. 제한907의 BG ROM 허용 시각 전후를 분리해 실제 임계 경로를 줄이는 후보만 평가한다. 작은 FF 절감/상태 번호/seed/FIT 반복으로 회로 부족을 해결했다고 주장하지 않는다. 두 예산 통과 전 whole71/fullRUN/FITSTA/실물60fps 승인 금지.
