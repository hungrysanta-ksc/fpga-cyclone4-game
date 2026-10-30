# NES 재현 범위와 다른 PC 입력

현재 실기는 **MMC502**이며493은 이전 기준,498은 보류 상태다. [현재 인계](HANDOFF.ko.md)·[감사499](../../docs/nes-audit499.ko.md)·[새 계획](../../docs/nes-audit499-plan.json)을 먼저 읽는다. 아래474–485는 과거 입력이며 현재 선택본이 아니다. clone만으로 전체 빌드 입력이 완결되지는 않는다.

## 이전493 기반 재현 입력

| 영역 | 고정 입력/근거 |
|---|---|
| ARM | `probes/nes-boot493/ARM01/src` 전체source/obj-nes-100 ELF; [493 제작](../../analysis/boot493-verification.json) |
| FPGA | 기존489 board02의70 QSF/제약/초기화 입력; [499 재대조 목록](../../analysis/audit499-verification.json) |
| 65816 | `probes/nes-output489/client04` body4311B/program5120B/ABI4891; [489 계약](../../docs/nes-output489-contract.ko.md) |
| 실기 | `probes/nes-hardware494/run01` 원본3TXT/receipt 및termination02; [494 원본 요약](../../analysis/hardware494-mmc493.json) |
| 보류 후보498 | 별도ARM01/candidate06/live04/board05; [498 검증과 한계](../../analysis/prefetch498-verification.json).493과 혼합 금지 |

`python tools/audit_nes499.py --board <489-board02> --arm <493-src> --raw <494-run01> --out <fresh-json>`은 선택hash와기존로그를 재검사한다. 합성·시뮬레이션·새 실기 성능시험을 실행하지 않는다. 실제 설치 산출물 hash는493 package를 따른다.

## 502 실기 수신503 재현

원본은 `probes/nes-hardware503/run01`의3TXT와receipt.json이다. `check_nes_hardware503_termination.py --arm <capture502-ARM01/src> --raw <run01> --out <fresh-termination01>`은 실제 linked502에서 종료4조건/반례16개를 확인한다. `analyze_nes_hardware503.py --receipt <nes-hardware503> --out <fresh-json>`으로 [503 분석](../../analysis/hardware503-mmc502.json)을 재계산한다. 물리 종료 순간 재생이나 새합성이 아니다. 다음 시험판부터는 RESTORE 폴더를 생략하되 아래502 기존ZIP과제작기록은변경하지않는다.

## 502 전달본 제작 입력

502는493 ARM 전체 source에 `release_nes_capture502.py prepare`의3개 label 변경만 적용하고 기존 `build_nes_mmc479_arm.ps1`로 빌드한다.781개 linked함수와32B header 뒤의label 이외bytes가493과같은지검증한다. `.ARG_VERSION`은생성된version cache로동일label변경만허용한다.

FPGA는capture502 board01의기존SOF/FIT/STA·70입력hash를사용한다. Quartus Lite CPF로RBF를내고 `release_nes_capture502.py assemble`로BI3를만든다. 같은회로의FIT/Questa를재실행하지않는다. `test_nes_nrom458_programmer.py`는새BI3/RBF를실제FatFS/programmer와모델GPIO로검사한다. 선택은programmer02이며01의sandbox GCC WinError623은실행환경실패다.

`package_nes_capture502.py`는hash가고정된493 ZIP에서복구파일을복사하고새ARM/BI3·고유502파일명·안내를묶는다. `analysis/capture502-package.json`과제작검증에최종hash가있다. 작업자료는 `probes/nes-capture502/ARM01`, `release01`, `trial01`, `evidence-release`, `release-archive01.json`에보존한다. 원래493/502 private전체입력의복구가필요하며상용ROM/license는Git에없다.

## 저장소만으로 가능한 것

- 현재 상태·성능·선택 산출물·보호 경계·실패 판단·다음 순서를 채팅 없이 확인한다.
- `analysis/nrom474-verification.json`의66 FPGA 입력/11 ARM 변경 해시와 `analysis/nrom475-hardware.json`의2회 실기 요약을 비교한다.
- 공개 자체 진단 생성기/단위 소스/변경 recipe를 읽고 새 수정의 범위를 검토한다.
- 문서 링크·형식·현재 상태를 `python tools/check_repository_docs.py`로 검사한다. Python3 표준 라이브러리만 필요하다.

**깨끗한 clone만으로 현재493 전체 firmware/FPGA/과거 원시 시험을 재빌드할 수 있는 상태는 아직 아니다.** 이 저장소 정리는 현재 소스·빌드·도구를 승격하거나 새로 검증한 작업이 아니다. 아래 입력을 복구하기 전 실패를 새 회로/라이선스 문제로 진단하지 않는다.

## 과거474/475의 외부·로컬 입력

