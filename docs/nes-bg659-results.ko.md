# NES 659 · 불변 BG의 PSRAM→VRAM 직접 DMA

**657 port를 유지한다.** 954의 BG 10개, 955의 9개는 로딩 때 바꾼 타일과 일치했다. 65816은 그 타일을 16 B씩 직접 DMA할 수 있었다. 하지만 657의 NES 우선 PSRAM 허가를 적용하면 두 시작 위상 모두 첫 타일에서 4 B만 유효했다. 완료를 거부해 957 표시 ACK에 도달하지 않았다. 전체 보드도 배치되지 않았다.

## 실제로 연결한 범위

- 384 KiB SMB3를 기존 순서로 적재한다. FPGA loader가 128 KiB CHR 영역 안에서만 하위 주소 비트를 순열 변환해 같은 행의 두 plane이 붙게 쓴다. 네이티브 NES·CHECK 읽기에 정방향 변환을 적용하고 응답 주소는 원래 공간으로 돌린다. ARM의 추가 변환 패스·전송 바이트·별도 PSRAM 사본은 0이다.
- canonical BG plan을 수락한 실제 tile producer가 원래 tile_store·bulk 경로에 16 B descriptor를 발행한다. tag에서 만든 주소·그 보수·bank·slot·generation이 들어간다. 53화면 268건을 RTL에서 발행하고 기존 plan과 독립 대조했다. 이 실험 프로필은 지원 밖의 BG 행 재배열을 fault 처리한다. OBJ·명시적 빈 타일은 기존 형식을 쓴다. 실험 RTL의 자격 판정에 세대 번호는 쓰지 않는다.
- 실측을 분리하기 위해 보드 동작 모델에서 기능을 954·955에만 켰다. 955 단독 시험은 954까지 원래 데이터를 사용한다. 동일 654 ARM ELF가 E9 plan·큐·credit·공유 SPI·IRQ를 실행한다. 연결 일정은 RTL이 실제 생성한 descriptor를 bulk의 원래 길이로 운반한다. 954의 10건·955의 9건은 해당 수신 패킷에서도 바이트 단위로 대조했다.
- 실제 65816 바이너리가 수신한 WRAM descriptor의 주소 정렬·bank·slot·generation·보수를 검사하고 PSRAM 창을 준비시킨다. $50/$51 bank를 DMA 원본으로 써서 VRAM으로 16 B씩 전송한다. 창은 최대 두 word(4 B)를 앞서 읽는다. 정상 NES 요청이 우선이고, 요청한 주소·남은 바이트·실제 읽기 순서가 맞아야 완료된다. 새 65816 코드는 413 B이고 ARM은 212,508 B(Flash 여유 484 B)다. 기존과 같은 WRAM DMA를 선택해도 새 분기를 실행하므로 동일 클라이언트의 기능 꺼짐 대조군을 별도로 돌렸다.

## 같은 master clock에서의 결과

시작 클록은 7,288,416 / 7,467,100이다. ‘경쟁 있음’은 기존 657과 같은 CPU/PPU/MMC3·70 ns PSRAM 시험의 측정 허가 달력을 재생한 것이다. 실제 SMB3 실기 버스를 계측한 결과와 구분한다. ARM CPI 2·IRQ·SPI 드라이버·두 bulk 슬롯·실제 65816 설정 및 폴링 시간을 포함했다.

| 연결 경로 | 위상 1 | 위상 2 |
|---|---|---|
| 657 | 954·955 각 3 VBlank, 957 ACK 68,589,578 | 각 3 VBlank, ACK 68,589,458 |
| 새 65816, 직접 기능 꺼짐 | 각 4 VBlank, ACK +166.843 ms | 각 4 VBlank, ACK +183.215 ms |
| 새 65816, 직접 DMA, PSRAM 경쟁 제거 | 각 4 VBlank, 19건 304 B 정상, ACK +166.560 ms | 954 BG 160 B 전송 뒤 후속 64 B DMA가 261선에서 시작해 0선에서 종료. 독립 검사 거부 |
| 같은 직접 DMA, PSRAM 경쟁 포함 | 954 첫 타일 준비→첫 읽기 1.255 ms, 4/16 B 후 거부 | 준비→첫 읽기 1.084 ms, 4/16 B 후 거부 |
| 955 단독, PSRAM 경쟁 포함 | 준비→첫 읽기 1.100 ms, 4/16 B 후 거부 | 준비→첫 읽기 1.092 ms, 4/16 B 후 거부 |

**SEAL 마감은 두 기준으로 구분한다.** 953 표시를 기준으로 한 954 SEAL 여유는 657의 1.658 / 1.592 ms에서 3.249 / 3.119 ms로 늘었다. 그러나 새 클라이언트의 공통 분기·DMA 일정으로 이전 표시들이 이미 밀려, 같은 절대 시작 클록의 648 마감보다 47.208 / 63.747 ms 늦었다. 두 위상의 951 공개선은 239 / 241이었다. 경쟁 경로에서는 954 표시 전에 거부했으므로 955 표시 간격이나 957 최종 대기를 0으로 집계하지 않는다.

