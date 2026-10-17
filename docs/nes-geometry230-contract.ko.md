# NES230: 실제 스크롤 자료를 생산 수집기·ARM에 연결한 공동 전송 예산

작업 의미: 회고228에서 요구한 실제 스크롤 입력·출력 비교를 수행했다. 같은 SMB3(J) 자료를 **변경하지 않은227 생산 RTL 수집기/전송기와 C 수신기/계획기/출력기**에 연결하여, 다음 성능 변경이 줄여야 할 바이트와 남아 있는 검증 범위를 구체화했다. 새 펌웨어나60fps 달성 결과는 아니다. PR126에229 수집 결과와 함께 기록한다.

## 확인한 결과

229와 동일한 ROM·입력으로 nametable/attribute 읽기와 행 시작 상태를 추가 관측했다. 입력/master-clock 기록과 공통71개 RGB 화면이 이전 관측과 일치했다.905..975의71프레임을 처리했고, 두 출력 은행을 채우는905/906을 제외한907..975의69프레임으로 warm 비용을 계산했다. 첫 프레임은 정지 카메라 기준,906부터 연속 스크롤이다. 전체 시험 구간은 약1.18초이며 장기 플레이 자료가 아니다.

- 생산 RTL7개 파일을 그대로 사용한 collector/exporter 재생71프레임 통과.
- 실제227 C 수신→상주 슬롯 계획→출력71프레임 통과. 독립186 변환기와 일반 배경 픽셀/스프라이트 바이트 등4,066,624회 대조했다. 전체 검사를 모두 픽셀 수라고 표현하지 않는다.
- 실제 C 패킷을 풀어 비활성 은행에 적용한 결과가 원하는 map/CGRAM/OAM/raster bundle과71프레임 모두 바이트 단위로 일치했다.
- raw 보존 행193·194의36,352픽셀은 관측 RGB와 일치했다.
- 패킷 내용, raw 행 geometry, raw RGB를 각각 훼손한3개 자료를 거절했다. 외부 해시만으로 거절하지 않도록 앞의 두 사례는 훼손 후 artifact digest도 갱신했다. 이는 분석 자료 오염 검사이며 생산 통신 장애 복구 시험이 아니다.

## 실제 코드가 발생시킨 비용

단위는 프레임당 바이트다. SPI2.625MHz의60Hz 순수 전송 상한은5,468.75B다. 아래 입력은 D1 레코드 payload, 출력은 실제 C 패킷 길이에 command/CRC3B를 더한 E1 비용이다. 상태/ACK polling, SPI 간격, CPU 시간 등은 포함하지 않았다.

| 항목 | warm 평균 | 최대 |
|---|---:|---:|
| 기존 입력 geometry payload | 6,335.01 | 6,492 |
| 기존 출력 메타데이터 SPI | 5,094.70 | 6,103 |
| 별도 병렬 경로의 타일 바이트 | 141.22 | 608 |
| 타일 생성 계획 수 | 6.03 | 24 |
| map VRAM 업로드 바이트 | 1,635.25 | 2,560 |

출력 메타데이터 평균5,094.70B의 구성은 map1,812.58B, CGRAM344B, OAM119.12B, raster bundle2,601B, BEGIN/SEAL218B다. **타일 원본 전송보다 반복되는 map과 예외 행 묶음이 훨씬 크다.**

특히 예외 행2개가 있는 이 자료에서는 bundle 내부 raw CHR2048B를 매번 보내며 framing 포함2,219B가 든다. 같은 비활성 은행의 이전 내용과 비교한 실제 CHR 변경량은 평균5.20B, 최대17B다. 나머지는 scroll40B, padding21B, patch tables321B다. 작은 변경에도 전체 묶음을 보내는 비용을 확인했으므로, 다음 후보는 타일 source 압축이나 polling만 더 손보는 방향으로 돌아가지 않는다.

## 공동 delta 모델과 채택 판단

`analyze_nes_geometry230.py`의 모델은 다음을 **실제 자료에서 바이트 복원한 뒤** 계산한다. 아직 생산 프로토콜 변경이 아니다.

