# NES265 header·ACK 교체와 내부 manifest 소비

기존 queue의 ACK 저장·header 재읽기를 제거하고, 검사 전용 requirements/map manifest/fence를 SNES에 노출하지 않도록 실제 RTL 경로를 바꿨다. 바이트 재전송 제거의 이득은 유지됐지만, 표시 문맥 보관과 새 제어를 포함한 동일 통합 경계는 **8230→8277LE(+47)**다. 시간과 면적을 모두 만족한 생산 후보로 선택하지 않는다.

## 실제 대체한 제어

queue의96bit ACK 저장소,12bit mask,checker index/wait/checking/valid,header 재읽기 주소 mux와 ACK 인터페이스를 제거했다. queue는 SPI 수신·불변4slot·parser retire만 담당한다. F8 status의 기존 ack_valid bit는0이며, ARM264 endpoint도 이 bit가0인 상태를 사용했으므로 실제 serializer bytes는 변경하지 않았다.

flow의 HCAP에서 packet sequence16/serial32/generation16을 이미 소유한 admission 문맥과 바이트별 비교한다. header[2..9]는 저장하지 않는다. 일반 ACK도 동일 identity 기대값과 opcode/sentinel을 순서대로 비교하며, header/read에 쓰던 at를 ACK 진행에 재사용한다. ACK12B와 publish1B 형식은 유지한다. 따라서 ACK 통신량까지 줄였다는 주장은 아니다. 순서 누락·중복·stale sequence·잘못된 serial을 거부한다.

일반 packet 전체 순차 읽기, tile DMA 전 byte 읽기와 정확한 token consume 조건은 그대로다. 검증된 ACK 이후에도 queue head/credit는 direct payload CRC·receipt 완료까지 유지한다. map batch는 각 범위의 실제 DMA·receipt 이후 마지막에만 retire한다. input commit ACK, queue retire, 최종 표시 ACK는 서로 다른 사건이다.

## manifest와 표시 문맥

op15 requirements→op10/11 dense/RLE map manifest→op3 fence를 동일 immutable queue port에서 FPGA가 직접 처리한다. 독립 요구 bitmap과 실제 receipt의 비교를 유지하며, SNES의 이 packet 읽기/ACK는 모두0이다. oracle은 실제 수신 queue RAM을 수동 관찰할 뿐 RTL에 값을 주지 않는다. 일반 실행은 기존 native C + SNES 버스 모델이다.

71프레임에서 내부 packet 215개, SNES packet 읽기 23062B와 ACK write 2795B를 제거했다. 대신 op15의16..39번24B 표시 문맥을 명시적 register 배열에 보관한다. sealed 이후6070..6087에서 순차1회 읽고 모두 읽기 전 최종 ACK를 거부한다. 새 문맥 읽기는총1704B, 순감소는24153 bus bytes다. 저장소·주소 mux·읽기 coverage 제어 모두 아래 MAP에 들어 있다. 추가256B bitmap이나 M9K는 없다.

24B 전달·bank 재사용·읽기 완료 소유권은 검증했다. 해당 설정의 모든 의미를 H2와 묶는 검사, 실제65816의 PPU 설정·VBlank 적용은 아직 구현/검증하지 않았다. 이를 완성된 표시 검증기로 부르지 않는다. 기존264의 단일 packet active-scroll prefix와 정렬된 raw-tail granule 제약을 유지한다. CRC는 인증/충돌 없음의 증명이 아니다.

24B의 구성은6개 section 길이12B,hofs/vofs4B,budget2B,mask2B,version2B,raw-count2B다. 수신71프레임에서 mask/raw-count가 기존 H2의 값과 모두 일치함을 별도 분석했다. BG/OBJ 길이와 hofs는 변하며, 이번 기록에서 고정인 나머지 값을 곧바로 production 상수로 축소하지 않는다. 다음 구조 후보는 이미 보관한 H2의 중복값을 재사용하고 실제65816에 필요한 필드만 확정하는 것이다. 이 분석을 RTL 의미검사나 회수된 FF로 계산하지 않았다.

## 같은 경계의 합성 비용

|Quartus Lite MAP|264|265|차이|
|---|---:|---:|---:|
|LE|8230|8277|+47|
|comb|6745|6760|+15|
|FF|2884|2924|+40|
|RAM bits|90368|90368|0|
|queue comb / FF|749 /436|586 /319|−163 /−117|
|output 포함 comb / FF|3489 /1797|3523 /1837|+34 /+40|
|core 포함 comb / FF|3052 /987|3041 /987|−11 /0|

부모/자식을 중복 합산하지 않았다. core source는264와 같으며 해당11comb 차이를 별도 설계 회수로 귀속하지 않는다. 전체490LE/40LAB 부족에 부분 경계의 queue 절감을 직접 빼지 않는다. proven whole-board LE reclaim=0, whole FIT/STA/CDC/IO는 미실행이다.

모듈 합성 경계는 같지만265에는24B 표시 문맥 보관이 명시적으로 추가됐다.264는 C oracle에 requirements를 보관했으며 실제 SNES WRAM/코드 비용은 미측정이었다. 따라서 이 표는 header/ACK 단독 절감량이나 완성된 전체 시스템의 동등 기능 비교가 아니다. 새 경계에서 빠뜨렸던 저장 비용까지 포함한 순변화를 보여 준다.

