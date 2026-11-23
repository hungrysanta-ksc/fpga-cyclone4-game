# MMC966 · 모험도 4 무입력 60초 실기판

1. 전원을 끄고 ZIP 안의 `MMC966-ADVENTURE-60SEC-SD-ROOT` 폴더 **안의 내용물**을 SD 카드 루트에 복사한다.
2. MMC955에 사용한 모험도 4 일본판 ROM을 `sd2snes/nes/mmc966.nes`로 복사한다. 비교 원본의 SHA-256은 `9d7402da135fd1290346ccc9332836daee3a9a3cda3789999c3f86efdb5b19c2`다.
3. SD 메뉴에서 **NES MMC3 966.nh1**을 선택하고 버튼 입력 없이 60초간 둔다. 오프닝에서 스테이지 데모로 전환되는지, 종료 후 메뉴로 돌아오는지 확인한다.
4. 재실행 전에 SD의 `sd2snes` 폴더에서 `nes-progress-mmc966.txt`, `nes-budget-mmc966.txt`, `nes-game-last-mmc966.txt`, `nes-frame-mmc966.bin`을 보관한다.

| 화면 공개 구간 | MMC955 실기 표시 수 | MMC955 표시 FPS |
|---|---:|---:|
| 1–30초 오프닝 | 675장 | 23.28 |
| 30–60초 스테이지 데모 | 717장 | 23.90 |

첫 1초를 제외하고 30초 경계에 공개한 화면은 데모로 센다. MMC955와 같은 계측 형식을 사용한다. BIN은 55–60초에서 map·OBJ·BG 작업량이 비슷한 화면의 ROM 공급과 최종 ACK를 대조하는 데 쓴다. ZIP에는 설치용 파일만 들어 있다.
