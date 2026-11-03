# 590: ARM 재사용 판정·FPGA 고정 행 공급의 전체 비용 조사

## 결론

**다음 최소 검증 대상으로 `행 CRC32+양끝 값 8B / ARM 판정 / 요청 bitmap 1회`를 남긴다. 제품 채택이나 시간·회로 동시 절감의 입증은 아니다.** 기존53입력에서 요청·확인·cold·nonmap을 포함한 밀집 입력 I/O 참조값은 MMC577의14.066→6.775ms다. 그러나 새 ARM parser/CRC/의미검사, source query/CDC, BUSY·IRQ·ROM·출력 일정과 실제 삭제 LE는 아직 측정하지 않았다. MMC577·R3 미선정·새 ZIP 없음은 유지한다.

589처럼 FPGA에 이전 frame base와 세 shift 비교·범용 block 실행기를 넣지 않는다. ARM이 기존 입력 map에서 후보를 만들고 FPGA는 현재 행의 고정 요약과 요청된 전체 행만 공급한다. 처음 비교한16B/행의 세 CRC 요약도 불필요하다. **완성된 행 후보를 ARM에서 CRC32로 비교하면 FPGA는 CRC32 하나만 계산하면 된다.**

[재현 도구](../tools/analyze_nes_roles590.py) · [숫자·원본 해시](../analysis/roles590-verification.json) · [589 실제 회로 실패](nes-source589-results.ko.md) · [현재 계획](nes-retrospective579-plan.json). 선택은 `analysis04`다. 원본 capture·ELF는 기존 private evidence를 재사용하며 공개 JSON에는 수치와 hash만 기록했다.

## 비교 범위와 수치

905–957의53개 hash-pinned geometry/raw를 사용했다. warm은 첫 두 화면을 제외한907–957, dense는951–955다. **실기5–40초/40–55초와 같은 구간이 아니다.** 실제577 압축 nonmap/RAW record 바이트와 generation 필드는 그대로 과금했다. 모든 후보의 map 복원은 원본과 정확히 일치했다.

| 입력 방식 | cold905 I/O ms | warm 평균 I/O ms | dense 평균 I/O ms |
|---|---:|---:|---:|
|MMC577 원본|13.223|13.294|14.066|
|항상 전체 고정 행|12.353|12.366|12.935|
|동일 행만: CRC32 4B·묶음 요청|12.353|7.649|8.169|
|**동일/좌우 이동: CRC32+양끝8B·묶음 요청**|**12.353**|**6.520**|**6.775**|
|세 CRC+양끝16B·묶음 요청|12.353|7.440|7.695|
|8B 요약·필요 행마다 요청/응답|12.353|8.085|7.996|
|8B 요약 뒤 모두 전체 행 요청|12.353|13.484|14.052|

선택 조사안의 dense payload는3406.8→1374B, D1 packet은16→8.8개다.29행 중18.4행 동일·6.8행 한 칸 이동·3.8행 전체 공급이다. warm의 전체 공급은평균4.784행이다. 단순한 문양 fixture가 아니라 기존 고정 SMB3 capture의 비교지만 새 실기 성능은 아니다.

| 입력 generation | 동일 행만 ms | 8B 이동 포함 ms | 이동 포함 전체 요청 행 |
|---|---:|---:|---:|
|951|11.728|5.756|0|
|952|6.756|7.322|6|
|953|5.446|6.012|1|
|954|11.728|9.029|12|
|955|5.190|5.756|0|
|957|11.661|6.780|4|

평균만 보고 shift를 버리면951/957의 큰 이득을 놓친다. 반대로 이동이 없는952/953/955는8B 요약이4B보다 느리다. 이를 새 출력의 VBlank나 ACK 개선으로 바로 바꾸지 않는다. 원래 첫 BG 계획은 전체 입력 완료 전에도 발행됐으므로, 아래의 요약·요청 장벽이 ROM 공급을 늦추는지도 다음 실제 결합에서 확인해야 한다.

### I/O 계산에 넣은 비용