| 작업 | 필요한 입력 | 저장소의 근거 |
|---|---|---|
| 474 ARM patch 생성 | 검증된471-04의 전체 ARM source에서 recipe가 읽는11파일 | [471 선택](../../analysis/nrom471-verification.json), [47411파일 pin](../../analysis/nrom474-verification.json), `prepare_nes_nrom474_arm.py --base <source> --out <fresh>` |
| 전체 ARM 결합 | 기존227 source/utils/mini 입력,407 build04 loader/Makefile,418 menu source, GNU Arm/make | `build_nes_nrom418_arm.ps1`의 입력 목록; 현재는 개인 경로·W/V drive 가정이 있어 경로 일반화가 필요 |
| FPGA source/bitstream 재현 | 검증된471-04 전체66 QSF 입력·제약·ROM 초기화, Quartus Lite | `analysis/nrom474-verification.json`의 FPGA_inputs와 artifact hash; source/bitstream을 임의 옛 모듈 조합으로 대체하지 않음 |
| M4 비교 | 실제471/474 ELF·firmware와 source packet 또는 live RPC 원본, Unicorn/pyelftools | `check_nes_nrom474_arm.py`; 기존 `.tools`/`probes` 가정도 먼저 대조 |
| native renderer/window 회귀 | 원본 reference fixture·source snapshot, C compiler | `test_nes_nrom474_native.py`; 내부 prepare 경로까지 확인 |
| 연결 회귀 | 실제 board source·선택 ARM C·자체 scene02·Mesen/.NET·Questa | `test_nes_nrom471_live.py`에474 arm 인자를 사용한 기록; HOST에는 DWT clock이 없어 quiet 시간은 별도 모델 검증 |
| 475 실기 재분석 | 사용자 원본6개 TXT | [원본 hash](../../analysis/nrom475-hardware.json), `analyze_nes_nrom475_hardware.py --raw <restored-raw> --out <fresh-json>` |

`probes/`는 저장소 형제인 로컬 작업 자료 공간이며 Git 자료가 아니다. 예전 PC의 디렉터리가 다른 PC에도 존재한다고 가정하지 않는다. 원본 부재 시 결과 JSON은 과거 증거 요약이지 새 PASS가 아니다.

## 옮길 때의 원칙

1. 먼저 current handoff/verification/package JSON으로 선택 source와 artifact hash를 정한다.
2. 해당 선택본의 입력·원시 로그·허가된 도구를 별도 안전한 자료 묶음에서 복구한다. 후보를 섞거나 빈 파일로 시험을 통과시키지 않는다.
3. 공개할 소스는 기존 고지/고정 upstream/라이선스를 검토해 선택적으로 승격한다. 오래된 whole workspace·상용 ROM·사용자 save/영상·license를 Git에 넣지 않는다.
4. 경로 일반화와 입력 복구 뒤 fresh output에서 필요한 최소 gate만 실행한다. 최초 재현의 성공/누락 범위를 기록한다.

이 이식성 미완료는 [현재 재개 안내](../../docs/development/RESUME.ko.md)의 명시된 후속 작업이다. 문서를 읽고 작업 판단을 이어가는 것과 설치본을 clean clone에서 재빌드하는 것을 구분한다.

## 과거 공개 단위 시험

`tools/run_nes_public_units.py`에는 자체 입력의 메모리/ROM service/boot 단위 경로가 있다. 유효한 설치 Questa 환경과 fresh ASCII output을 사용한다. 이 시험은 최신474 전체 경로·GBC 회귀·실기/60fps를 대신하지 않는다. 이번 문서 정리에서는 실행하지 않았다.

## 478에서 추가 확인한 합성 의존성

기존471의66 QSF 항목 외에 자동 발견 CIRAM/HEX와 board.sdc가 읽는 cdc181.sdc가 필요했다. [478 source closure](../../analysis/game478-feasibility.json)에69개 hash를 기록했다. 실제 실행 source·constraints를 `probes/nes-game478/mmc03`에 보존했으며 이는 아직 private다. 기존 board-source snapshot만으로 전체 재현 입력이 완결됐다고 가정하지 않는다. 현재 PC에서 이 자료를 사용하고, 다른 PC 재현 시 이식성 작업이 별도로 필요하다.

## 479 로컬 입력

`prepare_nes_mmc479.py`는 선택476 전체 ARM source, hash 고정 원래227 loader,478의69파일 closure/QSF를 요구한다.479 실행 source·ARM03/loader02/core01/board01·M4 결과는 `probes/nes-mmc479`에 보존한다. 새 PC에서는 `execution-location.json`의 경로를 그대로 쓰지 말고 대응 source/도구를 복구한다. 원본 ROM은 private147 PRG/CHR hex에서 기존 전체 SHA와 byte 동일하게 복구했으며 Git에 넣지 않는다. host20건·seeded core smoke·M4 기록 재생을 실제 live ARM/IRQ/tile/SNES 구동으로 오인하지 않는다. 새 설치본은 아직 없다.

## 480 연결 시험과 전달본

`test_nes_mmc480_live.py --prepare-only`는 시뮬레이터 없이 생성 runner를 검사한다. 실제 실행은479 board/ARM·원본 ROM·core01 자료와 기존 FLOAT wrapper/Mesen/.NET을 요구한다. `probes/nes-mmc480/executed`에 live01/ARM01을 보존했다. FPGA는 같은479 fitted DB에서 ASM/CPF만 수행했다. `analyze_nes_mmc480.py`의 CLI로 같은 근거를 재분석한다. ZIP은 `trial03/MMC480-SMB3-TRIAL.zip`이며 hash/구성은 analysis/mmc480-package.json이다. 원본 SMB3 ROM·private trace·upstream/license·물리 timing/실기 승인 범위는 공개 소스로 승격하지 않는다.
