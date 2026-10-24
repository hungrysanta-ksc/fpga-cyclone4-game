# NES312 record admission·2슬롯 실측 — 전체 실행기 교체는 미완료

**요청한 NES311 전체 교체는 아직 완료하지 못했다.** 이번 코드는 실제 ARM·IRQ·ROM 경로의 부분 교체 실험이며 최종 채택하지 않는다. 기존307 대비 시간·면적 동시 개선에 실패했다. canonical manifest 저장/late walker, ordinary의 공통 staging 소비, validator packet/RLE·완료 relay 삭제 및 새65816 소비 프로그램은 남아 있다. 2슬롯 배치 자체의 원리적 불가능을 증명한 결과도 아니다.

## 구현과 삭제 증거

- queue의4slot 주소, `lengths[4]`, host `HREAD/HCAP` raw header 읽기를 삭제했다. admission이 physical sequence/serial/generation/실제 wire 길이/CRC를 검사하고24B record와 compact payload를 두272B slot(480,752 시작)에 기록한다. batch token/count는 record로 옮기고3B range entry를 유지한다.
- queue RAM은 실제1024×8 M9K이며 단일 write/read 포트로 추론된다.0..479는 예약만 되어 있고 canonical manifest446B/directory32B의 기능 구현 완료가 아니다. receipt bounds는 아직 host에서 계산한다. encoded length도 기존 wire plen 의미이며 codec/receipt record 필드는 최종311형식으로 이관되지 않았다.
- 두번째192bit queue snapshot을 삭제하고 기존145bit active record에 reader 결과를 직접 넣는다. record의 가상 header view는 기존SNES/validator adapter 호환용이며 **삭제되지 않은 비용**이다.
- storage release와16bit 실제 소비 counter를 분리했다. 마지막batch의 staging 저장 후 slot을 반환하고 actual DMA/receipt까지 active record와 staging owner를 고정한다. metadata는 소비 counter에 포함하지 않는다. ordinary는 아직 receipt 뒤 slot을 반환한다.
- E2는14B/tag FB, E0는26B/tag FC다. CRC는 소비 counter까지 포함하며 ARM이 미래/역행/과대 credit을 거부한다. 짧은E9는 plan cache를 무효화해 checked E2를 사용한다. E1 공간이 없어도 기존E9 refill/IRQ 처리를 수행한다.
- 최종 ACK는 loader의 `packet_ready` 대신 실제 저장 occupancy가0인지 확인한다. record 로드 중인 nonempty queue를 empty로 오인하지 않는다. 기존12 display reads/token/VBlank 경로와 독립 receipt/CRC/H2는 유지했다.

`NORMAL/ACKWAIT/OSETUP/OTILE/OSELECT/XWAIT`, batch range parser, validator `E_READ/E_CAP/E_NEXT/E_ZERO` 및 SPI/plan의 별도 실행 제어가 남는다. 이 코드를 공통record 실행기 전체 구현이라고 표시하지 않는다. source/production227/GBC164/saveSRAM 변경은 없다.

## 동일 실제 ARM·IRQ·ROM 일정

단위ms. 실제 Cortex-M4 명령을 실행한 CPI1/84MHz 모델과 actual tile ROM/core 경쟁을 사용한다. ordinary65816은 기존 기록 bus trace 재생이며 새 full CPU 실행이 아니다. 정상/제한 각905..907을 같은 코드/RTL로 실행했다.

|모드/프레임|전체ms|307 대비ms|ARM instructions|SPI bytes|
|---|---:|---:|---:|---:|
|normal/905|86.010559|+7.517501|2254193|10448|
|normal/906|62.555931|+7.603272|1638508|11032|
|normal/907|14.992547|+0.635856|700000|1137|
|restricted/905|111.075894|+7.421138|2261000|10602|
|restricted/906|133.155357|+16.253623|1649508|11284|
|restricted/907|27.048357|+9.431432|703536|1221|

제한907은 시작286.323382 → 첫BG tile 307.393834 → 완료313.371739ms다. 시작→BG 21.070452ms, BG→완료 5.977905ms다.307의 같은 first-tile 표식은12.256694/5.360231ms다. ROM 허용 창과core 경쟁 규칙을 변경하거나 유리한 위상을 고정하지 않았다. 기존311의 BG grant 표식보다 first-tile 표식이273ns 뒤이므로 두 표식을 혼용하지 않는다.

