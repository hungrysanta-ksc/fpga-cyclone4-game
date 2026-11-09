# 693: 장시간판 종료·통계 경로 구현

MMC690의 60초 비교판은 그대로 보존하고, 장시간판의 ARM·65816 후보를 별도로 구현했다. 선택은 **patch04/arm03 + client02**다. [검증](../analysis/longrun693-verification.json) · [보존 근거](../analysis/longrun693-archive.json) · [692 비용 분해](nes-output692-results.ko.md). 설치본·실기 결과·새 성능 개선 판정은 아직 없다.

## 구현과 비용

| 항목 | 선택693 | MMC690 대비 |
|---|---:|---:|
| ARM 전체 Flash | 212,940B / 212,992B | −44B, 여유52B |
| ARM data / BSS | 10,040 / 19,552B | BSS +8B |
| 65816 본문 | 6,020B | +36B |
| 압축 ROM 저장 | 5,120B 영역, 여유25B | 기존 여유13B |
| 추가 영구 SNES 데이터 RAM | 0B | 코드36B 증가는 별도 |
| FPGA 논리 | 기존689D screen/status 경로 재사용 | ROM 초기값 변경, 새 FIT·STA 미실행 |

장시간판만 `begin(limit=0)`을 허용하고 고정 플레이 시간 제한을 없앴다. 기존 limit 저장 공간을 마지막 관측 tick에 재사용한다. tick이 바뀌면 step 감시를 초기화하므로 정상 플레이의 누적 반복 횟수로 종료되지 않는다. tick 정지 때의 4,194,304-step 차단, 기존 클록·전송·credit·ACK 고장 검사는 유지한다. 초기 arm01/02의 ‘5초 동안 표시 완료가 없으면 종료’ 후보는 정상적인 빈 화면에도 종료할 수 있어 폐기했다. 선택 arm03에는 그 제한이 없다. 새 감시는 전역 타이머 진행 감시이며 모든 종류의 논리적 교착을 탐지한다는 주장은 하지 않는다.

**L+R+Start+Select**를 함께 누르면 기존 완료된 joypad 읽기에서 요청을 인식한다. `$4212 & $81 == 0`을 읽기 전후 확인하는 원래 경로를 유지하므로 VBlank 및 autojoy busy 중에는 새 입력을 채택하지 않는다. `$6002/3` 입력 전달 뒤 sticky STOP을 우선 확인하고, `$7000` stage에 `$7e`를 기록한 다음 CPU를 대기시킨다. 별도 ACK나 DMA 완료를 만들지 않는다. 기존 FPGA의 host-qualified stage와 SPI73 원자적 snapshot을 ARM이 읽고 `USER=8`로 처리한 뒤 기존 STOP·base·메뉴 절차로 간다. `$7001`의 기존 오류 정보는 건드리지 않는다. 첫 표시 전 자발적 종료도 정상 취소이며, 실제 고장은 정상 종료로 바꾸지 않는다. 물리 RESET은 정상 종료 조합을 대신하지 않는다.

장시간 로그는 schema693을 사용한다. 기존12개5초 bin을 약60초 epoch마다 다음 frame-start에서 함께 초기화하고 `epoch_tick`을 기록한다. 첫5–40초·40–55초 완료 집계는55초 뒤 고정하여 tick wrap 뒤 다시 열리지 않게 한다. 전체 경과는 기존 progress checkpoint로 남긴다. 다른 누적32bit 진단 카운터는 여전히 modulo32이며 무한 비오버플로 누계를 주장하지 않는다. RUN 중 SD 쓰기는 추가하지 않았다. 현재 후보 이름은 아직690이며 **설치용 패키지가 아니다**.

## 실제 검증 범위