- 657의 BG 업로드는 954에서 144 B + 16 B, 955에서 144 B 한 번이었다. 직접 후보는 10회 + 9회로 나눠 총 16회의 DMA 시작이 더 필요하다. 분기 비용과 시작 위상 효과를 분리한 임시 소비 실험에서도, 경쟁을 없애고 19건을 모두 전송했을 때 954·955는 각각 4 VBlank였다. 임시 태그표 결과는 실제 링크 결과와 별도로 보관했다.
- 첫 DMA의 16번째 읽기는 첫 읽기에서 120 master clock 뒤였다. 해당 128클록 구간의 측정 grant를 동일한 aperture RTL에 재생했다. 954 위상 1/2에는 새 허가 2/1회, 955에는 1/0회였다. 미리 4 B를 채워 두고 메모리가 한 클록 만에 응답하는 유리한 조건에서도 네 경우 모두 4 B 이후 중단됐다. 더 이른 SEAL만으로는 SNES DMA가 요구하는 연속 바이트를 보장할 수 없다.

## 검증과 전체 비용

한 좌석의 Questa에서 최종 프로젝트의 loader·부트 ROM·실제 PSRAM reader·aperture를 연결했다. 전체 393,216 B의 물리 배치, 주소 경계를 포함한 96회 논리 CHECK, 원본 NES 읽기, 6 KiB SNES ROM 창 전체를 검사했다. 허가가 충분한 시험에서는 일반 NES 읽기와 BG 19×16 B가 모두 맞았다. 허가를 끊으면 미완료가 드러났고 STOP은 버스 구동을 해제했다. 실제 링크된 65816 루틴의 독립 Mesen 시험에서도 올바른 VRAM 16 B를 확인했다. 틀린 generation·slot·주소 보수는 첫 DMA 전에 거부했고 STOP 상태는 완료로 반환되지 않았다.

동일 ARM 바이너리에서 정상 메뉴 준비·reset 해제, base 정상 복구와 program·DONE·busy·token 고장 시 해제 차단을 다시 확인했다. 연결 실험에서 중단된 세션은 거부 시각에 재생을 멈춘다. 그 세션에서 물리 메뉴까지 연속 관측한 결과나 새 실기 FPS는 없다.

| Quartus Lite 25.1 EP4CE15F17C8 | 전체 LE | 필요 LAB | M9K |
|---|---:|---:|---:|
| 657 port | 15,425 | 977 | 56 |
| 로더·네이티브 읽기 주소 배치만 | 15,510 | 980 | 56 |
| 직접 aperture 포함 | 15,622 | 987 | 56 |
| 실제 BG descriptor producer 포함 | 15,688 | 991 | 56 |
| **링크한 6 KiB 65816 ROM·해당 주소 디코드·fault 연결까지 포함** | **15,711** | **993** | **56** |
| 소자 한도 | 15,408 | 963 | 56 |

최종 보드는 657보다 286 LE·16 LAB 증가해 **303 LE·30 LAB 부족**이다. ROM 이미지에 남은 공간은 12 B이며 전체 논리 RAM은 305,264→313,456비트다. 합성에서 병합된 기존 CDC 레지스터는 MAP 보고서로 확인한 동일 레지스터에만 명시적 제약을 연결했다. 최종 실패 원인은 LAB 배치 부족이다. 배치 후 STA·SOF와 실기 ZIP은 생성하지 않았다.

## 다음 실험

657의 기존 staging과 묶음 DMA를 기준으로, 사전 변환한 두 plane을 **허가 한 번에 16비트로 읽어 기존 staging에 넣는 방식**을 먼저 비교한다. BG 원본 읽기 160/144회를 80/72회로 줄일 수 있는지가 시험 대상이다. 앞선 결과로부터 확보된 시간으로 계산하지 않는다. 마지막 바이트를 확보한 뒤 기존 144 B 묶음을 발행하면 SNES DMA 도중 PSRAM 허가를 기다릴 필요가 없다. 별도 direct 주소 창과 범용 65816 분기는 이 비교에서 제외한다. source와 reader를 실제 교체한 전체 FIT, 두 시작 위상의 954·955·957·VBlank·STOP을 다시 판정한다.

## 재현 경계

1. 657 port의 보드와 635 client04·637 client01을 고정한다. `nes_bg659_client.py`로 65816 ROM을 링크하고 `prepare_nes_bg659.py BASE BOARD --jobs --client CLIENT`로 최종 보드를 만든다. `quartus_map board` 후 `bind_nes_bg659_sdc.py BOARD`와 `quartus_sh --flow compile board`를 실행한다.
2. 같은 단일 FLOAT에서 `check_nes_bg659_jobs.py`로 plan→descriptor를, `check_nes_bg659.py`로 loader·PSRAM 핀·부트 ROM·창을 시험한다. `check_nes_bg659_cpu.py`는 링크한 65816 루틴의 VRAM·손상 주입 시험이다.
3. 657과 같은 654 ELF·ROM 달력·samples·driver 인자로 `test_nes_bg659_dma.py`에 `--published JOBS/jobs.json --client CLIENT`와 두 시작 클록을 준다. `--mode calendar` / `open`, `--target 0`(954·955) / `955` / `-1`(기능 꺼짐)으로 비교한다. 657 port의 수신 준비 추적은 `--sender653`로 연결한다. 오류 시험은 `reject659.txt` 또는 독립 검사 로그에서 끝난다.
4. `check_nes_bg659_bound.py`로 네 실패 버스트를 실제 RTL에 재생하고 `analyze_nes_bg659.py`로 배치·메뉴·파형·수신 descriptor·ACK를 대조한다.

[검증 수치와 해시](../analysis/bg659-verification.json) · [657 대조군](nes-record657-results.ko.md) · [658 타일 적격 조건](nes-reference658-results.ko.md)
