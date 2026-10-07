# NES066 파일 쌍·SD 사전 점검 계약

범위는 **오프라인 FPGA/ARM 쌍 생성·전체 압축 복원·읽기 전용 백업·복원 계획 검증**이다. 제품 설치, 사용자 SD 복사, 실제 복원, 외부 IO 승인이나 물리 STM32 실행을 포함하지 않는다. [결과](../analysis/PAIR-PREFLIGHT-RESULT.ko.md), [준비도](development/NES-HARDWARE-READINESS-REVIEW.ko.md).

## 고정된 구성

066은 준비 도구의 번호다. 실행 펌웨어는065, FPGA는061/CF61/protocol59이다. `NES VERIFY 065 80.nh1`, `NES VERIFY 065 96.nh1` 표식을 유지한다. 표식을066으로 바꾸면065가 인식하지 못한다. ARM 이미지는065 최종 링크를 해시로 재사용하며 새 ARM 빌드가 아니다. FPGA는 동결061과41개 파일을 대조한 기존 Standard fit를 **새 폴더에 복사해서 ASM/CPF만** 실행했다.129개 DB 파일의 aggregate와23개 입력/fit·STA 요약을 고정한다. 새 map/fit/STA 또는 전체 코어059 검증이 아니다.

| 파일 | 크기 | 역할 |
| --- | ---: | --- |
| `sd2snes/firmware.stm` |179336|065 메뉴·복구 보호 펌웨어 |
| `sd2snes/fpga_nlv.bi3` |209943|061 적재·비교 전용 FPGA, 정확한 RLE |
| `reference/board.rbf` |510856|오프라인 전체 복원 대조, SD 복사 대상 아님 |
| `sd2snes/nes/fine_x.nes` |81936|승인된80KiB payload+16바이트 헤더 |
| `sd2snes/nes/banks32.nes` |98320|승인된96KiB payload+16바이트 헤더 |
| 두 `.nh1` 표식 |0|수동 메뉴 진입, 확장자를 바꾸지 않음 |

파일별 SHA256과 쌍 manifest SHA256은 [기계 판독 결과](../analysis/pair-preflight-verification.json)에 있다. manifest 자체의 digest를 패키지와 독립된 기록에서 공급해야 한다. 짧은 CF61 ID나 수정 가능한 manifest 단독으로 파일 동일성을 증명하지 않는다. `installable=false`, `start_enabled=false`를 강제한다. CPU/PPU RUN은 기존061/065에서 차단하며 준비 도구는 그 코드를 수정하지 않는다.

구형 C 압축기의 이번 RBF 출력은 원본510856바이트를510857바이트로 복원했다. 원본 prefix는 일치했지만 EOF 반복 뒤 `fseek(-1)` 때문에 마지막FF가 한 번 더 들어갔다. 별도066 encoder는 ESC9B/RUN5B/RUNLONG77 형식을 그대로 사용하며 EOF와65535 길이를 명시적으로 처리한다. 정확한 압축 파일은209943바이트다. 원래 C 프로그래머를 host 핀/FIL/tick 모형에 연결해서 **510856바이트 전부**와 장기 반복/특수 token 경계66309바이트를 비교했다. DONE 모형 성공은 실제 FPGA 설정 성공이 아니다. GBC/044 압축기·바이너리는 바꾸지 않는다.

## SD 읽기 전용 준비

`backup`은 여섯 변경 예정 파일과 기존 `sd2snes/fpga_base.bi3`, `sd2snes/m3nu.bin`의 존재/부재를 기록한다. 기존 firmware/base/menu는 반드시 존재해야 한다. base의 RLE 형식/상한과 menu의 예비 크기 한도만 검사한다. **실제 `smc_id`/`sgb_id` 분류 및 base 호환성 승인은 아직 없다.** 파일명과 작은 크기만으로 메뉴를 승인하지 않는다.065의 실제 분류 조건은 plain mapper0/1, carttype0–2, offset 유효, payload≤4MiB, 특수 FPGA/SGB/EGBC 없음이다. 전체 load_rom은 아직 host 전체 실행 근거가 없다.

백업은 SD와 후보 폴더 밖의 새 폴더에만 생성한다. 각 원본을 fsync 후 다시 읽어 해시를 대조하고, SD를 다시 읽어 백업 전후 일치를 검사한다. 중간 오류는 완성 manifest를 남기지 않는다. 기존 백업을 덮어쓰지 않고 path traversal·symlink/junction을 거부한다. 실제 사용 시 기기 전원을 끄고 PC가 SD를 점유한 상태로 수행한다. 운영체제 캐시·카드 내부 전원 손실까지 증명하는 절차는 아니다.

