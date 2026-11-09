# MMC704·705: 703B 수정 보드 실기 전달

**MMC704는 60초판, MMC705는 장시간판**이다. 두 판 모두 703B의 CPU·CHR 연속 읽기 경계 수정을 포함하며 설치·로그 이름을 갱신했다. 스페이드 진입·타일 깨짐·장시간·STOP·메뉴 복귀 확인용으로 준비했다. [설치·시험 안내](nes-mmc704-705-trial.ko.md) · [패키지 검증](../analysis/trial704-package.json) · [703B 원인·검증 범위](nes-bonus703-results.ko.md)

## 선택 구성과 검증

| 항목 | MMC704 | MMC705 |
|---|---|---|
| ARM 기준 | MMC700, 설치·로그 이름만 변경 | MMC701, 설치·로그 이름만 변경 |
| 동일 함수 | 799개 주소·크기·명령 바이트 일치 | 동일 |
| 전체 Flash / 여유 | 212,984 / 8 B | 212,940 / 52 B |
| 65816 | 기존685 정상판 그대로 | 기존694 장시간판 그대로 |
| FPGA | 703B RTL + 정상판 packed ROM, 별도 전체 FIT | 검증된703B SOF 재사용 |
| LE / LAB / M9K | 15,348 / 963 / 56 | 동일 |
| FF / RAM bits | 8,377 / 305,264 | 동일 |
| setup / hold / recovery / removal | +0.137 / +0.157 / +1.412 / +0.482 ns | 동일 |
| 종료 | 약60초 뒤 자동 STOP·메뉴 복귀 | L+R+Start+Select → STOP·메뉴 복귀 |

정상판의 고정 보드 입력은 703B와 `sink-program.hex`만 다르다. 두 RTL 수정·SDC·pin·seed는 동일하며, 정상판을 전체 Quartus Lite FIT·STA한 결과도 703B와 같다. word CDC·PSRAM reader·ROM 출력 관련 보고서 역시 양수다. LE 여유60개, LAB/M9K 여유0이다. 기존 제약 STA 통과이며 전체 외부 IO sign-off는 미완료다.

각 판에서 SOF→RBF→BI3 역변환 일치, 실제227 프로그래머/FatFS 전송, ARM marker4조건, 정상/실패 주입 base 복구5조건을 검사했다. 실패 주입 때 성공 복귀를 거짓으로 공개하지 않는다. 실제 sink bus에서 각5,120B 표시 ROM·ROM gap·STOP 상태·클록 정지 reset도 통과했다. 60초판은5–40/40–55초 집계, 장시간판은 시간제한 해제·tick wrap·종료 조합·기존 오류 처리 검사를 통과했다.

703B의 CPU/CHR36조건·중간 STOP36조건·두 위상106화면 근거를 그대로 연결했다. 이번 변경은 이름뿐인 ARM과 검증된 표시 ROM이므로 변경 없는 전체 프레임 재생을 반복하지 않았다. 이전 장시간 기능판의 정상판 대비 위상1 밀집+10.728µs/906 내부대기 증가도 그대로다. 이번 패키지가 더 빠르다는 주장이나 새로운 물리 FPS 측정은 없다.

## 산출물과 재현

- ZIP: `WORKSPACE/probes/nes-trial704/trial01/MMC704-60SEC-MMC705-LONG.zip` (1,024,350B).
- SHA256: `29e88da1c31a9f31c504e62d2c377aa47270310b5eee992f6e808d098a932a22`.
- 설치 폴더: `01-MMC704-60SEC-SD-ROOT`, `02-MMC705-LONG-SD-ROOT`. 한 번에 하나만 설치한다.
- ROM·세이브·RESTORE는 제외했다. 정상 STOP/base/menu에 필요한 `fpga_base.bi3`와 `m3nu.bin`은 이전 검증 ZIP과 해시가 같다.
- 준비: `tools/prepare_nes_trial704.py`, 원본 ARM은 `WORKSPACE/probes/nes-trial700/arm700`·`arm701`, 선택 출력은 `nes-trial704/arm704-02`·`arm705`다. `tools/build_nes_mmc479_arm.ps1`의 Base/Patch/Out은 **절대 경로**를 사용한다.
- 정상 보드: `%LOCALAPPDATA%/Temp/nes-trial704-board01`. `quartus_sh --flow compile board`와 기존 `report_nes_word660.tcl`, `report_nes_reader661.tcl`, `report_nes_oe612.tcl`을 실행했다. 장시간 보드는 `nes-bonus703-board02`다.
- 이미지: Temp `nes-trial704-image704`·`image705`, ROM bus: `nes-trial704-romchecks/rom704`·`rom705`. 기존 Starter FLOAT1좌석으로 순차 검사했다.
- 패키지: `tools/package_nes_trial704.py image/pack`, 검사 `WORKSPACE/probes/nes-trial704/checks01`, 실행 인자는 같은 폴더의 `invocation.json`·`package.ps1`·`rom.ps1`에 보존했다.
- [원시 근거 보존](../analysis/trial704-archive.json): 선택 소스·ELF·SOF·FIT/STA·이미지·ZIP·검사 로그를 파일별 SHA256으로 검증한다. 첫 `arm704`는 상대 Out 경로가 W: 작업 폴더 전환 뒤 잘못 해석되어 make 실행 전에 실패했다. 해당 폴더를 남기고 절대 경로의 `arm704-02`로 빌드했으며 제품 코드 수정은 없다.

## 다음 확인

1. MMC704로 첫 레벨5–40/40–55초와 일회성 타일 깨짐·자동 메뉴 복귀를 확인한다.
2. MMC705로 스페이드 안내→회전 게임→결과→월드 맵 복귀를 확인한다.
3. 장시간 다른 스테이지를 플레이하고 종료 조합·STOP·메뉴 복귀를 확인한다. 세 로그는 매 실행 후 따로 보존한다.
4. 타일 깨짐의 장면·시간·복구 여부와 예기치 않은 종료를 분리한다. 실제 스페이드 오류 해결은 아직 승인하지 않으며 안정성 확인 전 출력 속도 최적화는 보류한다.
