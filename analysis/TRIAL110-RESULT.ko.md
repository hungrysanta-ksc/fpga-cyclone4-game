# NES110 실기 조건 판정과 제한 시험 선택안

109의 파일 조합을 유지하면서, 미확인 전기 조건을 남긴 제한 기능 시험과 전 범위 규격 입증을 구분했다. **제한 시험 제안과 검토용 자료는 준비했지만, 사용자 선택과 실기 실행은 아직 미완료**다. 현재 E1/E2·설치·실기승인은false다.

## 새로 구체화한 근거

|근거|확인한 내용|잘못 대체하면 안 되는 항목|
|---|---|---|
|STM32F401 RM0368 Rev6 §6.2.7|HSE 고장 검출 시 HSI 전환/NMI, CSSC 처리 의미|고장부터 PA1 출력까지의 MCU 최악 실행시간|
|STM32F4 UM1840 Rev8 Table35|CSS 검출시간을 구현/클록 주파수 의존으로 분류|F401에 대한 특정ns/µs 상한. 계열 공통 설명이므로RM0368보다 우선하지 않음|
|Cyclone IV Handbook Vol1 §8 PS timing Table8-12|nCONFIG LOW→nSTATUS/CONF_DONE LOW 최대500ns, nCONFIG LOW 펄스 최소500ns|500ns를 사용자I/O high-Z나RAM CE HIGH 최대시간으로 전용 금지|
|동일 Handbook configuration 설명|설정 전/중 사용자I/O 비구동·내부 약한pull-up|보드 부하·전압·누설을 포함한 CE 상승시간|
|고정ISSI EBLL RevD3 p10/19/21/22|tCEM은refresh와관련, BLL VDD/VDDQ2.7–3.6V, 입력/시험조건 정의|8µs위반을 허용하거나 물리손상이 절대없다는 주장|

[ST RM0368](https://www.st.com/resource/en/reference_manual/rm0368-stm32f401xbc-and-stm32f401xde-advanced-armbased-32bit-mcus-stmicroelectronics.pdf), [ST UM1840](https://www.st.com/resource/en/user_manual/dm00148308-stm32f4-series-safety-manual-stmicroelectronics.pdf), [Intel Cyclone IV Handbook](https://cdrdv2-public.intel.com/653974/cyclone4-handbook.pdf), [ISSI EBLL](https://www.issi.com/WW/pdf/66-67WVE4M16EALL-BLL-CLL.pdf).

Intel/ISSI 직접PDF 요청은403이었다. Intel 내용은 공식도메인 검색색인의 PS표/설명을 확인했고, ISSI는 기존 고정 원본/추출문을 재사용했다. Intel 전체PDF를 새로 대조한 것처럼 기록하지 않는다. UM1840의 일반 초기화 문구를 코드에 옮기지 않고 실제F401 RM의 RCC_CR.CSSON을 유지한다. 같은부품/구형기판설계 조사는 반복하지 않았다.

## 판정

8µs 차단을 주장하려면 이미 경과한 CE LOW 시간에 HSE 고장 감지, NMI 진입과 PA1 출력, nCONFIG에서 I/O 해제, CE 전압 상승 시간을 모두 더해야 한다. 현재 각 단계의 보드 상한이 없어 합계를 확정할 수 없다.108/109의 호스트 모델이나 ARM store15개를 시간으로 환산하지 않는다. 두 클록 정지·locked HIGH에서 CE LOW9µs였던 반례도 유지한다.

E1은 전압·부하·PCB 및16조건의 물리 검증이 미완료다. E2는 HSE 단독 고장 뒤 소프트웨어 종료가 구현됐지만,8µs 차단과 공통 고장 보호는 미완료다. HSE가 정상인 FPGA 내부 정지, CPU/버스 정지, 공통 전원 상실을 CSS 보호 범위로 확장하지 않는다.

개발상 권장안은 **정상 전원·80KiB·1회·고장 주입 없는 기능 시험**이다. E1/E2 통과 선언이 아니라 미확인 항목을 남긴 범위 변경 제안이다. 기존 실기 진입 조건과 달라 사용자 선택을 요청했다. PR 병합을 이 선택에 대한 동의로 취급하지 않는다. [검토안과 복원 절차](../docs/nes-trial110-review.ko.md)에 완료·부분 관측·실패 판정을 구체화했다.

## 산출물과 작업 의미

검토 전용 ZIP에는109 조합에서 고른80KiB 시험6역할과044 복원3역할을 분리했다.96KiB 표식과 입력은 제외하고 ‘설치 금지’를 표시했다. 모든 ZIP 항목을 원본과 대조한다. 아직 실행용 패키지로 제공하지 않았으며, 펌웨어/FPGA 바이트와 기존109 manifest는 그대로다. 문서와 파일 대조를 새 펌웨어 시험 건수로 집계하지 않는다.

이번 작업은 실기 검증·배포 준비의 의사결정이다. 회로 자료나 계측 없이 닫을 수 없는 조건을 계속 재검사하는 대신, 선택할 수 있는 시험 범위와 복원 제약으로 정리했다. 코어 배선·게임 기능·호환성·실기 성공을 추가한 것은 아니다.

## 다음 행동

제한 시험을 선택하면 해당 사용자 메시지를 근거로 기록하고80KiB 실행용 패키지와 정확044 복원을 제공한다. E1/E2·8µs·전체NES 완성 여부는 별도로 미완료 상태를 유지한다. 보류를 선택하면 패키지를 발행하지 않고 기존107의 전원·IO·CE 계측 요구에 따라 근거를 확보한다. 응답이 없거나 단순히 ‘머지/계속’이라고 하면 동의를 추정하지 않는다.

새 C/RTL/ARM/fit/STA/ASM/Questa 실행과 실기는 없다.084/092 성공, SMB3(J) mapper4/384KiB 첫 목표, 준비도4완료/7부분/1미완료를 보존한다.
