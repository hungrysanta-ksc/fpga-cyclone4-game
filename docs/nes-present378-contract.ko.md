# NES378–382: 계산 완료와 실제 VBlank 표시를 구분한 검증

375 RTL·377 ARM은 유지한다. 이번 작업은 그 시간 이득이 실제 표시 제약에서도 유효한지 확인한 것이다. **기존 처리시간 개선은 보존되지만, 실기 60fps의 근거로 사용하면 안 된다.** 표시 전환만 연결한 경우에도 한 VBlank를 건너뛰며, PPU DMA까지 제한한 일정은 910번 캡처를 놓친다. 새 65816 STOP 검사와 같은 VBlank 표시 후보는 실제 CPU로 검증했으나, 현재 전체 경로의 해결책으로 채택하지 않는다.

## 이전 시간표에서 빠진 비용

기존 전체 모델은 FPGA의 12B 표시 문맥을 읽은 뒤 즉시 token/최종 ACK를 보냈다. 실제 415B 65816 표시 코드는 현재 VBlank를 벗어나 **다음 VBlank**를 기다리고 PPU를 설정한 뒤 ACK한다. 실제 두 bank의 Mesen trace에서 마지막 view read→첫 $4212 read는 122 master clocks다. 관측 polling 간격은 46/52/92 clocks이며, 여기서는 92를 사용했다. 관측값이지 WCET 증명은 아니다.

