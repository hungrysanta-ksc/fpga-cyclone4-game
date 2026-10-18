# NES235: 실제 query 변환과 두 은행 SPI, 인코더 자원 gate는 미통과

PR127의 같은 브랜치에 이어 기록한다. **두 RTL 끝점의 기능과 RAM 추론을 확인했다. 두 끝점 사이의234 증분 생성기는 아직 host fixture이며 전체 FPGA 송신기가 완성된 것은 아니다.** 생산227 및 새 실기 설치물은 변경하지 않는다.

## 작업 의미

기존 입력 SPI는 한 블록을 봉인한 뒤 D2 확인까지 다음 블록을 만들 수 없었다.235는 전달 중인 은행을 보존하면서 다음 은행을 채워 준비·전송을 겹치는 구현이다. 실제 frame201 자료를 canonical geometry로 한 번 읽는 회로도 구현했다. 60fps를 위한 입력 경로 작업이며 로그 확장이 아니다. 다만 끝점만 합성해도 논리 예산 대부분이 필요하므로 전체 증분 생성기를 곧바로 추가하는 계획은 승인하지 않는다.

## 연결된 것과 남은 것

실제 frame201 collector → query235 → canonical5741B는 RTL 시뮬레이션으로 연결했다. 별도 시험에서는 봉인된234 record fixture → SPI235의 실제 직렬 핀 → 받은 바이트 → 실제 C234 → planner/sink231을 실행했다. 두 시험은 같은230 관측 SMB3 첫 레벨 스크롤905..975의71프레임을 사용한다.

**query235와 SPI235 사이에 RTL delta encoder/base RAM/raw 생성기를 연결한 시험은 아니다.** 실제 게임 CPU·생산 ARM SPI decoder·전체 RUN/IRQ·SNES 실시간 소비기·전체 보드 CDC/STA·실기60fps도 포함하지 않는다. 출력355파일 동일성으로232의65816 결과를 재사용하며 이번에65816을 새로 실행했다고 주장하지 않는다.

## query235 계약

- geometry lease의 owned/valid/generation을 매 동작에서 확인하고, 상실·abort·잘못된 response 후 common reset 전까지 재시작하지 않는다.
- map1056×2, row224×1, object128×8, exception128×4, raster224×8, palette64×1, counts12+patch_count1의5741B를 순서대로 출력한다. 유효 count 밖은0으로 만들고 collector의 과거 RAM을 읽지 않는다.
- 실제 query는 유효 요소마다 한 번이다. source 데이터는64bit holding register로 받아 byte로 내보낸다. ready가 낮으면 byte/offset을 유지한다.
- 잘못된 count, hit 실패, 각 section의 허용 폭 밖 data를 거부한다. response가 영원히 없을 때 완료나 데이터를 만들지 않으며 외부 deadline/common abort가 필요하다.
- raw patch pixel(kind7) 조회, base 비교/잠정 갱신, record 작성과 END-count/CRC는 이 모듈에 없다. 다음 인코더는 raw와 fetch-time CHR/row-mask 의미를 유지해야 한다.

## SPI235 계약

512×8 simple dual-port RAM을256B씩 두 은행으로 사용한다. record1..243B를 block 최대248B에 통째로 넣는다. 남은 공간이 부족하면 현재 블록만 봉인하고 입력 record는 새 은행이 가능할 때 받는다. 마지막 record의 flush 또는248B 도달 시에도 봉인한다. 길이·CRC16의24bit descriptor는 기존 mailbox206 두 개로 전달한다. 송신측은 해당 은행의 D2 확인이 되돌아오기 전까지 RAM을 쓰지 않는다.

host84MHz/source 약22MHz, SPI2.625MHz 조건에서 시험했다. D0/D1/D2/D3 명령 공간은 기존과 같지만 D0 signature는 **D8**이다. 기존 D6 tagged-record decoder와 호환되지 않으므로 paired ARM 변경 없이 생산 경로에 넣으면 안 된다.

| 명령 | 역할 |
|---|---|
| D0 | D8, fault/ACK여유/sealed, tokenBE16, lengthBE16, CRC8 snapshot |
| D1 | 블록 전체와 CRC16. 정확히 length+3 SPI bytes를 끝내야 read_seen 설정 |
| D2 | 완전한 D1 후 matching token을 확인해 은행 소유권 반납. tokenFFFF는 wrap하지 않고 오류 |
| D3 | generation/accept를 PREPARED mailbox로 전달. source controller가 의미를 검증해야 하며 최종 SNES DISPLAYED ACK가 아님 |

control은8B, offsetBE24/arg/complement/CRC8/A5이며 부분 SS·잘못된 token·CRC·길이·중복 POP은 오류로 종료한다. CRC16은1021/FFFF, CRC8은07/00이다. 실패 시 은행을 임의로 재사용하지 않는다. abort 후 ACK valid도 차단한다. **common reset만 지원**하며 독립 endpoint reset은 지원하지 않는다. host 재시작이 source에 동기화되기 전에는 입력을 받지 않는다. bank POP, C COMPLETE, source COMMIT, SNES displayACK는 서로 다른 수명 단계다.

## 검증과 실패 보존

선택은 `test02/guards01/map01`이다. `test01`은 정상71프레임 SPI는 통과했지만 foreign-command 시험 후 D0를 다시 읽지 않은 test driver 때문에 length 검사에서 중단됐다. fresh status를 넣어 고쳤으며 실패 결과를 보존했다. 테스트 준비 중 추가한 host 재시작 gate와 ACK fault gate는 선택 RTL에 포함한다.

