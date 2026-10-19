# NES264 queue payload 직접 CRC·receipt와 ACK 이후 retire

SNES가 소비한 bytes를6060..6063으로 다시 보내던263 bridge를 제거했다. 실제 Cortex-M4 serializer의 manifest 순서와 FPGA queue/parser/ACK 생명주기를 함께 바꿨으며, 기록된71프레임의 source·tile·map·metadata·receipt·CRC·최종 표시 lease 경로가 일치한다. 실제 일반65816 프로그램과 full ARM RUN/IRQ를 실행한 결과는 아니다.

## 교체 경계

기존 queue ACK 검사기는12byte ACK를 검사한 즉시 head를 retire했다. 이제 ACK 확인은 소비 완료를 표시할 뿐이며, parser가 같은 queue RAM에서 후속 CRC·receipt 작업을 마칠 때까지 head와 credit를 유지한다. 다른 slot의 SPI 수신은 계속할 수 있으나 head는 불변이다. packet 전체를 순서대로 읽었는지도 확인한다. tile은 기존 DMA aperture의 전 byte 순차 읽기, 정확한 token4byte 제출/consume, section·slot·length를 확인한 뒤 queue payload의 token도 실제 완료 token과 비교한다. 그 뒤에만 receipt를 발행한다. ACK가 실제 PPU 쓰기를 증명하는 것은 아니며, 올바른 소비기 구현이 ACK 전에 쓰기를 끝내야 한다.

일반 payload 읽기는 H2/map의 PREAD·PCAP, parser_address와 같은 synchronous queue port를 쓴다.24bit consumed CDC mailbox도 공유한다. SNES write latch/mask/pending을 통한 byte echo는 제거했다. tile·CGRAM·raw bitmap receipt는 검증된 소비 범위에서 만들고, HDMA scroll/raw tail CRC는 수신 queue payload를 직접 읽어 만든다. COPY/FILL/PATTERN의 반복 주소를 실제 decoder가 계산한다. C event array는 oracle 내부에만 남고 RTL 입력으로 사용하지 않는다.

fresh scroll CRC는 일찍 계산해 기존16bit digest에 보관한다. 이후 같은 CRC 연산기가 raw-tail granule을 갱신하고,422byte manifest 검사 후 retained64B raw hash와 합쳐 H2 content/certificate CRC를 검사한다. 추가256B manifest bitmap이나 새 CRC RAM은 없다. 이전263의256B C bitmap도 검증용 저장소였으므로256B FPGA RAM을 회수했다고 주장하지 않는다.

실제 검증한 입력에서는 active scroll prefix가 한 packet에 들어간다. 현재 decoder는 쪼개진 active prefix와 부분 raw-tail granule을 거부한다. 일반1121B active-prefix scatter를 지원하는 생산용 decoder라고 확대하지 않는다. 기존 source/transport CRC 소유권과 clock/CDC는 유지한다.

## manifest 순서와 ARM 비용

| 순서 |263|264|
|---|---|---|
|출력 뒤 요구 정보|map manifest op10/11|원래 SEAL의190B payload를 op15 requirements로 먼저 발행|
|독립 bitmap 검사|SEAL 뒤 C가166B+256B를 재전송|op15의166B 요구→op10/11 dense/RLE256B를 queue에서 순서대로 검사|
|최종 확정|206B SEAL op3|16B header만 있는 op3 fence; CRC/certificate 후 sealed|

요구 bitmap은 실제 receipt에서 복제하지 않는다. C oracle은 수신한 독립 dense/RLE manifest와 DMA 이전 descriptor bitmap을 비교하고, FPGA는 DMA 이후 receipt와 queue manifest를 따로 비교한다. op15 이후 새 일반/map 명령, 잘못된 manifest offset/길이, 조기 fence는 거부한다. 최종 표시 ACK는 queue empty, owner 없음, receipt/sealed와 token 조건을 유지한다.

Cortex-M4에서71개 계획을 실행했다. text2320→2472B(+152), static312B 유지, 관찰 stack136→144B(+8)다. 프레임당 E1은19B, 모델 E0 조회는24B 증가해 총43B가 늘었다. 명령 수 증가는2182..3043개다.84MHz CPI1로 약0.026..0.036ms라는 민감도이며 실제 MCU cycle/IRQ 상한이 아니다.4credit,2069범위,16bit counter wrap65530→42 및18개 오류/선행검사를 통과했다.

requirements/fence 분리는 실험 protocol 변경이다. 기존 production 소비기에 설치할 firmware pair를 만들지 않았다. 실제65816은 requirements의 표시 설정을 fence까지 보관해야 하며 그 RAM/명령 비용은 미측정이다. C oracle의206B 저장을 target allocation으로 간주하지 않는다.

## 같은 통합 경계의 회로 비용

| Quartus Lite MAP |LE|comb|FF|RAM bits|
|---|---:|---:|---:|---:|
|263 bridge|7287|5791|2842|90368|
|264 direct|8230|6745|2884|90368|
|차이|+943|+954|+42|+0|

source/core·queue/parser·tile/map staging·lease를 포함한 동일 부분 통합 경계다. production 보드 전체에 이 차이를 바로 적용하지 않는다. 기존 제거 장부3336comb/2084FF/98560bits와 새 core+output {'comb': 6541, 'FF': 2784, 'RAM_bits': 90368}를 별도로 남겼다. 부모/자식을 중복 합산하지 않았으며 proven whole-board LE reclaim은0이다.490LE/40LAB 부족, whole FIT/STA/CDC/IO와 mapper 여유는 미해결이다.

