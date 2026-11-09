# MMC700·701: 699 수정 보드 실기 전달

699의 CHR 요청 수정과 기존 두 실행 모드를 결합했다. **MMC700은 60초 비교판, MMC701은 장시간판**이다. 이번 변경은 안정성 수정의 실기 확인용이며 새 FPS 개선을 주장하지 않는다. [설치·시험·로그 안내](nes-mmc700-701-trial.ko.md) · [패키지 검증](../analysis/trial700-package.json)

## 선택 구성과 결과

| 항목 | MMC700 | MMC701 |
|---|---|---|
| ARM 기준 | MMC695 → 설치·로그 이름만 변경 | MMC696 → 설치·로그 이름만 변경 |
| 동일 함수 | 799개 주소·크기·바이트 일치 | 799개 주소·크기·바이트 일치 |
| 전체 Flash / 여유 | 212,984 / 8 B | 212,940 / 52 B |
| 65816 | 기존685 정상판 그대로 | 기존694 장시간판 그대로 |
| FPGA | 699 RTL + 정상판 packed ROM, 별도 전체 FIT | 검증된699 SOF 그대로 |
| 전체 비용 | 15,349 LE / 963 LAB / 56 M9K | 동일 |
| setup / hold / recovery / removal | +0.536 / +0.152 / +1.332 / +0.481 ns | 동일 |
| 종료 | 약60초 자동 STOP·메뉴 복귀 | L+R+Start+Select → STOP·메뉴 복귀 |

정상판과 장시간판의 ROM을 혼용하지 않았다. 정상판의 82개 보드 입력 중 `sink-program.hex`만699와 다르며, 두 파일의 CHR 수정·SDC·핀·seed는 동일하다. 기존 제약 STA와 관련 PSRAM/84MHz/ROM_OE 경로는 통과했다. 외부 IO 전체 sign-off는 여전히 미완료다.

SOF→RBF→BI3의 역변환 바이트, 실제227 프로그래머/FatFS의 전송, ARM marker4조건씩, base 복구5조건씩을 검증했다. 실패 주입에서는 안전 복귀를 거짓으로 공개하지 않는다. 실제 sink bus에서 두 판 각각5,120B program·ROM gap·STOP 상태·클록 정지 reset을 확인했다. 60초판의5–40/40–55초 집계와 장시간판의시간 제한·tick wrap·사용자 종료·기존 오류 처리 검사를 통과했다. 하드웨어는 모델이며 이번 실기 설치·보너스 진입·장시간 종료 조합은 사용자 확인 대기다.

두 시작 위상 표시 시간은699의106화면 검증을 계승한다. 이번에는 ARM의 함수 바이트와 표시 ROM이 각 기준판과 같은 것을 확인했으며 변경 없는 전체 일정은 반복 실행하지 않았다. 694 장시간판의 기존 위상1 밀집 +10.728µs/906 내부대기 증가도 그대로이며 정상판보다 빠르다는 뜻이 아니다.

## 산출물과 재현 위치

- ZIP: `WORKSPACE/probes/nes-trial700/trial01/MMC700-60SEC-MMC701-LONG.zip`, 1,020,498B.
- SHA256: `6b90ab8c5f396ce2fc6d1ad8881f3659afb77805384a618348b1350b9275ec01`.
- 설치 폴더: `01-MMC700-60SEC-SD-ROOT`, `02-MMC701-LONG-SD-ROOT`. 한 번에 하나만 설치한다. RESTORE·게임 ROM·세이브 제외.
- ARM: `WORKSPACE/probes/nes-trial700/arm700`·`arm701`; 원본은695의`arm695`·`arm696`. 준비 entry는 `tools/prepare_nes_trial700.py`, 전체 링크는 `tools/build_nes_mmc479_arm.ps1`이다.
- 정상 보드: ASCII Temp `nes-trial700-board01`; `quartus_sh --flow compile board` 뒤 기존 `report_nes_word660.tcl`, `report_nes_reader661.tcl`, `report_nes_oe612.tcl`을 실행했다. 장시간 보드는 `nes-bonus699-board01`을 재사용했다.
- 이미지: ASCII Temp `nes-trial700-image700`·`nes-trial700-image701-02`. `tools/package_nes_trial700.py image`가 CPF·BI3·실제 프로그래머 검사를 묶는다.
- ROM bus: ASCII Temp `nes-trial700-romchecks/rom700`·`rom701`; `tools/check_nes_rom613.py`와 기존 Starter FLOAT1좌석을 순차 사용했다.
- 패키지: `tools/package_nes_trial700.py pack`; 각기 `--normal/--long`에 새ARM의`src`, `--normalbase/--longbase`에695의원본`src`, 두 보드·이미지·ROM checks와 기존695 `trial02` ZIP을 지정한다. 선택 검사는 `WORKSPACE/probes/nes-trial700/checks01`이다. 전체 인자·빌드 로그는 private archive에 보존한다.
- [근거 보존](../analysis/trial700-archive.json): 선택 소스·ELF·FIT/STA·프로그램·검사·ZIP을 파일별 SHA로 확인했다. `image701` 첫 실행의 sandbox GCC CreateProcess623 실패도 보존했다. 같은 코드의 승격 실행 `image701-02`가 통과했으며 라이선스 문제는 아니다.

## 다음 순서

1. MMC700으로 기존 첫 레벨5–40/40–55초 비교·자동 메뉴 복귀.
2. MMC701으로 월드1 레벨1·2 이후 스페이드 안내→회전 게임→월드 맵 복귀. 치트는 전달 ROM에 넣지 않았다.
3. 장시간 다른 스테이지를 진행하고 종료 조합으로 STOP·메뉴 복귀. 이전 약14분11초 종료보다 긴 실행을 확인한다.
4. 세 로그와 장면·시간·종료 사유를 판별로 수신한다. 수정 후 실기 성공 전 CHR 오류를 닫지 않고, 부팅 timeout은 별도로 추적한다.
5. 안정성 확인 뒤692의951 출력 병목을 LE여유59/LAB·M9K여유0 안에서 재개한다. 이번 안정성 수정을 성능 이득으로 합산하지 않는다.
