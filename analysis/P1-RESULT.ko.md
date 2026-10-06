# NES 영상 P1 첫 구현 결과 — NES-P1-001

2026-10-04. SPDX-License-Identifier: MIT.

**고정 장면의 SNES 출력 성립성을 두 방식으로 확인했다. Mode0 타일+HDMA의
한계를 검출했고, 해당 줄 중간 팔레트 효과는 Mode1의 제한된 4bpp 화소 패치로
실제 SNES PPU에서 재현했다. 전체 P1 gate와 SMB3 구동은 아직 통과하지 않았다.**

## 확인한 결과

| 경계 / 시험 | 결과 | 범위 |
| --- | --- | --- |
| 원시 증거 보존 | 기존 134개 파일, 계획 참고본 16개 해시 모두 일치 | 상용 ROM과 기존 GBC 원본은 열지 않음 |
| P0 파일 목록 | MiSTer 후보 13개 해시/개별 고지 기록 | 자체 P1 MIT 도구만 채택. 고지 불명확한 HDL 4개 반입 보류 |
| A→B 합성 패턴 | 10장 × 61,440화소 차이 0 | A는 합성 기준 renderer, MiSTer PPU 아님 |
| 부정/수명주기 시험 | 15개 오류 거부, 1,000개 순차 frame 전송, stale CHR 주입 차이 검출 | Python 모델; CDC/실시간 메모리 중재 아님 |
| C Mode0 WRAM 호스트 | 진단 OFF/ON 각각 2프레임 × 61,184 표시 화소 차이 0 | 고정 scroll=1, y=117 split, 사전 적재 |
| Mode0 오류 주입 | split 1줄 이동 시 각 프레임 256화소 차이, 최초 (0,116) | 비교기가 잘못된 split을 검출 |
| C Mode1 부분 패치 | 진단 OFF/ON 각각 2프레임 × 61,184 표시 화소 차이 0 | y=119, x=123 팔레트 전환; 17타일+4팔레트 |
| Mode1 오류 주입 | 패치 생략 시 각 프레임 91화소 차이, 최초 (123,119) | 부분 패치가 차이를 실제로 해결함 |
| C44 기준 검증 | 152 source hashes / Quartus inputs / 2,048 boot bytes PASS | 공통 MCU/FPGA/renderer 구현은 변경 없음 |

A/B 패턴: scroll 0/1/255/256과 nametable 경계, 비타일 정렬 split, 8개 CHR 창,
CHR generation 교체, palette/emphasis/greyscale, dot palette, 8×8/8×16 sprite,
앞/뒤 priority, 첫 8개 선택, left mask와 게임 blank. 각 화소 좌표·frame_id를
기록하지만 행 번호를 화면에 그리는 진단 UI는 아직 없다.

진단 ON은 이번 작은 호스트에서 추가 WRAM 표식 쓰기만 뜻한다. FPGA 진단
OFF 자원·타이밍 회귀나 장시간 프레임 pacing을 검증했다는 뜻이 아니다.

## 출력 방식 판정

1. **타일과 줄 단위 이벤트는 유지할 가치가 있다.** WRAM 코드가 실제 DMA/PPU를
   통해 미리 적재한 Mode0 BG1을 표시하고 HDMA로 split을 정확히 재현했다.
2. **Mode0만으로 일반 NES 출력을 승인할 수 없다.** 제한된 소프트웨어 후보에서
   dot palette 91화소, sprite selection 54화소, mask/blank 복합 38화소 차이가 났다.
   뒤의 두 결과는 실제 SNES sprite 시험이 아니라 선택 규칙 비교 모델이다.
3. **제한된 화소 패치의 실제 표현 가능성은 확인했다.** Mode1 BG3 2bpp 배경에
   BG1 4bpp 패치를 배치하고 다음 줄에서 BG3 map을 HDMA로 바꿨다. 해당 효과는
   타일당 최대 11색이라 Mode0의 2bpp 한 타일로는 부족하지만, 4bpp 패치에서는
   색 손실 없이 처리됐다. CGRAM 앞 32개는 배경, 이후 4팔레트는 패치가 사용한다.
4. **최종 채택은 보류한다.** 이번 호스트는 정적 장면을 startup forced blank 중
   적재한다. 게임 중 forced blank를 추가하거나 프레임을 나누어 전송한 결과가 아니다.
   계속 변하는 장면의 캐시 입장/프레임 소유권/VRAM resident mapping/우선순위와
   실제 deadline은 다음 실험이다. CPU/MMC3 전체 통합으로 아직 넘어가지 않는다.

Mode0 startup DMA 12,320B, Mode1 startup DMA 19,520B. 두 호스트의 steady-state
VRAM DMA는 0이다. 따라서 startup 결과로 매 프레임 이 바이트를 전송할 수 있다고
주장할 수 없다. Mode1의 필요한 패치 자체는 CHR 544B + map delta 34B + 팔레트
실사용 92B = 670B다. 팔레트 4개 전체를 갱신하는 계산은 706B지만 배경·OAM·전체
이벤트 준비·기존 resident 상태 보존 비용은 여기에 포함하지 않았다.

