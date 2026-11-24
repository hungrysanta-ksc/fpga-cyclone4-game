# MMC1010 · 모험도 4 화면 공개 지연 계측판

1. 전원을 끄고 ZIP 안의 `MMC1010-ADVENTURE-60SEC-SD-ROOT` 폴더 **안의 내용물**을 SD 루트에 복사한다.
2. MMC966에서 사용한 모험도 4 일본판 ROM을 `sd2snes/nes/mmc1010.nes`로 복사한다. 비교 원본의 SHA-256은 `9d7402da135fd1290346ccc9332836daee3a9a3cda3789999c3f86efdb5b19c2`다.
3. 메뉴에서 **NES MMC3 1010.nh1**을 선택하고 60초 동안 입력 없이 둔다. 오프닝이 스테이지 데모로 전환되고 종료 뒤 메뉴로 돌아오는지 확인한다.
4. 메뉴 복귀 후 SD의 `sd2snes` 폴더에서 아래 네 파일을 보관한다.

- `nes-progress-mmc1010.txt`
- `nes-budget-mmc1010.txt`
- `nes-game-last-mmc1010.txt`
- `nes-frame-mmc1010.bin`

1–30초 오프닝과 30–60초 데모의 표시 FPS를 기존 실기 기록과 대조한다. BIN에는 55–60초의 화면별 작업량과 공개·DMA·최종 ACK 시각이 들어간다. 이 판의 일반 조회는 MMC966보다 16B 길고 상세 타일 조회를 생략하므로 FPS 차이를 해석할 때 계측 비용을 함께 본다.
