# NES295 비최종 BG 완료·공동 경로 검증

프레임 END와 별개인 BG 범위 완료를 실제 ARM 생산·plan SPI·tile aperture·DMA·receipt 경로에 연결했다. 기능은 통과했지만 시간과 전체 회로가 함께 개선되지 않아 후보는 미채택이다. 기능 기준289·성능 기준287·production227을 유지한다.

## 계약과 실제 교체

- 3B `0x87, generation16`은 BG 완료다. 현재 구현은 6B framed batch 한 개와 추가 E9를 사용한다. 기존 최종 `0x83` END와 구별한다. 마지막 BG descriptor를 ARM에서 flush하고 FPGA에서 같은 열린 aperture를 SEAL한다. 원래 BG/OBJ 정렬 경계 예약을 유지했다.
- plan transport는 BG 완료 이후 BG/blank 또는 재완료를 거절한다. batch CRC, record 형태, 마지막 위치와 generation/lease 검사는 유지한다. BG 완료는 `closed`, 최종 `end_sealed`, plan SPI `ended`를 설정하지 않는다. OBJ 공급과 최종 END가 뒤따른다. 기존 marker 없는 legacy directed fixture도 허용하며, 새 ARM 생산기는 marker를 반드시 요구한다.
- 기존 34bit end mailbox의 kind 비트를 partial 의미로 재사용했다. 별도 CDC mailbox나 RAM은 추가하지 않았다. tile producer는 BG 완료에서 aperture만 닫고 in-frame/generation을 유지한다.
- 출력 mux의 `tile_ended` 저장·중계를 제거하고 producer의 `range_idle295`와 `chunk_ready`로 TILE 소유권을 해제한다. 실제 DMA 소비·token/receipt 완료가 aperture 반환의 선행 조건이며 BG 완료는 credit 반환이나 최종 ACK가 아니다.
- 독립 validator의 pre-DMA 범위 검사, 실제 소비 CRC, duplicate/coverage, manifest/H2 검사와 최종 ACK 경로는 유지했다. **host·validator 전체 FSM이나 receipt RAM walk를 통합 교체한 것은 아니다.** 이번 실제 제거는 출력 소유권 중계이며, 넓은 공동 실행기 예산은 아직 충족하지 못했다.

## 실제 ARM과 전체 일정

Native71은 원래 plan record 순서와 1,039개 출력 명령/73,260B가 byte 단위로 일치하며 fixture read는 0이다. marker/framing만 추가됐다. warm69 모두 조기 descriptor가 생겼지만 37개는 blank뿐이며 실제 그래픽 BG 조기 발행은 32개다(294는 1개). cold905/906 조기 비blank 범위는 각각1/6개다. 이 native71 시험의 dispatch는 intercepted sink이므로 71개 live 일정이나 실제 DMA 완료 증거로 세지 않는다.

실제 M4 ELF·컴파일된 IRQ·shared SPI·plan refill·tile ROM arbiter·출력 RTL을 정상/제한 ROM 각각905–907에 연결했다. 아래는 source replay 시간과 같은 프레임 live output 시간의 합계다. ARM 실행, polling/IRQ/timer fallback, E9·credit·ROM 경쟁과 마지막 표시 ACK 비용이 들어 있다.

| 조건 | 기준289 ms | 이전294 ms | BG 완료295 ms | 294 대비 ms |
|---|---:|---:|---:|---:|
| 정상905 |79.998358|80.152175|80.260491|+0.108317|
| 정상906 |56.574003|56.433459|56.588321|+0.154862|
| 정상907 |15.314998|15.423360|15.527359|+0.103999|
| 제한905 |105.718595|105.966910|104.875014|-1.091896|
| 제한906 |114.910303|115.759156|117.184094|+1.424937|
| 제한907 |17.999648|18.093828|32.216341|+14.122512|

정상907의60Hz 산술 여유는1.139308ms, 제한907은15.549674ms 초과다. 한 cold 프레임의 개선을 전체 이득으로 일반화하지 않는다. ARM text27330B/data0/BSS47092B/관측stack1288B이며294 대비 text+148/BSS+4B다. stack은 관측치이고 감소를 WCET/최대stack 증명으로 사용하지 않는다.

제한907의 로그는 원인을 드러낸다. 마지막 BG receipt가276.318812→275.542350ms로0.776462ms 빨라졌지만, 첫 OBJ plan은275.935211→276.271889ms로0.336678ms 늦어졌다. 첫 OBJ 출력 시작은275.935666→291.149302ms로 밀렸다. 새 완료 E9와 blocking descriptor/receipt 발행을 포함한 일정에서 후속 plan 공급이 늦어져 제한 ROM 창을 놓쳤다. 추가 E9 하나의 비용과 앞선 프레임에서 누적된 ROM 위상을 분리하는 A/B 시험은 하지 않았으므로14.123ms 전부를 E9 자체 비용으로 귀속하지 않는다. 이는 해당 periodic ROM fixture에서 관측한 회귀이며 실제 보드 전체 위상에 대한 WCET가 아니다. 새 제한907 timer fallback은2회다. 세부 E2/E9/SPI bytes·IRQ/ROM wait·최초 소비 시각은 CSV와 `restricted907_trace`에 기록한다.

