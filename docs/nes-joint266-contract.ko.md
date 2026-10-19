# NES266 H2·phase RAM 표시 문맥과 실제65816 최종 ACK

H2에서 이미 보관하는 표시 정보를 재사용하고, 별도24B 표시 register 배열을 없앴다. 기존1024×8 phase RAM의864..867에 화면 오프셋4B만 보관한다. 새 검사·RAM 읽기·양방향 CDC를 포함한 같은 통합 경계가 **8277→8149LE(-128)**로 줄었다. 기존 byte echo/manifest 재읽기 제거 이득도 유지했다. 부분 통합 비교의 시간·회로 개선이며, 전체 보드 배치 또는60fps 달성은 아니다.

## 실제 대체와 RAM 수명

기존 ARM264의 op15 payload24B는 wire 형식 변경 없이 FPGA에서 검사한다. BG 길이는16B 정렬/최대16384B,OBJ는32B 정렬/최대4096B를 확인한다. map4096/CGRAM512/OAM544,version2472,budget4192를 확인한다. mask/raw count는 H2와 비교하고 HDMA length는raw일 때3418,그 외에는H2 scroll length와 비교한다. 이 필드들은 검사 후 별도 저장하지 않는다. hofs/vofs의16bit 값4B만 저장한다. H2 CRC는 인증이나 충돌 없는 증명이 아니며, 실제 receipt·raw CRC·scroll digest 검사는 계속 유지한다.

RAM 배치는valid0..331,retained rawCRC332..395,received396..561,map562..817,H2 832..863,offsets864..867이다. 입력 source scratch512..1023의 소유권이 끝난 출력 phase에만 재사용한다. A port의D_CHECK는864..867에만 쓰고,H2/receipt의B port와 주소 충돌이 없음을 검사한다. 잘못된 필드·STOP·fault 뒤에는 새 쓰기를 허용하지 않는다. 매 frame24B를 모두 검사하기 전 receipt 요구사항 검사와 seal에 진입하지 못한다. 기존 source rec_i/build_i와 h_count/v_value를 해당 phase에서 재사용한다.

sealed 이후12B view는bank,mask,raw count,scroll length2B,raw HDMA lengths3B,offsets4B다. H2의8B와 phase RAM의4B를 읽으며,24B register 배열의 복제본은 없다. SNES는6054 ready를 확인한 뒤6070..607b를 순서대로 한 번 읽는다. 모든12B를 읽고 마지막 map token을 정확히 제출한 경우에만6058 최종ACK를 허용한다. 이 ACK 이전에는 display lease를 유지한다.

요청은 기존24bit consumed mailbox의kind8,op15검사는kind7을 쓴다. 응답은 기존 NES→host receipt mailbox를1→8bit로 넓혀 재사용한다. map receipt와 최종 표시 응답은 시간상 겹치지 않는다. 추가 동기화/ready/주소선택/FSM 비용과 왕복 지연을 아래 측정에 모두 포함했다. 새 RAM block이나 clock domain 간 직접 RAM 읽기는 없다.

## 회로 비용

|같은 통합 MAP 경계|265|266|차이|
|---|---:|---:|---:|
|LE|8277|8149|-128|
|조합 함수|6760|6830|+70|
|FF|2924|2755|-169|
|RAM bits|90368|90368|0|

실제 source/core,공유SPI queue,일반/typed parser,tile/map staging,receipt,표시 lease와 새 문맥 경로를 함께 합성했다. 출력 flow와 core 모두 FSM으로 추출됐다. 의미검사와RAM/CDC 읽기 제어로 조합 논리는 증가했지만,register 중복 제거를 포함한 통합 LE는 감소했다. 개별 계층 합계를 더하거나 원인을 단일 FSM 최적화로 환산하지 않는다. 세부 hierarchy는verification JSON에 보존한다.

Quartus **Lite25.1std MAP1회**이며,cold test02로 통과한 RTL hash에 묶었다. full71/guards/65816도 같은 RTL이다. 전체 보드 연결·FIT·배치·STA·CDC/IO 검증은 아니다. 기존240의490LE/40LAB 부족에서128을 빼서362LE라고 주장할 수 없다. mapper 여유와 최종 보드 margin은 미확정이다.

35개 경고의 종류별 개수는265와 같다. async_reg 속성 무시,기존 dual-clock transport RAM의read-during-write 경고,폭 절단/상수출력 경고를 원시 로그에 유지했다. 같은 경고 개수가 CDC 안전성 증명은 아니며,추가 waiver나 STA 통과 주장은 없다.

## 같은 서비스 배정에서의 시간

900 SNES master-clock DMA setup,400ns bus byte,560ns ordinary byte 배정은265와 같다. 실제 새 RAM/CDC/parser 상태와 ready polling을 포함한 출력 완료 시점을 비교했다. 단순 bus byte 감소량을 추가 절감으로 더하지 않는다.

|frame|265 출력ms|266 출력ms|265대비 추가µs|264대비 유지 절감µs|source+출력 진단ms|
|---|---:|---:|---:|---:|---:|
|905|26.823542|26.824724|1.182|18.682|46.107129|
|906|27.868211|27.869393|1.182|20.363|31.679438|
|907|2.540606|2.541879|1.273|22.636|6.625830|
|954|5.569706|5.570933|1.227|59.136|11.825904|
|955|5.689614|5.690932|1.318|57.863|9.969926|
|963|5.846112|5.847475|1.364|64.136|10.913505|
|970|5.615842|5.617296|1.455|61.817|11.893630|

