# 083 SD 접근 전 화면 표식과 첫 관측 패키지

SD 초기화 전에 mini 화면을 준비하고, 초기화·첫 mount 직전 표식을 표시하는 목표를 달성했다. **보고서 전용 첫 관측 ZIP과 정상044 복원 파일을 준비했다.** 아직 실기에서 표시·저장 성공을 확인하지 않았으며 사용자0바이트 원인은 미확정이다. [실행·복원 안내](../docs/SDREPORT083-RUN.ko.md)를 따른다.

## 변경과 검증

PR33 병합 master `413c4fd11a395e661a6d894fed1c283d4fdc2ecb`에서 `codex/nes-report-observation-083`을 시작했다. 이전081 native SD/상태 연결/FatFS/타이머/080mini·boot/079저장 checkpoint는 동일 입력을 사용한다. 새083 플랫폼, 호출 ID, TXT 이름만 바뀐다. GBC와 기존 NES 원본은 변경하지 않는다.

실제 순서는 `report_boot080 → STEP 1A INIT SD(1초) → sdn_report_initialize081 → STEP 1B MOUNT FAT(1초) → file_init/f_mount → 저장 단계2–8(각0.5초) → terminal`이다. 첫 표식은 파일쓰기 권한을 열지 않고 SD 명령 없이 내장 mini/boot만으로 준비한다. 실제 STM32 설정의 FPGA CCLK는 PB9, SD CLK는 PC12로 분리돼 있다. 실제 FPGA 초기화는 GPIO 설정이며 SD 파일을 열지 않는다. GPIO·SPI·timer·CIC 등 main 초기 설정은 여전히 runtime 진입 전제다.

새 표식은 문자열 SRAM write/read 비교와 보호 확인 뒤 RESET을 해제하고, 제한된 대기 후 다시 유지한다. 예산을 다시 시작하지 않는다. 이후 오류에서는 SD·SRAM·화면 출력을 강행하지 않는다. 첫 오류·USB 제외·쓰기권한 회수·불확실한 쓰기 재시도 금지를 유지했다.

| 검증 | 결과와 한계 |
| --- | --- |
| 실제 초기화/native/FatFS/화면/저장 단일 호스트 | 679검사 통과. FAT16/32×SDSC/SDHC 정상4조합. SRAM591접근 전체 고장,43응답 위치,화면변조/타이머/누적예산/wrap/재진입 등. 카드·핀·시간·SRAM은 모델 |
| 실제1초 타이머 | 5검사 통과. 84MHz 설정의84000000카운트, 완료/정지/시간wrap/overflow/기존fault. TIM2 레지스터와100Hz clock 모델 |
| 인과 대조 | 4개 통과. readback 비교 제거, 저장 checkpoint RESET 재유지 제거, 최초 표식 생략, 표식 RESET 재유지 제거를 모두 거부 |
| 최종 ARM | 실제main→083 연결과 mini→표식→초기화→표식→mount→writer 순서 확인. 15개 기존 핵심 소스 SHA 불변. MCU에서 실행한 결과는 아님 |
| TXT 판독기 | 정상3072바이트/0바이트/내용변조3경우를 구분. 파일 일치만으로 terminal·복원 성공을 판정하지 않음 |
| ZIP·복원 | 모든 멤버를 다시 읽어 원본과 바이트 일치 확인. 정상044 복원본은 사용자가 제공했던 해시 그대로. 실제 SD 적용/복원은 사용자 관측 대기 |

원래 초기화·타이머·저장 알고리즘의 오류 경계는 그대로다. 새 선행 표식 대기2초는 부팅/초기화 구간에 포함된다. 저장7×500ms는 기존 writer 예산에 포함된다. 전체 표시 대기는 모델상5.5초이며 실제 표시 가독성·전기 타이밍·벽시계 종료를 보증하지 않는다. 본체 시작부터90초 관측 후 전원을 끄는 기준은 사용자 시험 절차다.

## 산출물과 보존

- 후보 SDREPORT083: **132552바이트**, SHA `60d5ffcf283bdd1a69a62d8baac3f4f1dfad06c2562888c55e0491968663d91b`.
- `FXPAK-SDREPORT083-TRIAL.zip`:176727바이트, SHA `a37f26dca1476b5364bbf6cceb89eae07a2c8b26cf84a8bcab129522d6a9c293`. test와restore를 구분하며 둘 다 firmware.stm 한 파일이다. 기본 FPGA·메뉴·게임·세이브는 들어 있지 않다.
- `FXPAK-SDREPORT083-SOURCE.zip`:8593789바이트, SHA `e714732d336bda93ecf065a4b540e3075277fcf14a2e0b873d3c48a40de02268`. 실제 준비 소스와 라이선스·빌드 도구·소비한 생성 헤더를 포함한다.
- 정상044 복원:169056바이트, SHA `1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b`. HW002성공125260바이트 파일과 구별한다. 없는 백업명을 다시 요구하지 않는다.
- 최종 normal-03/negative4종-03/ARM01/package-02. 동결2119파일 manifest SHA `4b60051cd38f38cb9ef48ed20cbe918aed1c8e265bda58df1c6ebca58e0723df`. [메타데이터](report-observation083-verification.json)와 [검증기](../tools/verify_nes_report083.py)에서 확인한다. 기존082 verifier도 통과했다.

첫 no-early-marker-02는 잘못된 변이를 GPIO 보호가 더 일찍 거부했는데 결과 수집기가 다른 assertion 문구를 기대했다. 수집기 기대만 고쳐03에서 확인했다. package-01은 Make가 갱신한 `src/.ARG_VERSION` 캐시 차이를 거부했다. 정확한083 문자열을 별도 검사하고 나머지 소스 해시를 유지한 package-02만 최종이다. Make 최초 의존성 실패/재시도 로그와 이전 실행도 보존했다. 생산 기능 실패로 오인하지 않는다.

완료한 freeze/update 스크립트 재실행과044–083 동결 증거 편집은 금지한다. 공개 Git에는 텍스트 소스·가이드·요약만 포함하며 ZIP/펌웨어/사용자 백업/원문 로그는 별도 로컬 증거에 둔다. 새 RTL/Questa/fit/ASM/CF68 쌍은 만들지 않았다.

## 다음 입력과 완료 조건

다음은 사용자가083을 한 번 실행하여 **전원 직전부터의 TV 영상, 새 HW083nnn.TXT 또는 파일 없음, 정상044 복원 후 메뉴/GBC 결과**를 전달하는 것이다. 표식 없음은 적용·startup·mini·초기표시 범위이고,1A만 있으면 초기화 범위,1B 이후면 mount/후속 범위로 좁힌다. 마지막 표식은 다음 작업의 예고이므로 정확한 원인 코드로 바꾸어 해석하지 않는다.

이번 완료 범위는 보고서 관측 시험의 코드·오프라인 패키지다. P1의 실물 가독성/저장과 P3의 실제 복원 확인은 대기한다. CF68 제한 적재·전체 비교·STOP·메뉴 복귀 시험과 전체 NES 게임/오디오/입력은 별도다. 준비도4완료7부분1미완료를 자동 상향하지 않는다.

새 결과를 받으면 `tools/check_sdreport083.py <TXT>`로 전체 내용을 확인하고 영상 순서를 대조한 뒤 필요한 고장 경계만 수정한다. 같은074시험, LED, 분해, PC USB, 이미 받은 파일·확인한 부품을 반복 요구하지 않는다. 전체 SD/세이브 독립 백업은 사용자 수행 항목이며, 보유한 firmware044 사본이 전체 SD 백업을 대신하지 않는다.
