# NES324 — 소비 ABI와 독립 검증 경계 재설계

319+317 metadata 선행 발행을 비교 기준으로 유지한다. 이번 작업은 기존 실제 ARM/RTL/65816 trace와 전체 Lite 보고서를 재분석한 구조 검토다. 새 RTL·ARM·65816 실행이나 Quartus 합성은 하지 않았다. 323의 −11comb와 cold 회귀는 보존하며 새 후보의 절감으로 합산하지 않는다. 재현 가능한 입력 해시와 집계는 `analysis/abi324-verification.json`, 분석기는 `tools/analyze_nes_abi324.py`다.

## 기존 byte ABI가 남기는 비용

319는 압축 payload를 staging에 전달하고 SNES가 6060..6068의 op/section/start/encoded/span/bank를 읽어 해석한다. FPGA는 같은 명령으로 receipt 좌표를 만들고, encoded staging read와 별도로 RLE를 순회하여 scroll/raw CRC를 계산한다. 323은 unit 좌표를 도입했으나 SNES용 byte 주소를 다시 복원했기 때문에 양쪽 비용이 남았다.

기존 CPU313 trace의544 ordinary 명령에서 descriptor 읽기는4,896회(명령당9), token 읽기/쓰기는각2,176회(명령당4)다. 출력은128,041B, service는3,027,214 master clocks이며 그중 dma_setup_service 집계는753,566이다. 이는71프레임 입력의 별도 CPU 시험 집계이고 319 warm 한 프레임 시간으로 더하거나 전량 제거 가능한 시간으로 볼 수 없다. token의4회 쓰기는604C..604F, 완료는6059다.

현재 독립성은 **별도 manifest 기대 coverage/CRC와 실제 staging 순차 읽기·token 완료의 비교**다. cartridge read 관측만으로 PPU 목적지 쓰기를 직접 증명하지는 않는다. 새 ABI도 ARM의 receipt 필드를 기대값과 실제값 양쪽에 복사해서는 안 되며, 목적지 관계는 고정 domain 규칙과 실제65816 PPU/WRAM 실행 시험으로 결합해야 한다. 이것은 물리 SNES 쓰기 전부를 FPGA가 관측한다는 주장이 아니다.

## 후보 비교

| 후보 | 실제 삭제 가능한 경계 | 추가 비용/판정 |
|---|---|---|
|unit descriptor를 SNES가 직접 소비|FPGA의 구형9B descriptor 복원 mux, SNES 구형 section 해석을 새 domain 해석으로 대체|SNES base/shift 계산은 남음. RLE CRC shadow와 validator 제어가 남아 단독 해결 후보로 부족|
|ARM에서 literal로 전부 확장|FPGA/SNES RLE 실행 제거|warm907 payload만+1,604B, 아래 비용 때문에 우선 제외|
|압축 wire 유지, FPGA에서 한 번 확장하여 native 소비 record+검증 event 생성|구형 byte ABI 복원, host RLE CRC shadow, SNES RLE 해석을 함께 대체|공유 staging write 중재·확장기·chunk 완료 비용을 새로 청구. 우선 최소 실험할 구조이며 아직 채택 아님|
|ARM이 DMA 주소와 receipt를 모두 제공하고 FPGA가 그대로 승인|주소 계산을 많이 없애는 듯 보임|주소와 receipt의 독립 관계가 사라지므로 제외|

실제319 전송9일정(3프레임×고정/제한/정상)에서 ordinary op2/4/5/8은 동일했다. tile op7/map batch는 이 표 밖이다.

| 비용 |905|906|907|
|---|---:|---:|---:|
|ordinary 명령|29|29|6|
|압축 payload B|2,848|2,840|109|
|확장 출력 B|4,474|4,474|1,713|
|ARM literal 전송의 payload 증가 B|1,626|1,634|1,604|
|기존240B payload 한도로 추가 패킷|5|5|5|
|추가 E1 header/CRC B|95|95|95|

