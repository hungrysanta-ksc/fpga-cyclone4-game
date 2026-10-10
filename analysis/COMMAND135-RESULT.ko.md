# 135 최소 RUN 명령 경로와 같은 클록 타이밍 개선

PR80 병합 2fc0e0e9591cd238718d6bdedad9f7e3dadbac73에서 시작했다. **134 최소 RUN 회로의 같은 클록 실패를 수정했다. 최종135fit03 memory168 setup은 +0.152ns이며 세 corner의 같은 클록 setup·hold가 통과했다.** 실기 패키지와 전체 타이밍 승인은 아직 없다.

## 작업 목표

134fit02의 diagnostic_release → pending_body_error[2] −0.330ns를 고치되 명령 판정/실행 시점과 오류 우선순위를 유지한다. 실제95핀 셸의 변경 경계와 CPU RUN을 확인하고 다음 MCU 연결의 누락을 기록한다.

## 작업 내용

- 인코딩된 SPI 오류4비트 레지스터를 독립 원인5비트로 바꾸고 다음 실행 단계에서 우선순위를 인코딩한다. 기존과 같은 동기화 SS 상승 edge에서 판정하고 같은 다음 memory edge에서 실행한다. load_ready를 미리 저장하거나 명령 지연을 늘리지 않았다. 우선순위는 command3 → offset5 → lifecycle6 → not-ready4 → verification8이며 hard fault는 대기 START보다 먼저 처리한다.
- boot sticky check_failed 식에서 check_ready를 전개하고 이미 실패한 상태의 항을 흡수했다. invalid owner, reader 준비, 주소 범위, 적재/RUN 충돌 조건을 유지한다.
- 두 번째 배치에서 발견한17비트 loaded_bytes ENA 경로에만 clock-enable/synchronous-control 자동 인식을 끄는 합성 속성을 추가했다. 상태/주소의 기존 속성은 유지했다. 최종17개 레지스터의 동기 입력은 모두 D이며 ENA 경로가 없다. RTL 동작식은 변하지 않았다.

134 shell/관측 회로/PLL/QSF/SDC/실제 핀95개는 동일하다. 주파수 완화·false path를 추가하지 않았다. 새135 파일을 materializer로 연결하고 과거 원본을 보존한다.

## 작업 결과

선택 **test02 / fit03**. 원인 조합4,194,304개를 이전 실제 SPI 식과 대조하고, boot sticky 다음 상태4,096개를 실제 clock edge에서 대조했다. 전자는2-state 조합 논리 시험으로 도달 불가능한 조합도 포함한다. 후자는 loader/reader 출력 강제 입력 모델이다. 전체 순차/4-state/게이트 등가 증명이 아니다.

실제 SPI 경계 시험은 halfSCK60ns/18ns 각각166검사·18오류 사례를 통과했다. hard-fault/대기 START 충돌, raw reset, memory clock 정지, 겹친 frame, ACK carry 경계를 포함한다. 실제 core 셸은 source 위상0/3.5ns에서 CPU ROM sample 총6,712회/관측14회를 확인했다. 포화 경계의 별도 주입8회는 CPU 실행 수에서 제외한다. PLL 이상 모델·70ns RAM·합성 JMP8000·적재 수/verified 초기값을 사용했으며 전체 적재/CHECK를 재실행한 결과가 아니다.

오류5 제거, hard-fault 우선순위 훼손, CHECK owner 검사 제거의 세 부정 대조가 각각 원인 비교·실제 START 경계·sticky 상태 검사에서 검출됐다. 정상 시험 오류는 없었다.

| 배치 | 변경과 관찰 | memory168 setup 최소 |
|---|---|---:|
| 134fit02 기준 | 인코딩 오류 레지스터 | −0.330ns |
| 135fit01 | SPI 원인 분리 후 boot CHECK 경로 | −0.183ns |
| 135fit02 | boot 식 전개 후 loaded_bytes ENA 경로 | −0.318ns |
| **135fit03 최종** | loaded_bytes D 경로로 매핑 | **+0.152ns** |

매번 상세 경로를 근거로 수정했다. 무작위 seed 탐색이 아니며 중간 실패 배치를 삭제하지 않았다.

