# 126 — 영상 bridge의 명시적 동기화 배치 적용

## 작업 목표

PR71 병합 `5cd4d28f71fd8d0a340f4be34a67c91e95c6046f` 이후,125에서 남긴 제어6쌍의 실제 동기화 체인과 reset 해제 경로를 확인했다. **체인 구조·단계 간 타이밍 확인과 bridge의 명시적 배치 속성 적용을 달성했다.** 전체 아날로그 CDC·외부 IO·실기 RUN은 미완료다.

## 작업 내용

같은124 배치에서 reader request/ack,bridge request/ack,양방향 peer-up의 첫 단계 출력을 조사했다. 여섯 체인 모두 첫 단계는 두 번째 단계 하나에만 연결됐다. core/reader/host reset 해제에 RAM 초기화용 init_release도 더해,총10개 체인의 첫 단계 fanout·두 단계 구조·setup/hold를 확인했다. 기존 init_done 비동기 종착점6비트와 이번에 조사한 release4체인8비트는 서로 다른 집합이다.

reader와 reset 해제 회로는 Quartus에서 `User Specified`로 잡혔지만,bridge4체인은 기존 `async_reg` 표기가 있어도 실제 보고서에서는 `Automatic`,MTBF 포함 플래그 `No`였다. 따라서 양 단계8개 레지스터에만 `SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS`를 명시했다. 검증된 정확한 설정은 [nes_bridge_sync126.qsf](../src/nes/diagnostic/nes_bridge_sync126.qsf)에 보존한다.

설치된 Quartus25.1 공식 도움말은 이 속성을 바꾸면 Fitter를 다시 실행하도록 안내한다. 매핑 결과와 RTL을 포함한 고정 입력47개를 유지하고 실제 Fitter/STA를 다시 실행했다. 새 배치에서는 bridge4체인 모두 `User Specified`/포함 플래그 `Yes`로 바뀌었다. 같은 RTL 기능시험을 다시 실행하지는 않았다. 속성 적용이 모든 경로의 slack 개선을 보장하는 것은 아니며 실제 수치를 각각 검사했다.

## 작업 결과

| 검사 | 최종126 결과 |
| --- | --- |
| 제어6 + reset 해제4체인 | 모두2단계,첫 단계 fanout1,다음 단계에만 연결 |
| 체인 단계 간 타이밍 | 10체인×setup/hold×3corner=60개 모두 양수 |
| 최소 단계 간 setup / hold | +4.762ns / +0.196ns |
| 로컬 reset 해제 후 recovery/removal | 4,290경로 모두 양수,최소+1.171ns |
| init_done의 비동기 reset 종착점 | 기존6비트/36 recovery-removal 경로 유지;원시 입력 검사는 미완료 |
| 재배치 자원 | 13,568LE,933/963LAB,4,955레지스터,26M9K,PLL1 |
| 실제 핀 / 가상 핀 | 46 / 264,기존 실제 핀 배치 유지 |
| NES / host84 / reader168 내부 setup | +8.845 / +3.221 / +1.313ns |
| 전체 원시 최소 slack | −7.976ns,전체 타이밍 통과 아님 |

125 데이터 제약을 새 배치에서 다시 검사했다. 이것은 배선이 바뀌어 필요한 회귀이며,변경 없는125 시험 반복이 아니다.

| 데이터 경로 | 쌍 | 새 최대 데이터 지연 | 그대로 유지한 데이터 예산 | 새 SDC 최소 slack |
| --- | ---: | ---: | ---: | ---: |
| reader 주소 | 22 | 1.271ns | 4ns | +2.176ns |
| reader 반환 | 257 | 10.088ns | 40ns | +37.476ns |
| bridge 요청 | 46 | 6.688ns | 40ns | +40.862ns |
| bridge 응답 | 47 | 1.263ns | 10ns | +7.787ns |

