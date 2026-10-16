# NES198 계획 묶음 전송과 현재 SPI 예산

PR117 같은 branch의 후보 구현이다. 배포186은 변경하지 않았다. 작업 의미는 타일마다 계획을 쓰고 상태를 조회하던 왕복을 줄여, FPGA 타일 생성→SNES 직접 DMA 경로의 제어 비용을 낮추는 것이다. 새 디버그 관측기는 추가하지 않는다.

## 전송과 소유권

- E8 상태는 20B이며 D7/version2이다. flags의 bit0=credit, bit1=END latch, bit7=fault; accepted는 BE16 묶음 수다. 뒤에 기존12B descriptor, reserved0, CRC8이 온다. version1인197 서비스와 혼용하지 않는다.
- E9는 `E9,lengthLE16,plans8,payload,CRC16BE,CRC8,A5`이며 총 payload+8B다. payload는196의16..32B 계획을 연결하며 개별CRC는 생략하고 전체payload CRC16을 검사한다. framing CRC8은 명령부터CRC16까지 포함한다. SS 상승에서 정확한byte/bit 길이와 tail을 검사한다.
- RTL은 1..16계획/16..512B를 받는다. RAM은1024×8, 512B 두 bank다. 용량상 한M9K 구성이지만 MAP/FIT 결과는 없다. payload는 reset하지 않는다.
- host는 seal과CRC 확인 후 `{bank,count,plans}`를 기존 mailbox165로 넘긴다. handoff에서 writer bank를 바꿔 다른bank를 채운다. 두 번째seal은 첫bank 반환까지 기다린다. 범용 비동기FIFO나 새 포인터CDC를 도입하지 않았다.
- NES는 계획 길이·kind·shape·generation·총길이·계획 수·END가 마지막인지 검사한다. 마지막 계획의 모든bytes를 decoded fields로 복사한 CHECK에서 mailbox를 반환한다. 해당 fields는 tile_done까지 유지하므로 bank 재사용과 RUN이 겹쳐도 안전하다.
- CRC는 batch 공개 전 검사하지만 의미 검사는 계획 순서대로 한다. 뒤쪽 계획의 의미 오류 전에 앞쪽 타일이 staging됐을 수 있다. 오류는 common cancel이며 최종SEAL/displayACK로 승인하면 안 된다.
- reset/STOP/source fault는 양쪽 endpoint의 공통 취소다. 독립domain reset 허용을 주장하지 않는다. accepted는 framing 수신 확인이며 decode/consume/display 완료 수가 아니다.

## C 서비스와 기존 DMA 한도

실제186 `nes_native165_bulk.inc`는 한 전송을259B로 제한한다. 이를 늘리지 않고 C198은 payload240B/최대15계획, 전체248B로 제한했다. 길이32B 계획은 한 묶음에7개까지 들어간다. RTL512B는 protocol 여유이며 현재 C가 최대 크기를 보내는 것은 아니다.

C workspace에는248B 송신buffer 하나만 두고 TX==RX로 사용한다. callback은 동기 완료 및 buffer 비보유, in-place 지원 계약이다. status20B는 별도 작은 송수신 배열이다. emit 성공은 local queue에만 들어갔다는 뜻일 수 있다. finish가 END를 붙이고 남은 묶음을 보낸 뒤 END latch와 빈chunk 상태를 기다린다. finish도 최종 화면 표시ACK를 대신하지 않는다.

credit 대기 중 준비된chunk는 실제195 C sink/op7로 먼저 소비하고 상태를 다시 읽는다. emit/송신/대기에서 guard를 호출하며 오류/응답 불명확/세대 변경은 terminal이다. 같은 묶음을 재전송하지 않는다. 배포runtime의 audio/input/deadline guard와 공통취소 호출은 아직 결합되지 않았다. 전체ARM/RUN/IRQ 승인은 별도다.

## 검증 범위

SELECT: `probes/nes-batch198/test02`, `faults02`, `c03`, `dma01`, `evidence01`.