## 전송 예산

[video-budget.json](video-budget.json)은 모든 식·가정과 진단 ON/OFF를 기록한다.
NTSC odd-frame short line 4 clocks를 차감한 여유 시간은 224줄 48,984 clocks,
239줄 29,124 clocks다. 아래는 진단 OFF이며 CPU/설정/추정 HDMA 초기화 비용 포함.
실기 측정이 아니라 보수적인 일정 모델이고, 완성된 streaming encoder의 비용이 아니다.

| 부하 | payload | 사용 clocks | 239줄 여유 | 판정 |
| --- | ---: | ---: | ---: | --- |
| 따뜻한 캐시 예시 | 736B | 7,818 | +21,306 | 모델의 80% 목표 이내 |
| 새 BG 64 + OBJ 64 예시 | 3,808B | 32,394 | -3,270 | deadline 실패 |
| 관측 패치 단독 / 6 DMA 설정 | 706B | 7,794 | +21,330 | 단독 모델만 통과 |
| 8KiB CHR 양쪽 역할 갱신 | 25,312B | 204,426 | -175,302 | 실패 |
| 256×240 전체 4bpp | 30,720B | 247,690 | -218,566 | 실패 |

224줄에서 3,808B 예시는 통과하지만 240→224 crop을 해결책으로 채택하지 않았다.
A/B의 cold CHR만도 최대 8,192B이고, 진단용 resolved run은 최대 126,736B다.
이 JSON 이벤트 기록을 그대로 매 프레임 전달하는 설계는 아니다. 대상 SMB3의
실제 최악치나 평균 cache hit는 아직 측정하지 않았다.

## 화면 높이와 남은 결정

원본 비교는 256×240 전체다. 이번 C 실험은 256×239로, **마지막 1줄 / 256화소가
표현되지 않는다.** 224줄이면 16줄 / 4,096화소다. 정적 패턴의 이 손실까지 포함하면
전체 240줄 exact PASS가 아니며 crop 승인을 얻었다는 뜻도 아니다.

| 선택지 | 현재 확인 / 미확인 |
| --- | --- |
| 239줄에서 1줄 제외 | 239줄 재생 확인. 원본 내용 손실 256화소. SMB3 마지막 줄의 장면별 내용 미조사 |
| 224줄에서 16줄 제외 | 예산 여유는 증가하지만 4,096화소 손실. 실제 호스트 비교는 239줄만 수행 |
| 축소 또는 interlace 기반 보존 | 별도 scaler/필드 매핑/움직임/종횡비 검증 필요. 현재 구현·승인 없음 |

제품 정책은 위 대안의 실제 영상과 SMB3 내용 표본을 더 확보한 뒤 사용자와 결정한다.
지금은 어느 손실 정책도 기본값으로 확정하지 않는다.

## 재현과 증거

- [인터페이스/가정](../docs/interfaces.md), [파일별 source lock](source-lock.json).
- 모델: `python -X utf8 tools/video_schedule_model.py --out <새 로컬 디렉터리>`.
- [WRAM 호스트 재현](../snes/video_probe/README.md). Mode1은 builder를
  `build_patch_probe.py`로 바꾸고, 부정 시험은 `--omit-patch`를 사용한다.
- [소스·결과 해시](p1-artifacts.json), [에뮬레이터 요약](host-verification.json).
- 원시 JSON 패킷·화소·PNG·실패/정상 로그·도구 복사본은 ignore된 로컬 폴더에 보존했다.
  결과는 MesenCE 2.2.1 + emucap patch에 한정한다. 다른 emulator/실기와의 교차검증은 없다.
- 최초 C 비교기는 RGB555를 floor로 확장해 실패했다. Mesen 소스의 bit replication과
  대조한 수정 뒤 차이 0이며, 처음 캡처한 화소 바이트는 동일하다. 비교 좌표를 옮기지 않았다.
- Lua Windows 파일 출력은 한글 경로에서 실패했다. 이후 ASCII 임시 출력 사용을 검사한다.
- RTK gain은 tracking DB 접근 실패로 측정 불가. 절감량이나 총 대화 비용을 추정하지 않았다.

## 다음 실험 하나

Mode1 부분 패치를 두 개 이상의 실제 새 프레임으로 갱신한다. compact event와
resident CHR/map/palette를 컴파일하고, VBlank DMA 및 HDMA를 함께 실행해 commit
기한·reset 중단·이전 세대 보존을 검증한다. sprite 선택 패치와 emphasis도 C로 확대한다.
이후에 최소 NROM 기능 컴파일 목록 정리, MMC3 대조, 전체 메모리/보드 fit/STA 순서다.

Questa NROM 기능 시뮬레이션은 기존 v7 컴파일 실패 상태를 유지하며, 이번 C 성공은
그 실패를 해결한 것이 아니다. 실기 이미지·SMB3 실행·공용 MCU 변경·SD 쓰기·배포는 없다.
