# NES394: 공통 DMA ABI의 실제 연결과 교체 결과

## 판정

ARM의 최종12B DMA record·payload 생산,FPGA의 공통 수신·실제 read 기반 검사·receipt,실제65816의 저장·DMA·표시·최종 ACK를 연결했다. 기존 FPGA host 실행기와 context FSM,tile의 자동 chunk 제어,ARM의 map packet 재구성과 SNES의 job 재구성·64열 순회·gather를 제거했다. **source 전송·NES plan decoder·SPI snapshot/CRC8 본체는 남아 있다.393의 전체 삭제 범위를 완료했다고 판정하지 않는다.**

최종 whole Quartus Lite MAP은22416LE/17574comb/9024FF/300640bits다.392 대비55LE/170comb 감소,39FF 증가,RAM 동일이다. 순삭제2491 목표 중170만 확보했고,155comb 여유를 포함하면2321이 더 필요하다. 물리 자원15408comb보다2166이 많다. FIT/STA를 반복하지 않는다.

같은 시작 fixture·ROM 위상 조건의 실제 ARM·SPI·IRQ·ROM 연속 시험은 cold905/906을 완료한 뒤 **264.068523ms에서 고정907 시작 기한250.090632ms를 넘겨 실패**했다.911에 도달하지 못했다.392의 첫911 capture 실패보다 퇴행했으므로394를 생산 또는60fps 후보로 채택하지 않는다. 세부 시각과 원시 근거 해시는 `analysis/jobs394-verification.json`에 기록한다.375RTL/377ARM 기준과392의 부정 결과를 보존한다.

## 공통 record와 소유권

record는 destination16,WRAM store16,decoded16,attributes8,WRAM bank8,VMAIN8,canonical region8,canonical first16의12B다. TILE/MAP/CGRAM/OAM/HDMA의 영역·단위 좌표를 명시한다. ARM이 완성한 필드를65816이 그대로 복사·검사·실행하며,SNES에서 새 job을 만들지 않는다.

- wire E1은10B 공통 envelope(kind,flags/count,sequence16,serial32,body length16)와 command/CRC16을 포함한다. generation/epoch/bank는84bit admission·H2로 한 번 결합한다. serial32·sequence 검사는 유지한다.
- JOBS90은 record+encoded payload,HEAD91은 큰 literal의 record 저장,DATA92는 offset16+후속 payload다.HEAD 저장 credit을 실제 소비 완료와 분리해2슬롯의 순환 대기를 막는다. fragment는 하나만 열리고 offset은 연속이어야 한다.
- literal/repeat16/repeat32 압축을 유지한다. HDMA1100B zero tail은2B seed를 실제로 검사한 뒤65816의 고정 ROM DMA로 채운다. N5 D4/MASK/SHIFT와 compact E9 wire는 보존한다.
- MAP은 변경된 word만 정확히 한 번 공급한다. 행/열 순서 변경 때문에 validator의 ascending frontier 비교만 제거했다. 중복 bitmap·정확한 expected bitmap·CRC·H2 의미 검사·최종 검사는 남는다. unchanged hole을 묶어서 보내지 않는다.
- CGRAM/OAM은 source STORE와 전체 PPU REF를 분리한다. REF는 source byte/coverage를 만들어내지 않는다. MAP REF는 금지한다. inactive bank cache8948B는 source spool과 별도 예산이다.
- FPGA는32B tile CDC mailbox와 명시된 job 경계를 사용한다. 기존 tile producer의 독자적 append/seal/descriptor 생성은 삭제했다. actual read 완료·CRC/coverage drain·fresh32bit token 확인 뒤에만 source 소비를 공개한다.
- END는 빈 map 여부와 무관하게 fresh fence를 배정한다.12회의 정확한 view read 뒤에도 PPU 실행·VBlank·최종 token ACK가 필요하다. storage credit,source 소비,PPU 완료,display lease 해제는 다른 사건이다.
- native 출력 kernel은 초기 무효화6006 ACK,프레임 serial 재사용 차단,다음 프레임 수신 루프를 갖는다. CPU abort606F/EE는 실제 host fault와 공통 취소로 연결된다. STOP 뒤 정상 보드 재개 전체는 아직 미검증이다.

## 실제 삭제와 남은 제어

`nes_jobs394.py`는392의 고정 materialization에서 기존 함수/RTL 본체를 치환한다. 런타임의 legacy fallback을 두지 않는다. 삭제된 host context/tile producer는 보드 QSF와 기능 compile 목록에서도 제거했다. source·plan·SPI는 기존 본체를 유지하므로 해당 비용을 삭제로 세지 않는다.

