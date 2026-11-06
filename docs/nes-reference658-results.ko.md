# NES 658 · sd2snes+ v2.19에서 참고할 표시 경로

사용자가 제공한 배포본의 NES 렌더러 32 KiB, FPGA 4종, STM32 firmware를 공식 v2.19 릴리스 ZIP의 여섯 파일과 바이트 단위로 대조해 모두 일치했다. ZIP과 소스 태그의 식별자는 [검증 기록](../analysis/reference658-verification.json)에 있다. 공개 NES 프로젝트와 657 보드는 같은 EP4CE15F17C8을 지정한다. 이 조사에서는 공개 소스를 읽고 로컬 배포본을 대조했으며 sd2snes+를 보드에서 재측정하거나 비트스트림을 재합성하지 않았다. [제공된 소스 태그](https://github.com/ludufre/sd2snes/tree/v1.11.2-br-v2.19) · [공식 릴리스](https://github.com/ludufre/sd2snes/releases/tag/v1.11.2-br-v2.19) · [디바이스 설정](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/verilog/sd2snes_nes/main.qsf#L45)

## 화면 하나가 이동하는 경로

- FPGA는 NES PPU의 쓰기와 mapper 상태를 관찰한다. nametable 변경을 연속 범위로 묶고 팔레트·OAM·CHR 상태 등과 함께 두 8 KiB mailbox에 명령 스트림을 만든다. SNES가 자기 버스의 창에서 읽으므로 657처럼 ARM이 map을 SPI로 받고 표시용 패킷으로 다시 발행하는 왕복을 이 경계에서 피한다. [FPGA 명령·버퍼](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/verilog/sd2snes_nes/nes_bridge.v#L498-L525) · [mailbox 선언](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/verilog/sd2snes_nes/nes_bridge.v#L727-L728) · [연속 범위 발행](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/verilog/sd2snes_nes/nes_bridge.v#L2349-L2379)
- 65816은 활성 표시 중 채널 1 DMA로 mailbox 창에서 WRAM으로 최대 512 B씩 옮기고 명령을 해석한다. map 변환량은 현재 주사선에 맞춰 조정한다. VBlank에서는 별도 채널 0으로 준비된 VRAM·OAM·CGRAM을 반영한다. 우리 경로도 이미 VBlank DMA를 쓴다. 참고할 차이는 그 전에 **FPGA→SNES로 직접 공급하는 데이터와 준비량**이다. [mailbox DMA](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/snes/nes/nes_transport_device.a65#L271-L331) · [주사선 예산](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/snes/nes/nes_render.a65#L3775-L3804) · [VBlank 적용](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/snes/nes/nes_render.a65#L11165)
- CHR-ROM 게임은 ARM loader가 시작 시 NES 타일을 BG용 2bpp와 OBJ용 4bpp로 미리 변환해 PSRAM에 둔다. 이후 65816은 필요한 CHR 창의 일부를 그 주소에서 VRAM으로 DMA한다. CHR-RAM 게임에는 별도의 변경 추적이 있다. SMB3의 128 KiB CHR-ROM 기준으로 BG 사본은 128 KiB, OBJ까지 두면 추가 384 KiB다. [loader 분기](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/src/nes.c#L1461-L1487) · [타일 변환](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/src/nes_chr.c) · [BG 직접 DMA](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/snes/nes/nes_render.a65#L7685) · [OBJ 직접 DMA](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/snes/nes/nes_render.a65#L7758)

공개 구현의 ACK는 WRAM 소비·해석 뒤에 나갈 수 있고 VRAM 표시보다 앞선다. 같은 seq에서 두 번째 해석 실패가 나면 진행을 위해 ACK하는 분기도 있다. 657에서는 입력 저장 공간 반환과 독립 검사·실제 표시 후 최종 ACK를 분리한다. 체감 속도와 같은 기준의 표시 FPS, 사용자가 본 깨짐의 원인은 이 소스 비교만으로 확정할 수 없다. v2.19에는 전용 MMC5 파일도 있으며 loader 허용 목록은 미국판 Castlevania III 한 종이다. [ACK 동작](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/snes/nes/nes_transport_device.a65#L146-L198) · [MMC5 허용 목록](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/src/nes.c#L580-L600)

## MMC643·657과 같은 SMB3 데이터로 대조

MMC480에서 식별한 동일 ROM과 905–957의 계획을 사용했다. 각 계획의 tag·plane·row·mask·대체 tag로 현재 타일의 바이트를 복원하고, 두 위상의 657 실행이 요청한 실제 CHR 주소·종류의 다중집합과 세대별로 대조했다. 원본 한 타일을 그대로 쓸 수 있는 조건은 모든 plane이 기본 tag와 원래 행을 읽고 OBJ에는 부분 마스크가 없는 경우다. 빈 타일 표식은 제외했다.

| 53화면 | 작업 수 | 사전 변환 타일과 구조적으로 일치 | 기존 재구성 필요 |
|---|---:|---:|---:|
| BG | 268 | **268** | 0 |
| OBJ | 123 | **53** | **70** |

직접 복사 가능한 출력은 총 5,984 B다. 나머지 OBJ 70개를 모두 직접 복사하면 실제 게임 데이터에서 54개의 출력 바이트열이 달라진다. 다른 16개도 ROM 값이 우연히 맞았을 뿐 조건상 기존 경로 대상이다. 이것은 우리 경로에서 생길 오류를 보여주는 실험이며 sd2snes+ 영상의 결함을 재현한 결과와 구분한다.

954는 BG 10개, 955는 9개 모두 해당한다. 현재 두 위상에서 각각 ROM 공급 160회·144회를 썼다. 1 KiB 단위로 무조건 가져오면 빈 캐시 기준 954에서 2개 창(2,048 B), 955에서 1개(1,024 B)가 필요하다. 따라서 첫 시험은 **같은 16 B BG 타일만** 사전 변환 주소에서 직접 DMA하는 경우다. PSRAM 읽기와 SNES DMA는 여전히 버스를 사용한다. 이 조사에서는 절약 시간·실기 FPS·배치 면적을 산출하지 않았다.

## 다음 판정 순서

1. 657 port를 대조군으로 유지한다. SMB3의 불변 CHR-ROM BG에 한해 loader 변환·주소 범위, SNES 직접 읽기와 NES ROM reader의 배타적 소유권을 연결한다. 기존 slot 배치·할당 이력·ARM plan은 그대로 둔다. 16 B 단위 경로와 인접 타일만 합친 경우를 각각 같은 결과 바이트로 검사한다. OBJ 마스크·대체 행, CHR-RAM, 실패한 주소 검사는 기존 경로로 보낸다.
2. 두 위상에서 실제 PSRAM 경쟁, VRAM DMA 설정·VBlank 사용량, 다음 캡처와 957 마지막 표시 ACK까지 비교한다. 954·955 각 3 VBlank, 951 공개선, 957 최종 대기 0회, 독립 검사·STOP·메뉴 복귀가 통과해야 한다. 로딩 시간·PSRAM·ARM Flash·전체 보드 FIT도 함께 계산한다. 657의 부족분 17 LE·14 LAB는 남아 있다.
3. FPGA→SNES 변경 스트림은 개별 시험으로 둔다. 공개 구현의 mailbox만 16 KiB여서 현재 M9K 56/56 보드에 추가할 수 없다. 기존 record·SPI·staging을 **대체할** 메모리와 회로, mapper split·누락·cold 재전송 시 일치성부터 계산한다. 두 아이디어의 이득을 합산하지 않는다.

[재현 도구](../tools/check_nes_reference658.py) · [검증 수치](../analysis/reference658-verification.json) · [657 보드 기준](nes-record657-results.ko.md)
