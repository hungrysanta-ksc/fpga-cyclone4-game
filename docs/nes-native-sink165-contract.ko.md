# NES165 C 송신기와 SNES WRAM 수신·표시 응답

이번 구현은 기존 SNES 내부 비교를 **동시에 실행되는 C 송신기와 SNES 수신기**에 연결한다. 실제65816이 mailbox 데이터를 WRAM으로 옮기고 비교·DMA를 수행한 뒤 응답한다. C는 그 응답이 와야 다음 패킷을 보낸다. 이전 시험처럼 C 표시 완료를 호스트에서 임의로 주입하지 않는다.

중간 mailbox는 PC 파일 모델이다. **실제 MCU 게임 루프와 SPI↔FPGA↔SNES 버스는 아직 연결하지 않았다.** 이는 물리 왕복·실기 성능·메뉴 복귀 검증이 아니다. 기존164가 설치 후보이며 새165 SD 패키지는 없다. 다른 게임의 카트리지 SRAM·세이브·복구 공간을 사용하지 않는다.

## 구현

- [C 송신기](../src/nes/firmware/nes_native_sink165.c): `begin → pattern → seal`로 순차 패킷을 전송한다. 이전/새 표를 MCU로 다시 읽지 않으며 C 차분 명령 목록도 만들지 않는다. 기존 C 표시 변환기의 pattern callback에 맞는 인터페이스다. 이번 왕복 시험은 이미 변환된 두 장면을 재사용했다.
- [SNES 수신기](../tools/build_nes_sink165.py): header·serial·generation·순서·영역·연속 offset·길이를 검사하고 inactive WRAM 후보에 DMA한다. 마지막 길이가 실제 받은 길이와 같아야 비교를 시작한다. 실제 표시 완료 후에만 상태1 ACK를 보낸다.
- [동시 실행 시험](../tools/test_nes_native_sink165.py): C 프로세스의 패킷 파일을 mailbox에 노출하고, 실제 SNES register 쓰기로 만들어진 ACK 파일을 C가 읽는다. 비교/WRAM/PPU 명령이나 표시 성공 ACK를 모델이 생성하지 않는다. 캡처를 위해 표시 ACK 전달을 두 모델 프레임 동안 지연하므로 시험 소요 시간을 전송 성능으로 해석하지 않는다.

응답 유실·실패·다른 serial/generation/sequence는 C FAULT로 끝난다. 게시 전에 BUSY를 설정해 재진입도 막는다. 모호한 결과에 자동 재시도하지 않는다. C·전송부·SNES를 함께 초기화하기 전 재사용 금지다. 이전 C stage의 임시 실패 후 재시작 계약을 이 경로에 그대로 적용하지 않는다.

## wire 계약

패킷은16바이트 header+최대240바이트 payload다. 모든 다바이트 정수는 little endian이다. **하드웨어 어댑터는 완전한 패킷의 CRC/길이를 검증한 다음에만 ready를 게시하고 ACK까지 내용을 고정해야 한다.** 현재 파일 모델은 무결한 파일을 원자적으로 게시하며 물리 CRC 회로를 대신 검증하지 않는다.

| header offset | 내용 |
| --- | --- |
| 0 / 1 | opcode1 BEGIN,2 DATA,3 SEAL / section0..5(DATA만) |
| 2 | sequence16; BEGIN=0, 다음 패킷마다+1 |
| 4 / 8 | serial32 / generation16 |
| 10 / 12 / 14 | 영역 내 offset16 / payload길이16 / 예약0 |

BEGIN은 빈 payload, section/offset0이다. serial은 공통 reset 후1부터 정확히 증가하며 소진 시 중단한다. generation은 반복 가능하다. DATA section은 BG/OBJ/map/CGRAM/OAM/HDMA이며 각 영역에서 offset0부터 연속이어야 한다. 실제 주소·한도는 수신기의 고정 표로 정하므로 패킷이 임의 WRAM 주소를 지정하지 않는다. SEAL payload18바이트는 여섯 영역 길이12바이트, HOFS/VOFS/예산 각2바이트다.

ACK12바이트: status,opcode,sequence16,serial32,generation16,65,9A. status0은 BEGIN/DATA 수신,1은 **SEAL 표시 완료**다. E0은 잘못된 패킷, E1/E2/E3은 기존 비교 입력/명령/예산 실패, E4는 비교 중 STOP이다. 신뢰할 header조차 없으면 ACK 없이 quiescent로 들어가며 MCU의 유한 시간 가드가 종료해야 한다.