|disjoint self comb|392|394|
|---|---:|---:|
|host 실행기|1937|2022|
|host context|102|0|
|queue|213|221|
|SPI frontend|576|579|
|source transport|400|398|
|NES plan transport|350|354|
|plan endpoint|100|99|
|tile adapter/link|200|43|
|교체 제어 합계|3878|3716|
|보존 codec+독립 checker|2374|2347|
|나머지 전체 회로|11492|11511|
|whole comb|17744|17574|

parent inclusive 수치를 중복 합산하지 않았다. 최종 제어3716을,다른 경계를 고정한다면1395 이하로 줄여야155 여유 목표에 도달한다. **host2022만으로 이미 전체 교체 제어 예산1395를 넘는다.** source/plan만 삭제하면 해결된다는 계산도 성립하지 않는다. opcode/FSM seed 조정이나 불가능한 whole FIT 재시도로 이 차이를 가리지 않는다.

## ARM·SNES·보드 입력 비용

|항목|392|394|
|---|---:|---:|
|actual M4 text|36570|35692|
|M4 data|4|4|
|M4 BSS|48724|48720|
|SNES 출력 코드 body|3543|1738|
|SNES tile+job+map 예약|23841|15360|
|FPGA whole FF|8985|9024|
|FPGA whole RAM bits|300640|300640|

M4는377 기준으로는text290B 감소/BSS244B 증가다.71개의 실제 생산기 component에서 관측 stack304B는 전체 RUN/IRQ stack 상한이 아니다. full IRQ stack/WCET를 승인하지 않는다. 중간 copy를 없애기 위해 pending wire buffer를 E2 처리 중에도 소유하도록 보호했다. 보호 중 early metadata 발행은 건너뛰며 이미 준비된 metadata의 선행 경로는 유지한다. 별도7168B job/payload 배열은 없다.

SNES15360B는 TILE8192+job3072+MAP4096이다. nonmap 두 bank cache8948B,DP/stack/주민 프로그램은 별도다. DP 예약14..57은68B로393의64B 목표를4B 넘는다. fullresident RAM 승인이 아니다.

새1738B kernel을 실제 보드의 `sink-program.hex`에 넣었다. 물리4KiB 프로그램 ROM aperture는 동일하며,4032B body 영역과64B header/vector 영역에 실제 candidate bytes를 설치했다. 이것은 기존 공간에 맞았다는 결과이지4KiB를 고집하는 정책이 아니다. 기능 compile과 전체 MAP의 공통 RTL29개는 모두 같은 해시다. 실제 M4 PT_LOAD도 component와 live 시험 사이에서 일치한다.전체 resident/audio/input firmware 설치나 실기 부팅의 증거는 아니다.

## 검증과 실패를 구분한 결과

1. 실제 Cortex-M4 최종 record 생산71frame PASS. 변경 map 집합·값·중복 없음·wire CRC/serial/sequence를 확인했다.9077map jobs/40B,9082column jobs/32B,91415jobs/82B를 생산한다.907 output wire753B,908632B이며 batching 예산을 실제 전송 성과로 바꾸지 않는다.
2. 실제 physical SPI·2슬롯·공통 host·독립 checker의 cold2+warm10 frame PASS.25462 source bytes와25462 actual read events가 일치한다. CRC/checksum의 X를 실패로 처리한다.
3. RTL 오류/STOP17case PASS. skip/repeat byte,wrong token,early ACK,중간 STOP,view 뒤 STOP,serial/destination/offset/bank/CRC 오류,중복 MAP,exact bitmap 누락,trailing byte,odd fragment,wrap span,CPU abort를 포함한다. 중복과 bitmap 오류는 독립 checker가 각각 fault2/3으로 거부한다. 공통 취소 뒤 RAM/queue/staging의256host-clock 동결과 ACK/retire/admission 차단을 확인했다.
4. 실제65816 cold2+warm10 및 STOP PASS. 전체 MAP/CGRAM/OAM/HDMA와 tile 값을 확인했다. warm PPU DMA와 최종 ACK는 같은 VBlank다. cold는 forcedblank 초기 DMA와 법적 blank의 최종 표시를 사용한다. warm의 prior bank 상태는 explicit fixture다.
5. 실제65816 reset 한 번으로12frame을 실행하며 중간 WRAM 재초기화 없이 모든 값을 확인했다. source/SPI availability는 fixture이므로 전체 시스템의12frame 성공이 아니다. CPU STOP/경계7case도 forcedblank·HDMA off·최종 ACK 없음으로 종료했다.
6.962 native stress는 실제 M4 record와 실제65816 30PPU jobs를 사용해 ACK line260에서 PASS했다. TILE 값은 명시적 synthetic fixture다. 실제962 source ROM·공유 SPI·ARM 연속 일정 또는 WCET 성공으로 세지 않는다.49104 제한과512 reserve·기존 cutoff를 완화하지 않았다.
7. live 시험은 실제 ARM foreground/refill/IRQ·공유 SPI·2슬롯·source/query/ROM 경쟁과 native CPU에서 계측한 bus service를 결합한다.754B receipt/64B CRC digest와 canonical source 값을 실제 경로에서 확인한다.65816 instruction lockstep/fullresident WCET 증거와 구분한다. master46561ps,SNES phase0,ROM_WINDOW1,고정907 capture cycle5371247을 그대로 유지한다. 결과는 앞의 판정처럼 startup 실패다. 실제905 source start는39214.243080ms/39414.242474ms로606ns 차이가 있고906도 누적 일정에 따라 달라졌다. **907/908 동일 actual source-start·ROM cycle의 pair 비교는 도달하지 못해 미실시**다. 위상을 고정한 fixture 시험을 그런 pair 성공으로 바꾸지 않는다.

