# NES263 일반 명령·manifest 생산과 묶음 공통 문맥

현재 PR130의 검증 범위는 일반 SPI 패킷을 읽어 실행하는 native C 소비기와 실제 RTL 버스/CDC/core 연결이다. 일반 명령 전체를65816에서 실행한 결과는 아니다. 별도 실제65816 실험은 동일한 map DMA 경계에서 묶음 공통 bank·generation·token 재사용을 비교한다. 두 실험을 합쳐 full ARM→SNES 프레임 실측으로 표현하지 않는다.

## 확인 결과

기록된 ARM262의71개 계획을 H2·BEGIN·일반 명령·tile·map·manifest·SEAL 순서 그대로 실제 E1 SPI에 보냈다. 이전261/262처럼 sequence/token을 다시 배정하지 않았다.4credit queue, 실제 tile producer, 공유 staging, source/core, 범위별 receipt와 최종 표시 lease를 연결했다. source 83240B, map124묶음/2069범위/13406B, tile 포함 DMA 26350B, 일반 명령 844개, 소비 이벤트 55237개를 검증했다. metadata8570B×71, 최종 receipt754B×71, raw-tail CRC64B×71가 독립 기대 결과와 일치한다.

C 소비기는 실제 SNES packet aperture에서 읽은 bytes를 입력으로 받는다. COPY/FILL/PATTERN, dense/RLE map manifest를 실행하고, tile DMA의 실제 aperture bytes를 range/stream으로 발행한다. CGRAM/raw bitmap의 완전한16B 갱신, raw-tail16개 granule(마지막9B), 매번 새로 받은 scroll terminator까지를 검증한다. 기존 op10/11 manifest를 디코딩하므로 새 SPI 패킷이 없다. 요구 map bitmap과 DMA 전 관찰한 descriptor bitmap을 C에서 대조하고, 별도로 FPGA가 실제 DMA 이후 작성한 receipt를422B manifest와 대조한다. manifest를 receipt 자체에서 만들어 자기 자신과 비교하지 않는다.

새6060..6063 버스 명령은24bit word의3byte와 publish를 쓰고6064의 완료를 확인한다. 기존24bit consumed mailbox의 제어 tag 공간을 공유하여 range/stream/check/hash/finish를 보낸다. H2/BEGIN/map 단계와 배타적이며 mailbox가 남아 있을 때 ordinary ACK를 시도하면 fault로 처리한다. map byte 소비·token4byte 제출·범위별 receipt·최종 ACK는 유지한다. 잘못된 tag나 부분 word, mailbox busy 중 재발행은 fault다.

BEGIN은 기존262의 정확한 기록 packet 검사/ACK 뒤 C 소비기 상태를 초기화한다. C의 임의 BEGIN 의미검사를 실제65816 admission으로 확장했다는 주장은 하지 않는다. C의 metadata/touched/event queue는 검증 저장소이며 MCU/SNES의 새 RAM 할당안이 아니다. 일반 CPU 코드 생성·실행 시간과 대상 RAM 배치는 아직 필요하다. tile 내용도 기록된 planner 출력이며 실제 ROM read 경쟁은 이 실험에 들어가지 않는다.

## 실제65816의 공통 문맥 재사용

기준/재사용 ROM은 각각217B/250B다. 둘 다 bank와generation을 검사하고 매 DMA에서 token4byte를 기록한다. 재사용 버전은6053에서 현재 batch의 남은 범위 수를 한 번 읽고, WRAM에 token을 보관해32bit carry를 포함해 증가시킨다. count가0이 되면 다음 batch의 문맥을 다시 읽는다. FPGA의 token 비교나 DMA 완료 검사를 없애지 않는다.

실제 cold905에서 두 ROM 모두64회 DMA/4096B VRAM 일치, VBlank BG1SC/unblank, 최종 ACK와 core/lease retire를 통과했다.64범위/22batch 기준 bank·generation 읽기는192→66회, token 읽기는260→92회(최종 ACK4byte 포함), count 읽기는0→22회다. token 쓰기는두 버전 모두260회다.

