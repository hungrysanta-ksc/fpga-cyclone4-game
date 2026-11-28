# NES 1056 배포판과 디버그판

ZIP 한 개의 `sd2snes` 폴더를 SD 루트에 덮어쓴 뒤 파일 목록에서 기존 이름의 `.nes`를 선택한다. 네 게임용 FPGA 이미지와 이를 선택하는 펌웨어를 함께 설치해야 한다.

| 확인할 한글판 | 추가한 카트리지 동작 | 실기 확인 지점 |
|---|---|---|
| 모아이군 | CNROM의 8 KiB CHR 뱅크 전환과 수직 미러링 | 타이틀에서 첫 퍼즐로 들어가 캐릭터와 바닥 타일 확인 |
| 배틀토드 | 확장 AxROM의 32 KiB PRG 뱅크 16개, 단일 화면 선택, CHR RAM | 스테이지 진입 후 이동하며 배경과 캐릭터 확인 |
| 와이와이 월드 2 | VRC4의 PRG·CHR 뱅크, 미러링, IRQ | 오프닝과 첫 스테이지의 스크롤·화면 분할 확인 |
| 드래곤 퀘스트 IV K1.2 | 1 MiB PRG, 8 KiB CHR RAM과 배터리 RAM, CPU에서 접근하는 1 KiB ExRAM | 모험의 서를 만들고 대사·이동, 게임에서 저장 후 재실행 확인 |

드래곤 퀘스트 IV는 첨부판의 전체 CRC32 `9ac62bb9`와 NES 2.0 구성을 확인한다. MMC5의 확장 배경·IRQ·추가 음원까지 쓰는 다른 카트리지는 별도로 지원해야 한다. 강제 저장·불러오기는 기존 FF3용이다. 모아이군과 와이와이 월드 2는 기존 CHR-ROM 실행 시간을 이어받아 약 60초 뒤 메뉴로 돌아온다. 배틀토드와 드래곤 퀘스트 IV는 CHR-RAM 실행 경로를 사용한다.

배포판은 시작 시 로딩 진행률을 표시한다. 문제를 재현할 때 디버그판에서 생성되는 `nes-progress-debug1056.txt`, `nes-game-last-debug1056.txt`, `nes-frame-debug1056.bin`을 게임별로 구분해 보관하면 된다. VRC4 보드는 공간 제약으로 커비용 SPI 0x78 타일 뱅크 계측값을 제공하지 않는다.

### 검증과 재현

1055 실기에서 FF3의 시작, SRAM 저장, 퀵로드 속도 개선과 메뉴 복귀를 확인했다. 사슨성 탑 계단의 간헐적인 전환 타일 깨짐은 후속 확인 대상으로 남겼다.

1. `probe_nes_carts1056.py`로 사용자 ROM과 Mesen을 지정해 각 1,800프레임의 매퍼 쓰기와 주소 기준값을 수집한다.
2. `prepare_nes_carts1056.py`로 매퍼 3·7·21·5 보드를 생성한다. Questa FLOAT 래퍼에서 `test_cart_rtl1056.ps1`과 `test_cart_boot1056.ps1`을 실행한다. 두 시험은 각각 Mesen의 쓰기를 RTL에 재생하고 실제 T65 코어가 각 ROM의 리셋 벡터부터 PPU에 쓰는지 확인한다.
3. `prepare_cart_arm1056.py`로 release·debug 소스를 생성하고 각각 `build_nes_trial577.ps1`로 링크한다. `check_carts1056.py`로 배포판의 실제 ARM 코드에서 FatFS 선택, PSRAM 페이지 내용과 주소, START·STOP·base 및 메뉴 반환 순서를 검사한다. 이 시험은 물리 장치를 모델로 대체한다.
4. 네 보드에 `fit_ff3_display1037.ps1 -ExportPSRAM`을 적용하고 CHR-RAM 두 보드는 `-ExportSRAM`도 지정한다. 결과를 `final-<mapper>`에 저장한다. `package_nes_carts1056.py`가 FIT·STA, 핀 지연, 프로그래머 바이트 재생, 최종 링크 및 ZIP 해시를 확인한다. 수치는 `analysis/nes-carts1056.json`에 있다.