- 실제 SPI→198 RAM→192 qualified arbiter/70ns READ16→193 aperture: 8합성장면97계획1840B가186 reference와 동일. 11묶음이다.8MHz 시험은 protocol capability 모델이다.
- 512개의16B 계획+END는35묶음,8192B/4chunk로 완료했다.8MHz와 실제설정에 맞춘2.625MHz 모두 통과했다. 후자는76SPI calls/689356NES cycles, 모델시간32.096399ms다. 두 run 모두 fullwait/sourcewait0이어서 포화 검증은 아니다. 실제SNES CPU/C scheduler와 함께 실행한 시험도 아니다.
- SPI/decoder23검사: 최대512B,16계획, 두bank 보유,8묶음128계획bank wrap, queued STOP, CRC/길이/bit/tail/version/credit/sticky fault, plan count0/17/누락/남은bytes. faults02는2.625MHz다.
- 실제C198+195 sink24검사.8장면과512pressure의46송신frames가 RTL시험의 독립Python encoder와 byte-exact. 최대32B계획 분할, buffered generation 변경, finish 재호출,13오류 포함. SPI/SNES ACK는mock이며 throughput 결과가 아니다.
- 기존 배포186 DMA 코드를 그대로 사용한 비동기register model: in-place1..248B×3속도744성공, 각byte 위치의248DMA fault와 무재시도/정리/경계 보존 통과. STM32 bus arbitration/WCET나 실기 증명은 아니다.
- 195 actualC+65816 증거와 이전197까지13개 archive는 그대로 재사용하고 hash를 확인한다. 신규 FW/FIT/STA/ZIP/실기 결과는 없다.

중간 test01/faults01/c01은 넓은512B C전송 조건 또는 이전helper 결과로 보존하며 선택하지 않는다. c02는240B 한도에서 normal batch 수를8로 가정한 harness assertion 실패다. 기대값11로 고친 c03을 선택했고 production C는 바뀌지 않았다.

## 60fps 판정과 다음 단계

이전197의8MHz 계산은 실기 설정이 아닌 모델이었다. 실제186 코드는84MHz/PRESCALER4로 SPI2.625MHz이며198에서 클럭은 바꾸지 않았다. 네 번의2us wait도 유지한다. 최대259B 제약과 함께 증거 source pin을 남겼다.

512개16B 계획의 payload8192B만 보내도2.625MHz에서는24.966ms로16.67ms를 넘는다. status/framing/END/타일 생성/SNES 처리를 포함하면 더 길어진다. 따라서35묶음으로 줄었다는 사실을60fps 달성으로 해석하면 안 된다. 합성32.096ms 또한 게임FPS가 아니다.

다음은 **stable physical pattern 재사용과 변경분 계획**으로 스크롤 중 보내야 할 계획 자체를 줄이는 것이다. 물리CHR tag만으로 재사용하면 안 되며 content epoch/CHR-RAM 변경, row/alt/mask 변환, destination slot ownership, 실제표시bank/base generation을 포함한다. 미확인 상태는 bounded rebuild로 되돌린다. SPI 속도만 올리거나 입력/사운드/게임 진행을 생략해 통과시키지 않는다.

그 뒤 generation별 frame lease/epoch·END 재무장·fresh token·board mux·production runtime을 최소 결합한다. 현재 한frame/commonreset session이며 프레임마다 NES 전체reset으로 연결하면 안 된다. 전체ARM/FIT/IO 및 실제SMB3 첫레벨 스크롤을 거쳐야 한다.

`analysis/scroll193-measurement-plan.json`의 collected_runs는 아직 비어 있다. 숫자1+A→첫레벨 확인→RIGHT+B 유지/A press-release 반복으로 원본읽기·신규/재사용계획·전송량·고유표시간격 median/p95/max를 비교한다. 오프닝/정지/합성 반복/ACK수로 스크롤 부하 감소를 대신하지 않는다.186/GBC164/saveSRAM 보존, AV약60fps→장기플레이/오류·reset로그→입력유지 품질 순서다.
