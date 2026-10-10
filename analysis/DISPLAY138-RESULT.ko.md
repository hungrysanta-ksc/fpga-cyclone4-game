# 138 화면 실기 시험 패키지

## 작업 목표

137 화면 경로에 MCU의 표시 전환·유한 실행·정상 복귀를 연결해 실기에서 화면을 확인할 수 있는 패키지를 제공한다.

## 작업 내용

- PR83 병합을 확인했다.136의 실기 CPU RUN·메뉴 복귀·복원 성공을 유지한다.
- 전용5A/D5 식별을 MCU/FPGA에 함께 적용했다.136의59/D4는 거부하며 기존094를 직접 수정하지 않는다.
- ARMED→RELEASING→DISPLAY→ARMED 상태를 추가했다. RESET 해제 후1ms 정착 구간만 양쪽 sense를 허용하고 이후에는 해제 상태를 확인한다. 표시 중1ms마다 소유권/공통고장/RDY를 확인하며 USB IRQ·CSS/NMI·bit별 SPI 검사를 유지한다.
-200회 관측과50ms씩의 대기로 약10초 표시한 뒤 RESET을 먼저 유지한다. STOP의 flags2/count81920, base/menu 및044 복원을 연결했다. RUN/표시 동안 SD 기록은 없다.
-137 선택 fit03에서 기능 소스는 SPI 식별 상수 두 곳과 관측 식별 한 곳만 바꿨다. 이 변경에 따른 새 fit01을 수행했고, 픽셀/소비자 동작은137 증거를 재사용했다.

## 작업 결과

**화면 실기 패키지 전달 준비 목표를 달성했다. 실물 화면과 게임 구동은 아직 미확인이다.** [실행 안내](../docs/nes-display138-instructions.ko.md) · [검증 메타](display138-verification.json).

- 호스트07: 실제 MCU/FatFs/보호/복귀 코드16사례 통과. 정상·활동 없음·ROM 오류·STOP 후 카운터 변화, 구형 식별2종·RDY·STOP 실패·표시 중 RESET/USB/SD 소유권/로그권한/DONE/공통고장·정착 중 RESET·표시 중 잘못된 finish를 검사했다. 외부 FPGA/보드/타이머는 모델이다. 정상 경로의 대기는10초 이상이며 SD 기록 금지와 RESET 선행 STOP, 실제 메뉴 복사·복귀 경로를 확인했다.
- RTL01: 실제 코어와70ns PSRAM 모델, 고정80KiB 초기화,5A/D5·부트 opcode/vector/epoch·STOP 버스 격리21검사 통과.4.152ms 모델이며 새 전체 적재/3프레임/10초 RTL 시험이 아니다.137의 실제 코어184320픽셀·별도 SNES183552표시픽셀·카운터26112검사를 정확한 소스 경계로 재사용한다.
- fit01:13651LE,929/963LAB,5122register,50/56M9K,PLL1,122실핀/0가상. 같은 클록 setup+0.305ns/hold+0.177ns. raw setup−6.220ns를 전체 타이밍 통과로 바꾸지 않았다.
- CDC:3366보고행/668쌍 중 held-data363쌍×3corner=1089검사 통과.17체인의 첫 fanout1,setup+4.783/hold+0.194ns. reset7122행 중114음수는 release 체인 비동기 입력에 한정하며 기능 하류 최소+0.492ns다. CHR 안정구간·RUN lifecycle은 변경 없는133 계약을 재사용한다.
- I/O:PSRAM70ns,95.232ns 읽기 창에서 입력6.936ns/읽기 출력11.793ns,setup/uncertainty2ns·미측정 PCB왕복2ns 가정으로+2.503ns. SNES 입력최대14.283ns/출력19.299ns/raw 해제21.276ns. 기존 합성 시험의160ns 샘플에 대해8 host주기와PCB4ns/setup2ns를 합한134.814ns 조건부 예산이다. 실측 최소 펄스/보드 지연·MTBF·전기적 signoff는 아니다.
- ARM02:186028바이트, 호스트 시험과 실제 MCU 소스 일치, 강한 CSS NMI 벡터/종료15store 보존, 표시 enter/leave 호출 확인. ASM01:510856바이트 RBF→402988바이트 packed, 전체 decode 일치.
- 사용자 패키지는 시험 파일과 정확한044 복원을 함께 포함한다. Git에는 소스·문서·해시만 올린다. `run_passed`는 CPU 활동/STOP만 뜻하며 화면 통과는 사용자 사진·영상/관찰로 확인한다.

준비 스크립트의 대상 문자열/범위 오류와 기존 호스트의 RESET 가정을 수정했다. 모든 초기 결과는 보존했다. 라이선스는 기존 Starter FLOAT를 사용했고 새 유료 라이선스가 필요하지 않았다.

## 작업 의미

디버그 기반 확장이 아니라 마일스톤 C의 **실제 영상 표시를 실기에 연결하는 작업**이다. A 패키지/B CPU 실기는 완료 상태를 유지하고 C의 화면 실기·입력, D SMB3 mapper4·384KiB·플레이·오디오, E 실제 실패에 따른 호환성 확장이 남는다.

138 화면 실기에서 두 TXT·패턴 표시·메뉴 복귀·044 메뉴/GBC 복원을 먼저 확인한다. 실패하면 마지막 성공 단계와 실제 화면을 근거로 해당 경계만 수정한다. 통과하면 패드 입력을 연결하고 이후 SMB3 mapper4·384KiB·플레이·오디오로 진행한다. 새 실패 없이 같은 배치·전체 적재·영상·저장 시험을 반복하지 않는다.

재현 순서: `nes_display138.py --kind fit/arm`, `build_nes_display138_arm.ps1`, `test_nes_display138.py`, `test_nes_display138_rtl.py`(기존 FLOAT wrapper), `check_nes_display138_arm.py`, `inventory_nes_display138.py`, `nes_display138_sta.py`, `nes_display138_io.py`, `assemble_nes_display138.py`, `release_nes_display138.py`. 각각 새 출력 디렉터리를 사용한다. 동결 후 `verify_nes_display138.py --evidence <138 evidence>`는 읽기 전용으로 검사한다.

E1/E2·MTBF·8µs/양클록 정지 CE9µs 반례·124 격리·source-lock4건·044 및 SMB3 최초 목표를 유지한다. 과거 동결 자료/완료 finalizer는 수정·재실행하지 않는다.