- 기존2.625MHz 공유 SPI와503의 실제 driver 호출 평균을 재사용했다. D1 payload 외에 packet당 D1 overhead3B+D2 8B+확인D0 8B, 기존 시작/PREPARE/COMMIT 확인40B를 포함한다.
- 새 **HELLO24B+확인D0 8B**를 매 입력에 넣는다. ARM base identity/validity가 FPGA에 무료로 전달된다고 가정하지 않았다. warm에는 추가 **REQUEST24B+확인D0 8B**가 반드시 한 번 있다. 요청 bitmap이0이어도 완료 허가를 보내야 한다.
- 새 명령의 driver는 기존D3 평균49.906µs를 쓴 **민감도 가정**이다. 실제 새 명령 실행 시간·BUSY 재시도는 미측정이다. SPI byte만으로 시간을 계산하지 않았다.
- D1 payload≤254B, packet마다 phase/ordinal2B, record는 packet을 가로지르지 않는다. 요약 완료→ARM 결정→행 응답은 서로 다른 seal이며 경계를 넘어 공짜로 재포장하지 않았다. 행별 요청안은 응답도 별도 packet으로 센다.
- BEGIN32B, 요약 완료8B, 행 응답 완료8B, META/END/COMMIT 각8B다. full row는6B 범위 header+66B 값이다. 기존nonmap record를 다시 만든 비용이나 새로운 생산 overlap은 인정하지 않았다.

한 번의 full-map repair는 **추가8.716ms I/O**이며 CRC 재계산·의미검사·query 대기는 별도다. cold에서는 요약을 보내지 않고 HELLO의 cold 명시 후 전체 행으로 간다. cold I/O 이득은0.870ms뿐이므로 새 계산 비용으로 회귀할 수 있다. warm 요약이 모두 실패하는 경우도 표에 넣었으며 언제나 빨라진다고 보장하지 않는다.

## 고정할 역할·소유권

### FPGA

1. 한 immutable capture lease에서 현재 map을 순서대로 읽는다. 각33word의 CRC32와 first/last15bit word만 생산한다. FPGA는 이전 map·same/left/right 판정을 보관하지 않는다.
2. fresh canonical CRC16은 **논리 값의 첫 순회**에서만 누적한다. 요약 후 요청된 행을 다시 읽는 것은 전송 재조회이며 canonical CRC를 중복 갱신하면 안 된다. map seal에는 신선한 map CRC16을 넣고 META/END에는 전체 canonical CRC16/개수를 넣는다.
3. ARM의 bounded bitmap을 identity와 함께 받아 오름차순으로 전체 행을 공급한다. 예비 partial/mask/RLE 선택기를 추가하지 않는다. old nonmap 압축은 보존한다.
4. 요청이0이어도 응답 완료 표식을 보내야 nonmap 단계로 진행한다. D1의 CRC16·완전 read·D2 token retire·D3 PREPARE 경계는 유지한다. 요청 수신/소비 완료/단계 전환은 새 CDC 비용이다.

검토용24B 명령 필드는 opcode/version2B,epoch4,serial4,generation2,summary-token2,bitmap4,mode/reserved2,CRC16 2,tail2다. BEGIN은32B identity/count, map seal8B는tag/행수/freshCRC16/generation이다. tag 값·opcode·CRC 적용 범위의 target ABI는 아직 구현/채택하지 않았다. 도구의 control dummy bytes는 **길이 예산**이며 실제 wire CRC 시험이라고 해석하지 않는다.

### ARM

1. 요약의 행수/순서/identity/packet CRC를 확인한다. 현재577 BEGIN의 `nes_native165_reset()`은 map도 지운다. **map을 남기는 reset과 base-valid 규칙을 함께 바꾸지 않으면 재사용이 불가능하다.** 다른 fields/required bitmap을 지우는 동작은 유지해야 한다.
2. 기존 `maps[1056]`의 실제 바이트에서 CRC32를 다시 계산한다. 같으면 동일 행, 아니면 old[1..32]+new-last 또는 new-first+old[0..31]을 시험한다. 별도 cached CRC만 믿으면 retained RAM 손상을 놓칠 수 있으므로 캐시 digest는 두지 않는다.
3. 어느 후보도 맞지 않는 행만 bitmap에 넣는다. 받은 행은 범위·중복/누락·15bit 의미를 검사하고 map CRC16을 확인한다. 재사용 행도 required-tile/coverage·순서를 생략하지 않는다. 모든 map이 확정되기 전 후보 row를 새 BG plan으로 공개하지 않는 것이 이번 참조의 보수적 경계다.
4. source input-COMMIT identity와 display-bank 최종 ACK 이력은 별개다. source base는 canonical/coverage/PREPARE/COMMIT+D2 확인 뒤에만 유효하다. 표시 이력은 실제 소비 검사와 VBlank 최종 ACK 뒤에만 바뀐다. 기존577처럼 최종 ACK→EA→다음 입력 허가를 보존한다.