제한907의 E2 31회/434B, E0 4회/104B와 실제 IRQ/추가polling을 모두 포함했다.307 E2 25회/300B, E0 4회/96B와 비교한다. 실제 전체 SPI는+142B, ARM은+6518명령이다. 고정 횟수의2B 증가만으로 전체 회귀를 설명하지 않는다. cold905/906의 일정 변화에 따른 다음 frame 시작/ROM 대기도 포함한 결과다.

60fps 예산16.666667ms보다 제한907이10.381691ms 초과한다. 마지막batch의 storage release→receipt 지연은 각 실제 이벤트로 별도 기록했고, 반환 후 descriptor/staging 불변도 검사했다. 저장 credit을 소비 완료로 계산하지 않았다.

## 전체 Quartus Lite

|지표|307|312|변화|
|---|---:|---:|---:|
|LE|22402|22884|+482|
|comb|17583|18061|+478|
|FF|8965|9023|+58|
|RAM bits|307808|307808|0|

comb15408 기준 부족분은2175→2653이다. host own comb2093→2029(-64), queue118→561(+443), SPI713→779(+66), validator1251→1284(+33)다. parent/child를 합산하지 않으며 나머지 전체 최적화 영향까지 whole MAP 결과를 사용한다. validator 소스가 같아도 통합 최적화 결과가 달라질 수 있다.

초기board01은 여러 procedural write 분기가 RAM을register로 바꿔25426comb/17415FF/299616bits가 되어 폐기했다. board02에서 단일 port로 고쳐18200comb/9215FF/307808bits를 얻었고, board03은 두번째record snapshot을 삭제했다. board04는 실제 occupancy 최종ACK 검사까지 포함한 최종 source다. 새control latch/undriven은 없고 기존ROM `cache_index141` latch 경고는 유지된다. FIT/STA/seed 반복은 하지 않았다.

## 검증·보존·남은 작업

- SELECT: `window06`, `normal01`, `board04`, `guards03`, `retained04`, `armguard02`, `supply01`; local archive `probes/nes-slots312`.
- live6 frames의 metadata/receipt/CRC/final ACK 및 최대2credit PASS. queue RTL14건(최대payload/compact batch·typed/CRC/identity/길이/가득참/wrap/STOP), 기존 독립 검사·STOP·최종ACK25건, actual ARM counter/CRC/credit20건, 공급 우선순위20건 PASS.
- 실패 window01 forward declaration,02 기존12B prefill,03 오래된 queue-head 소유권 assertion,04 기존raw queue observer 주소를 보존했다.05는 두번째snapshot이 남은 중간PASS이며 최종 선택이 아니다.
- retained01의 삭제한HCAP 주입 참조와02/03의 fixture4credit 발행을 보존했다. 수정 전 일부 PASS는 최종 guard 증거로 세지 않는다. retained04만 사용한다.
- ARM text=28238B/BSS=47132B/observed stack=1288B. fullRUN/전체71·heavy7/live새65816/FITSTA/실물60fps는 미검증이다.

재현: `tools/probe_nes_live312.py`, `tools/guard_nes_slots312.py`, `tools/guard_nes_record312.py`, `tools/guard_nes_credit312.py`, `tools/map_nes_slots312.py`, `tools/analyze_nes_slots312.py`. Questa는 기존 승인된 임시FLOAT wrapper, 합성은 설치된Quartus Lite를 사용했다.

이번 부분 adapter를 최종312공통실행기로 오인하지 말 것. ordinary 가상header/queue read·ACK relay와 validator packet/RLE·completion을 실제 삭제하고 canonical expected manifest walker 및 staging descriptor 소비로 연결하는 코드가 남음. 두 슬롯은 새 실행기에서 재평가할 미채택 배치이며 부분 adapter 미세합성/seed/FIT 반복 금지. 독립 receipt/CRC/H2·STOP·12read/token/finalACK·VBlank 및 고정 ROM 창을 유지. 307 대비 전체 최소2175comb/.950258ms 개선 gate 유지.