- 입력: 고정 배열5741B의 직전 수신 완료 기준에 offset16/length8 변경 span을 적용한다. 제어16B와248B당 transport3B를 가정한다. raw512B는 매번 별도로 보낸다. 생산 수신기의 required bitmap과 raw 저장공간이 union이므로, bitmap 열거 뒤 raw를 그대로 유지할 수 있다고 가정하지 않는다.
- 출력: 마지막 표시 화면이 아닌 **이번 비활성 은행의 내용**을 기준으로16B 단위 변경을 합친다. E1 header+command/CRC19B를 계산하며, 해당 section의 기존 전송보다 클 때는 기존 경로를 선택한다. BEGIN/SEAL은 유지한다. 전체 section coverage를 요구하는 현재 소비기에 패킷을 단순 생략해서는 안 되며, 새 base/dirty 계약이 필요하다.
- 모든 span 적용 결과가 원래 geometry/metadata와 같아야 한다. 프레임 하나의 소스 기준과 두 출력 은행의 기준을 혼동하지 않는다.

| 모델 항목 | 평균 | 최대 |
|---|---:|---:|
| 입력 delta SPI | 2,160.99B | 3,817B |
| 출력 delta SPI | 1,350.90B | 1,997B |
| 같은 프레임의 입출력 합계 | 3,511.88B | 5,788B |

평균 합계의 wire 시간은10.70ms지만 **프레임938·954·963·970의4개는 이미5,468.75B를 넘는다.** 이는 순간 프레임 예산 초과이며, 평균 처리량만으로 가능한 buffering/overlap을 포함한 지속60fps 불가능 증명은 아니다. 반대로 아직 제외된 제어/계획/CPU/SNES 비용이 있으므로60fps 승인 근거도 아니다. 출력을 그대로 둔 입력 delta만으로는 평균7,255.68B이므로 그 단독 구현은 채택하지 않는다.

### 전체 장부에서 아직 남은 항목

| 공유 자원 | 이번에 확인한 것 | 아직 필요한 것 |
|---|---|---|
| SPI | 같은 스크롤의 입력/출력 payload·framing, 공동 delta 모델 | D0-D3/E0/E8 상태, E8/E9 계획, 간격, deadline·버퍼 누적 |
| source/PSRAM | 실제 ROM 물리 tag/byte를 이용한 계획 및 타일 수 |242..259 허용창에서 실제 읽기 서비스 시간, core 경합 |
| ARM | 생산 C 경로 결과 동일성 | 기존geometry를 덮어쓰는 delta 수명, full RUN/IRQ stack, 계산 시간 |
| SNES | 실제 C 패킷과 두 은행의 복원 바이트 | 실제65816 dirty coverage/ACK/STOP, CPU·VRAM·VBlank 비용 |
| FPGA | 현재7개 RTL 무변경 재생 | source 기준 RAM/포트와 변경 검출 제어, 배치·전체 타이밍 |

현재 여유는159LE·2LAB·9M9K, ARM margin1800B(최소 gate1024B보다776B 여유), SNES ROM body224B다. 입력 기준5741B를 별도8비트1024-depth RAM으로 단순 보유하면 최소6M9K 상당이며 포트·제어·배치가 포함되지 않는다. 출력 전체8570B 복사본을 ARM에 추가하는 안은 성립하지 않는다. 출력 변경을 생성 중 검출하고 두 은행의 dirty 집합을 보존하는 방식은 후보일 뿐, 현재 planner가 기존 buffer를 초기화하는 부분과 실패 수명을 먼저 해결해야 한다. 게임 세이브 SRAM을 사용하지 않는다.

## 다음 구현 순서

1. **반복되는 raw/CGRAM·map 출력과 입력을 묶은 후보 한 개**를 만든다. raw/행 상태 보존을 없애거나 MMC3의 최종 bank snapshot으로 대체하지 않는다. 입력의 행 공통값·coarse 이동과 출력의 비활성 은행 dirty를 함께 표현해, 위4개 최대 부하 프레임을 포함한 비용을 낮춘다. 이 단계에서 기존 ARM 저장공간을 대체/재사용할 수 있는지와 FPGA 제어 자원을 먼저 고정한다.
2. 같은 자료로 대안 B를 함께 비교한다. B는 FPGA 준비 metadata를 기존 병렬 aperture로 직접 보내거나 계산 위치를 옮기는 안이다. **ARM이 같은 바이트를 SPI로 aperture에 다시 채우는 방식은 SPI 우회가 아니다.** SNES 변환 CPU·4KiB 코드·source RAM을 포함해야 하며, DMA 바이트 시간만으로 채택하지 않는다.
3. A가 전체 예산/자원 조건을 넘으면 codec 변형이나 FIT 반복 없이 B로 전환한다. A의 평균3.5KB만 보고 채택하거나, 현재4개 burst만 보고 B가 자동으로 적합하다고 판단하지 않는다. 최소한 sustained 처리량, 최대 화면 나이, bounded queue를 확인한다.
4. 선택한 구현에서 현재 실제 C/RTL 자료를 재사용하고 실제65816과 STOP/epoch/base 오류 경계를 연결한다. 그 뒤 한 번의 whole-board gate와 paired build를 거쳐 실기 첫 레벨 오른쪽+B/A 반복으로 간다.228의 실패한8B-map 후보는 자동 재개하지 않는다.