## Quartus Lite 전체 비용

기존287 whole board의 동일 입력을 복사하고 변경 경계만 적용해 새 Lite MAP을 수행했다. 새 board와 live의 plan decoder/tile producer/validator는 hash 일치하며 mux의 board-only 관측 포트만 정규화해 비교한다. 다른 board 입력도 기존287과 hash 일치한다. 한 번의 실제 MAP이며 FIT/STA나 seed 반복은 하지 않았다.

| 전체 MAP | 기존287/294 | 295 | 변화 |
|---|---:|---:|---:|
| LE |22569|22603|+34|
| combinational functions |17671|17703|+32|
| FF |9025|9029|+4|
| RAM bits |307808|307808|0|
| 한도15408 대비 comb 부족 |2263|2295|+32|

own 합계로 겹침 없이 계산하면 host2361→2352, validator1090→1088, queue129→128, plan568→573, SPI658→657, glue47→49다. 고정 경계4853→4847로6개 감소했지만 경계 밖12818→12856으로38개 늘어 전체는32개 증가했다. 수정하지 않은 RTL도 전체 합성 최적화 결과가 달라지므로 일부 own 절감을 합쳐 보드 회복으로 주장하지 않는다. tile producer 자체는193→200이며 고정 경계 바깥에 포함되어 있다.

현재 outside12856을 그대로 둘 경우 고정 경계 예산은2552로, 현재4847에서2295개를 더 줄여야 한다. 기존2590 예산을 그대로 적용하지 않는다. host/validator 전체 공유 실행기의 구현·절감 근거는 아직 없으며, 2295개 부족과 제한ROM 회귀가 남아 있으므로 P2와 physical60fps는 승인하지 않는다.

## 검사·재현 범위

선택 native01/armguard01/h2guard01/irqguard01/test03/window01/close02/guards01/board01/analysis01. native commit/실패/STOP6개, BG 경계/early DMA 실패/STOP/ISR6개, H2 9개, IRQ8cases/33exceptions를 새 ELF에 실행했다. native01은test01 ELF를 사용했으나 test03과 PT_LOAD segment가 동일하다. raw ELF hash는 경로에 따라 달라 별도로 보존한다.

close02의9개 plan RAM/CDC 검사는 partial→OBJ→final·retire rearm,중복완료,완료후BG,잘못된generation,CRC,예약opcode,STOP,clock-pause STOP,partial뒤조기retire를 포함한다. tile_done은 이 단위시험에서 모델링한다. guards01의38개 실제 출력 RTL 오류주입은 독립CRC/receipt/manifest·orderedACK·STOP/clock freeze·최종ACK를 유지했는지 검사한다. legacy guard에서는 partial 입력을0으로 고정하므로 nonfinal 의미 자체의 증거와 구분한다. 해당 fixture의 미연결 progress IRQ 출력 경고3개는 유지되며 실제 IRQ는 별도live/ARM 시험에서 검증한다.

live 정상/제한각3개는 원래 E1 명령·최대4credit·실제tile/metadata8570·receipt/CRC·최종표시 ACK와 finish267→commit285를 확인했다. 단위/오류시험을 제한ROM에서 동시에 모든 STOP 경우를 실행한 증거로 합치지 않는다.

원본은 `../probes/nes-joint295/`에 보존한다. test01 TB 선언순서 compile 실패, test02 partial END를 final로 관측한 tile-count oracle 실패, close01 TB ternary literal 문법 실패도 남겼다. 최종 관측은 `ev&&er&&!ep295`로 프레임 종료만 기다린다. RTL 의미를 완화한 수정이 아니다. 라이선스 실패는 없었다.

재현 도구는 `probe_nes_live295.py`, `probe_nes_native295.py`, `guard_nes_close295.py`, `guard_nes_joint295.py`, `map_nes_joint295.py`, `analyze_nes_joint295.py`다. 시뮬레이션은 승인된 Starter FLOAT wrapper, 합성은 Quartus Lite를 사용한다. 분석기는 source/ELF/RTL/명령·MAP hash를 묶고 `--base ../probes/nes-joint295 --out <새 폴더>`로 실행한다.

source timing replay·기존 ordinary65816 bus trace·map/tile/display bus 모델·84MHz CPI1와 IRQ exception 할당 한계가 남는다. 새 full71 시간/heavy7 live/fullRUN/전체 live65816/CDC STA/실물60fps 증거는 아니다. production227/GBC164/saveSRAM은 변경하지 않았다.

## 다음 경계

별도 BG 완료 E9를 기존 batch 완료 의미와 결합하는 것과, pending DMA/receipt를 기다리는 동안 후속 OBJ plan refill을 진행하는 실행 순서를 함께 비교해야 한다. marker 몇 바이트만 줄여서 회로 부족을 해결했다고 계산하지 않는다. packet reader·descriptor admission·manifest·receipt·retire의 중복 주소/진행 제어를 실제로 제거하되 concurrent CRC tap·독립 검사·RAM port·CDC 비용을 포함해4847→2552 예산 근거가 있어야 한다. 그런 후보에만 전체 Lite와 normal71/heavy7/restricted를 확대한다. 현재295는 후보 기록으로만 남기며 자동 merge하지 않는다.
