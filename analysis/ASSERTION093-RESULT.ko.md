# CF86 비동기 차단 경로 분석093

## 작업 목표

PR42 병합(master `02ccce30618a19ffebe44421722db4e74fe660d7`)을 확인한 뒤, 실제 기준클록 가용성092 근거를 CF86 보호 검토에 반영하고 미확인 비동기 차단 경로를 수치로 추적한다. 실패 처리 범위를 정해 최신MCU/전체세션 통합으로 진행할 수 있게 한다.

## 작업 내용

CF86의 고정 fit을 복사해3개 코너 VO/SDF를 생성하고, 클록 없이 비동기 clear와 조합 논리만 지나는264경로를 분석했다. 고장/qualification Q 이후 최대23.699ns, CE 최대21.080ns이며 실제 export 변조4개를 검출했다.092 기준클록 실기 활동은 유지하고, 두 클록 동시 정지/전기 승인/최신MCU·전체세션은 별도 미완료로 남긴다.

| SDF 코너 | Q→메모리 제어/데이터 출력 최대 | Q→CE 최대 | 경로 |
| --- | ---: | ---: | ---: |
| slow 1.2V 85°C |23.699ns|21.080ns|88|
| slow 1.2V 0°C |21.672ns|19.665ns|88|
| fast 1.2V 0°C |11.732ns|9.701ns|88|

각88경로는 ref_fault/mem_fault/ref_qualified/mem_qualified 네 출발점과 CE2/OE/WE/byte2/data16개의22출력 조합이다. 데이터 출력의 경로 끝은 모두 OE→O이며, 각 경로에 memory_release[1]의 clrn→q가 있다. 상승/하강·min/typ/max 중 큰 값을 취하고 PORT+IOPATH를 합산했다. 조합·비동기clear 외의 clock-to-Q/RAM/PLL은 통과시키지 않는다. 따라서 클록이 멈췄을 때 일반 FF 동작으로 차단된 것처럼 잘못 계산하지 않는다. 각 코너8529arcs/1328비동기FF를 파싱하며 최장 경로의 모든 배선 PORT에 실제 주석이 있다.

실제 export에서 비동기 IOPATH 제거, clear 지연100ns 증가,1ps→1ns 단위 변조, memory_release[1] clear 연결 해제의4대조가 모두 거부됐다.100ns 전파 할당은 분석 도구의 검출 기준이며 PSRAM 데이터시트 규격이 아니다.

원본086 fit03의 모든 source 및 복사입력 해시를 확인했다. EDA는 복사본의 board.qsf에 정확한4개 버전/출력 설정을 추가하고 db/board.cmp.hdb·cmp.rdb를 변경했다. 원본은 그대로다. 초기 작업경로 오류, parser의 비대상 PORT/RAM/상수셀 처리 오류, EDA 변경 허용 목록/QSF suffix 검사의 첫 실패를 보존했다. 마지막 normal03/causal01이 최종 근거이며 이전 snapshot을 섞지 않는다.

## 작업 결과

**이번 목표인 비동기 차단 지연의 SDF 추출·재현 검사와 고장 범위 정리는 달성했다.** [고장 정책093](../docs/nes-fault-policy093.ko.md)에 단일 클록 조건부 보호, 동시 정지 미보호, 중단 이미지 무효화·전체 재적재/비교, 호스트 실패 유지 조건을 명시했다. 최신MCU가 실제로 이 정책을 구현했다고 주장하지 않는다.

23.699ns는 고장 검출을 포함하지 않는 구조적 SDF 합산이다. 실제 논리 감응성, SDF 파형 실행, CDC metastability, 전압/부하/PCB·보드 전기 승인은 아니다. 기존086의 내부STA 최소0.158ns·128정지/4대조·외부3168경로는 이번에 재실행하지 않고 같은 생산 회로의 기존 근거로 유지한다. 두 클록 동시 정지/locked HIGH의9µs CE 반례도 유지한다.092 활동 관측으로 고장 시 독립성을 증명할 수 없다.

다음 목표는 **실제 MCU와 CF86의 ID/RDY/고장 뒤 세션 무효화 연결**이다. ID 숫자만 바꾸지 말고 클록 재개/PLL 복귀로 적재·CHECK 승인이 되살아나지 않는지 검사한 뒤80/96KiB 전체핀 적재·비교·STOP 및 같은fit ASM/최종ARM/044복원 쌍으로 진행한다. 외부 IO·공통고장 미해소를 명시하며 아직 실기 패키지를 내지 않는다. 기존084·092성공과 SMB3(J)/mapper4/384KiB첫목표를 보존한다.

새 RTL/fit/STA/ARM/Questa/설치 패키지는 없다. [메타데이터](assertion093-verification.json). 동결592파일 manifest `c33bf3a1f24eb45135676628defe791229b1aa670c7a03cdd9410d5cc5a19de8`. 전체 준비도4완료/7부분/1미완료, installable=false 유지.

## 재현

`python -B tools/run_nes_assert093.py --fit <frozen086/fit03> --out <fresh ASCII directory> --quartus-bin <Quartus bin64>`

`python -B tools/test_nes_assert093.py --export <above output> --out <fresh controls directory>`

`python -B tools/verify_nes_assert093.py --evidence <frozen093 evidence>`

재현은 새 출력 디렉터리에만 한다. 완료 finalizer나044–093동결 경로를 다시 쓰지 않는다.