372쌍×3corner=1,116개 모두 통과했다. 데이터 예산과 수신 한 주기의 SDC 최대 지연은125 그대로다. 전체 false-path/clock-group 면제를 추가하지 않았다. 원시 비동기 첫 단계의 위반을 기능 경로의 동기식 위반과 혼동하지 않되,도구 보고에서 숨기지도 않았다.

도구의 `Available Settling Time`은 최종 단계 출력 slack까지 포함할 수 있어 첫 단계→두 번째 단계의 setup 여유와 다르다. 둘을 별도로 저장했다. **포함 플래그 Yes는 MTBF 계산 성공이 아니다.** 최종 보고서도 전체 타이밍 미충족 때문에 MTBF를 계산하지 않았다. 기본 toggle rate는 실측값이 아니며 이를 바탕으로 수명이나 실패 확률을 주장하지 않는다. 비동기 reset 최소 펄스·아날로그 metastability·보드 외부 지연·전압/부하·공통 클록 고장은 여전히 별도 조건이다.

### 실패와 보정

첫 `fit01`은 TimeQuest의 entity:instance 경로를 중괄호와 함께 QSF에 쓴 탓에8개 속성이 무시됐다. Fitter 종료는 성공했지만,실제 체인이 여전히 Automatic인 것을 검사해 거부했다. `fit02`는 QSF용 instance 경로로 고쳤고,이제 `Ignored assignment`가 있으면 드라이버에서 바로 실패한다. 두 배치와 원시 경고를 모두 보존했다.

최초 fit02 검증은 LE 수가124의13,540과 같아야 한다는 불필요한 가정으로 실패했다. 재배치의 packing은13,568LE로 바뀌었고933LAB·4,955레지스터·26M9K는 유지됐다. 검증기를 장치 한도와 실제 보고서 검사로 고쳐 같은 결과를 재검사했으며 새 빌드는 반복하지 않았다. 초기에 도움말 명령 형식/반환 문자열 출력도 보정했고 공식 도움말 원문을 남겼다.

최종 `fit02`와 초기 실패를 포함한2,078파일을 동결했다. manifest `0b81e9d875b04683f59a0de3599a2770c2b86437bca51e9ce6bdc3d85550a5d0`. [검증 메타](control126-verification.json)와 `verify_nes_control126.py`로 재검사할 수 있다. 과거 완료 증거·GBC·원래 NES 소스는 유지했다. ARM/ASM/설치 패키지나 실기 결과는 새로 만들지 않았다.

## 작업 의미

**실기 코어의 클록 간 제어 배선을 위한 FPGA 배치 설정 구현과 검증**이다. 문서 분석을 넘어 실제 bridge4체인을 명시적인 동기화 최적화 대상으로 지정하고 다시 배치했다. 논리 기능이나 mapper 호환성을 추가한 작업은 아니다.

다음은 **126 fit02를 기준으로 로더 WRITE375ns·CHECK/RUN 메모리 소유권·guard를 통합하는 실제 배선 작업**이다. 새 프로젝트에도8개 QSF 설정을 함께 가져오고 적용 결과를 검사한다.8MHz WRITE3를168MHz에 그대로 옮기면17.856ns이므로 금지한다. 이어 실제 SNES 소비자·진행 관측·오류 종료·독립044복원을 연결해 최소 RUN 실기로 간다. 외부 조건을 전체 보장으로 포장하지 않으며,변경 없는 동기화 분석만 반복하는 PR은 만들지 않는다.

119 전체80KiB/메뉴/044복원,122/124 기능 기준,SMB3(J) mapper4/384KiB 첫 게임 목표를 유지한다. E1/E2·8µs·양 클록 정지 lockedHIGH CE9µs 반례,113 원인 미확정,119 GBC 플레이 미보고는 남는다. 제한 진단6완료/5부분/1미완료는 게임 완성률이 아니다. 아직 사용자가 설치할 새 실기 패키지는 없다.
