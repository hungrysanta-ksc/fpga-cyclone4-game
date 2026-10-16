# NES197 SPI 계획 송신과 대기 중 chunk 소비

## 작업 의미

196의 host byte 입력에 실제 Mode0 SPI 핀 endpoint를 연결하고, MCU가 계획 수신 여유를 기다리는 동안195 op7로 완성된 타일을 SNES가 읽게 하는 C 서비스를 추가했다. 타일 픽셀을 MCU로 복사하지 않는다. 배포186/GBC164/save SRAM은 유지한다. 실제 board mux·프레임 controller·epoch·runtime 호출은 아직 연결하지 않았다.

## 프로토콜

E8/E9는 기존6x/7x/D0..D3/E0/E1과 겹치지 않는다. endpoint,196 host RAM 및193 descriptor는 같은 host clock을 사용한다. SPI Mode0, MSB first, 시험8MHz/host84MHz, transaction 후 SS high 최소2us. IRQ/service는 SPI 소유권 밖에서 수행한다. 이 속도의 실물 IO/CDC 승인은 아직 없다.

E8 상태는 command를 포함해20바이트다. 응답0은 무시하고1=D7,2=version1,3=flags(bit0 plan credit,bit1 END latched,bit7 fault),4..5=accepted BE16,6..17=194와 동일한 descriptor12,18=0,19=CRC8(poly07/init0,bytes1..18)이다. descriptor는 ready/kind/lengthLE16/offsetLE16/generationLE16/tokenLE32 순서다. ready0이면 descriptor 전체0. command 완료 시 snapshot을 잡아 이후 consume/변경과 섞이지 않는다.

E9는 `command,length,payload[length],payloadCRC16BE,framingCRC8,A5`로 총length+6바이트다. payload는196 version1 형식. CRC8은 command부터 payload CRC16까지 포함한다. valid credit가 있을 때만196 RAM에 쓰며 SS 상승 시 정확한 byte/bit 길이·framingCRC·tail을 검사한 뒤 seal한다.196이 payloadCRC·형태·generation을 추가 검사한다. accepted는 framing 수락 수이고, 타일 완성/표시 수가 아니다. 잘린 쓰기·credit 위반·오류는 sticky fault이며 재시도하지 않는다. FFFF accepted에서 추가 송신을 거부한다. source fault를 endpoint가 별도로 유지하므로 downstream reset이 원인을 지워도 오류를 잃지 않는다.

SPI에서 consume하지 않는다. SNES194만 token을 확인한 뒤 consume한다. END pulse는 상태 조회까지 유지한다. 현재 서비스는 **common reset 후 한 프레임/session** 계약이다. 여러 프레임 생산 controller의 generation별 재무장/END clear와 fresh token은 후속 작업이다. 단순 프레임마다 전체 NES를 reset하는 방식으로 연결하면 안 된다.

## C 서비스

`nes_plan197_emit`는191 planner callback으로 사용할 수 있다. 호출자는 service를0 초기화하고 transfer/guard/context/sink/poll_limit을 설정하며, sink는 같은 generation의 BUILD 상태여야 한다. 실제runtime 호출부는 아직 이 API를 사용하지 않는다.

매 상태 조회마다 chunk ready를 먼저 처리한다.195 bulk의 실제 ACK 검사를 통과한 뒤 상태를 다시 조회하므로 이전 descriptor snapshot을 재사용하지 않는다. credit가 있어도 chunk 소비를 건너뛰지 않는다. bounded poll_limit 및 guard로 STOP/deadline/audio/input을 서비스한다. false 이후 caller는 공통 취소해야 한다. END를 보낸 finish는 END latched+남은chunk 없음까지 기다리지만, 표시 완료는 기존 sections/SEAL/finalACK에서만 성립한다.

## 검증

SELECT `test03`, `faults01`, `c03`, `evidence01`.

- 실제 핀 SPI→196→192 arbiter/70ns READ16→193 raw aperture: 기존8합성장면97계획1840바이트와 완전히 동일.512계획 반복8192바이트도4chunk로 완료. SPI descriptor snapshot을 대조하고 시험 SNES bus consumer가 읽은 뒤에만 consume했다. saturation 시험은 아니며 해당 run fullwait/sourcewait는0이다.
- SPI17경계: 최대32바이트 계획, 무관 명령 비선택, descriptor snapshot 유지, END pulse 유지, sticky fault, 멈춘 NES clock의 STOP, credit 위반, 잘린 payload/bit, CRC16/CRC8/tail/length/version 오류. 이전 잘못된 데이터를 노출하지 않았다.
- 실제 C197 서비스+실제 C195 sink:8장면97계획/97chunk 소비,105개E9 프레임이196 wire와 동일. mock SPI는 chunk가 남아 있으면 credit0을 반환하여 소비 없이는 진행할 수 없게 했다.13오류를 포함한21검사 통과. SPI와 SNES ACK는 이 C 시험에서 mock이며, 위 RTL과 실제 C를 동시에 실행한 시험은 아니다.
-195 실제C+65816 결과는 재사용. 이번에는 SNES CPU/FIT/전체ARM/새FW/ZIP/실기 시험 없음. 호스트gcc stack 보고는 ARM stack 승인이 아니다.

test01은 sandbox에서 시험 산출물 전에 종료. test02는 통합 시험의 forward declaration 오류, test03에서 수정. c01은 sandbox DLL623, c02는 시험 도우미 misleading-indentation 경고, c03 통과. 완료 기록은 수정하지 않는다.

## 60fps 예산과 다음 순서

현재 per-plan 상태20B+최소E9 22B+두 번의SS gap4us는8MHz에서 최소46us다.512계획이면 **23.552ms**로, CHR 읽기·SNES 소비·geometry/raw·표시 시간을 빼고도16.67ms를 넘는다. 이것은 가정에 따른 하한 계산이며 게임 FPS 측정이 아니다. 합성512반복 시험 전체39.293ms도 실제 스크롤 부하나 성능 향상률이 아니다.

따라서 이 경로를 그대로 최종60fps 경로로 승인하지 않는다. 다음은 이미 사용하는 작은 M9K의 여유 공간을 활용한 복수 계획 credit/batch 전달과 physical pattern identity 기반 재사용을 검토하여 per-tile status 왕복을 줄이는 것이다. batch에서도 chunk service와 공통 취소를 유지하고, pixel 전체를 MCU로 가져오는 방식으로 돌아가지 않는다. 그 뒤 generation별 frame lease/epoch·END 재무장·descriptor/board mux·production runtime을 결합하고 전체ARM/FIT/IO를 확인한다. 불필요한 독립 boot/FIT 반복은 하지 않는다.

실제 수용 기준은 SMB3 숫자1+A→첫레벨→RIGHT+B 유지/A press-release 반복의 연속 스크롤이다. collected_runs는 비어 있다. 같은generation 원본 읽기/계획/전송/고유 표시 간격을 측정하고16.67ms와 비교한다. 사운드/조작 유지, AV약60fps→장기play/오류reset로그→입력유지 순서를 지킨다.