## 독립 검사와 복구

**같은 CRC16을 재사용 요약과 최종 canonical 검사에 쓰는 안은 제외했다.** 유효한15bit 값33개로 된 서로 다른 두 행을172회 생성 안에 찾았고, 두 행의 CRC16뿐 아니라 동일 prefix/suffix를 붙인 전체 stream CRC16도 같았다. 같은 선형 CRC와 동일 길이를 쓰면 최종 CRC가 이 잘못된 생략을 잡아주지 못한다. 실제 게임에서 발생했다는 보고가 아니라 결정적인 합성 반례다.

조사안은 서로 다른 CRC32 요약과 fresh CRC16을 사용한다. 둘 다 유한한 비암호학적 오류 검사이고 충돌 없는 증명은 아니다. query 생산자·값 의미·required tag·coverage·fresh canonical 검사·실제 DMA 소비 검사를 계속 독립 경계에 둔다. CRC만으로 그 검사를 대체하지 않는다.

map CRC 실패 시 같은 lease에서 **전 행 REPAIR 1회**만 요청한다. repair가 완료되기 전 required-tag/계획 공개를 확정하지 않는다. 두 번째 실패, identity 손실, timeout은 fail-closed/STOP이다. STOP으로 lease를 잃었으면 같은 generation을 계속 읽지 않고 다음 capture를 cold 전체 행으로 시작한다. partial map·cold·epoch 변경 뒤 재사용 validity는 모두 무효다. 기존 표시 화면은 바뀌지 않아야 한다.

참조20조건은 COMMIT 전제4개, stale identity/범위3개, 부분행 STOP4개, repair 횟수, COMMIT≠표시ACK/EA 순서, retained RAM 손상, 거짓 요약의 fresh CRC 실패/전체복구, edge 의미, same/left/right/full을 포함한다.53개 capture에는 right-shift가 없으므로 별도 synthetic case로 확인했다. **새 RTL의 clock-stop/IRQ·메뉴 시험은 아니다.** 기존589에서 통과한 즉시 STOP/클록정지 보호를 새 request/CDC에 연결해 다시 검증해야 한다.

## ARM·RAM·회로 예산

기존MMC577 ELF의 `crc32_update`를 그대로 M4에서 실행했다.256개 연속 byte update가 Python CRC32와 일치했다. 함수20B·기존표1024B가 이미 링크돼 있고 함수 본체는 update당6개 명령이다. **추가1KiB CRC 표를 만들 필요는 없다.** 이는 caller loop/BL·Flash wait·IRQ·전체 cycle 계측이 아니다.

8B안의 ARM hash byte work는 warm2936.35/dense2864.4B다. 동일 행만의1914B보다 늘지만16B안의2905.37/2835.6B와는 거의 같다. FPGA hash work는16B안5626B→8B안1914B로 줄고 CRC32 accumulator는3개→1개다. canonical CRC16과 ARM required-tag/semantic/shift-copy 작업은 별도다. standalone6명령만 곱한 결과를 실제 처리 시간으로 쓰지 않는다.