| 최종 항목 | 결과 |
|---|---|
| LE / LAB / register / M9K / PLL | 12,026 /885 /4,088 /12 /1 |
| 실제 핀 / 가상 핀 | 95 /0, 위치95개 대조 |
| NES setup / memory168 setup / 같은 클록 hold 최소 | +8.217 /+0.152 /+0.180ns |
| pending_causes / check_failed / loaded_bytes setup 최소 | +0.355 /+1.201 /+0.190ns |
| raw setup 최소 | **−6.767ns**, reader held-data → CPU 포함 |
| 미제약 외부IO | 입력19 /출력44 |

같은 클록18행/raw6행/대상9행을 세 corner에서 확인했다. raw 음수를 숨기지 않았으며 새 CDC/reset/IO·MTBF 승인으로 확대하지 않는다.131/132의 다른 hierarchy 승인을 상속하지 않는다. SNES arm0·bus idle로 화면 transport가 제거되어 이 자원을 전체 게임 여유로 계산할 수 없다.

**test02와 fit03:** SPI/boot 및 나머지 HDL은 같고 loader의17비트 선언 속성 하나만 다르다. 그 정확한 속성을 제거하면 test02와134 loader 텍스트가 동일하다. 기능 시험을 이 근거로 재사용했으며 최종 gate simulation을 수행했다고 기록하지 않는다. 공개 materializer 설명문과 test 출력 two→three 문구만 정리했고 실행 원본·정확한 차이를 verifier로 대조한다. timing134.tsv/same134-*는 계승된 이름이며 **135fit03 안의 새 결과**를 사용한다.

**MCU 차이:** 기존 nes_cf86_session094.py는 단축 식별 응답86을 검사한다. 새 셸은65 로더 응답59와70 관측 응답D4를 제공한다. 기존116 ARM을 그대로 묶으면 안 된다. 새 후보 전용 식별/유한 RUN 경로를 만들고116의 shared fault·CSS/NMI·SD 전이 보호를 유지해야 한다. 이번에는 C/ARM/ASM/패키지를 변경하지 않았다.

초기 verifier의 속성 개수 가정과 Quartus degree 문자 인코딩 가정을 수정했다. 이는 RTL 실패가 아니다. 원본 MAP/FIT/STA/시뮬레이션 로그와 warnings를 보존했다. FLOAT 작업과 임시 서버는 종료됐으며 새 실기·라이선스 오류·승인 거부는 없다.

## 작업 의미

**실기 코어 동작을 위한 회로 구현·검증**에서 같은 클록 타이밍 장벽 하나를 제거했다.135 타이밍 수정은 달성했으며 관측 가능한 최소 RUN 실기까지는 부분 달성이다. 화면·입력·소리·mapper4·SMB3 실행 성공은 아직 아니다.

다음: 선택135fit03를 재사용해 새 hierarchy의 reader held-data/guard/reset/관측 reset과 외부IO 계약을 확인한다. 무변경 MAP/FIT/전체 적재를 반복하지 않는다. 이어 최소 RUN 전용 MCU 식별59+D4, bit별 shared-fault/RDY/예산, 유한 RUN/STOP·진행TXT·base/menu·044복원을 연결한다. ARM116의 CF86 식별86을 그대로 쓰거나 여러 ID를 무조건 허용하지 않는다. 전체 화면/MMC3는 별도다.

119의 전체80KiB 적재/비교/STOP/base/menu/044복원, 기존 GBC 증거와 SMB3(J) mapper4 첫 게임 목표를 유지한다. 진단 준비도6완료/5부분/1미완료는 게임 완성률이 아니다. E1/E2·외부 전기 조건·MTBF·8µs·양클록 정지 lockedHIGH CE9µs 반례는 미해결이다.

## 재현과 보존

run_nes_command135.ps1에 기존 FLOAT wrapper/Python/Questa/새 ASCII 출력/인접 baseline을 전달한다. nes_command135_fit.py로 배치하고 그 디렉터리에서 quartus_sta -t nes_command135_timing.tcl을 실행한다. verify_nes_command135.py --evidence <frozen135>는 manifest/실행소스/기능/핀/타이밍/속성 정규화를 검사한다. 무변경 전체 쓰기나 새 배치는 필요하지 않다.

동결1359파일, manifest 92cbf82a7a19750c8fb6803fb6b569af989fce6bcf4b00576164f36ca9d365a5. 완료 finalizer/archive044–135 수정 금지.124 격리 문제는 재사용/복구하지 않았다.
