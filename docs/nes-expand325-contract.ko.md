# NES325 — 압축 입력의 단일 확장과 native SNES 소비

319 RTL과317 metadata 선행 ARM을 기준으로 구현했다. 최종 수치와 소스 결합은 `analysis/expand325-verification.json`에 기록한다. 먼저 시험한 단일 staging안은 `analysis/expand325-single-stage.json`에 별도로 보존한다. production227/GBC164/saveSRAM은 변경하지 않는다.

## 실제 변경 경계

ARM wire와 ELF의 실제 PT_LOAD 이미지들은319 그대로다. 빌드 경로가 포함된 ELF container hash 차이는 실제 실행 코드 변화로 세지 않는다. ordinary op2/4/5/8의 compressed payload를 기존2슬롯 queue에서 한 번 읽고 FPGA가 literal/RLE2/RLE4를 staging에 확장한다. staging에 완전히 저장한 뒤 storage credit을 돌려주고 active record를 실제 소비·receipt까지 보존한다. seed는최대4B, 새 expanded cursor는12bit다. 추가 E1이나 cold packet 분할은 없다.

SNES의6060..6068 ABI를 mode/section/WRAM 목적지16bit/staged length16bit/PPU 주소16bit/bank로 바꿨다. token4B 읽기·4B 쓰기와6059 소비 ACK는 유지한다. 구형 op/start/encoded/span을 재구성해 SNES가 다시 RLE 해석하는 경로는 없다. SNES는 staging→최종 WRAM DMA 후 필요한 CGRAM/OAM DMA를 실행한다. 임시 WRAM으로 복사한 뒤 MVN으로 확장하는 경로와 OAM pattern ROM은 제거했다. 실제 ROM 본문은864→536B다. ROM 상한 때문에 선택한 변경은 아니다.

HDMA의 정확한1100B zero-tail은 기존 STOP-aware bank 재사용을 유지한다. FPGA가 op5/section5/start21/span1100/2B zero seed를 확인한 경우에만 mode1과 실제2B staging 읽기를 사용한다. SNES가 cold에서 ROM zero DMA를 실행하고 유효 bank이면 재사용한다. 일반 RLE에 대한 fallback이나 임의의 소비 생략은 아니다. 이 예외와 fresh scroll CRC 영역은 분리한다.

독립 검증은 producer write가 아니라 실제 SNES staging read strobe와 순차 read_count에서 얻은 **확장된 값**으로 CRC를 진행한다. host의 별도 RLE shadow pattern/반복 CRC 순회를 제거했다. 정확한 read count·token·ACK를 충족한 후만 receipt를 확정하며 별도 manifest expected cursor/coverage/CRC와 비교한다. expected를 새 producer 결과로 대체하지 않았다. 기존 validator RAM 프로토콜은 유지하되 host 입력 데이터 흐름을 바꿨다.

삭제된 것은 구형 byte descriptor 공개·SNES의 주소 복원/RLE dispatch·중복 RLE CRC 순회다. **주소 계산 전체가 삭제된 것은 아니다.** FPGA의 native destination base+start, PPU 주소 shift, 독립 byte 범위/alignment/receipt granule 변환, manifest 해석·최종 RAM 검사와 source/plan 제어는 남는다. ARM에 단위 변환을 추가하지 않았으므로323의 inverse-unit decoder도 도입하지 않는다. 남은 검사 식과 새 mux 비용은 전체 MAP에 포함한다.

## staging 경쟁에서 발견한 회귀와 수정

첫 안은 같은4KiB RAM을 단일 immutable chunk로 바꿨다. 전체 Lite17,720comb로−104였고 고정 위상905/907은각1.573935/0.331860ms 빨라졌다. 그러나906은13.493565ms 느려졌다. 제한 연속907도19.538901894ms로 회귀했다.

고정906에서 token73 소비는244.190642→258.997587ms, token76은260.150430→275.230036ms로 지연됐다. 이후 map 소비가약15.080ms 밀렸다. 첫BG backend 수락은 그대로이며 마지막OBJ 생산은259.022914→259.777405ms다. 단일 staging으로 tile 선행 생산이 제한되어 ROM 허용창과 공급 일정의 비용이 커졌고, SNES 소비 시간 감소가 이를 상쇄하지 못했다. tile/map 저장을 없앤 회로 절감을 공짜 시간 이득으로 세면 잘못된 결론이 된다.

