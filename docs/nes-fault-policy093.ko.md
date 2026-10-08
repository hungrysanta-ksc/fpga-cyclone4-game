# CF86 메모리 진단의 고장 범위와 다음 통합 조건

093은 기존 CF86 회로의 지연 분석과 실패 처리 계약이다. 생산 RTL·MCU를 바꾸거나 새로운 실기 설치를 승인하지 않는다. [분석 결과](../analysis/ASSERTION093-RESULT.ko.md), [기존 CF86 계약](nes-clock086-contract.ko.md), [실기 관측092](../analysis/CLOCK-HARDWARE092-RESULT.ko.md)를 함께 사용한다.

## 확인된 것과 아직 가정인 것

| 항목 | 현재 근거 | 적용 한계 |
| --- | --- | --- |
| RESET 유지 중 SNES 기준 클록 | 사용자 보드의 CF87 실기에서 연속 두 구간 활동 확인 | 다른 실행·전원 이상·CLKIN 고장 시 독립성이나 절대 주파수를 증명하지 않음 |
| 한 클록 정지의 논리적 차단 | 기존086 디지털128경우, 감지 최대4374ns·CE LOW 최대3350ns | 8MHz 메모리와20/약21.477/22MHz reference 입력 모형의 결과 |
| 고장/qualification Q 이후 전파 | 같은086 fit에서 생성한3개 SDF 코너,264경로, 최대23.699ns | 조합 논리와 비동기 clear만 지나는 구조적 상한. 파형 시뮬레이션·논리 감응성·실측·보드 승인 아님 |
| 정상 외부 PSRAM 시간 | 기존086 FPGA3168경로, 각 PCB leg20ns+추가5ns 가정에서는 최소64.565ns | 가정값이며 실제 전압·부하·PCB 범위를 보장하지 않음. 각60ns 반례는−15.435ns |
| 두 클록 동시 정지, locked HIGH | 기존086 CE LOW9µs 반례 유지 | 보호되지 않음.092 활동 관측이나093 전파값으로 해소되지 않음 |

23.699ns는 **감지 레지스터 Q가 이미 변한 시점**부터의 SDF 합산이다. 동기화·감시 카운터·metastability·source clock-to-Q·PCB·PSRAM 출력 해제·전원 변동은 포함하지 않는다. 기존4374ns/3350ns에 단순 합산해 모든 조건의8µs 규격 승인으로 쓰지 않는다. 분석기의100ns는 오류 검출용 내부 전파 할당값이며 데이터시트 수치가 아니다.

## 실패 시 처리 계약

1. **한 클록만 멈추고 반대 클록이 계속 유효한 경우**를 조건부 보호 범위로 둔다. CF86은 memory_release의 비동기 차단, 메모리 영역의 동기 해제,1600클록 초기 대기를 유지한다. raw guard를 일반 데이터 경로에 다시 연결하지 않는다.
2. 읽기·쓰기 도중 감시 fault가 발생하면 적재 이미지와 CHECK 승인을 모두 무효로 본다. 쓰기 중간 차단은 해당 바이트의 올바른 값을 보장하지 않는다. ACK 재전송이나 클록 재개만으로 이어서 실행하지 않는다. 원인 해소 후 별도 새 세션의 FPGA 재구성→전체 ROM 재적재→전체 비교를 요구한다.
3. 기존 RTL sticky fault는 raw PLL lock 상실 또는 재구성으로 지워질 수 있다. 따라서 **호스트도 세션 실패를 유지**해야 하며, 뒤늦은 RDY/ID 복귀만으로 원래 이미지의 RUN을 허용하면 안 된다. 이 호스트 계약의 최신CF86 구현·통합 검증은 다음 작업이다.
4. **두 클록 동시 정지/전원·PLL 공통 고장**은 현재 보호 범위 밖이다. STM32의 느린 timeout이나 소프트웨어 nCONFIG 제어만으로8µs 보장을 주장하지 않는다. 무조건적인 보호를 요구하려면 독립된 시간 기준과 실제 비활성화 경로의 최악 지연 근거가 추가로 필요하다. 현재 이미지는 무조건적인 클록 고장 보호를 광고하거나 제품 승인으로 승격하지 않는다.
5. 공통 고장·전원 이상 뒤에는 현재 세션을 끝내고 정상044로 수동 복원하는 기존 절차를 사용한다. 실패한 공유 SPI/SD를 통해 화면·TXT·자동 메뉴 복원을 강행하지 않는다. 보호 종료와 사람이 읽을 결과는 별도 상태로 관리한다.

## 다음 구현을 끝내는 기준

다음은 또 다른 정보 수집 펌웨어가 아니라 **최신 보호 MCU와 CF86의 연결**이다.

- CF86 ID, 시작 RDY, RESET/USB 소유권, 실패 후 IO 금지를 실제 제품 호출 순서에 연결한다. 구형071/CF68 MCU와 CF86의 잘못된 조합은 계속 거부한다.
- CLKIN/reference 정지·재개, PLL 상실 후 RDY 재등장, DATA 응답 손실, CHECK/STOP 경계에서 세션 승인이 되살아나지 않는지 시험한다. ID 상수 변경만으로 통합 완료로 보지 않는다.
- 같은 최종 C가 만든80/96KiB 적재·전체 비교·STOP 파형을 CF86 핀 회로에 연결한다. 전체 길이와 마지막 ACK까지 확인한 후 같은 fit의 ASM/압축·최종 ARM·044 복원 파일을 묶는다.
- 정상 외부 IO 가정과 실제 승인에 남은 항목을 쌍 manifest에 남긴다. 범위가 해결되기 전에 자동 SD 설치나 사용자 실기 패키지를 만들지 않는다. 독립적으로 진행 가능한 MCU·전체 세션 검증은 계속한다.
- 성공한084 저장/메뉴/GBC·092 클록/저장/복원 시험, 부품 사진, 분해, LED, PC USB 질문을 반복하지 않는다. 첫 게임은 SMB3(J)/mapper4/384KiB이며 현재80/96KiB 진단의 성공을 게임 지원으로 확대하지 않는다.

## 재사용할 분석 원칙

Quartus의 recovery/removal 검토와 비동기 assertion의 여러 clear→Q 단계를 구별한다. 이번 도구는 기존 예외를 바꾸지 않고 같은 routed DB의 복사본에서 VO/SDF를 내보낸다. SDF의 PORT 배선 지연과 IOPATH 셀 지연을 정수ps로 더하고, 일반 clock-to-Q·RAM·PLL 통과는 차단한다. 상승/하강과 min/typ/max 중 큰 값을 취하므로 실제로 동시에 감응되지 않는 경로도 포함할 수 있다. 이 수치는 기능 시뮬레이션을 대체하지 않는다.

관련 도구의 공식 설명은 [Intel Timing Analyzer 리소스](https://www.intel.com/content/www/us/en/support/programmable/support-resources/design-software/sof-qts-timinganalyzer.html)와 [Standard Edition 타사 시뮬레이션 문서](https://www.intel.com/content/www/us/en/docs/programmable/683080/18-1/back-annotating-simulation-timing-data.html)를 참조한다. 이번 수치의 직접 근거는 로컬 Quartus25.1std가 생성한 세 코너 VO/SDF다.