| 경계 | 삭제/유지/추가 | 입증 수준 |
|---|---|---|
|589 이전 frame base2336B·세 비교·mask/범용 복귀|새 설계에서 제외|구조 결정.577에는 이base가 없어577 대비 절감으로 셀 수 없음|
|577 map literal/packed/repeat 결정|고정 row 공급으로 대체 후보|정확한 순삭제 LE/Flash 미측정|
|577 nonmap 압축·semantic parser|유지|logical_record1112B 전체 삭제 credit 불가|
|host record 폭/field pack 선택|byte 공급과 함께 제거할 후보|source로 같은 formatter를 이동하면 순삭제가 아님|
|CRC32 1개·CRC16·요청 bitmap·phase/identity/CDC|추가|기존CRC/기존D0에 무료 포함시키지 않음|
|ARM map2112B|기존 입력 배열 제자리 재사용 후보|BEGIN/reset·planner 생존기간 검증 필요|
|ARM digest cache|0B|실제 retained 바이트 재검사|
|행 scratch≤66B/ARM 새 state·scratch≤160B|명시적인 설계 상한|최대 stack/IRQ 증명 아님; 기존RX alias 성공 전 여유로 환급 금지|

제품의 Flash84B·148LE·5M9K 여유는 그대로다. packet1434B를 **실제로 전부 교체할 경우에만** 새 packet/요약/요청/복구 실행기의 산술 상한은1518B다. 유지하는logical1112B까지 더한2630B 상한은 이 혼합안에 적용하지 않는다. shared CRC 표 재사용이 parser/STOP/identity 코드를 무료로 만들지는 않는다.

회로는 같은 경계MAP 기준1668LE보다 작아야 “절감”이다.1668+148은 local screening 참고치일 뿐 보드FIT 통과가 아니다. 기존 보드의 source/mailbox/host1433LE도 같은 보드 경계에서 줄여야 한다.5894014LE에서 크게 내려가는 것만으로 제품보다 작아졌다고 판단하지 않는다. 추가 행 scratch는 최대1M9K를 목표 상한으로 두며 실제 register/M9K 추론을 확인한다. 새 MAP/FIT 수치는 만들지 않았다.

## 전체 시간과 다음 순서

밀집 입력의 조건부 I/O 여유는 **7.291ms**, warm은6.775ms다. 여기에 source query/CRC·ARM 판단/의미검사·추가 IRQ/BUSY·첫 BG 공급 지연이 들어와야 한다. 기존 두 ROM 위상의 비입력 비용 합59.983/59.989ms는 그대로 남는다. 이 값들은 old 일정의 항목 합이며 새 retimed lower bound도, 새FPS도 아니다. 이번 결과만으로60Hz가 가까워졌다고 말할 수 없다.

다음 순서는 다음 하나의 비용 gate로 제한한다.

1. **8B 요약·묶음 요청만** 실제 old nonmap/단일256B D0–D3 경로와 연결할 삭제표를 고정한다. ARM packet/BEGIN/required semantics와 source/host byte formatter의 이동·잔존 코드까지 대응시킨다.16B 세CRC·행별 요청·589범용 실행기는 재개하지 않는다.
2. 최소 경계의 ARM 전체 링크와 동일경계 Lite MAP으로 **순 Flash≤84B, 순 LE<0, 추가 scratch≤1M9K**를 확인한다. 목표는 이전 코드를 남긴 adapter 추가가 아니다. 모델-only canonical/요청 상태를 실제로 구현해야 하며 두 비용 중 하나라도 실패하면 그 후보의 전체 결합은 중단한다.
3. 통과한 경우에만 실제 immutable query·STOP/clock-stop·cold/repair와 ARM/IRQ/ROM/65816을 연결한다. 같은 두 시작 위상에서 첫 BG 준비, 첫 두 화면 이후 표시 간격, 마지막 ACK·다음 capture를 비교한다. 입력6.775ms를 기존 timeline에서 단순 차감하지 않는다.
4. 전체16.667ms/Flash/RAM/보드 예산이 성립한 후보만 R3 전체FIT/STA·실기 전달로 올린다. 그 전에는MMC577과메뉴/GBC/save·README를 유지한다. 새 실기로그는 계속5–40초·40–55초, 새 파일명, RESTORE 제외다.

이 조사는 역할 변경의 가능한 시간 여유와 정확한 실패 조건을 찾은 단계다. **아직 제품에서 실제 삭제된 제어는0개, 얻은 새 실기 성능도0**이라는 경계를 남긴다.