최종905/906 full finish·commit까지 실제 SPI는16275/10986B,E2는882/994B(63/71회),WFI 요청14/19회,exception charge1296/1296clock이다. foreground ARM은1522520/1074171명령을 실행했다.CPI1·IRQ foreground checkpoint·entry/exit24clock 할당 모델이며 하드웨어 cycle/WCET가 아니다. `armF.json`은 finish 이전에 저장되므로 이 표는 누락되는 finish/commit 응답까지 원시 RPC로 다시 합산했다.42,162 ROM 요청/응답,pending0과 input 경쟁4228쌍을 확인했다.

## 시간 퇴행의 원인과 거부한 대안

단일 ABI가 SNES 후처리를 줄였지만,기존 tile 자동 prestaging을 없앤 위치가 source 공급에 backpressure를 만들었다. 최종 TILE job이 확정되어 전송될 때까지32B link가 막히고,실제 ROM 허용창을 놓치는 비용이 생겼다. default trial의905 첫OBJ request는약66.145ms로 기존약66.142ms와 비슷하지만,마지막OBJ 공급은약82.047ms로 기존66.296ms보다 늦다. 감소한 SPI 바이트만으로 실제 시간을 예측할 수 없다는 반례다.

별도 cold256B job 조기 발행도 실제 구현·시험했다.첫BG 저장은약66.682→49.303ms로 빨라졌지만 첫OBJ request가약82.533ms로 밀리고,cold906 완료는297.346ms로 default trial264.070ms보다33.276ms 나빠졌다.905 job23→29,wire8566→8716B가 추가된다.이 실험은 거부하고 기본 quantum0으로 유지한다. `--cold-quantum 256`은 거부한 대안이며 채택된 최적화가 아니다.원래 실행 코드는 private joint08에 보존했다.현재 CPU startup ACK를 사용해 재시험하려면 해당 quantum의 새 ARM vectors와 새 native profiles를 생산해 `--native`로 지정해야 한다.이전 native03을 새 startup 시험에 섞지 않는다.

초기 trial에서는 actual bus_valid 이전의 read capture가 X CRC를 만들었다. 이를 제거하고 known CRC·전체64B digest 검사를 강화했다. 앞선 약한 PASS는 최종 검증을 대신하지 않는다. compile/fixture/driver 실패와 전체 일정 실패 원본은 private `probes/nes-jobs394`에 보존한다. 라이선스 문제로 분류하지 않는다.

## 다음 경계

새 ABI와 native receiver의 의미·안전성 증거는 재사용하되394 구조를 생산에 적용하지 않는다. 다음 설계는 TILE 생산과 명시적 record admission 사이의 bounded prestaging 소유권을 먼저 정해야 한다. source·plan·host·queue를 실제로 함께 삭제할 RAM 실행기의 clock/port/resume 경계를 잡고,보존 검사와 bridge를 포함한 **최소2321 순삭제** 및 같은 ROM 창의 cold/startup 일정이 동시에 가능한지 먼저 판정한다.단순히 기존 host에 adapter를 추가하는 방식은 중단한다.

이 구조가 예산을 만족하지 못하면 ROM 중재·ARM/FPGA/SNES 역할·하드웨어 용량을 재검토한다. 더 많은 독립 FSM/seed/FIT 실험을 반복하지 않는다.911 캡처·71/heavy7 연속 일정·복수 위상·STOP 뒤 정상 재개·live mapper·fullresident/WCET·whole FIT/STA·실기60fps는 모두 OPEN이다. MMC4/5 여유로170comb 또는 단독 CPU의 blank 여유를 배정하지 않는다. production227/GBC164/saveSRAM은 변경하지 않는다. 자동 merge/구매/실기 배포는 하지 않는다.