## 관측 어댑터의 한계

Mesen 관측을 그대로 FPGA 코어의 cycle trace라고 부르지 않는다. [고정 버전 NesPpu.cpp](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp)의 attribute fetch와 sprite 읽기 구조를 확인하여 어댑터를 만들었다. Mesen은 OBJ의 두 plane 읽기를 같은 dot에 보고하므로 high plane을 다음 native load phase에 배치했다. 이 변경은 mapper 타이밍 등가성 증명이 아니다.

렌더링을 끄는193/194에서 행 시작 관측이나 완전한 fetch pair가 없으면, 실제 mask 변경 증거가 있는 경우에만 명시적으로 전체 raw 행 fallback을 선택한다. 이 부분의 무효 geometry 값은 관측한 PPU 상태가 아니다. raw는 관측 RGB를 [고정 기본 팔레트](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesDefaultVideoFilter.cpp)의 동색 최저 index로 역변환한다. 원래 index가 중복 색일 때 원래6비트 값을 복원했다고 주장하지 않는다. 가시 구간 palette write, grayscale/emphasis, 설명되지 않는 누락은 거절한다.

일반 배경/OBJ는186 reference와 비교했으며 **전체 Mesen 화면과 최종 SNES 합성 화면을 비교한 것은 아니다.** PREPARED/display ACK와 ROM source read는 host fixture다. 실제 FPGA 게임 코어 전체, PSRAM 경합,65816 실행, 실기 FPS는 이번 검증 밖이다. 이후 코드에서 이 자료를 쓸 때 이 한계를 유지한다.

## 재현·보존

선택 결과는`probes/nes-geometry230`의capture02/stim05/rtl02/host06/analysis03/negative01이다. capture01의 host timeout, stim01/02/04의 관측 가정 오류, host01의 sandbox DLL623와 host02의 include 누락, 이전 성공 결과도 보존한다. capture timeout을300초로 늘린 것은 호스트 관측 대기이며 실기 timeout이나 클럭을 변경하지 않았다. Questa FLOAT wrapper는 기존 승인된 방식 그대로 사용했다. ROM·원자료·라이선스는 Git에 포함하지 않는다.

```powershell
python -B tools/run_nes_geometry230.py --rom <user-ROM> --mesen <pinned-Mesen> --out C:/temp/capture --frames 1020 --capture-first 905 --capture-last 975
python -B tools/prepare_nes_geometry230.py --capture C:/temp/capture --prior <229-capture01> --out C:/temp/stim
# 아래 RTL 호출은 승인된 probe_float.ps1 -RunOnly -AfterSmokeScript <absolute-job> 안에서 실행
python -B tools/test_nes_geometry230.py --stimulus C:/temp/stim --out C:/temp/rtl --questa-bin C:/altera_standard/25.1std/questa_fse/win64
python -B tools/test_nes_geometry230_host.py --rtl C:/temp/rtl --rom <user-ROM> --out C:/temp/host
python -B tools/analyze_nes_geometry230.py --host C:/temp/host --capture C:/temp/capture --out C:/temp/result.json
python -B tools/test_nes_geometry230_analysis.py --host C:/temp/host --capture C:/temp/capture --out C:/temp/negative
```

명령은 신규 출력 디렉터리를 요구한다. 생산 RTL/C pin과 이전229 봉인 파일을 검증하고, 선택 증거 및 중간 실패는 새230 manifest로 보존한다.227 펌웨어/FPGA/GBC164/세이브 공간은 변경하지 않는다. 같은227 또는044 실기 반복은 요청하지 않는다.
