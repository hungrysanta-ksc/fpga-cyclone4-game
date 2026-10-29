# MMC482 — 표시 시작 진단 전달본

**이번 전달본은 MMC480의 검정 화면 원인을 좁히는 비공개 실기 진단용이다.** 481에서 보류했던 관련 타이밍 문제를 해결했다. 실제 게임 표시 시작·FPS가 개선됐다는 판정은 아직 아니다. 같은 ROM을 사용하며 STOP·독립 검사·최종 ACK·base/메뉴 복귀를 유지한다.

## 설치·실행

1. 전원을 끄고 **01-MMC482-BOOTDIAG-SD-ROOT** 내용을 SD 루트에 복사한다. firmware·FPGA·base/menu·실행 항목을 함께 복사한다.
2. 지난번의 **mmc480.nes를 복사해 sd2snes/nes/mmc482.nes**로 이름을 바꾼다. 내용은 그대로다.393232B/CRC32 `5a04eed7`인 동일 원본이며 ZIP에 SMB3 ROM은 넣지 않았다.
3. 메뉴에서 **NES MMC3 482.nh1**을 실행한다. 이번에는 버튼을 누르지 않아도 된다. ROM 적재/검증 시간과 화면 시작 이후 대기 시간을 구분한다.
4. 화면이 검정이어도 자동 메뉴 복귀까지 기다린다. 지난 실패와 같으면 적재 완료 뒤 시작 대기를 약5초에 끝내고, 이어서 base/menu 복구 후 돌아온다. 게임 표시가 시작되면 약60초 실행 뒤 복귀한다. 게임이 나오면 Start·방향키·A/B를 시험해도 된다.
5. 화면 상태와 메뉴 복귀 여부를 알려주고 아래 새3TXT를 전달한다. SD를 PC 개발 환경에 연결하거나 같은480을 다시 실행할 필요는 없다.

- sd2snes/nes-progress-mmc482.txt
- sd2snes/nes-budget-mmc482.txt
- sd2snes/nes-game-last-mmc482.txt

메뉴의 BLOCKED_RESET_HELD 같은 오류로 자동 복귀하지 못하면 전원을 끄고 아래 원복을 사용한다. 이전 로그는482와 별도로 보관한다.

## 원복

전원을 끄고 **02-RESTORE476-SD-ROOT** 내용을 SD 루트에 복사하면 정상 실기 기준476으로 돌아간다.03은 기존164,04는467 원복이며480 ZIP에서 byte 그대로 보존했다. 개인 세이브는 ZIP에 포함하거나 덮어 쓰지 않는다.

## 이번에 바꾼 것과 검증

검증 실패 신호를 오류 종류마다 먼저 적용하던 경로를 바꿔, 종류 계산 뒤 마지막 단계에서 차단 여부를 선택한다. 같은 클록에서 같은 오류코드를 기록하며 WRITE/HOLD 중 STOP 처리·기존 코드 보존도 같다. 별도 파이프라인·대기 연장·검사 생략·SDC/클록/seed 변경은 없다.

| 확인 | 결과 |
|---|---|
| 기존481 loader와 차등 | 상태294912·순차1056·전체19bit count524288·이전 코드131072건 일치, 잘못된 두 구현 검출 |
| 실제 C/FatFS/programmer/run136 | 22사례 통과, 전체384KiB 비교·CRC·START/STOP/base 실패 처리·옛79/7a 혼용 거부; 외부 peer는 모델 |
| 실제 보드 RTL | 부팅 ROM4100read·profile7b·status3·버스 해제·STOP 통과; 이상적 clock/pin/ROM 모델 |
| 실제 C 프로그래머 | 이번 BI3 복원이 원래 RBF와 byte 동일 |
| 전체 Quartus Lite | 15254LE/14049comb/8392FF/256608RAM bits,154LE 잔여 |
| 관련 setup / hold | +0.133ns / +0.132ns; 전체 reset/CDC/IO 승인은 여전히 미완료 |
| ARM | text202313/data10040/BSS18552B, firmware212356B·Flash636B 잔여, RUN31848B 유지 |

[검증 JSON](../analysis/mmc482-verification.json) · [패키지 해시](../analysis/mmc482-package.json) · [원래480 실패와481 보류](nes-mmc481-startup.ko.md). 수신·계획 실행기는 그대로이며 이 수치를 게임 처리 시간이나 FPS 이득으로 계산하지 않는다.

## 다음 분석에서 볼 값

profile은7b, 상태 형식은3이다. 기존 낮은3bit는 reset vector/program read의 사건 표식이다. 높은5bit는 RD·ROMSEL·WR·active·내부 drive의 SPI 순간값을 ARM이 누적한다. **관측되지 않은 bit는 짧은 펄스 부재의 증명이 아니다.** 내부 drive는 물리 데이터 수신의 증명도 아니다.

시작 실패 시 budget의 **boot_first_hex/boot_last_hex**는 STOP 전에 저장한 결과다. game-last의 최종 screen_flags는 STOP 뒤 읽기도 포함하므로 부팅 중 관측과 분리한다. 이 값으로 실물 시작 경계를 먼저 판정하고, 게임 표시가 시작된 뒤 수신·계획·표시 비용과 연속 FPS 분석을 재개한다. 현재 성공 성능 기준은 제한 NROM476 약24fps다.
