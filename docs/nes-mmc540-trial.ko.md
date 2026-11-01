# MMC540 제한 실기 시험

MMC533에서 사용한 SMB3(J) ROM을 그대로 복사해 `mmc540.nes`로 이름을 바꾼다. CRC32는 `5a04eed7`이다.

1. SD 카드의 현재 설치를 백업하고 ZIP의 `01-MMC540-SD-ROOT` 안의 파일을 SD 루트에 덮어쓴다.
2. 게임은 `sd2snes/nes/mmc540.nes`에 둔다.
3. 전원을 다시 켜고 `NES MMC3 540.nh1`을 실행한다.
4. MMC533과 비슷한 첫 레벨 동선으로 약 60초 플레이하고 메뉴 복귀를 확인한다. 전반 1–40초와 후반 40–60초를 나눠 비교한다.
5. 실행 후 아래 세 로그를 전달한다. 화면 정지·깨짐·입력 이상이 생기면 발생한 구간도 함께 알려준다.

- `sd2snes/nes-progress-mmc540.txt`
- `sd2snes/nes-budget-mmc540.txt`
- `sd2snes/nes-game-last-mmc540.txt`

MMC540은 ARM에서 동일 map 행의 중복 비교를 생략하고, 65816에서 SEAL DMA 예산과 표시 descriptor를 먼저 준비한다. compact raw DMA 전 STOP 서비스의 중복 호출도 줄였다. 최종 ACK의 128µs 폴링, 첫 BG 즉시 발행, 독립 검사와 246행 최종 빔 검사를 유지한다.

시험 기준은 사용자가 승인한 MMC529·MMC533 동등 조건의 제한 실기다. 전체 보드의 관련 setup·hold 통과 및 전체 STA 무회귀를 요구하며 기존 전체 setup −7.081ns·recovery −8.480ns와 미제약 IO가 남아 있다. 이 전달본의 물리 FPS와 메뉴 복귀는 이번 실기 결과로 판정한다.

ZIP에는 새 firmware·FPGA와 기존 검증된 menu/base가 들어 있다. 게임 ROM은 사용자가 준비한다. RESTORE는 기존 백업을 사용한다.
