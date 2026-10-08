# NES087: 메모리 비활성 기준 클록 관측 회로

## 작업 목표

기존 base의 명령FE를 근거 없이 실기에 적용하지 않고, PSRAM 접근 없이 기준 클록을 관측할 소스가 명확한 경로를 만든다. PR37 병합과 master `4017a50d716474df76e43e2698feb685fbb6f8c1`에서 기존 head 도달을 확인했다.

## 작업 내용

087은 메모리 접근 없이 RESET-held 기준 클록을 관측할 별도 CF87 회로다. 20MHz 기본800만 주기1경우와3주파수 축소 구간·고장 대조3개, 새 fit/내부STA/배선 감사를 통과했다. 10제어핀 비활성·32데이터핀 출력 차단을 배선 결과에서도 확인했다. 실제 MCU GPIO/TXT 통합·ARM/ASM·실기 패키지는 다음 작업이며 CF86 자체와084 성공 결과는 유지한다.

기존 base90개를 조사한 결과88개는18바이트 fixture이고 실제 수신 파일의2사본 외에 빌드 대응 근거를 찾지 못했다. CF87은 PLL·메모리 controller·RUN 없이 CLKIN800만 주기 동안SNES_SYSCLK/16 rising edge를 계수한다. C0의16바이트 snapshot에 구간 순번·count·window·분주값·현재/이력 flags를 함께 고정한다. 알려지지 않은254개 명령·부분frame·과다읽기는 메모리 출력을 바꾸지 않는다.

## 작업 결과

**이번 관측 RTL·새 배치 검증 목표는 달성했다. 사용자에게 전달할 TXT 수집 패키지는 아직 미완료다.** 337LE/27LAB/247registers/메모리0/PLL0/135물리핀, 내부3corner18summary 최소0.187ns다. 예외 제거 후 inter-clock6경로는 모두 첫 동기화 FF뿐이고,10메모리/버스 제어는HIGH·32데이터 출력은disabled다. 구성 이후 양클록 정지에서도 메모리 비활성을 확인했다. CF86의 active write 중단 문제를 해결했다는 뜻이 아니다.

실제 기본창20MHz에서1250000회 계수·읽는 도중 publish되어도 일관된 snapshot·254개 명령 거부·양클록 정지를 통과했다. 20/22/약21.477MHz 축소80000주기에서12500/13750/13424회 계수와 완전 부재구간/재개 flags를 통과했다. same-clock·live-snapshot·memory-enable 대조는 각각 부재 오판·섞인 snapshot·메모리 활성화 오류를 검출했다.

normal02의 다음22MHz 기본창은 TB의1ps 시간 양자화를 무시한 기대값 때문에 실패했다(1375017 vs1375000). 이 실패를 보존하고 기대값 계산을 실제 stimulus 주기로 수정했다. 전체3주파수 기본창 성공으로 표시하지 않는다. 첫 compile 문법/timeout 경고 및 같은 클록 대조에서 더 이른 올바른 실패가 나온 수집기 기대 오류도 보존했다. RTL은 최종fit/전체창20MHz/축소시험 사이 동일하다.

외부SPI3입력4경로/1출력2경로, 아날로그/구성 전환/RESET 소유권과 실제 클록 가용성은 미확인이다. MCU_RDY는 서비스 표식이고 valid는 구간 완료이며 둘 다 기준 클록 PASS가 아니다. 가정8MHz로 환산한 값과 실측값을 구분한다. [계약·응답·다음 완료 조건](../docs/nes-clock-observation087-contract.ko.md)에 자세히 기록했다.

다음은 실제 bounded C GPIO reader와084 관측→RAM보관→mini복귀→SD TXT/화면 session, 같은 CF87 fit의ASM/ARM/정상044복원 패키지다. 사용자에게 그 패키지의 새TXT/영상만 요청한다. 성공한084 저장·복원 시험을 반복하거나 부품/LED/분해/PCUSB를 묻지 않는다. CF86 외부타이밍/비동기 차단·최신 코어MCU/전체SPI는 별도다.

동결 `probes/nes-clock-observation087/evidence/` 458파일, manifest `2b13e7bf14b1ed1e0d5c4230f6ee9ed8600fb73f1ed82aa96b73a748ba604d76`. [메타데이터](clock-observation087-verification.json)와 verifier087을 사용한다. 완료된 finalizer나044–086 archive를 다시 쓰지 않는다. 준비도4완료/7부분/1미완료, installable=false.