warm의 증가 최소1,699B는 응답·credit·CS·ARM 준비를 제외한 수치다. 순수 wire 증가는8×1,699/R초이며 R은 SPI bit/s다. 기존 zero-bank 재사용도 이 단순 literal 후보에서는 잃는다. 새 응답 수를 이전323의+47B로 대신 계산하지 않는다. ROM 대기와 겹칠 수 있으므로 wire 시간을 그대로 frame 회귀로 합산하지도 않는다.

## 우선 후보의 구체적 인터페이스

wire는 압축 및2슬롯, batch와 metadata 선행 정책을 유지한다. SNES 공개 record는 고정 domain, unit_first, unit_count, 유효 마지막 byte 수, staging offset, 소비 byte 수, bank/generation/token과 mode(STREAM 또는 검증된 REUSE)로 구성한다. **아직 packing/길이는 확정하지 않았다.** 구형6060..6068 byte descriptor와 병존시키지 않는다. SNES가 고정 domain template으로 VRAM/CGRAM/OAM/WRAM 목적지를 결정하며 arbitrary PPU 주소를 wire로 허용하지 않는다. raw 마지막9B와 fresh byte domain은 명시적으로 검사한다. 새 record 읽기가 기존9B보다 늘면 실제 CPU 시간에 청구한다.

validator 입력은 기존 host의 ordinary_range/first/end, 별도 tap/hash continuation 묶음 대신 다음 transaction으로 바꾼다.

1. `begin(epoch,serial,bank,generation,token,domain,first,count,valid_tail,mode)`에서 lease·한도·identity를 검사한다. 별도 receipt 주소는 받지 않는다. 고정 domain-to-coverage 관계만 사용한다.
2. `read_accept(token,index,value)`는 실제 SNES staging read strobe에서만 발생한다. validator의 독립 cursor가 index 연속성·정확한 길이를 확인하고 해당 expanded value로 CRC를 진행한다. producer의 staging write는 소비 event가 아니다.
3. `consume_commit(token)`는 정확한 읽기 수·token4B·완료 strobe를 모두 충족한 뒤 receipt를 확정한다. manifest expected cursor는 이 cursor와 공유하지 않는다. coverage와 CRC는 별도 expected stream과 대조한다.
4. REUSE는 기존 유효 bank/generation/hash/길이 증거가 모두 있는 경우만 허용한다. 읽기 생략을 임의의 read_accept로 위조하지 않는다. 재사용 invalidate/STOP 경로와 SNES의 실제 zero/native DMA 동작 검증을 유지한다. REUSE 전용 제어는 남는 비용이다.

expanded staging의 CRC 순회와 SNES RLE expansion을 둘 다 없애려면 실제 데이터 경로를 이 방식으로 바꿔야 한다. 이름만 event로 바꾸고 옛 tap FSM을 남기는 구현은 교체로 인정하지 않는다. CPU 목적지/패턴 회전/partial tail은 독립 원본 byte oracle과 실제65816 실행으로 확인한다.

## 삭제·유지·추가 경계와 RAM 소유권

삭제 대상은 host의 구형 byte descriptor export와 역변환, receipt용 byte→granule 감산/경계 분류, 별도 RLE shadow tap_pos/tap pattern 순회, SNES의 압축 명령 dispatch다. 기존 주소 식 일부는 새 domain template/독립 한도 검사로 대체되므로 전량 LUT 절감으로 세지 않는다. manifest parser의 압축 해석은 아직 삭제 대상이 아니다. expected446B 재읽기와 검사도 그대로 청구한다. source/plan FSM도 이 ABI만으로 없어지지 않는다.

