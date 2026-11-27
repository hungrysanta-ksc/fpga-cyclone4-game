# NES 1055 배포판과 디버그판

각 ZIP의 `sd2snes` 폴더를 SD 루트에 덮어쓰고 같은 FF3 한글판을 선택한다. 배포판과 디버그판 중 하나씩 설치한다. 기존 SRAM과 퀵세이브를 그대로 사용한다. 이번 확인 동선은 사슨성 탑이다.

1. 배포판에서 기존 SRAM이 있는 FF3를 시작한다. `Starting NES`부터 첫 화면까지 걸린 시간을 확인한다.
2. 퀵메뉴에서 `SRAM WRITE`를 실행하고 게임으로 돌아오는 시간을 확인한다. `EXIT TO MENU`로 파일 목록이 나타나는지 확인한 뒤 같은 ROM을 다시 실행한다.
3. 사슨성 탑에서 저장한 슬롯을 불러오고 같은 계단을 올라갔다 내려온다. 닫힘·열림 중 타일과 전환 뒤의 방을 확인한다.
4. 디버그판은 같은 경로를 실행하고 `nes-progress-debug1055.txt`, `nes-game-last-debug1055.txt`, `nes-frame-debug1055.bin`을 수집할 수 있다.

두 판 모두 8 KiB 배터리 SRAM의 13바이트 명령을 SPI1 DMA로 전송한다. 쓰기 뒤 인덱스와 값 재확인, 파일 CRC, 두 세대 파일 보호는 유지한다. 배포판의 메뉴 복사에서는 전송 완료와 PSRAM 준비를 순서대로 확인하고 64 KiB를 모두 다시 읽어 원본과 대조한 뒤 RESET을 해제한다.

계단 전환은 캡처한 합성 행의 256픽셀이 전부 공통 배경색과 같고 같은 화면에 빈 배경 행이 이미 있을 때 그 행을 재사용한다. 스프라이트나 무늬가 한 픽셀이라도 남으면 행 전체를 보존한다. 최종 ARM 링크와 시뮬레이션 결과는 `analysis/nes-pair1055.json`에 기록했다. 실기 시간과 전환 중 깨짐의 해소 여부는 위 동선에서 확인한다.

### 재현

`prepare_ff3_pair1055.py`로 두 소스를 준비하고 각각 `build_nes_trial577.ps1`로 링크한다. serial 15 슬롯, 기존 한글 ROM과 `tests/nes-functional/ff3_stairs1055.json`을 `trace_ff3_walk1048.py`에 지정한다. `--serial 15 --frames 55 56 57 58 95 96 97 98 134 135 136 137 218 219 220 221`로 생성한 자료의 출력 경로는 `probes/nes-pair1055/tower`다. FLOAT 래퍼로 `check_ff3_ports1055.py`를 실행한 뒤 `check_ff3_pair1055.py <슬롯> <Mesen>`과 `package_ff3_pair1055.py`를 순서대로 실행한다.