회로 여유 확보에는 실패했다. core 포함 계층은3117→3052comb(-65), output은2470→3489comb(+1019)이며 queue 자식은749comb/436FF 그대로다. output 부모 자체는1261→2256comb로 늘었다. ACK의 즉시 retire를 없앴어도 기존 ACK 검사기 자체를 대체해 줄인 것은 아니다.

core FSM은 추출됐지만 output의 main state는263과 달리 FSM 목록에서 빠졌다. state를 after_event register 값으로 되돌리는 구조가 정적 FSM 추출의 장애 후보다. 도구가 직접 원인을 진단한 것은 아니며, 이 조건만 바꾼 대조 합성을 하지 않아943LE 전체를 FSM 미추출 탓으로 돌리지 않는다. 새 범위·RLE·CRC dispatch/비교 로직도 함께 들어갔다. 추출만 되면 회수된다는 가정으로 추가 FIT를 반복하지 않는다.

## 시간 비교

동일한900 master-clock DMA setup,400ns bus byte,560ns ordinary byte 배정에서 실제 RTL 일정을 비교했다. 추가 E1 bytes·SNES packet 읽기/ACK·직접 parser/CDC/receipt 지연이 출력 구간에 들어간다. native C 계산 시간은 target CPU 시간으로 청구하지 못했다. ARM E0 refill/IRQ·ROM 경쟁은 별도 endpoint이므로 full-frame 시간이나 상한이 아니다.

| frame |263 출력|264 출력|절감|source+264 직렬 진단|
|---|---:|---:|---:|---:|
|905|36.017431ms|26.843405ms|9.174026ms|46.125810ms|
|906|37.451232ms|27.889756ms|9.561476ms|31.699801ms|
|907|3.698092ms|2.564515ms|1.133577ms|6.648466ms|
|954|7.258413ms|5.630069ms|1.628344ms|11.885039ms|
|955|7.440956ms|5.748795ms|1.692162ms|10.027789ms|
|963|6.958962ms|5.911611ms|1.047351ms|10.977641ms|
|970|6.625648ms|5.679114ms|0.946534ms|11.955447ms|

warm 출력 최대는5.911611ms(frame963), source+출력 직렬 진단 최대는11.955447ms(frame970)다. 모든 warm 프레임의 출력 시간이 줄었고 최소 절감은0.946534ms다. 이전 CPU 문맥 재사용263의 국소566clocks 이득은 합산하지 않았다.

별도 ARM endpoint의 status 전송과 CPI1을 직렬로 더한 민감도 최대는19.730269ms(frame970)다. warm9프레임이16.667ms를 넘는 민감도다. retimed 공유SPI 일정이나 WCET가 아니므로60fps 불가능의 증명은 아니며, 남은 비용을0으로 놓고60fps를 승인하지도 않는다. output 모델에 포함된 E1 전송은 다시 합산하지 않는다. 실제 VBlank·일반65816·full ARM 입력 decode/plan/refill/IRQ·tile ROM 중재·STA는 미측정이다.

## 검증과 판정

ARM264 E1 packet을 sequence/token 변경 없이 SPI에 보냈다. source83240B,124묶음/2069map범위/13406mapB,총DMA26350B,일반packet915개,metadata8570B×71,receipt754B×71,raw CRC64B×71 일치다. SNES echo는55237이벤트→0회다. 최초 일반 payload 읽기와 검사 전용 manifest를 SNES가 읽고 ACK하는 비용은 남아 있다.915개 ordinary ACK→parser retire 구간을 별도로 기록했다. 이 head 점유 시간은 cold905 합계0.272412ms, warm 최대0.138646ms(frame955)이며 이미 출력 모델에 포함돼 있다.

RTL19오류는 잘못된 ACK/누락 읽기, CRC8B 뒤 STOP/조기 표시 ACK, 요구/scroll CRC/map bitmap 변조, manifest offset/순서, tile token, 비정렬 granule, parser 중 중복 ACK, map token/bank/generation/sequence, 조기 fence와 RLE marker/truncated literal을 검사했다. 모두 완료 차단과1024B RAM 동결을 확인했다. tile 내용은 기록된 planner 출력이며 실제 ROM 중재가 아니다. CRC는 인증이나 충돌 없음의 증명이 아니다.

test01 선언 순서 컴파일 실패, test02 cold 성공, test03 공유 읽기 정리 전71프레임 성공을 보존했다. 최종 test04/guards01과 동일 RTL hash를 MAP01에 연결했다. FLOAT는 승인된 wrapper, 합성은 Lite만 사용했다. whole FIT/STA/P2/physical60fps 미승인. production227·GBC164·saveSRAM은 변경하지 않았다.

직접 payload CRC/receipt와 ACK 이후 queue 소유권을 유지한다. 다음은 admission/header/ACK의 중복 identity 검사·상태를 같은 경계에서 줄이고, 검사용 manifest의 SNES 재읽기·ACK까지 없앨 수 있는지 비교한다. 최종 fence의 실제65816 표시 문맥 보관/소비, ARM E0 refill/IRQ와 실제 tile ROM 중재를 함께 연결해 시간·회로 표를 갱신한 뒤 P2를 판단한다. 개별 FSM/opcode/FIT 반복으로 회수량을 추정하지 않는다.

재현: probe_nes_arm264.py→guard_nes_arm264.py; 기존 FLOAT wrapper에서 probe_nes_joint264.py --last975와 guard_nes_joint264.py; map_nes_joint264.py --test 해당검증폴더; analyze_nes_joint264.py. 새 실행 폴더를 사용하고 원시 로그/해시를 보존한다.