| CPU 비용 | 범위마다 읽기 | 묶음 공통 재사용 |
|---|---:|---:|
|64개 범위 service master clocks|112464|113612|
|최종 표시 ACK master clock|307352|307352|

service는 ready=1 읽기→consume뿐 아니라 consume→첫 다음 status 읽기까지 포함한다. 따라서 consume 뒤 software token 증가 비용도 빠지지 않는다. cold에서는 재사용이 1148master clocks, 약0.053452ms 더 느리다. 묶음당1~3범위라 새 묶음의 count 검사와 범위마다 token 증가 비용이 읽기 감소를 초과했다.

반면 warm907의7범위/1batch/40B에서는 8960→8394master clocks, 566clocks(0.026353ms)를 줄였다. bank/generation 읽기21→3, token 읽기32→8, token 쓰기32회 유지다. 앞선905/906은 기존 RTL 버스 모델로 실행하고 첫 warm CPU DMA 직전에 독립 검증된905 VRAM image를 초기 상태로 넣었다. 변경하지 않은 나머지 map까지4096B를 검증했지만 연속3프레임 실제65816 실행은 아니다. 따라서 항상 재사용을 켜는 방식은 선택하지 않으며, 충분히 긴 묶음의 국소 후보로 남긴다. 다른 warm 범위 길이·refresh 정렬·MCU 경쟁의 WCET는 미측정이다.

readiness polling 대기와 VBlank는 별도다. 최종 ACK는 같은 VBlank에 묶일 수 있으므로 service 절감과 표시 프레임 단축을 같다고 보지 않는다. CPU와 RTL은 file RPC로 논리적으로 연결되어 각각 시간이 흐르며 물리 버스 지연 측정이 아니다. 이 CPU 비교에서 일반 생산자는262 fixture 경계다.

별도 실제65816 mock-bus8사례는47+17범위,16/24bit 경계 token carry,32bit 상단 값, 잘못된 bank/generation/count0/count48을 확인했다. mock 결과를 실제 RTL이나 물리 실행으로 혼동하지 않는다.

## 회로와 전체 비용의 판정

| Lite MAP 동일 통합 경계 | LE | comb | FF | RAM bits |
|---|---:|---:|---:|---:|
|262 기준|7216|5755|2806|90368|
|263 common 조회만|7216|5755|2806|90368|
|263 일반 소비 bridge+common|7287|5791|2842|90368|

묶음 재사용 조회는 기존remaining 값을 사용해 동일 합성 결과를 얻었다. bridge 추가는71LE/36comb/36FF이며 새 RAM은 없다. 이 값은 같은 부분 통합 경계의 MAP이다. 실제 보드 전체의 LE 여유로 빼거나 더하지 않는다. whole FIT/STA를 실행하지 않았으며 기존490LE/40LAB 부족은 해소되지 않았다.

기존 source/queue/bulk/control 제거 장부는lease 제외3336comb/2084FF/98560bits다. 새 core+output의 포함 계층 합계는5587comb/2743FF/90368bits로 장부상+2251comb/+659FF/−8192bits다. 이 장부는 동일 합성 경계가 아니므로 보드 LE 회수량은0으로 남긴다. 계층 수치는 부모와 자식을 중복 합산하지 않았다. 연결 조건이 바뀌면 동일 core RTL도 최적화 결과가 달라지므로71LE 전체를 mailbox 자체의 크기로 귀속하지 않는다.

일반 소비 bridge는 이미 읽은 bytes를 다시 SNES 버스의3byte+publish+poll 이벤트로 보낸다. 이 두 번째 전송 비용이 크므로60fps 구현으로 선택하지 않는다. 다음 숫자는900 master-clock DMA setup,400ns bus byte,560ns 일반 copy/fill byte를 배정한 실제 RTL 일정이다. C 함수 안의 decode 계산은 target CPU 시간으로 청구하지 못했으며 ARM E0 status/refill도 이71프레임 시험에서는 실행하지 않았다. 추가 기능을 포함하므로262와의 차이가 동일 기능 최적화 절감량은 아니다.

