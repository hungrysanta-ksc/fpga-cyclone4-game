# DMC/OAM 실제 경쟁 — NES-P2-DMC-OAM-017

2026-10-05. **전송 중재·데이터·CPU 복귀는8조건 통과. Mesen과 DMC 요청 시점은 불일치하여 미해결.**
구현NES-P2-RDY-014 유지, 코어 수정 없음. 이번 결과를 전체 DMC 정확성 통과로 간주하지 않는다.

CPU가 $4010=$0F(IRQ/loop off), $4011=0, $4012=0, $4013=1, $4015=$10을 쓴다.
$C000 시작17-byte sample을 설정하지만 OAM 검사 뒤 채널을 끄므로17bytes 전체 재생/완주 검사가 아니다.
OAM trigger 전 NOP0/40/100/180 × padding2개 =8조건. RAM page02/03과 OAM start00/01/FC/FF 사용.
DMC/APU/RDY/DMA/IRQ 어느 입력도 강제하지 않는다. 렌더링 off, CPU IRQ masked, ideal external memory다.

실제 Questa RTL와 actual Mesen runtime 각각에서:
- OAM8회, source2,048bytes/read+write4,096accesses/OAM snapshot2,048bytes가 진단 패턴과 일치한다.
- DMA 중 DMC fetch는 RTL9회/Mesen10회. 각각의 timeline에서 DMC가 OAM read 슬롯을 사용하고 다음 put 슬롯은 idle, 이후 원래 OAM byte부터 손실 없이 이어진다.
- 기본513/514 pause에 overlap fetch당2cycles가 추가된다. RTL에서는515/516/518cycles 관측.
- RTL의 request/ack/버스 주소·data 및 다음 sample_buffer/have_buffer를 대조하여 overlap9건 실제 수신 확인.
- DMA 동안 CPU read 주소 유지, 완료 뒤 INC$10 정확히1회, 누적1..8과 OAMADDR wrap 확인.
- 변조10종(data/address/tick/pause/ack/request/buffer/OAM/INC/truncation) 모두 거부.

정확한 요청 시점 비교는 실패다(`runtime_timing_match=false`). 첫 case에서 DMC enable write 기준
첫 byte는 둘 다+5cycles지만 두 번째 byte는RTL+123/Mesen+275cycles다. 차이는152CPUcycles.
첫 OAM trigger 기준으로는+112/+264cycles. 이후 case의 상대 요청 시점, 읽은 sample index,
overlap 횟수가 달라진다. 두 번째 fetch부터 관측되었다는 사실만 확인했으며 reset/timer/shift state 중
어디가 원인인지는 아직 확정하지 않았다. 이 차이를 상수 offset 보정으로 숨기거나 한쪽 코어를 임의 수정하지 않았다.
두 overlap을 관측한 구간에서는432cycles 간격이나, 이것으로 전체 APU 타이밍 정확성을 추론하지 않는다.

ROM SHA256: `935e243c87e77b0944e59bc74aa1c816c04beaea669e60496165be67b6714d91`.
Questa 두 실행의 dma-bus.tsv/oam.tsv와 arbitration 기존8열이 동일하다. 두 번째 실행은 buffer/have 열만 추가했다.
각 실행 약9.346ms, 오류0/기존 경고42, period/unknown0. compiled inventory17개는016과 동일하며 T65는
`884a7c84128a9936690f1a73a14036b7742aed646a78209471a769071edfa692`다.
Mesen exe/dll/core/settings 해시는capture.json에 고정 기록했다. prior IRQ/Mapper4 영상 회귀는 이번에 새 실행하지 않았다.

처음 verifier의 마지막 cycle 식이 첫 접근+510으로1 작아 잘못 실패했다.512접근의 마지막은첫 접근+511이다.
수정 전 소스/실패 보고서를baseline/에 보존했고 최종 검사는 원시 기록을 바꾸지 않고 통과했다.

직전016의117hashes를 상태 갱신 전에 확인/보존했다. GBC152source hashes/Quartus inputs/2048boot bytes PASS,
upstream clean, 기존 원래 초안 보존. FLOAT process/listener0. 라이선스/runtime 메타데이터와 서버로그는 복사하지 않았다.
원시 증거는 ignored `analysis/local-dmc-oam-017/`; sanitized source/summary/contract/manifest만 allowlist에 추가했다.

다음 우선 작업: **DMC enable 이후 첫 refill 차이의 기원을 reset timer·bit counter·buffer empty 상태 관측으로 분리**.
DMC 단독 진단부터 양쪽 clock 기준을 맞추고 원인을 확정한 뒤 수정 필요성을 판단한다.
이번8조건은 start/end boundary collision, DMC IRQ/loop/wrap, DMA abort, RMW $4014, CPU write halt,
controller read 부작용, rendering-time OAM, audio waveform, 외부 stall 검증을 포함하지 않는다.
NES→SNES·SMB3·전체 fit/STA·실기 및 upstream license hold도 미완료다.
