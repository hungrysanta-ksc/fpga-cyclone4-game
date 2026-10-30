# MMC489 — compact raw·직접 DMA 실기 비교본

**이번에는 ARM과 FPGA를 함께 갱신한다.** 실제 SMB3 원본은 포함하지 않았다. 기존 MMC485는 대기13.55fps/첫 레벨 플레이 포함8.22fps이며,489의 실기 FPS·메뉴 복귀는 아직 확인 전이다. 실제65816·전송 모델의71개 비교는4234.84→3903.40ms(7.83%)였고, 같은 소스의 Quartus Lite 관련 timing은 통과했다. 이 수치를 실기 개선율/60fps 달성으로 해석하지 않는다.

## 설치·실행

1. 기존 SD 파일·세이브를 보존한다. ZIP의 `01-MMC489-SD-ROOT` **안의 내용물 전체**를 SD 루트에 복사한다. firmware와 `fpga_mmc489.bi3`는 한 쌍이다.
2. 기존에 사용한 원본 `mmc480.nes`, `mmc482.nes` 또는 `mmc485.nes`를 바이트 변경 없이 **`sd2snes/nes/mmc489.nes`**로 복사한다.393232B,CRC32 `5a04eed7`,SHA256 `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`다.
3. 메뉴에서 **NES MMC3 489.nh1**을 선택한다. 약60초 뒤 메뉴로 복귀하는 것은 기존과 같은 동작이다.
4. 이전처럼 대기1회와 첫 레벨 플레이1회를 구분하면 비교에 도움이 된다. 가능하면485 때와 같은 조작·장면을 사용하고, 각 실행 뒤 로그를 따로 보존한다. 장면이 다르면 FPS 차이만으로 원인을 확정할 수 없다.

## 돌려줄 로그

- `sd2snes/nes-progress-mmc489.txt`
- `sd2snes/nes-budget-mmc489.txt`
- `sd2snes/nes-game-last-mmc489.txt`

다음 실행은 같은 로그를 덮어쓴다. 복사본에 `-1차-대기`, `-2차-플레이`처럼 이름을 붙여 보존하면 된다. 화면·입력·메뉴 복귀 여부도 함께 확인한다. 검정 화면·표시 오류·복귀 실패가 생기면 증상과 로그를 보존하고 정상본으로 원복한다.

## 이번 변경과 확인할 점

raw 사용 행의6plane을 DMA 순서대로 보내고, 비활성 VRAM에 직접 복원한다. 사용하지 않은 행/암묵 plane만 bank별로 관리하며 색상 데이터는 매번 새로 쓴다. 행 수 변경·부분 clear·STOP 뒤에는 이전 인증을 사용하지 않고, 표시가 완료된 뒤 최종 ACK를 발행하는 구간에서만 새 bank 인증을 확정한다. 기존 독립 검사·CRC·credit/실제 소비 구분·VBlank·STOP/base/menu 경로를 유지했다.

loader는 실제 쓰기를 허용하는 제어를 유지한 채 inactive payload 선행 저장을 분리했다. whole Lite는15272LE/51M9K, 관련 setup+0.183ns/hold+0.168ns다. ARM Flash124B 잔여·새 global RAM0B, SNES 문맥8B 추가다. 전체 reset/CDC/IO·full ARM stack/IRQ 승인은 아직 남아 있다. 제한된 사용자 시험용이며 공개 릴리스가 아니다.

실기에서는 수신/계획·타일 공급/SEAL·최종 ACK, 완료 수·capture·SPI·종료 상태를 함께 본다. DWT의 op/quiet 비용은 각 단계에 중첩되므로 다시 더하지 않는다. 동일 시작의 모델 시간은 실제 ARM·IRQ·공유 SPI·ROM 경쟁의 공통 물리 시간 증명이 아니다.

## 원복

- `02-RESTORE485-SD-ROOT`: 마지막 정상 실기485.
- `03-RESTORE482-SD-ROOT`: 이전 게임482.
- `04-RESTORE476-SD-ROOT`: 문양476 회귀본.
- `05-RESTORE164-SD-ROOT`, `06-RESTORE467-SD-ROOT`: 기존 복원본.

원하는 폴더 **안의 내용물**을 SD 루트에 덮어쓰고 해당 marker를 선택한다. 각 원복 파일은 기존 전달본과 byte/hash가 동일하다. 기존 ROM 별칭과 세이브를 삭제하거나 SD를 포맷할 필요가 없다.