| frame |262 출력 모델|263 일반 생산 포함 출력 모델|source+263 출력 직렬 진단|
|---|---:|---:|---:|
|905|16.063080ms|36.017431ms|55.299836ms|
|906|16.139443ms|37.451232ms|41.261278ms|
|907|1.036897ms|3.698092ms|7.782043ms|
|954|3.368141ms|7.258413ms|13.513383ms|
|955|3.369687ms|7.440956ms|11.719950ms|
|963|3.834454ms|6.958962ms|12.024992ms|
|970|3.740182ms|6.625648ms|12.901982ms|

warm 출력 최대7.440956ms(frame955), source+출력 직렬 진단 최대13.513383ms(frame954)다. 16.667ms와의 산술 차이를 사용 가능한 MCU/mapper 여유라고 부르지 않는다. 이전 ARM endpoint의 status bytes·CPI1 시간을 직렬로 더한 민감도도 비용 CSV에 남기지만 polling 횟수와 중첩을 다시 실행하지 않은 수치이므로 상한이나 실제 프레임 시간은 아니다. 기존260 전체 시간에263 출력 증가분을 통째로 더하면 기존에 포함된 일반 wire/서비스를 중복 계산할 수 있다.

## 증거와 다음 경계

test01의 선언 순서 컴파일 실패를 보존했다. test02는 첫 cold 성공/MAP01 결합, test03은 같은RTL의71프레임 결과다. guards01은 정상용 assert가 예상 오류를 먼저 잡았고, guards02는3개 통과 뒤4번에서 시험 구동기 중단 시 read 신호 해제가 빠져 대기했다. 해당 시험 simulator만 식별해 종료했으며 라이선스 결함이 아니다. guards03에서 버스 해제를 고쳐8개를 완료했다. native C16오류와3개 tile byte/범위 분할 벡터, bridge8오류를 검증했다. bridge의 부분 word·잘못된tag·stream8B 뒤STOP·조기최종ACK·manifest/CRC 변조·busy중재발행·잘못된token 시험에서 완료 차단과1024B 공유RAM 동결을 확인했다. 기존262의H2/BEGIN 및 source 검증은 유지한다. CRC는 인증이나 충돌 없음의 증명이 아니다.

바이트별 소비 결과 재전송 bridge는 P2로 선택하지 않는다. 기존 SPI queue의 header/ACK/parser와 manifest 발행 순서를 함께 정리해, 이미 수신한 ordinary payload에서 직접 CRC/receipt를 만들고 두 번째 바이트 전송을 없애는 경계를 검토한다. 독립 manifest 대조·DMA 후 receipt·STOP·최종 표시 ACK를 유지하며 full ARM refill/IRQ·ROM 경쟁과 같은 전체 시간/회로 표에서 판정한다.

다음 후보는 독립 manifest 검사를 유지하면서 순서와 저장 공간을 함께 증명해야 한다. 예를 들어 non-map 요구166B와 map manifest 발행 순서를 바꾸면 decoder가256B bitmap을 별도로 보관하지 않고 순서대로 검사할 가능성이 있지만, HDMA CRC와 receipt/최종 ACK 생명주기를 포함한 검증 전에는 절감으로 계상하지 않는다. 현재의 software 공통 문맥 재사용은 국소 옵션으로 보존한다. P2/full RUN/whole FIT/STA/실기60fps는 미승인이다. production227·GBC164·saveSRAM을 변경하지 않았다.

재현 도구: tools/probe_nes_joint263.py,guard_nes_joint263.py,guard_nes_producer263.py,probe_nes_common263.py,probe_nes_common263_warm.py,guard_nes_common263.py,map_nes_joint263.py,analyze_nes_joint263.py. Questa는 기존 승인된 FLOAT wrapper에서 새 ASCII run directory로 실행하고, MAP은 Quartus Lite만 사용한다. CPU 기준은 --cached 없이, 재사용은 --cached를 사용한다. warm907은 probe_nes_common263_warm.py로 별도 실행한다. native C는 Questa DPI 실행 모델이다.
