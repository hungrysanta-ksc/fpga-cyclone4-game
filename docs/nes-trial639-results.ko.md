# MMC639 실기 전달 검증

638 결합 후보를 MMC639로 전달했다. 실기 측정 기준은 MMC613이다. 설치 파일은 작업 공간의 `probes/nes-trial639/trial01/MMC639-TRIAL.zip`이며 SHA-256은 `aa336258d3e37cfe151ab806c420b3e701ae1bfe17082671065e0757e7ae2133`이다. [설치·로그 안내](nes-mmc639-trial.ko.md) · [패키지와 시험 기록](../analysis/trial639-package.json)

## 1,152 B 선행 map DMA와 STOP

빔 확인과 실제 DMA 시작 사이에는 65816의 추가 검사·설정 시간이 있다. 그래서 늦은 DMA 시작과 늦은 빔 확인을 각각 시험했다. H는 해당 scanline 내 master clock이다.

| 638의 실제 동작 | 빔 latch | MDMAEN 쓰기 | 첫 VRAM 쓰기 | 1,152번째 VRAM 쓰기 |
|---|---:|---:|---:|---:|
| 252번 선 늦은 DMA 시작 | 251:H1022 | **252:H1164** | **252:H1200** | **259:H1140** |
| 252번 선 늦은 빔 확인 | **252:H1162** | 253:H1304 | 253:H1340 | **260:H1280** |

두 경우 모두 첫 VRAM 쓰기에서 STOP과 후속 head를 제시했다. 비활성 bank의 진행 중인 동기 DMA가 VBlank 안에서 끝났고, STOP이 latch되어 후속 head 수락·ACK와 추가 표시가 일어나지 않았다. 이전 표시 bank와 영상, 옮긴 VRAM 바이트 및 실제 descriptor의 진행을 대조했다. DMA 직전 STOP과 head를 함께 제시한 경우 전송은 0 B였고, head만 제시한 경우에도 DMA보다 패킷을 먼저 처리했다.

637의 자연 polling 위상에서는 원하는 수평 시각을 재현하지 못했다. 639의 지시 시험은 실제 906 map 입력으로 충분한 선두 범위를 수락한 뒤, **호출자에서만** 합성한 위상으로 진입한다. 원래 JSR의 반환 주소와 레지스터·플래그를 보존하는 테스트용 JMP 루프를 WRAM에 잠시 둔다. 선행 DMA 루틴 입구에서 호출자·scratch를 복원하고 배포 본체 5,760 B 전체를 byte 단위로 대조한다. 이후 실제 PPU 빔 latch, MDMAEN, VRAM 첫·마지막 쓰기와 STOP을 관측한다. 전달 ROM에는 정렬용 코드가 없다. 이는 Mesen의 위치 제어 경계 시험이며 실기 결과는 사용자 로그로 확인한다.

## 설치 이미지와 메뉴 복귀

- 전체 링크에서 파일명·marker·보고서 표기를 같은 길이의 MMC639로 바꿨다. ARM 함수 798개의 주소·크기·내용이 638과 같고, 이름 치환 후 firmware payload 전체가 일치한다. 이미지 길이·CRC·보수 CRC도 확인했다. Flash 212,932 B, 여유 60 B다.
- 새 ELF에서 정상 메뉴 prepare/release, marker 4조건과 5–40초·40–55초 집계를 실행했다. base 정상 복구와 program·DONE·busy·token 실패를 각각 실행해 성공 때만 safe return을 허용함을 확인했다. 주변장치 응답은 모델을 사용했다.
- 선택된 637 Lite SOF의 해시와 FIT·STA 보고서를 확인했다. 동일 client를 실제 ROM bus에서 5,120 B 읽어 대조하고, CPF로 변환한 RBF 전체를 BI3 왕복 및 실제 227 programmer·FatFS 경로에서 검증했다. ZIP은 다시 열어 CRC와 파일별 바이트를 검증했다.
- 초기화용 marker와 새 firmware·FPGA, MMC613과 같은 정상 복귀용 base·메뉴 파일을 넣었다. 사용자 ROM·세이브·RESTORE는 제외했다.

## 재현

1. 637의 `client01`, `nes-dma637-head-edges05-input`과 Mesen으로 `tools/check_nes_beam639.py --client <client> --trace <input> --mesen <exe> --out <edge>`를 실행한다.
2. `tools/prepare_nes_trial639.py --base <638 both> --edge <edge>/result.json --out <639 arm>`, `tools/build_nes_trial577.ps1 <639 arm>`으로 링크한다.
3. 새 ELF로 `check_nes_menu533.py --trial 639`, `check_nes_windows518.py --layout trimmed`, `check_nes_transfer512_recovery.py --trial 639`의 다섯 fault를 실행한다. 단일 FLOAT 래퍼로 `check_nes_rom613.py`에 637 보드·client SHA를 지정해 ROM 버스를 점검한다.
4. Quartus Lite `quartus_cpf -c board.sof board.rbf`로 선택 SOF를 변환한다. `nes_cf68_pair_preflight.encode`로 `fpga_mmc639.bi3`를 생성한 뒤 `test_nes_nrom458_programmer.py`로 검증한다. `package_nes_trial639.py`에 위 결과와 해시가 고정된 MMC613 ZIP을 넘겨 패키징한다. 원자료는 `probes/nes-trial639` 및 Temp의 `nes-beam639-edge01`, `nes-trial639-{image01,rom01,programmer01}`에 있다.
