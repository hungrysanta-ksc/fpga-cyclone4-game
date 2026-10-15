# NES181 — 실제 렌더링 대조와 32비트 OAM RAM

SELECT `oamports181/map02 + primitive01 + render02 + route01 + check01`. 기존 OAMREAD 후보의 69개 보드 입력 중 PPU만 변경했다. 전체 FIT는 통과했으나 nominal setup −0.240ns로 **미채택**, ASM/FW/ZIP은 없다.

## 작업 의미

OAMREAD의 반 주기 읽기를 실제 CPU/PPU 렌더링 전환에서 확인하고, RAM을 8비트 조각에서 byte-enable이 있는 32비트 워드로 묶었다. OAM은 M9K16→4개, 보드 전체는54→42개로 줄었다. 남은14개는 미래 매퍼/상태 기능과 화면 전송 개선에 활용할 자원이며, 미래 기능을 이미 구현했거나14개면 충분하다는 뜻은 아니다. CPU/PPU 속도·전송 압축·세이브 SRAM은 그대로다.

## 포트와 충돌 계약

각 writer·read port에 32비트×32행 RAM 두 개를 둔다. `altsyncram`의 Cyclone IV E/M9K/simple dual port, byte_size8/byteena4, write clock0=clk, read address clock1=~clk, unregistered read output을 명시했다. 양의 edge 쓰기와 음의 edge 주소 캡처를 사용하며 기존 소비는 다음 양의 edge다. 주소·제어의 반 주기 안정성이 필요하다.

runtime과 savestate 저장은 분리하고 기존 byte owner로 최신 작성자를 고른다. 같은 바이트의 동시 쓰기는 runtime 우선, 서로 다른 주소 쓰기는 모두 보존한다. byte 속성E3 마스크·8바이트 행복사·secondary OAM은 유지한다. RAM `power_up_uninitialized=TRUE`이며 초기 내용의 새 의미를 부여하지 않는다. mixed-port 동시 쓰기/읽기 결과는 DONT_CARE로 지정했으므로 **같은 edge 충돌에 기대지 않는다.** 반대 edge 모델 검사와 STA가 모두 필요하다.

native 관찰/검사용 비동기 backing 배열은 남겨 두었지만 내부 main/copy/extra/repeat/state 소비는 RAM 출력에서만 읽는다. 현재 보드에서 사용하지 않는 backing·SS·extra/state 포트는 제거된다. 미래 상태 기능을 켤 때의 물리 자원/연결 승인과 구분한다.

## 검증

- `render01`: 실제 CPU/PPU/MMC3 + 자체 6502 프로그램이 PPUMASK/OAMADDR/OAMDATA를 직접 조작했다. 메모리 backend는 ideal이며 SMB3가 아니다. 기존 OAMREAD와 원래 코어를 별도 실행해 CPU/PPU/최종OAM trace가 완전히 같았다.
- `primitive01`: 설치된 Altera `altera_mf.v` 모델로 실제 OAMEval 대조. 216362cycles, 행복사2426, CPU쓰기3111, 상태쓰기10473, 충돌2012 통과. 읽기 clock과 owner를 잘못된 양의 edge로 옮긴 음성 fixture는 mismatch를 검출했다. 제조사 모델은 private evidence에만 보존한다.
- `render02`: 새32비트 RAM과 동일한 실제코어·프로그램을 실행했다. baseline은 소스·bench·ROM·trace 해시 확인 후 render01 결과를 재사용했다. CPU/PPU/최종OAM trace 전부 일치. 반주기 입력안정920545회, rendering180740회, 행복사153회, CPU쓰기512회(DMA초기화 포함), PPUMASK쓰기513회다.
- PPU trace230136행/262scanlines/알려진30색. 기준에도 같은8개 `xx` 색 표본이 있다(line40/dot39..46). 차이가 없다는 검증이며 전체 픽셀 정확성·게임 호환성 승인으로 확대하지 않는다. generic OAM 검사는 PAL/extra/SS를 포함하지만 새 actual-core 렌더링은 NTSC·현재보드 구성이다.

## 자원·배선