수정안은 **tile/map에는 기존2×2KiB ping-pong**, ordinary에는같은4KiB 전체 구간을 제공한다. owner가 ordinary일 때만 wide 주소를 선택한다. tile chunk가 남아 있는 동안 ordinary owner로 넘어갈 수 없고, ordinary는 EXPAND→SEAL→실제 consume 이후 다음 producer를 허용한다. 별도 RAM이나 포트는 추가하지 않는다. 따라서 tile producer의 선행 채우기를 유지하면서 최대3418B ordinary 범위를 추가 packet 없이 처리한다.

단일 슬롯안의 정상 일정9건은 보존했다. 시간 회귀 확인 후 추가 fault batch는 자체 프로세스만 정리해 중단했으며 전체 fault PASS로 세지 않는다. 수정안에 동일 오류 검사를 수행한다. fixed01 선언 순서 컴파일 실패도 보존한다. FLOAT entitlement 문제가 아니다.

## 검증과 한계

원본 압축 명령을 oracle로 실제 Mesen65816에서544명령/128,041B와2회zero DMA/2,200B를 검증했다. 별도36경계 명령은bank 무효화·교차 쓰기·3418B 전체 범위·raw240B·마지막9B를 포함해32,274B가 통과했다. WRAM과 CGRAM/OAM 데이터 비교를 유지하며 ROM/DMA 버스 trace를 실제 ARM/RTL 일정에 연결한다. 별도 CPU 시험은 forced blank이며 그것만으로 VBlank/fullpixels를 증명하지 않는다.

동일 source 시작/ROM cycle 고정 A/B와 제한/정상 연속905/906/907을 비교한다. 실제 Cortex-M4 명령·IRQ·SPI 응답·2슬롯 credit·tile ROM 경쟁·새 CPU trace 서비스·최종 표시 ACK를 포함한다. instruction CPI1/84MHz와 기존 ROM/호스트 clock 모델의 결과이며 물리 MCU 주기나Fmax 증명은 아니다. ARM PT_LOAD 동일성, SPI byte 합, max credit≤2, metadata release/firstBG/최종 완료 시각을 분석기로 결합한다.

확장 중 STOP, source/plan/부분E1/E9 STOP, ROM drain, 조기 소비·최종 ACK, 독립 manifest mismatch와 consumed-byte CRC corruption을 검사한다. fault 후 phase/queue RAM뿐 아니라 전체 staging4KiB의 쓰기 정지와 seal/lease/ACK 비노출을 확인한다. 독립 aperture 시험은 tile 두 chunk의 동시 보존,3418B 실제 RAM read, 잘못된 token 거부와 부분 확장 STOP을 검사한다. 큰3418B의 전체 ARM/manifest 일정은 별도 실행하지 않았으므로 CPU/aperture 경계 시험을 fullpath 증명으로 확대하지 않는다.

기존 최종12회 display 읽기/token ACK·VBlank 절차와 metadata 선행 발행을 유지한다. cartridge read/token 관측은 물리 PPU 목적지 직접 감시가 아니다. 목적지 의미는 원본 oracle과 실제65816 실행으로 결합한다. 새 단계는 실제 CPU trace replay이며 live full65816/71 ARM/fullRUN/FIT/STA/실물60fps는 여전히 미검증이다.

## 전체 비용 판정

319 기준 전체 Lite22,618LE/17,824comb/9,022FF/307,808RAM bits다. tile 선행 생산을 유지한 수정안은22,617LE/17,802comb/9,021FF/307,808bits로 **−1LE/−22comb/−1FF/0RAM**이다. 부족분은2,416→2,394comb다. isolated FIFO 삭제나 부모/자식 MAP 합산으로 더 큰 회수량을 주장하지 않는다. 새 latch/undriven 경고가 없는지 확인하고 기존cache_index141 latch는 별도로 유지한다.