- 두 clock phase3.5/17ns 각각 실제 SPI71프레임,2,229records,350blocks,62,967payload bytes가 fixture와 byte-exact였다. record 분할 없이 수신했다. 정상 시험의 총 SPI75,318bytes는 의도적21회 재읽기와 제어를 포함한 시험값이며 프레임 성능 값이 아니다.
- 다른 은행이 봉인된 동안50,493/50,490byte 쓰기를 관측했다. 양쪽 은행이 찬 backpressure와 재읽기에서도 전달 은행에 쓰지 않았다. 이는 buffer overlap 기능이며 encoder 준비 시간이나 전체 파이프라인 throughput 증명이 아니다.
- 실제 SPI 수신 바이트를 C234에 투입해71프레임/4,066,624 reference checks 및 geometry/raw/metadata/packet/plan355파일 동일성을 확인했다. 실제 C의1,459 fault/restart 검증도 통과했다.
- 실제 collector→query235는71프레임 각각5741B와 canonical zero, 실제 valid query 개수가 기준과 같았다. 출력 ready에 주기적 stall을 넣었다.230 관측 adapter의 OBJ timing/raw anchor/RGB alias 한계는 그대로다.
- 별도 좁은 경계 시험: SPI19checks, query21checks. byte 중간 SS, partial record abort, ACK backpressure, stopped-clock common reset, token wrap/duplicate, invalid count/hit/width, 응답 누락+abort, generation/lease 상실, stalled output, 새 generation0 재시작을 검사했다. 이미 통과한71프레임 전체를 반복하지 않았다.

재현 도구: `tools/run_nes_source235.ps1 -Out <새 ASCII 절대경로>`, 추가 경계만은 `-GuardsOnly`. 기존 승인 FLOAT wrapper/Starter를 사용하고 license/server 로그는 private temp에 둔다. `tools/map_nes_source235.py --out <새 ASCII 절대경로>`는 각 endpoint를 한 번 MAP만 한다. user ROM/관측 raw 자료·생성 binary는 공개 Git에 포함하지 않는다.

## 자원 결과와 제한

Cyclone IV E EP4CE15F17C8, Quartus25.1std.0에서 각 endpoint를 별도로 MAP했다. FIT/배치/STA는 하지 않았다.

| 회로 | LE | FF | RAM |
|---|---:|---:|---|
| SPI235 + mailbox206×3 | 766 | 430 | 512×8 simple dual-port M9K 하나로 추론 |
| query235 | 356 | 151 | 없음 |

두 standalone 결과의 합은1,122LE이다. 기존 exporter644+SPI479+spare159=1,282LE를 회수한다는 산술과 비교하면 **160LE만 남는 계산**이다. standalone MAP 합과 whole-board FIT 차이를 무시한 가용 공간 보증이 아니며, 아직 없는 delta encoder·raw controller·base address/control이 들어간 결과도 아니다. 따라서 A 전체 구현의 자원 gate는 미통과로 유지한다. 기존54/56M9K 용량 모델의 SPI1M9K 재사용 가능성만 구체화했으며 base6/scratch1의 포트 및 배치는 미검증이다.

합성 경고도 보존했다. `async_reg`는 이 Quartus에서 인식되지 않는다(재사용 mailbox206 포함). 이것으로 CDC를 승인하지 않으며 board 결합 시 Intel synchronizer 지정/실제 first-stage fanout/held-data bounds/reset recovery를 확인해야 한다. dual-clock RAM read-during-write는 정의되지 않는다. 비봉인 은행의 미리 읽힌 값은 사용하지 않고 유효 D1 동안 해당 은행 쓰기를 금지하는 소유권으로 다룬다. CRC8의32→8 truncation은 다항식07 연산의8bit 결과, palette32/64의32→7 truncation은 표현 가능한 상수이다. query index 상위2bit/fault bit3의 stuck-low는 명시한 범위에 따른다. 경고를 제거했다고 주장하지 않는다.

## 다음 순서

1. 완전한 증분 encoder를 곧바로 추가하거나 작은 FIT 최적화를 반복하지 않는다. 먼저 기존 SPI 명령 수신/CRC/ACK 제어를 공유할 수 있는 실제 결합 경계와 query byte 출력의 제어·RAM 포트 비용을 검토한다. 최소 encoder/base/raw 제어까지 포함한 자원 예산을 만든다.160LE 산술만으로 진행 승인하지 않는다.
2. 같은 스크롤 데이터에서 A(증분 SPI)의 전체 비용과 B(준비된 병렬 metadata aperture)의 재사용 가능한 자원·전송 비용을 비교한다. B에서도 수신·변환·source lease 비용과 ARM 공간을 포함한다. 단순 SPI 속도 상승/확인 생략/mapper 기능 제거로 맞추지 않는다. 통합 예산이 성립하지 않으면 B로 전환하고 이번 endpoint 증거는 보존한다.
3. 선택 경로에서 source BEGIN/END/epoch/base serial·raw·source error를 실제 C234 및 전체 RUN/IRQ에 연결한다.233의1616B 여유는 입력 parser를 포함한 승인값이 아니므로 다시 판정한다. 그 뒤 whole-board CDC/IO/STA와 실제 SNES 최종 displayACK를 확인해 paired 시험판을 만든다.
4.232의5개 map/OBJ VBlank 초과는 별도로 남아 있다. shared SPI·source 준비·ARM·SNES의 전체16.67ms와 첫 레벨 RIGHT+B/A 스크롤을 기준으로 실기 확인한다. 같은227/044 재시험이나228 자동 재개는 하지 않는다.

GBC164, cartridge save SRAM, 생산227 및 기존 봉인 자료를 보존한다. 새 칩이나 mapper 여유를 확보했다는 주장도 하지 않는다.
