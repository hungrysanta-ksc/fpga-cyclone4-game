# NES167 CHECK 판정·반영 단계 분리

NES167 CHECK의 오류 판정(C2)과 카운터 반영(C3)을 분리해 카운터 경로+1.011ns·판정+0.699ns를 확보했다. 기능·SPI 응답은 통과했으나 전체 setup은 로더 fault→명령 자격-0.190ns, 적재 카운터-0.041ns여서 후보는 미채택이다. 새 실기 ZIP은 없고 승인 FPGA는boundary165/map02를 유지한다.

## 변경 계약

기존 C0 캡처→C1 명령 판정→C2 실행에서 **CHECK 카운터 효과만 C3로 이동**했다. C2는 live 오류 검사를 통과한 clear/inc를 저장하고 C3에서 반영한다.168MHz 기준 약5.95ns가 추가된다. RAM 쓰기·READ·RUN·STOP 실행 펄스와 데이터·오류 판정 edge는 그대로다. 같은 edge 등가라고 주장하지 않는다.

C2에서 hard fault9, 잘못된 응답7, SS 재활성1이 있으면 승인하지 않는다. C2에 이미 승인된 카운터 효과는 C3 직전 오류가 생겨도 반영한다. 이는 이미 승인된 명령의 메타데이터이며 이후 명령은 fault로 차단된다. **비동기 reset은 승인 큐와 카운터를 즉시 취소**한다. C3까지 SS 겹침 검사를 확장해 중간에 새 명령이 끼어들 수 없게 했다. 명령 수신 순간의 잘못된 응답을 이전 값으로 대체하거나 오류를 늦추지 않는다.

현재167 MCU의 실제 전송 엔진은84MHz/32 mode0 SPI, SS high 및 setup 최소2µs를 요청한다. CHECK READ는 ready/busy/done을 확인하고 실제 바이트를 비교한 뒤 ACK한다. 이 간격에서 counter·carry·주소 비교가 다음 응답 snapshot 전에 안정되므로 명령/CRC/응답 ID **0x74를 유지**했다.219개 실제 SPI 파형의14,016비트 MISO가 기존 구현과 일치했다. 이 근거는 RTL 시뮬레이션과 MCU 소스 확인이며 실기 전기 신호 계측이 아니다.

## 검증과 배치 결과

|항목|결과|
|---|---|
|C2 승인/C3 카운터|1,048,576조건 통과|
|clear/inc × C2/C3 × 오류·reset|24경계 통과|
|실제 SPI 파형|219프레임/14,016비트 일치,100읽기·7ACK·19응답 손상·72취소·2겹침|
|잘못된 회로 검출|C2 fault 무시, C3 승인 취소, C3 SS 겹침 누락3종 검출|
|입력 재현|61파일 동일 재생성,60파일은pacing167/map04와 동일|
|전체 배치|14,964LE /963LAB /35M9K,용량 통과|
|CHECK 카운터|+1.011ns|
|C2 clear/inc 승인|각+0.699ns|
|전체 setup|**-0.190ns,실패**|
|적재 카운터|-0.041ns,실패|

3개 corner와4개 실제 클록의 setup/hold를 확인했다. seed·Standard Fit·SDC·클록·false-path·multicycle 예외는 바꾸지 않았다. 전체 FIT는 한 번 수행했다. 엄격한 개발 예산 보고서와 실제 클록 보고서를 따로 보존했다. 전체 타이밍이 실패했으므로 외부 IO/reset 재분석·ASM·패키지는 진행하지 않았다.

현재 최악 경로는 로더 fault→run_enable→check_active→body_causes→pending_causes다.5단계 논리, 데이터 지연6.043ns 중 배선4.214ns(70%)다. CHECK 경로 개선이 다른 영역의 배치까지 보장하지는 않는다. 전체 최선 후보는 여전히pacing167/map04의-0.003ns이며 이것도 승인되지 않았다.

첫 test01은 이전 같은-edge 벤치의 불일치 캐리 주입을 그대로 가져와 실패했다. C3는 C2에서 갱신된 캐리를 사용하므로, 실제 통신 간격에 맞는 안정된 캐리로 test02를 수정했다. 모든19비트 카운터 값·8패턴/오류 조합과 새 단계 경계 검사를 유지했다. 실패 원본과 실행 도구도 보존했다. 비교는 C2의 기존 상태 효과와 C3의 최종 카운터를 구분한다.

167 fill/export/arbiter, 전체 ARM 링크·스택 여유1076바이트, 기존 MCU/SNES45ACK·61184픽셀 근거는 바이트 확인으로 재사용했다. 이번에 게임·전체 ROM 쓰기를 다시 돌렸다는 뜻이 아니다. GBC·164 복원·세이브 SRAM은 보존한다.

## 다음 작업과 의미

CHECK 카운터는 더 작은 식으로 반복 배치하지 않는다. commitstage167/map01은 후속 구조 연구용이며 승인/최선 전체 타이밍 기준은 아니다. 남은 fault→run_enable→check_active→body_causes→pending_causes의5단계(배선70%)를 대상으로, SS 캡처 C0에서 원시 자격을 저장하고 이후 단계에서 명령 원인·오류를 판정하는 명시적 파이프라인을 설계한다. C0 관측 값, live fault 차단, STOP/write drain, 단계별 SS 겹침/reset, 실제2us 간격 및 응답 snapshot 호환성을 먼저 검증한다. 기존 loadcount167의 적재 산술 분리 결과는 재사용하되 새 SPI와 결합 경계는 검증한다. 그 구조 변경 뒤 한 번 FIT하고 실제 클록·조건부 IO/reset이 통과하면 기존167 MCU/영상 근거를 재사용해 패키지와 SMB3 실기로 간다.166·044·무변경 부팅·seed 순회는 반복하지 않는다.

이 작업은 영상 대기 수정판의 **FPGA 타이밍 장애를 줄이는 구현 작업**이다. 기능 계약과 CHECK 경로는 확보했지만 전체 배포 목표·실기 영상 복구는 미달이다. 사용자 추가 실기 시험은 아직 필요 없다.

재현: `nes_commitstage167.py --baseline <pacing167/map04> --out <새 ASCII 경로>`.
**생성 결과는 실험용이고 설치 승인본이 아니다.** [검증·해시](../analysis/commitstage167-verification.json) · [앞선 카운터 후보](nes-counterpulse167-contract.ko.md).