| 항목 | 이전 OAMREAD | 새 OAMPORTS |
|---|---:|---:|
| OAM 저장 bits |4096|4096|
| OAM M9K |16|4|
| 전체 M9K |54/56|42/56|
| FIT LE |13311|13247|
| FIT LAB |928/963|924/963|
| 전체 FF |6499|6499|
| nominal setup / hold |0.000 / +0.150ns|**−0.240 / +0.132ns**|
| 강화 setup |−0.162ns|−0.692ns|

넓은 packed array 선언만 쓴 `map01`은 MAP14997/6499와 기존16개byte RAM이 그대로여서 FIT하지 않았다. 명시적32비트 primitive의 MAP14980/6499, OAM조합1118/FF318/4096bits, 32×32 simple dual-port4개를 확인한 뒤 전체 FIT 한 번만 실행했다.

배선 후 OAM2220보고경로/3corner: 입력setup+3.864ns, 출력+11.048ns, 전체OAMhold+0.188ns. 반주기22.727ns이며 새 OAM 경로가 현재 최악 경로는 아니다. 기존 scoped CDC486행/reply24행 통과, 조건부 PSRAM70ns여유+6.047ns/SNES69.792ns/270ns/SPI159.893ns/190.476ns/native payload 음수recovery/removal0. 전체 비동기reset·CDC·MTBF·전기적IO 승인은 아니다.

nominal은 동기/관련PLL 분류이며 전체STA의 비동기 NES↔PLL 경로를 숨긴 전체PASS가 아니다. 이번 nominal 최악은 `reader.check_response_address[7] → control.check_enable/verified`, 5.952ns clock 관계, data6.111ns,6 logic levels,배선59%다. `error_response → checked_data~0 → check_enable`의 우선순위/상태 갱신 논리가 연결된다. 관련PLL 최저+1.051ns지만 같은clock CHECK가 실패하므로 채택하지 않는다.

원본 FIT426파일을 보존하고 별도route01 사본에서 STA했다. 기능 모델+실제 배선 STA이며 postfit SDF 시뮬레이션은 아니다. 클럭/핀/SDC/packed1813/stream1815 변경 없음.

## 다음 작업

1. OAM 기능/RAM 절감 검증은 완료된 범위에서 재사용한다. 지금 문제는 ROM CHECK 응답 주소 검증에서 상태 승인까지 이어지는6단 논리다. 이전 counterpulse/commitstage/rawstage 기록과 현재 `nes_rom_spi.sv`의 `command_retire_ok`, `error_response`, fault 우선순위를 함께 읽는다.
2. 응답 검증과 승인 경계를 나누거나 미리 계산할 경우 response/address/tag/data를 같은 응답으로 묶는다. hard fault·잘못된 tag·STOP/reset·동시 command·coherent status·MCU2µs 간격을 유지한다. 오류를 늦춰 RUN이나 verified가 먼저 승인되는 변경은 금지한다. 바뀐 계약만 bounded loader/SPI 공동 검사 후 구조적 효과가 있을 때 FIT한다. 작은식/seed 반복배치는 하지 않는다.
3. nominal 및 관련PLL·OAM반주기·기존CDC/조건부IO가 승인 가능하면 paired ARM여유1384B/실제SNES1815를 재사용해 SMB3 숫자1 타일→A 실기로 간다. 계획상8M9K 여유는 넘었지만97LAB·ARM4KiB 목표는 미달이며 이것만으로 최소MMC3실기를 막지 않는다.
4. raw7 최소22.154ms 모델과 단일capturelease는 실제60fps의 미완료 조건이다. 이번 OAM 변경은 그것들을 유지할 자원 확보이며 프레임률 자체를 높였다는 실측은 없다. AV→longplay/error-resetlogs→heldinput 순서를 유지한다.

관련 근거: [Cyclone IV 공식 handbook의 byte-enable 규격](https://cdrdv2-public.intel.com/653974/cyclone4-handbook.pdf), [Standard 설계 권고의 byte-enabled RAM 예제](https://www.intel.com/programmable/technical-pdfs/683323.pdf). 이번 웹 확인은 검색 본문에서만 가능했고 직접 문서 요청은 접근 실패였다. 실제 적용 근거는 설치25.1의 생성된CycloneIV RAM 구현·제조사 시뮬레이션 모델·MAP/FIT/STA이며 다른 세대 FPGA 규격으로 대신 승인하지 않았다.

배포180/GBC164/세이브 SRAM/완료archive를 보존한다. 원시 결과·선택/실패·검증 한계를 다음 인계에 유지한다.
