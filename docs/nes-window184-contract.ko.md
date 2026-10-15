# NES184 — 4개 패킷 연속 전송과 소비 완료 묶음 확인

PR114가 `91b0bf79cb8cc128a8ad83fefaf66f76c070ff57`로 병합된 뒤 `codex/nes-stream-window-184`에서 진행했다. NES183 실기에서 화면 개선이 미미했으므로 상태 조회의 작은 최적화를 반복하지 않고 MCU→FPGA→SNES 전송의 대기 구조를 바꾼다. **이번 결과는 구현·검증 후보이며 설치용 시험판이 아니다.**

## 작업 의미

화면 조각마다 MCU가 SNES 소비 완료를 기다리던 경로에 최대 4개 패킷을 보관하는 큐를 넣었다. MCU는 여유 공간이 있는 동안 DATA를 연속 전송하고 누적 소비 수로 공간을 돌려받는다. 실제 화면 전송을 위한 배선·펌웨어 구현이며, 디버그 항목만 추가하는 작업이 아니다.

수신과 소비를 겹칠 기반은 생겼지만 전체 프레임 생산·전송·표시를 동시에 처리하는 것은 아직 아니다. FPGA→MCU의 단일 capture lease도 유지된다. 기존 raw 화면의 전송량만으로도 16.7ms를 초과하므로 이 큐만으로 60fps 달성을 주장하지 않는다.

## 소유권과 호환성

- 기존 1개 M9K에 256바이트×4슬롯을 배치한다. enqueue 이후 해당 슬롯은 소비 완료까지 불변이며 save SRAM을 사용하지 않는다.
- E1은 기존 command+16..256바이트 packet+CRC16BE 형식이다. CRC/길이/여유 공간 확인 후 accepted가 증가한다. 꽉 찬 큐, 손상된 패킷, 애매한 전송 실패는 재시도 없이 중단한다.
- E0 응답은 20바이트: dummy, `F7`, flags, accepted BE16, retired BE16, ACK12, CRC8. flags는 bit0 nonempty, bit1 completed ACK valid, bit2 full, bit7 fault. 기존 F6 클라이언트와 혼용할 수 없다.
- accepted/retired는 16비트 순환 카운터이며 미소비 수는 최대 4다. MCU는 accepted 일치, retired 전진 범위, flags, CRC를 확인한다.
- FPGA는 SNES가 발행한 ACK12 전체와 현재 큐 머리의 op/seq/serial/generation을 대조한 뒤에만 retired를 증가시킨다. 동기 RAM 읽기 포트를 이 검사와 공유하며 검사 중 다음 packet_ready를 숨긴다. ACK 오류 뒤 후속 패킷을 공개하지 않는다.
- 완료 ACK 스냅샷은 다음 ACK의 부분 쓰기와 분리한다. SNES1815 실행 코드와 기존 버스 인터페이스는 변경하지 않았다.
- MCU DATA enqueue 성공은 **보관 완료**다. ACK를 만들어내거나 표시 완료로 계산하지 않는다. BEGIN/SEAL은 앞선 큐를 비우고 자기 실제 ACK까지 확인하는 barrier다. 프레임 표시 완료는 여전히 최종 SEAL ACK가 결정한다.
- 매 SPI 거래 전 시간·STOP·서비스 guard를 유지한다. STOP이 큐를 임의로 소비하지 않는다. COMMON reset은 소유권을 초기화하며 RAM 데이터 전체를 reset하지 않는다.

## 선택한 검증

private `probes/nes-window184/progress.json`과 [검증 요약](../analysis/window184-verification.json)을 기준으로 이어간다. 완료된 raw 자료는 수정하지 않는다.

