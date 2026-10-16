# NES209 실기 결과: 직접 타일 경로 동작, 스크롤 성능 미달

사용자 제공 `nes-progress-209.txt`, `nes-game-last-209.txt`를 원본 그대로 보존했다. 사용자는 프레임 개선을 느꼈지만 스크롤 개선은 미흡하며 사운드·조작은 정상이라고 보고했다. 영상은 없고 메뉴의 실제 표시 여부는 별도로 보고되지 않았다.

## 작업 의미

188–209에서 구현한 직접 타일 DMA 경로가 실제 SMB3에서 표시 완료를 반복하고 사운드·조작을 유지함을 확인했다. 이제 구현 연결 여부보다 실제 스크롤의 전송·대기 비용을 줄이는 작업이 우선이다. **60fps 또는 정상 플레이 품질 달성은 아니다.** 이번에는 결과와 계획만 기록하며 새 펌웨어·FPGA·ZIP·FIT는 만들지 않는다.

## 측정 결과와 해석 범위

| 전체 실행 누적값 | NES186 | NES209 |
|---|---:|---:|
| DISPLAY 구간 | 60.06초 | 60.06초 |
| 확인된 표시 완료 | 182회 | 205회 |
| 수신 단계 | 27.71초 | 12.36초 |
| 구성 단계 | 7.90초 | 20.88초 |
| 나머지 전송·표시 완료 대기 단계 | 23.95초 | 26.48초 |
| SPI 호출 | 263,091회 | 278,289회 |
| SPI clocked bytes | 7,574,556B | 7,340,541B |
| sink packet | 8,147개 | 7,911개 |

표시 완료는 약12.6% 늘었다. 입력과 장면이 다른 두 실행이므로 통제된 개선율이나 스크롤 FPS가 아니다. 209의 전체 구간 평균은 약3.41회/초이며 CRT 주사율이나 순간 게임 FPS와 구분한다.

209 구성 단계는 계획 인코딩·SPI credit·물리 CHR 준비·chunk 전송 대기를 포함한다. 186의 변환·CHR 처리 단계와 내용이 달라 CPU 계산이 2.64배 느려졌다는 해석은 불가하다. 마지막 단계도 palette/map/raw/window/VRAM/최종 ACK를 포함하므로 순수 VBlank 대기가 아니다. SPI 바이트에는 상태·헤더·poll이 포함되고 직접 SNES aperture 전송량은 빠진다. 현재 로그만으로 명령별 poll 비중이나 전체 버스 대역폭 절감률을 산출할 수 없다.

## 종료·복구

- ROM 393,216B 로드·비교 통과, ROM/RUN/STOP/plan/sink/video/window 오류0.
- BEGIN206, END205, COMMIT205, 표시 완료205, ABORT0. 마지막 표시는59.95초, generation310이며 다음 수신 generation311에서 종료했다.
- native_result1은60.06초 제한 종료다. receiver23은 D1 callback 실패 또는 CRC 실패의 공용 값이다. 실제209 소스의 첫 오류 유지 및 전송 전후 deadline 검사와 함께 해석하면 제한 종료에 따른 다음 수신 실패와 부합하며 독립 CRC 오류 증거가 아니다.
- sink sent=retired=7,911, pending0, 마지막 ACK1. plan_sent0/plan_end0은 성공한 retire 뒤 지워지는 값이며 END 미전송을 뜻하지 않는다. 유효하지 않은 sink trace의0값도 실패 ACK로 읽지 않는다.
- screen_frames0은 telemetry_trusted0인 비신뢰 항목이다. SPC A9/unmute1과 사용자 사운드 정상 보고가 있다. 입력 기록90회/마지막16변화는 유지 입력 품질 전체를 증명하지 않는다.
- STOP/base 복원/safe 성공, MENU_PREPARED295,760ms. 이는 메뉴 준비 확인이며 실제 메뉴 화면의 사용자 확인과 구분한다. DISPLAY_NEXT232,570ms는 초기 로드·검증 이후 단계 시각이지 최초 가시 화면 시각이 아니다.
- 마지막 PPU16기록은 reject8/recovery8,224행/29group, fetch01×5/04×1/06×2이며 ROM fault는 없다. 위치·시각·전체 이력이 없어 스크롤별 누락률이나 원인을 확정하지 않는다.

## 다음 작업

1. 실제 첫 레벨 스크롤에서 E8 계획/소스/chunk 대기와 E0/window/SEAL, map/raw payload 비용을 분리한다. 기존 캡처·재생에 해당 장면이 있는지 먼저 확인하고 정지 화면·오프닝으로 대체하지 않는다.
2. 같은 위치의 맵 재사용과 동적 slot 번호 변경이 스크롤에서 얼마나 재전송을 만드는지 확인한다. 현재 로그에는 physical cache hit·장면별 payload가 없어 원인 확정 전이다. 기존 자료에 필요한 값이 없으면 다음 성능 변경과 함께 제한된 명령·단계 카운터를 추가한다. 로그 최대4047/4096B이므로 기존 항목 재배치 등 예산 검토가 필요하다.
3. 실제 최종 표시 ACK, 불변 lease, 코어 우선 접근, ROM/CHR-RAM content 유효성을 유지한다. ACK를 가짜 성공으로 처리하거나 세이브 SRAM을 작업 공간으로 쓰지 않는다.207 여유148LE/1LAB, ARM 여유9260B와 MMC4/5·state/mute/frameskip 예산을 함께 지킨다.
4. 같은209/044 복원·pad-only 시험이나 변경 없는 FIT/독립 codec 반복은 요구하지 않는다. AV약60fps→장기 플레이/오류·실기reset 로그→입력 유지 품질 순서를 유지한다.

이번 실제 사용자 관찰은 새209 기록에 보존한다. 과거 불변 `scroll193-measurement-plan.json`의 collected_runs는 수정하지 않으며, 장면을 맞춘 ingress/egress·시간 측정은 아직 없다.

재현: `tools/analyze_nes_game209.py --inputs <원본 폴더> --out <새 보존 폴더>`.
공개 결과: [game209-hardware01-verification.json](../analysis/game209-hardware01-verification.json).
원본/분석: workspace `probes/nes-game209-hardware01/`. 시험판과 기존 보존 자료는 변경하지 않는다.