고정 동일 source 시작/ROM cycle에서905/906/907의 절대 완료는각1.573935/1.586845/0.391768ms 빨라졌다. ARM 명령 준비나 응답을 무료로 둔 isolated CPU 합산이 아니라 실제 통합 일정의 차이다.

제한 연속907은 시작263.146933→261.559270ms(−1.587663), 첫BG274.905315ms 동일, 완료280.266864→279.873414ms(−0.393450)다. duration은17.119885468→18.314098410ms,60Hz 초과는1.647431743ms다. 더 빨리 시작한 만큼 ROM 대기를 더 포함한 결과이므로 duration 증가를 소비 코드가 느려진 것으로 해석하지 않는다. 반대로 같은 위상의0.392ms 개선을 원래0.453219ms에서 단순 차감해 새 실측 잔여61µs라고 발표하지도 않는다. 시작 위상별 전체 일정의 목표는 아직 충족하지 못했다.

정상 ROM의warm907은14.763186476→14.370236646ms(−0.392949830)다. 정상cold905/906 duration도각1.633162220/1.646707512ms 줄었다. 정상907 절대 완료는앞선cold 개선까지 합쳐3.672819ms 빠르므로 이를warm 단독 개선으로 발표하지 않는다.

| 최종 수정안 비용 | 고정 위상 | 제한 연속 | 정상 연속 |
|---|---:|---:|---:|
|3프레임 SPI bytes|21,847|21,847|21,483|
|SysTick / EXTI|36 /66|27 /68|18 /62|
|관측 ARM stack|1,304B|1,304B|1,304B|
|warm907 duration ms|26.186594848|18.314098410|14.370236646|

고정 위상은 별도160ms 간격으로 source 시작을 고정한 비교 실험이므로 그26ms를 원래 제한 연속17ms와 직접 비교하지 않는다. E1/E9 byte stream과 ARM PT_LOAD는 각각 같은 조건의319와 동일하다. SPI 총량 차이는 실제 polling/응답 경로를 포함하며 새 wire 압축 이득으로 세지 않는다. stage325의tile_owner_wait는 owner grant 대기만 세며 tile 내부 ready 대기 전체와 같지 않다. 실제 tile/staging backpressure는 통합 일정과 ROM 요청·소비 event에 포함됐다.

host 자체 comb는2,485→2,411(−74), aperture는177→205(+28)이다. 코드가 동일한 validator도mapping에서+8이고 다른 전체 보드 mapping 변화가 더해져 최종−22다. CPU 별도 시험의905 master clocks320,442→115,788 감소를 통합 프레임 시간에 추가로 빼지 않는다. 회로 부족2,394개를 해소하지 못하므로60fps/보드 배치 승인으로 승격하지 않는다. 다음 구조 검토는 남은 byte→receipt/manifest 검사와 native destination의 관계를 실제로 단순화할 범위를 대상으로 해야 하며, 검증된 tile 선행 생산을 다시 지우거나 FSM/seed 조정으로 부족을 메우지 않는다.

독립 manifest mismatch는fault3, 소비 byte CRC 변조는H_CERT의digest 대조에서fault7, STOP/조기 ACK는fault4로 거부됐다. 최초 분석기의 CRC fault3 가정은 실제 checker의fault7 의미를 확인해 수정했으며 RTL을 바꿔 통과시킨 것이 아니다. board/simulation host는관측용tile_closed267 output alias만 다르며 나머지 host/validator/aperture 텍스트는 정확히 일치함을 검사한다.

실제65816 STOP 추가 시험은첫bank0 채우기 직후 STOP 상태를 주입해6006의A5 응답과cache 무효화를 확인했다.36명령/32,274B가 같고zero DMA는10→11회/12,100B로 증가하여 이전bank를 잘못 재사용하지 않았다. cpustop01/02는명령 완료 후Mesen 종료 요청이 반영되기 전callback이37번째 명령을 검사한 harness 실패를 보존한다. 완료 후ready/status 응답을0으로 내려cpustop03에서 통과했다. 소비 ROM은변경하지 않았으며 정상CPU/통합 일정의ROM hash와 동일하다.