| 대상 | 결과와 한계 |
| --- | --- |
| test03 RTL SPI + 기존 SNES bus | normal/phase/wrap 각 33패킷, 51거래, 3691 clocked bytes, 3904검사 통과. 소비는 합성 버스 구동이며 실제 65816 실행을 새로 결합한 결과가 아니다. |
| 실제 C로 RTL 응답 재생 | 조건별 51거래·51guard, 107실패 주입 통과. old F6, CRC, 잘못된 accepted/retired, transfer/guard 실패 포함. |
| 큐 경계 | 4슬롯 포화와 5번째 거절, 미완료/12바이트별 잘못된 ACK, 동시 enqueue/retire, 응답 일관성, STOP, 큐 보유/송신 도중/ACK 검사 중 COMMON reset. wrap은 카운터를 fffc로 설정한 뒤 경계를 실제로 넘긴 것이며 65536패킷 전체 실행은 아니다. |
| ARM arm01/check02 | 전체 링크 201396B, static 26588B, foreground RUN 37096B, IRQ 508B, 잔여 1232B. 183보다 static +24B, RUN +120B. RUN 동안만 사용하는 소유권이나 context는 기존 global runtime 안에 있다. |
| FPGA map01 | 전체 FIT 13587LE/939LAB/42M9K. 기존181 대비 +306LE/+16LAB, M9K 수 동일. 24LAB·14M9K 잔여는 미래 mapper 수용 보증이 아니다. |
| STA | nominal setup +0.194ns, hold +0.144ns. 별도 엄격한 implementation budget setup −0.258ns는 미통과. 변경된 배치의 conditional IO/CDC/reset/OAM/reply 검사는 아직 수행하지 않았다. 전체 타이밍 승인으로 표현하지 않는다. |

test01은 C 경고를 오류로 처리해 중단했고 줄 구분을 고쳐 test02를 통과했다. test03은 RTL/C를 바꾸지 않고 reset 시점을 보강했다. ARM check01은 sandbox WinError623으로 실행 실패했으며 check02에서 실제 전체 검사를 수행했다. 실패 자료를 성공 자료로 대체하지 않는다. ARM 검사에 재사용된 옛 scope 문구는 새 큐의 실기 로그 형식 승인 근거가 아니다.

33패킷 합성 조건에서 기존 패킷별 3거래 방식의 최소 99거래가 51거래가 되었다. 이는 실기 FPS나 실기 지연 측정치가 아니다.

## 60fps 예산

기존 실제 C/65816 시험에서 보존한 요청·응답 219쌍, 완성 7프레임으로 동일 분할의 wire 하한을 계산했다. 한 번의 조회에서 4슬롯을 모두 회수할 수 있다고 가정하고 CS 간격 8µs를 적용했다. 추가 poll, MCU/SNES 연산, FPGA→MCU 수신, 서비스, capture 대기는 제외한 **낙관적 하한**이다.

| 장면 | 기존 최소 거래→큐 거래 | 기존 wire 하한→큐 하한 |
| --- | --- | --- |
| normal 23패킷 | 69→32 | 11.798→9.807ms |
| raw 7행 38패킷 | 114→50 | 22.154→18.667ms |
| 나머지 raw 37패킷 | 111→49 | 21.700~21.914→18.327~18.541ms |

raw는 전송만으로 이미 16.7ms를 넘는다. 다음 성능 작업은 목적 VRAM bank의 기준 세대에 맞춘 차등/불필요한 map·CHR 전송 축소와 capture·전송·표시 겹침을 함께 검토한다. 중간 세대가 빠진 차등을 그대로 적용하거나 ACK만 삭제해서는 안 된다.

## 다음 작업과 배포 조건

1. 실제 production C→큐→실제 65816의 최소 normal/raw 및 STOP 결합 검사를 한다. 기존 unchanged boot와 모든 화면 모델을 반복하지 않는다. 현재 재생 검사는 독립 C와 RTL의 바이트 계약까지만 확인했다.
2. map01의 변경된 배치로 conditional IO/CDC/reset/OAM/reply 경로를 점검한다. nominal 통과와 stricter budget 미달을 분리해 판단하고, 옛 loader 경로의 작은 seed/FIT 반복으로 되돌아가지 않는다.
3. 기존 TXT에 새 window의 오류·sent/retired를 최소한으로 반영한다. 기존 io170 진단을 새 큐의 실제 응답처럼 보고하지 않는다. 위 결합 검사 후에만 184 이름과 짝지은 펌웨어/FPGA를 패키징한다. 현재 ARM 바이너리는 이름이183인 compile-only 후보이므로 배포 금지다.
4. 최소 결합 조건이 충족되면 SMB3 실제 첫 레벨(숫자1 타일→A)에서 화면·사운드·메뉴 복귀와 처리 시간을 확인한다. 같은183/044 복원이나 불변 FIT를 반복하지 않는다. 그 다음 payload와 겹침 개선을 계속해 실제 약60fps를 목표로 한다.

ASM/RBF/ZIP/실기/60fps 통과는 아직 없다. 현재 실기 기준은183이며 GBC164, 세이브 SRAM, 완료 archive는 보존한다. AV60fps→장기 플레이·오류/실기 reset 시 로그→입력 유지 검증 순서와 향후 MMC4/5·state·mute·frameskip 요구를 유지한다.