## 새 SNES 접속부 요구

| SNES 주소 | 동작 |
| --- | --- |
| 006000 | bit0 packet ready |
| 006001 | bit7 STOP 요청 |
| 006004–006005 | 고정된 전체 패킷 길이16..256 |
| 400000–4000FF | 고정된 패킷 읽기 창; 실제 SRAM이 아님 |
| 006010–00601B | ACK bytes 쓰기 |
| 00601C | A5 쓰기로 ACK 원자 게시·패킷 해제 |
| 006002–006003 | 기존 입력 샘플 low/high 전달 |

ACK와 패킷 소유권은 새로운 FPGA 접속부에서 보장해야 한다. 기존164의6000/framebuffer 또는40뱅크 출력과 동시에 활성화하면 안 된다. 새 연결은 명시적인 paired 식별로 구분하고 기존6B/E5를 무조건 허용하지 않는다. FPGA 접속부·타이밍 확인 전 기존164에 이 client만 설치하지 않는다.

프로그램 body2,651바이트, compact ROM4,096바이트다. 기존2,048바이트 프로그램 decode와 맞지 않으므로 새 ROM index와 벡터 mirror(FFCx→0FFCx)를 함께 변경해야 한다. 실행은7E2000부터, header/수신 상태는1200–1239, 영역 수신량은1080–108B다. 기존 local 비교의1000대/1100대와 DP40–6F는 그대로 사용한다. stack1FFF와 bank7F 두 후보를 침범하지 않는다.

기존 SPC bootstrap을 재사용했다. 수신 대기와 비교 service에서 자동 joypad를 읽고 STOP을 확인한다. 비교 중 STOP은 비교 반환 후 DMA 전에 검사한다. 즉시 하드웨어 중단의 최대 지연이나 물리 리셋/메뉴 복귀를 증명한 것은 아니다. 선택된 fixture의 STOP 후 새 표시 ACK가 없음을 확인했다. 실제 bridge/MCU 시간 가드와 기존 공통 STOP을 연결해야 한다.

## 결과와 제한

sink01 정상:3표시/137패킷, C가 보낸18,727바이트+ACK1,644바이트. 세 번째는 무변경 장면이며 후보를 다시 반전했다. 마지막에 잘못된 section 요청을 보내 E0으로 끝났다. 비교 결과6명령/5,493바이트→2명령/18바이트→0명령/0바이트다.

STOP:90패킷,12,462바이트+ACK1,080바이트. 첫 장면만 표시되고 두 번째 비교 도중 STOP은 E4로 반환했다. 두 실행 합계227응답,4캡처의 유효 영역229,376픽셀과 캡처 전체 바이트가 기존 기준과 일치했다. 새 장면은 두 개뿐이며 게임 부팅·첫 레벨을 다시 실행한 시험이 아니다.

SPC A9 초기화, 출력 후 forced blank 없음, visible PPU 쓰기 vblank, 입력 DOWN 샘플150/94회를 확인했다. 이는 고정된 입력 레지스터 모델의 전달 확인이며 실기 마리오의 입력 유지나 소리 품질 검증은 아니다. 별도로 C의 I/O 실패·stale serial/generation/sequence·실패 ACK5종이 재시도 없이 FAULT가 됨을 검사했다.

ARM context24바이트(호스트32), text704바이트, 직접 stack packet304/ seal88/ pattern24바이트다. callback과 호출자는 중첩되며 전체 stack 승인값이 아니다. 이전 stage460바이트 대신 sink24바이트를 사용하는 단순 정적 합계는60,340바이트다. 링커 영역65,424바이트와 차이5,084바이트는 실제 전체 link·heap·IRQ 여유를 보장하지 않는다.

**다음:** 이 ABI의 유한 SPI 패킷/ACK 접속부와 SNES bus/4KiB ROM decode를 구현하고 기존 MCU 게임 루프의 guard/time/STOP에 연결한다. 기존38M9K framebuffer를 교체하며 전체 자원·링크·타이밍의 변경 부분만 검사한 뒤 SMB3 첫 레벨 실기로 간다. 기존39.59ms SPI와29.7ms 비교 병목은 계속 열려 있다. 정상 플레이·60fps 목표 미달성. 동일 boot/A-B/044 시험이나 일반 진단 확장은 하지 않는다.

[검증 요약](../analysis/native-sink165-verification.json) · [기존 SNES 내부 비교](nes-native-local165-contract.ko.md)
