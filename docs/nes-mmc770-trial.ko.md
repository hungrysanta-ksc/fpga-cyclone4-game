# MMC770·771 첫 레벨 계측

1. 전원을 끄고 `01-MMC770-A-60SEC-SD-ROOT`의 **내용**을 SD 루트에 복사한다. 기존 시험에 쓴 같은 SMB3 ROM을 `sd2snes/nes/mmc770.nes`에 둔다.
2. 메뉴에서 `NES MMC3 770.nh1`을 선택해 MMC763 때처럼 첫 레벨을 플레이한다. 25초나 30초에 버튼을 누르거나 멈출 필요가 없다. 60초가 지나 메뉴로 복귀하면 SD의 `sd2snes`에서 `nes-frame-mmc770.bin`, `nes-budget-mmc770.txt`, `nes-progress-mmc770.txt`, `nes-game-last-mmc770.txt`를 복사한다.
3. 전원을 끄고 `02-MMC771-B-60SEC-SD-ROOT`로 교체한다. ROM 이름과 메뉴 항목, 로그 이름의 숫자를 **771**로 바꿔 같은 동선을 한 번 더 플레이한다. 같은 번호로 재실행하면 로그를 덮어쓴다.
4. 장시간 플레이는 `03-MMC772-B-LONG-SD-ROOT`와 `mmc772.nes`를 쓴다. L+R+Start+Select로 메뉴에 복귀하면 772 로그가 저장된다. 25–30초 비교에는 앞의 두 60초판이면 된다.

## 기록을 읽는 방법

`python tools/read_nes_frame769.py nes-frame-mmc770.bin nes-budget-mmc770.txt`로 화면별 CSV를 읽는다. 각 시도의 BIN과 TXT를 함께 사용한다. 25.00초 이상 30.00초 미만에 처리를 시작한 화면을 수집한다. 5–40초와 40–55초 프레임 수는 예전처럼 표시 완료 시각 기준이다.

* 화면당 36B에 시작 tick(10ms), generation, map 변경 그룹 수, OBJ·BG 범위, 65816의 SEAL 처리 진입·첫 SEAL 이후 PPU DMA 시작·최종 ACK 직전의 VBlank 번호를 담는다. VBlank 번호는 256마다 순환한다. SEAL 표식은 opcode 3을 인식한 시각이며 그 뒤에 독립 검사와 DMA가 진행된다. 같은 실행의 인접 유효 행에서만 간격을 구한다. 496B 선행 DMA는 재생의 별도 바이트 추적으로 검증한다.
* E0는 발행 여유 확인, 4슬롯 credit, 미반환 패킷, 최종 ACK, 이미 반환된 큐의 재확인으로 나눈다. retired 값과 map 진행 비트가 모두 같으면 quiet로 센다. E8은 flush·finish·retire·rearm으로 나누며, 새 descriptor·종료·반환 응답의 준비 여부를 센다. 화면 전체의 사유별 횟수와 별도로 실제 출력 함수 안의 E0·E8과 그중 quiet·ready를 기록한다.
* `valid=0`인 행은 VBlank 비교에서 제외한다. `saturated=1`인 행의 조회 횟수는 하한이다. 227행을 넘기면 budget의 `dropped`에 초과 수를 기록한다. 원본 5초 집계와 개별 행을 비교할 때 이 세 값을 확인한다.
* 계측 비용에는 VBlank마다 65816 NMI, 이벤트의 카트리지 쓰기, 선택 구간에서 화면마다 8B SPI 1회가 든다. SD에는 base 복구 후 쓴다. 계측 보드에서는 종료 뒤 버튼 16개 이력과 구형 stage 6 프레임 카운터의 자원을 사용한다. 게임 입력, STOP 상태와 오류 코드, 최종 ACK 검사는 계속 작동한다.