이 백업은 **변경 대상/복구 의존 파일의 제한 백업**이다. 게임·GBC FPGA·세이브 전체 백업은 별도로 준비하며 도구가 그 파일을 변경하지 않는다. 현재 사용 중인 SD를 읽은 결과는 아직 없다. 모형의 `original working firmware` 등은 테스트 문자열이며044 또는 사용자 SD의 해시가 아니다.

`rollback-plan`도 SD를 수정하지 않는다. 백업 manifest의 독립 digest와 모든 백업 파일을 재검증하고 현재 SD가 기존 원본 또는 정확한 후보인지 확인한다. 후보로 바뀐 파일은 원본 복원, 원래 없었던 파일은 신규 파일 제거를 계획한다. 제3의 내용, 바뀐 base/menu, 손상 백업이면 거부한다. 복원 실행기와 원자적 설치/전원 손실 복구는 아직 제공하지 않는다.044 package는 실기 기준 자료일 뿐 현재 SD 원본의 대체물이 아니다.041 기준을 요구하는 과거 installer를 새 후보에 사용하지 않는다.

## 재현

공개 clone만으로 바이너리/DB가 제공되지 않는다. 명시적으로 제공한 기존061 Standard fit와065 private ARM이 필요하다. 동결 archive를 작업 폴더로 사용하거나 finalizer를 다시 실행하지 않는다. 경로는 예시 입력이며 실제 설치 명령이 아니다.

```powershell
python -B tools/nes_pair_assemble.py --fit <original061-fit> --out <new-ascii-directory> --quartus-bin <Standard25.1-bin64>
python -B tools/nes_pair_preflight.py prepare --firmware <verified065.stm> --rbf <new-ascii-directory>/output_files/board.rbf --out <new-pair-directory>
python -B tools/nes_pair_preflight.py verify --package <pair-directory> --manifest-sha <independent-pair-digest>
python -B tests/nes-functional/pair_preflight_test.py --package <pair-directory> --manifest-sha <independent-pair-digest> --out <new-local-test-directory>
python -B tools/nes_pair_preflight.py backup --package <pair-directory> --manifest-sha <independent-pair-digest> --sd-root <confirmed-sd-root> --out <new-independent-backup-directory>
python -B tools/nes_pair_preflight.py rollback-plan --package <pair-directory> --manifest-sha <independent-pair-digest> --sd-root <confirmed-sd-root> --backup <backup-directory> --backup-sha <independent-backup-digest>
```

`pair_programmer_host.c`를 production `nes_diag_runtime.c`와 함께 host GCC로 빌드한다. include는 `src/nes/firmware`이며 실행 인자는압축 `.bi3`,원본 `.rbf`다. `verify_nes_pair_preflight.py --evidence <frozen066>`는 저장 근거 검사이며 신규 실행이 아니다.

## 실기 진입 때 남은 시험

| 순서 | 준비·관측 | 통과 조건 |
| --- | --- | --- |
|1|PSRAM 부품/speed grade/보드 대응,min/max·외부 IO |정확한 대상의 제조사 자료와 제약 검토. 임의70ns 채택 금지 |
|2|원본 SD/base/menu/GBC·세이브 백업,실제 menu 분류 |독립 해시/백업 readback·호환성 및 복원 절차 확정 |
|3|같은 쌍의 SD readback·카드 쓰기 방지·공간·로그 |후보 digest 일치,PREPARED 쓰기 정책 확인. 쓰기 방지 시 선택 로그 실패와 native 오류를 구별 |
|4|80/96KiB 적재/전체 CHECK/FINISH/STOP |CPU/PPU START 없이 전체 수 일치,실제 시간 기록. wire 추정68.3/82.0s는 측정값 아님 |
|5|LED/UART·base/menu 복귀 |LED 밝기·덮어쓰기·단계/오류 가독성,실제 메뉴 화면 관측. RAM/UART RETURN_READY만으로 화면 성공 주장 금지 |
|6|SD 제거/CRC/busy/STOP/base/menu 실패,RESET·전원·재진입 |실제 종료 시간,재시도/추가 IO 없음,unsafe RESET/USB 해제 없음,수동 복원 가능 |
|7|정상 GBC 재실행 및 독립 재삽입 readback |기존 동작·세이브 보존과 복원 완료 관측 |

현재 H11/H12는 부분 완료다. 파일 쌍 생성으로 외부 타이밍이나 물리 설치 허용을 대체하지 않는다.
