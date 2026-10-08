# NES086: 비동기 reset 경계 수정과 새 배치 검증

## 작업 목표

CF85의 새 기준 클록을 선언한 실제 배치에서 CDC/reset 경계를 검사하고, 발견된 직접 연결을 고쳐 같은 RTL의 기능·내부 타이밍을 검증한다. PR36 병합과 master `2995577f37280dbe23398ba39d5238b867f20366`에서 기존 head 도달을 확인했다.

## 작업 내용

086은 실제 CF85 배치에서 발견한 raw 감시 신호의 영역 간 직접 연결을 수정했다. CF86 동일 생산 입력16개로 새 fit/STA·CDC 감사와4 GPIO/128정지/130360응답 비트·보호 제거4개를 통과했다. 제약된 내부39 summary 최소0.158ns, 새 PSRAM3168경로의 가정상 최소64.565ns다. 외부 IO·비동기 clear 지연·실제 기준 클록/공통 고장·최신 MCU 쌍/전체 세션·실기는 미완료이며 설치 파일은 없다. 084 저장/화면/정상044복원·메뉴/GBC 성공은 유지한다.

CF85 fit01에서 ref fault/qualification이 일반 제어 FF까지 전달되며 최소−5.354ns가 나왔다. CF86은 기존 비동기 assert/2단 동기 해제 경계 뒤에서 초기 대기와 downstream reset을 생성한다. raw guard를 다시 OR하지 않는다. ID86을 부여하며 기존 MCU는 거부해야 한다. 예외는 첫 동기화 FF와 reset-release FF clear의3개뿐이며 실제 배선의36행을 전부 분류했다. 수정 전 실제 배선은 같은 감사에서 거부된다.

## 작업 결과

**이번 수정과 제약된 내부 타이밍 검증 목표는 달성했다. P2 전체/실기 준비는 미달성이다.** 3corner39 summary 양수, 최소0.158ns;2446LE/191LAB/1514regs/44M9K. 기능4경우·128고장·130360응답 비트·인과 대조4개 통과. 비동기 assert 제거 대조는 멈춘 메모리 클록에서 차단 실패를 검출한다. 최대 검출4.374µs/CE LOW3.350µs는 디지털 모형 값이다.

외부 input54포트744경로/output49포트1391경로는 미제약이다. 새3168경로 계산의64.565ns는 PCB각 leg20ns/추가5ns 가정이며 leg60ns 대조는−15.435ns다. 실제 PCB 승인·비동기 clear→Q 상한·MTBF는 확보하지 못했다. 두 클록 정지/locked HIGH의 CE9µs 반례를 유지한다. Quartus의 기존 RAM/포트/IO 경고를 보존했으며 경고0으로 보고하지 않는다.

보존 base 소스의 FE는96MHz에서96000000계수+1갱신 주기이나, 실제 사용자 binary와 소스의 동일성 및 RESET-held 기준 클록은 미확인이다. 다음은 기존 base provenance 또는 PSRAM 접근 전용 차단 상태의 자체 클록 관측, 외부 타이밍/공통 고장 정책, 이후 최신 MCU와 전체 SPI/동일 파일 쌍이다. 새로운 ARM·ASM·전체80/96KiB C SPI·실기·설치 패키지는 만들지 않았다.

재현·정확한 경계·실패 기록은 [계약](../docs/nes-clock086-contract.ko.md), [메타데이터](clock086-verification.json), 현재 HANDOFF를 따른다. 새 로컬 `probes/nes-clock086/evidence/` 1793파일, manifest `f210693b8ecb48392adc4ae535282c9e5252f9b3e833a4d3b24839192a388d54`. 수정 전 fit01/예외 전 fit02/최종fit03·감사 API 오류·음성 대조를 함께 보존했다. 완료된 finalizer와044–085 archive를 다시 쓰지 않는다. 준비도4완료/7부분/1미완료, installable=false.