- 전체 링크 ARM16조건: 60초 초과·한 시간 경과값 주입·tick wrap·빈 화면 지속·정지 tick·상태 오류 우선·실제 USER 전달·16bit queue credit wrap·stale ACK·SEAL 대기 중 취소·첫 화면 전 취소·통계와 출력 버퍼 검사. 한 시간 값 주입은 한 시간 연속 실행이 아니다.
- 실제65816 서비스12조건: 정상 입력, 전체 조합, 추가 버튼, 각 필수 버튼 누락, VBlank/busy/두 번째 읽기의 busy, STOP 우선. 대상 본문 바이트를 확인했고 가짜 ACK·DMA가 없었다. fixture가 본문을 WRAM에 적재했으므로 실제 packed reset loader 부팅 검증은 아니다.
- 기존 screen RTL: 비한정 쓰기 차단, SPI snapshot 중 stage 변경의 원자성, 요청 유지, 비활성/reset 무효화. 승인된 단일 Starter FLOAT 작업으로 통과했으며 라이선스 관련 파일은 보존 ZIP에서 제외한다.
- 링크된 메뉴 준비·해제5조건과 marker4조건, 기존 base 복구5조건 통과. 오류 주입에서는 잘못된 base 복구 성공을 선언하지 않는다.
- 저장 ROM 스트림을 풀어6020B 본문과 완전히 일치함을 확인했다. CPU client02는 client01과 실행 바이트가 같고 본문 한도/복원 크기 메타데이터만 정정했다.

검사들은 실제 경계값으로 연결되지만 하나의 공통 시간축에서 전체 ARM·FPGA·65816을 함께 실행한 결과는 아니다. 기존 STOP/독립 검사 코드를 보존한 것과 새 장시간 후보의 모든 DMA/SEAL 취소 경계를 재검증한 것을 구분한다. 새 두 위상 시간·전체 FIT·실기 안정성 통과로 확대 해석하지 않는다.

## 재현과 다음 순서

저장소 루트 기준 `tools/prepare_nes_longrun693.py`로 MMC690 ARM과685 CPU에서 새 출력 경로에 생성한다. ARM은 `tools/build_nes_mmc479_arm.ps1`의 Base=nes-trial690/arm02, Patch=생성경로로 전체 링크한다. 선택 근거는 WORKSPACE/probes/nes-longrun693의 patch04, arm03, client02, guards08, menu03, base03-*이다. CPU/RTL의 선택 원본은 Temp/nes-longrun693-cpu05 및 rtl01이며 보존 ZIP에도 포함된다. CPU fixture 출력은 ASCII 경로를 사용한다. 원래 Unicode 경로·fixture 가정·컴파일 경계 실패와 초기 후보는 삭제하지 않았다.

1. packed reset loader와 보드 ROM 초기값을 연결하고, 실제 입력→plan→receipt→SNES의 세대65535→0 및 DMA/SEAL 경계 취소를 검사한다. queue credit wrap 통과로 세대 전체 경로를 대체하지 않는다.
2. 실제 ARM·SPI·IRQ·ROM 경쟁과65816을 같은 일정으로 두 시작 위상에서 재생한다. MMC690의7블록 선행 수신,911 마감·951 공개선·952 표시3회·957 최종대기0회와 밀집 표시 간격·마지막 ACK를 유지하는지 확인한다. 코드 증가·ROM 압축 해제·종료 입력 감시 비용도 포함한다.
3. 변경 ROM을 포함한 전체 Quartus Lite 비용과 기존 제약 STA 무회귀를 확인한 뒤 고유 설치/로그 이름의60초·장시간판을 함께 준비한다. RESTORE는 제외한다. 새 이름으로 전체 링크·marker·메뉴 복귀도 다시 확인한다.
4. 692에서 정한951 마지막 tile ACK→SEAL 발행 병목 개선을 계속한다. 새 장시간 기능만으로 FPS가 올랐다고 판단하지 않는다. 드문 stage0 부팅 실패는 별도로 보존하고 원인 없이 timeout/재시도를 바꾸지 않는다.