warm 출력 최대5.847475ms,source+출력 직렬 진단 최대11.893630ms다. 새 문맥 경로의265대비 최대 추가는1.455µs이고,264대비 모든warm에서 최소22.636µs의 절감이 남았다. 문맥 data는24→12reads이나 ready poll도 청구했다(71프레임총1064회). 실제source cycle도 새 replay값을 쓴다. byte echo0과내부 manifest215개 처리는 유지한다.

별도 ARM E0 polling+CPI1 직렬 민감도 최대19.668451ms이며,warm9개가16.667ms를 넘는다. 이 값은 retimed SPI 일정/WCET가 아니므로60fps의 성공/불가능 판정이 아니다. actual ARM264 E1 bytes는 변경 없이 재사용했으며 새 full ARM RUN/IRQ 실행은 아니다.

## 실제65816 표시·HDMA·최종ACK

Mesen에서 실제415B 65816 ROM을 실행했다.905/906/907의은행0/1/0을 각각 actual RTL의seal까지 진행한 뒤,CPU가12B view를 읽고VBlank를 기다려 BG/OBJ/map bank,window mask,16bit scroll,HDMA channels1/2/3를 설정한다. 마지막map token4B와6058 ACK가 실제 mailbox를 지나 core/lease를 retire하는 것까지 확인했다. ACK 뒤 한 visible frame의 실제HDMA WRAM 읽기도 각source table의 기대값과 비교했다.

각 run에서 앞선 frame들은 native C/bus모델로 진행해 persistent bank/CRC 이력을 유지했다. 일반명령·tile/mapDMA 전체를 이ROM이 실행한 것은 아니다. HDMA WRAM은 매frame 독립 검증한8570B metadata에서 명시적으로 preload했다. 전체 렌더링 픽셀이나 실제upstream DMA를 검증했다는 주장도 아니다. 관찰된mask18/raw2 세 프레임이며,raw0/mask1e의 실제CPU 실행은 새 증거에 포함하지 않는다.

Mesen 로그에는 preload한HDMA 주소의uninitialized-read 경고가 남아 있다. 해당 읽기 주소의WRAM 값은 독립metadata와 비교했으며 경고 로그도 보존했다. 이것을 실제CPU uploader에 의한 WRAM 초기화 검증으로 해석하지 않는다.

|frame|bank|첫~마지막view read master clocks|마지막read~설정시작(VBlank대기 포함)|설정시작~최종ACK|ACK scanline|scroll/mode/window 실제HDMA reads|
|---|---:|---:|---:|---:|---:|---|
|905|0|2320|303274|2060|226|241,241,241|
|906|1|2374|303222|2042|226|241,241,241|
|907|0|2212|303378|2060|226|241,241,241|

file RPC 때문에 RTL bus 시간은 늘어나며 CPU master clocks와 독립적이다. 위 CPU 관찰값을 앞의 모델 시간에 그대로 합산하거나 실기 latency bound로 쓰지 않는다. VBlank대기와 최종 서비스가 남은 예산에 들어가는지는 실제공유일정에서 다시 결합해야 한다.

## 회귀·오류 검증과 남은 게이트

71프레임source83240B,124묶음/2069map범위/13406mapB,총DMA26350B,700일반packet,215내부packet,최대4credit를 확인했다. 매frame metadata8570B/receipt754B/rawCRC64B는 독립 oracle과 정확히 일치한다. 수신 ARM packet/source output bytes는265와 동일하다.

기존29개 ACK/identity/token/CRC/manifest/RLE/순서/STOP 오류를 다시 실행했다. H2 mask/raw 불일치,HDMA길이/version/budget 변조,BG비정렬/OBJ초과,offsetRAM쓰기 중STOP,seal전 표시읽기의9개를 더해38개 모두 완료 차단·1024B RAM동결을 확인했다. 이 테스트에서는 독립C oracle이 RTL보다 먼저 오류를 막지 않게 했다.

test01은 새864..867 영역을 금지하던 구 ownership assertion에서 실패했다. test02부터는 허용주소와D_CHECK상태를 함께 검사한다. CPU03은+acc 관측을 유지한905/906/907 warmup 중240초 wall-time 준비 한도에 걸렸다. 해당로그의 종료EOF/라이선스process exit는 harness가 자기 simulator를 종료한 결과이며 새 라이선스 오류가 아니다. CPU04는 RTL/ROM/CPU clock을 그대로 두고 준비 wall timeout만600초로 늘려 재실행했다. 이 실패와 모든 실행 원시 로그를 보존한다. 선택run은progress/manifest 및분석 입력해시를 따른다.

266의 H2/phase-RAM 표시 경계를 유지하고, 실제 ARM E0 refill/IRQ·tile ROM 중재와 일반65816 명령/DMA를 같은 일정에 연결한다. 기존 보드의 실제 교체 목록·동시 수명·남는 제어를 확정한 뒤 whole-board Lite 자원 게이트를 수행한다. 부분 MAP의128LE를 기존490LE/40LAB 부족에서 빼지 않는다. 다음 후보는 잔여 admission/packet identity와 실제 소비 제어의 중복을 공동 제거하는 경계이며, 독립 FSM/opcode/seed/FIT 반복은 하지 않는다.

production227,GBC164,saveSRAM은 그대로다. P2선정,firmware 배포,실기60fps 승인 또는자동머지는 하지 않는다.