추가는 단일 literal/RLE staging producer, domain dispatch, chunk cursor와 completion, validator transaction cursor, SNES native consumer다. 기존 tile/map producer와 staging write 포트를 공유한다. 기존4KiB staging을 확장하겠다고 가정하지 않는다. chunk가 소비될 때까지 해당 범위를 재사용하지 않으며 tile producer와 동시 write 불가, DMA·plan refill 우선권과 starvation 상한을 실제 일정에서 검사한다. 큰 command는 packet을 더 보내지 않고 로컬 chunk로 처리할 수 있지만 추가 SNES setup/IRQ/readiness 비용을 반드시 측정한다.

queue port A는 SPI ingress, port B는 실행기 slot/canonical 접근을 유지한다. phase RAM validator 포트와 persistent valid/hash는 살아 있으므로 공짜 공유 포트나 RAM 회수로 세지 않는다. 저장 credit은 encoded payload를 모두 안전하게 확보하거나 소비한 뒤만 반환한다. 아직 읽을 queue payload를 가리킨 채 slot을 재사용할 수 없다. source/plan 포트와 clock-domain mailbox도 유지한다.

STOP은 producer pending write·validator pending receipt를 무효화하고 ROM 응답을 drain한다. 재시작 token/bank/generation 혼동을 거부하고 STOP 이후 RAM write/seal/display-ready/finalACK를 금지한다. 최종 ACK는 독립 coverage/CRC seal과 VBlank 표시·12회 display read/token 절차 뒤에만 허용한다. metadata 선행 발행은 terminal 소비 완료를 뜻하지 않는다.

## 전체 예산과 실험 중단 기준

측정된319 전체 Lite는22,618LE /17,824comb /9,022FF /307,808RAM bits다. 목표15,408comb까지2,416이 남는다. host+validator3,492만으로 해결하려면1,076 이하(69.2% 감소), 전체 교체 경계6,700을 쓰면4,284 이하가 필요하다. source+plan2,235를 모두 공짜로 만들어도 부족분을 메우지 못한다. 따라서 위 ABI는 **작은 통합 시험 후보**이며 목표 달성이 가능한 회로 구조로 확정한 것이 아니다. 새 comb/FF/RAM/ARM cycle은 null로 남긴다. 삭제 식 개수와 FSM 개수로 채우지 않는다.

제한907의17.119885468ms에서0.453218801ms를 줄여야 한다. 마지막 소비 이후0.236063ms를 전부 없애도 앞 구간0.217155801ms 개선이 필요하다. 이번 후보가 terminal 검사를 유지하므로 실제 필요한 upstream 절감은 이보다 크다. expanded staging은 SNES 바이트 이동이 늘 수도 있으므로 service 전체를 이득으로 잡지 않는다.

최소 구현 순서는 새 native consumer와 transaction checker를 동일 압축 입력의 한 ordinary 경로에 연결하고, old byte export/RLE shadow를 실제 삭제한 뒤 cold 경계·raw9B·REUSE를 검사하는 것이다. 이어319와 동일 source 시작/ROM cycle 고정 A/B 및 정상/제한 연속905/906/907에서 실제 ARM instructions/IRQ·E1/E2/E9·2슬롯 credit·staging wait·ROM request/accept·최종 ACK를 비교한다. metadata 준비는 DMA/plan/IRQ보다 낮은 우선순위로 유지한다. 시작 위상 이동과 ROM 허용창 수락 단축을 분리한다.

fault 시험은 잘못된 domain/count/tail, 반복/누락 read, 값 변조 CRC, descriptor 목적지 변조, premature consume/finalACK, stale reuse/token, 두 슬롯 overwrite, 확장 중 STOP/ROM drain을 포함한다. baseline 검사와 독립 원본 oracle을 유지한다. 이후 같은 전체 보드 경계의 Quartus Lite MAP 한 번으로 평가한다. 시간 또는 전체 comb가 회귀하거나 새 buffer/port 비용이 예산을 깨면 후보를 중단하고 전송/표시 역할을 다시 검토한다. 국소 MAP 절감으로 whole deficit 해소를 주장하지 않는다. FIT/STA/실물60fps/full71 ARM은 여전히 미검증이다.
