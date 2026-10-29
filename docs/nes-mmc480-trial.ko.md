# MMC480 — 실제 SMB3 실기 비교

현재 보드(FXPAK Pro/Mk.III, EP4CE15F17C8)용 **비공개 실험 전달본**이다. NROM 문양 대신 원래 SMB3(J)를 실행한다. 새 조합의 실기 FPS·게임 전체 호환성·60fps는 아직 미확인이다. [검증 범위](nes-mmc480-contract.ko.md).

## 설치와 실행

1. 전원을 끄고 기존 SD·저장 자료를 백업한다. `01-MMC480-SMB3-SD-ROOT` 내용을 SD 루트로 복사한다. firmware·`sd2snes/fpga_mmc480.bi3`·base/menu와 실행 항목을 함께 복사한다.
2. 본인이 보유한 **동일 SMB3(J) 원본**을 `sd2snes/nes/mmc480.nes`로 넣는다. 예전 시험의 `sd2snes/nes/game227.nes`가 남아 있으면 그것을 복사해 이름을 바꿀 수 있다. **SMB3 ROM은 이번 ZIP에 포함하지 않았다.**
3. 대상은 정확히393232B, iNES mapper4·PRG256KiB/CHR128KiB, CRC32 `5a04eed7`이다. 다른 지역판/수정본/추가 header는 거부한다. NROM 문양을 이름만 바꿔 넣지 않는다.
4. 메뉴에서 **NES MMC3 480.nh1**을 실행한다. 적재/readback 완료 뒤 게임 도입부가 나오는지 확인한다. 가능하면 Start로 게임에 진입하고 방향키·A/B로 이동/점프·달리기를 시험한다. 화면 깨짐·속도·음악/효과음 유무를 함께 관찰한다.
5. RUN 시작 후 약60초 자동 STOP·메뉴 복귀를 확인한다. 앞선 ROM 적재/readback 시간은 FPS 관측 구간과 다르다. 새 조합의 메뉴 복귀도 이번 실기에서 확인할 항목이다.

오류나 `BLOCKED_RESET_HELD`가 보이면 강제로 계속 실행하지 말고 전원을 끈 뒤 아래 원복을 사용한다. 화면·경과 시간과 생성된 로그를 보관한다. SD/보드를 작업 PC에 직접 연결할 필요는 없다.

## 돌려줄 결과

- `sd2snes/nes-progress-mmc480.txt`
- `sd2snes/nes-budget-mmc480.txt`
- `sd2snes/nes-game-last-mmc480.txt`

메뉴 복귀 여부와 짧은 게임 동작 영상이 있으면 함께 비교한다. 재실행 시 첫 회차 로그를 먼저 별도 보관한다. **cost_schema=474, input2232, client2271은 의도적으로 유지**했고 파일명·후보 marker는MMC480, 보드 ID는79다. 이전 NROM476의 약24fps와 실제 게임 FPS를 같은 장면의 개선율로 계산하지 않는다.

## 원복

전원을 끄고 **02-RESTORE476-SD-ROOT** 내용을 SD 루트에 복사하면 직전 실기 정상 NROM476 조합으로 돌아간다. **NES NROM 476.nh1**로 확인한다.03은 기존164 복원,04는467 복원이며 이전 전달본 bytes를 그대로 보존했다. 사용자 세이브는 포함하거나 덮어 쓰지 않는다.

이번 기능 시험은 실제 MMC3/source·타일 ROM·ARM C·FPGA queue/staging·65816 DMA·독립 검사/최종ACK/EA·STOP을 한 실행에 연결했다. NES PPU 원본과 SNES 표시57,344픽셀은 모두 일치했다. 그러나 이는 부팅 도입부 한 캡처이며 실제 ARM/IRQ·연속 게임 비용은 이번 로그로 측정해야 한다. 전체 reset/CDC/IO 승인, 전 게임 호환성과 MMC4/5·제품 공개 릴리스 승인은 별개로 남는다.