또한 inactive VRAM bank라도 active display 중에는 VRAM DMA를 자유롭게 할 수 없다. VRAM 접근에는 VBlank 또는 forced blank가 필요하다. 기존 ordinary325 CPU ROM은 시작 때 INIDISP=$80으로 설정했으며, 그 A-bus 소비 trace만 재생한 전체 모델은 이 PPU 조건을 검증하지 않았다. [PPU 레지스터](https://snes.nesdev.org/wiki/PPU_registers), [PPU 메모리 접근](https://snes.nesdev.org/wiki/Reading_and_writing_PPU_memory).

보드의 NES ext_clk는 SNES_SYSCLK에 연결된다. 기존 TB의 약22MHz 대신 quantized master period 46,561ps를 적용했다. high/low는 23,280/23,281ps다. capture 기한은 같은 master cycle 수로 유지하며, PPU 상대 위상은 실행 전 정한0이다. 이 fixture의 357,368 cycles/frame은 16.639411448ms, VBlank는 2.349840548ms다. 실측 보드 주파수·NTSC의 프레임별 변화·PAL·interlace 증명은 아니다. 위상을 옮겨 성공 결과를 만들지 않았다.

## 분리 실행 결과

|실행|추가한 제약|결과|
|---|---|---|
|control02|공유 master clock만 보정, 즉시 표시 ACK 유지|905–916 배출12, 다음 capture10/10; warm 최대16.482012ms|
|present02|cold부터 실제 구형 표시 trace/VBlank 대기|905/906 뒤 고정907 시작을 놓침; startup 실패 보존|
|present03|cold prefix는 기존 fixture, warm부터 표시 trace/VBlank 대기|배출12/capture10/10이지만 warm 최대33.011120ms, 표시 간격 최대33.280477ms|
|dma01|present03 + warm tile/map/OAM의 VBlank 접근 제한 + 실제 descriptor port 읽기|capture908/909 승인,910 실패; warm907도 표시 완료 전|
|commit382-01|dma01 + 실제381 CPU의 같은 VBlank 표시 service|같은910 실패; 표시 준비가 이미 늦어 개선 없음|

present03의 warm 표시 VBlank index는16,17,18,19,20,21,22,23,**25**,26이다. 915에서 한 번 건너뛴다. capture 승인과 매 VBlank 표시를 별도 조건으로 판정한다. control02의 SPI45,458B/IRQ42/EXTI252와 present03의45,616B/IRQ44/EXTI261도 각 실행 시간에 포함된다. 관측 ARM stack은 둘 다1,288B다.

dma01/382의 typed tile/map은 $6040..$604b의 실제 ready·flags·length·position·generation·token을 읽는다. 주소/길이/token을 TB 내부 신호에서 가져오는 기존 경로를 대체했다. 150개의 descriptor 확인과13개의 warm PPU command 종료 창 검사를 통과했다. 150에는 cold descriptor도 포함한다. section5 WRAM은 VBlank로 제한하지 않는다.

typed tile/map은 command당1000+10×bytes master clocks, CGRAM/OAM은 actual325 CPU trace의 마지막 event+32 clocks를 접근 예산으로 사용했다. **CGRAM/OAM은 WRAM 사전 복사까지 command 전체를 VBlank에 넣는 보수적인 일정이다.** 따라서 실패를 최적 일정의 불가능성으로 해석하지 않는다. PPU 창 준수만으로 화면 전체·palette/OAM 원자성·실제 PPU DMA 완료가 증명되지도 않는다.

## 910 캡처 실패의 위치

dma01과382는 첫 warm907의 접근 제한 대기가 합계약23.290ms다. 한 map command는 현재 blank 끝에 도달하여 다음 blank까지14.294412804ms 기다린다. 이 command를 뒤로 옮긴 부담이 출력 queue와 공급 일정에 전파된다.

|382 event|절대 시각 ms|의미|
|---|---:|---|
|source907 시작|264.333059|기존 고정 master-cycle 일정|
|907 입력 ACK|266.936634|입력 완료와 최종 표시 완료는 다름|
|source908 시작/물리 입력 확정|280.972517 /281.563796|FPGA 입력은 다음 프레임까지 진행|
|907 OAM 마지막 command 종료|298.296518|PPU window 안, 전체 프레임 원자성은 미증명|
|907 표시 ready|299.299847|scanline258|
|첫 표시 $4212 poll|299.406281|scanline260, 같은 blank 허용 cutoff257 이후|
|capture910 실패|300.009146|collector owned=1, release=0, fault=0|

새 kernel은 이 시점에 현재 blank 사용을 거절해야 한다. cutoff를 늦추거나 capture 기한을 완화해서 성공시키지 않았다. ARM의 실행 worker는 프레임마다 source_receive367→계획/전송→finish267→commit285를 순차 실행한다. 이전 표시를 기다리는 동안 다음 source를 소비하지 않는다. FPGA의 입력/표시 문맥 분리와4packet ring만으로 이 ARM 순서까지 해결되지는 않는다.

## 실제 65816 수정과 STOP

구형415B kernel은 view 뒤 $6001 fault를 읽지 않는다. mocked STOP이 이미 있어도 PPU bank 설정28회와 ACK 시도를 수행하는 반례를 실제 CPU로 확인했다. FPGA의 ACK 거절만으로 이미 실행한 PPU write를 취소할 수 없다.

380은 apply·unblank·ACK 직전과 ACK 직후에 fault를 확인한다. precommit abort는 HDMA off/forced blank 후 ACK를 보내지 않는다. ACK 이후 STOP은 이미 commit한 표시를 무효화하는 별도 경우다. 415→472B이며 old witness/normal bank0·1/STOP4지점의7case가 통과했다. 이는 polling 지점의 검사와 fail-closed 동작이며, 비동기 STOP의 모든 instruction 간 race나 정상 재시작을 증명하지 않는다.

381은 VBlank 중 ready가 되면 STAT78/SLHV/OPVCT로 Vcounter를 latch하여225..257선에서만 현재 blank를 사용한다. 그 이후와 active 구간으로의 wrap은 다음 blank를 기다린다. 516B(+101B/구형), $1010의1B scratch를 쓴다. **WRIO.7이 켜져 있어야 latch가 유효하다.** standalone fixture의 reset WRIO=$ff 전제이며 production에서는 기존 output shadow와 함께 명시적으로 보장해야 한다.

381 실제 CPU12case는 old STOP witness, 두 bank의 normal/line240/line255/line259/프레임 끝355000 release와 STOP wait다. line240→ACK243, line255→ACK258은 같은 frame, line259/끝 release→ACK226은 다음 frame이다. STOP wait는 ACK 없이 blank한다. view/status/token은 mocked이고 HDMA의 zero terminator를 명시적으로 미리 넣었다. 전체 resident CPU·HDMA upload·전체 pixel 증명은 아니다.

382는381의 실제 early head/current-blank tail을 합친 service capsule을379 일정에 연결했다. raw 두 trace와 SHA를 보존하며, counter read의 관측 비용도 tail offset에 포함한다. 다음 blank 경로에도 추가 counter 비용을 보수적으로 부과한다. **임의 시작 위상의 CPU를 전체 재실행한 결과가 아니다.** 새 kernel이 native case에서 안전해도 전체 일정의910 실패는 그대로다.

별도 cancel02는 실제 M4/RTL에서12view read 뒤 STOP을 주입했다. replay의 PPU write0/최종ACK 없음/lease·staged 해제, validator1024B+queue1024B+shadow512B의256host-clock freeze를 확인했다. replay는 wait 중 fault를 확인하므로 구형 실제 CPU보다 강한 취소 동작이다. 이를 구형415B의 STOP 안전성으로 세지 않는다.

## 전체 비용과 다음 교체 예산

FPGA와 ARM PT_LOAD는375/377과 같고 모든 compiled production 공통 RTL을375 wholeMAP 입력과 해시 비교했다. 새 FPGA 면적 이득은0이다. Quartus Lite wholeMAP22,390LE/17,663comb/8,985FF/300,640bits를 상속한다. 부족2,255comb, 예비155 포함 순삭제2,410은 그대로다. 새 MAP/FIT/STA를 반복하지 않았다. 새516B SNES prototype도 production firmware에 설치하지 않았다.

첫 warm의 tile/map200B+OAM544B와, 이 표본 최대768B의 순수8clocks/B PPU wire 시간은 각각약0.277/0.286ms다. VBlank2.350ms보다 작지만 setup·WRAM 복사·queue·SPI·IRQ·refresh·manifest·표시 준비를 포함하지 않는다. **순수 대역폭만으로 현재 실패가 불가능성이라고 결론내릴 수 없다.** 반대로 작은 wire 시간만으로 성공도 주장하지 않는다.

다음 교체는 아래 세 경계를 함께 다룬다.

1. WRAM staging 수신/CRC와 PPU DMA 실행을 분리한다. active 동안 허용되는 WRAM 복사를 앞당기고 tile/map batch와 OAM/CGRAM·표시 전환을 합법적인 VBlank 예산에 배치한다. 현재 source 소비 receipt는 FPGA read 증거이며 실제 PPU destination write 완료와 같지 않다. token/credit을 언제 반환할지와 PPU 완료 증거를 함께 정의한다.
2. 현재 출력 payload가 immutable하게 확정된 뒤 다음 source를 수신할 수 있도록 ARM의 receive와 display commit을 분리한다. receiver280/history286/certificate286/video285/dirty/resident 및 source RX·shared SPI의 수명을 추적한다. current commit에 필요한 identity/used/stale/history 요약을 고정하고 STOP 뒤 두 문맥을 무효화한다. 현재는 추가 상태 크기·RAM 배치·시간 이득이 null이며 무료 overlap으로 계산하지 않는다.
3. FPGA source·host·queue·plan·manifest·receipt 제어의 실제 삭제 목록과 clock/RAM port/CDC 비용을 같은 경계로 합성한다. 기존8모듈+helper5,957comb에서 codec/checker2,375를 보존한다면 제어3,582→1,172 이하는 mapper 증분 전의 상한 예산이다. 새 staging/PPU 완료·동시 수신 제어도 그 안에 포함해야 한다.

MMC4/5는376 gate를 유지한다. 실제 live core ROM 기회·mapper latch·높은 CHR tag·ExRAM/split/IRQ/audio/PRGRAM의 시간/회로 증분은 아직 null이다. 예전195µs나 이번 wire 여유를 mapper 예산으로 전용하지 않는다. 기존 CRC·epoch·bank·token·STOP·최종ACK 도구는 이 구조 변경과 mapper 검증에도 재사용할 수 있다. 다만 현재 구조의 성공을 보장하는 근거는 아니다.

이 경계가 합법적인 PPU 일정과 whole 회로 예산을 함께 맞추지 못하면 ROM 중재·렌더링 표현·역할 분담·대상 하드웨어를 다시 비교한다. 작은 FSM/counter·시작 위상·기한 완화·검사 삭제로 성공을 만들지 않는다. 이어서71/heavy7·다중위상·live core/mapper·전체65816·WCET·실기 gate가 필요하다. production227/GBC164/saveSRAM은 유지하며 자동 merge/구매하지 않는다.

근거: `analysis/present378-verification.json`; raw `../probes/nes-present378/`. control01의 compile 오류, present02의 startup 실패, cancel01의 compile 오류, dma01/382의 capture 실패를 원본과 함께 보존했다. 이 분석의 audit 완료와 후보의 전체 일정 성공을 구분한다.