register 값 after_event로 복귀하던 제어를3bit operation selector와 상수 다음 상태 case로 바꿨다. 이번 합성에서는 output main state가 다시 FSM으로 추출됐다. ACK/header/manifest/표시 문맥을 함께 바꾼 결과이므로 FSM 추출 하나의 독립 절감량은 없다. FSM 추출 성공 자체가 전체 면적 감소를 보장하지 않는 실제 반례다. 추가 seed/FIT 반복은 하지 않았다.

## 시간 비교

같은900 SNES master-clock DMA setup,400ns bus byte,560ns ordinary byte 배정과 실제 RTL 완료 시점을 비교했다. 제거된 bus bytes를 별도 절감으로 더하지 않는다. SPI 수신과 겹친 SNES 작업은 critical path에서 그만큼 줄지 않는다. 신규24B 문맥 읽기와 FPGA 직접 해석 시간도 포함된다.

|frame|264 출력 ms|265 출력 ms|추가 절감|source+265 직렬 진단 ms|
|---|---:|---:|---:|---:|
|905|26.843405|26.823542|19.863µs|46.105947|
|906|27.889756|27.868211|21.545µs|31.678256|
|907|2.564515|2.540606|23.909µs|6.624557|
|954|5.630069|5.569706|60.363µs|11.824676|
|955|5.748795|5.689614|59.181µs|9.968608|
|963|5.911611|5.846112|65.499µs|10.912142|
|970|5.679114|5.615842|63.272µs|11.892130|

warm 출력 최대 5.846112ms(frame963), source+출력 직렬 진단 최대 11.892130ms(frame970)다. 모든 warm 출력에서 최소 23.909µs의 추가 절감을 확인했다.263 byte echo 제거 이득도 유지한다.

ARM264 실제 Cortex-M4 실행 결과의 E1 packets를 sequence/token 변경 없이 재사용했다. 새 ARM 실행이나 새 poll 횟수를 주장하지 않는다. E1 byte 수,2472B text/312B static/144B 관찰 stack은 이전 evidence다. 별도 E0/CPI1 직렬 민감도 최대는 19.666951ms(frame970),warm 9프레임이16.667ms를 넘는다. 이는 retimed 공유SPI 일정이나 WCET가 아니며60fps 가능/불가능 판정 근거가 아니다.

native C 계산 시간, 실제 일반65816,full ARM 입력/plan/refill/IRQ,실제 tile ROM 중재,VBlank와 물리 timing은 열려 있다. 이전263의 CPU 국소566clocks 절감도 중복 합산하지 않는다.

## 검증과 재현

71프레임 source83240B,124 map batches/2069 ranges/13406 map bytes,총DMA26350B,metadata8570B·receipt754B·retained CRC64B가 매 프레임 독립 기대값과 일치했다. 일반 packet은915→700개(별도 BEGIN 제외),내부 packet 215개,byte echo0,최대4credit다. 수신 ARM packets와 source outputs를 모두 바이트 비교했다.

29개 RTL 오류는 기존19개 ACK·누락 읽기·scroll/manifest 변조·token/bank/generation/sequence·STOP/조기ACK·RLE 검사를 새 경로에서 다시 실행하고,ACK byte 누락/serial 변조/중복/stale sequence/마커 누락/마커 변조,표시 문맥 마지막 byte 누락/순서 오류,내부 manifest 중 ACK/STOP을 추가한 것이다. 모두 완료 차단과1024B shared RAM 동결을 확인했다. C oracle이 먼저 막지 않도록 오류 실행에서는 해당 oracle 실행을 비활성화했다.

선택: test04(71)/guards01(29)/map01/analysis02. MAP01은cold test03으로 먼저 검사한 RTL에 묶었고 test04·guards01도 같은 전체 RTL hash임을 확인한다. test01/02는 테스트 생성기 assertion 실패이며 compile 전이다. 최초 wrapper의 sandbox TEMP 경로 불일치도 기록했다. 라이선스 오류가 아니다. analysis01은 source cycle이264와 완전히 같다는 잘못된 가정으로 실패했다. 새 출력 일정에서9프레임이±1cycle 달랐으며, source bytes는 모두 같고 analysis02는 실제 새 cycle을 청구한다. 원시 실패/성공 로그를 보존한다.

재현은 승인된 FLOAT wrapper에서 probe_nes_joint265.py 및 guard_nes_joint265.py를 새 ASCII 실행 폴더로 실행한다. map_nes_joint265.py --test 통과폴더는 Lite MAP만 실행한다. 분석은 보존한 probes/nes-joint265를 대상으로 analyze_nes_joint265.py를 실행한다. ARM264 입력·이전 기준과 해시를 함께 검증한다.

24B 표시 문맥의 의미·H2 결합과 실제65816 설정/최종 VBlank ACK를 먼저 확정하고, 문맥·parser 상태를 기존 phase RAM에 함께 넣는 교체 경계의 포트/수명/전체 비용을 비교한다. ACK 12B 축소는 stale serial/generation/sequence 방어를 유지할 때만 후보로 삼는다. ARM E0 refill/IRQ와 실제 tile ROM 중재를 같은 일정에 연결해 전체 시간·회로 게이트를 확인한다. 단독 FSM/opcode/seed/FIT 반복이나 개별 계층 절감의 보드 회수 환산은 하지 않는다.

production227·GBC164·saveSRAM은 변경하지 않았다. 새 firmware ZIP/실기 배포/머지는 하지 않는다.
