# NES067 진단 메모리 준비·유지 구간 결과

이번 범위인 **진단 전용 준비/유지 회로와 지연 반례 해소·회귀·새 내부 fit/STA**를 달성했다. 외부 IO 승인·전체 SPI 회귀·새 ARM/설치 쌍·실기 실행은 남는다. PR21 병합 `ea6d576a6df176eabde7744a851168c515040191` 기준이며 기존061/065/066 및044/GBC는 보존했다.

- 쓰기 전에 SETUP1클록, 읽기 전에 SETUP1클록을 추가했다. 읽기 샘플 뒤 CE/OE를 HOLD1클록 유지하고 핀 해제 뒤 완료 응답을 낸다. 쓰기 완료는 RELEASE 뒤 count에 반영한다.8MHz/125ns 명목 구간이며 실제 배선 min/max 승인이 아니다.
- 네 정상 지연 경우에서 총344064바이트 쓰기·같은 수 읽기와 모든 byte/tag를 비교했다.80KiB 세 경우와96KiB 한 경우, 각9회 오류/리셋 취소를 확인했다. 주소2ns 지연 반례가 통과하고, 가정20ns 주소/데이터/수신 지연도 통과했다. 연속 범위 검증은 아니다.
- 쓰기SETUP 제거,읽기SETUP 제거,읽기HOLD 제거의 세 변형은 정확한 주소/샘플 유지 assertion에서 실패했다. 보호 구간을 넘는126ns 주소 지연도 의도한 실패를 검출했다. 종료 코드만으로 통과 처리하지 않았다.
- 실제060 C GPIO의 bounded load33184샘플/29024응답 비트/256pin bytes와CHECK49472샘플/43288비트/256검증 byte가 새067 물리 top에서 일치했다. CHECK의96KiB 준비는TB loader 핀 주입이다. 전체SPI80/96KiB 성공 세션이 아니다. PLL 상실·클록 정지+reset 해제·복구·START 두 장벽을 유지했다.
- 새 Standard25.1 map/fit/STA: **2372LE/184LAB/1466registers/44M9K/135physical pins/0virtual/PLL1**.3corner의30 내부 timing summary 통과. 최소 setup2.395ns,hold0.150ns,recovery4.838ns,removal1.139ns,pulse5.605ns. 외부 입력54포트744경로,출력49포트1355경로는 미제약이며 외부 IO 승인으로 쓰지 않는다.
- 단위 정상·파형·fit의 실행 생성RTL 해시가 일치한다. 기존 전체 코어059959LAB/4여유·마지막8프레임은 새로 실행하지 않았다. ARM/ASM/압축 패키지도 새로 만들지 않았다. FPGA식별CF67과 기존CF61 펌웨어를 섞지 않는다.

원시 근거는 로컬 `probes/nes-diag-memory-067/evidence/`의401파일 manifest로 동결했다.112개 fit DB 파일도 private archive에 포함한다. [기계 판독 요약](diag-memory-verification.json)의 digest와 공개 verifier로 대조했다. 첫 정상 unit/fit/wave는 모두 통과했으며 의도한 네 실패 대조를 보존한다. 라이선스 작업 두 개는 정상 종료하고 임시 서버를 정리했다.

준비도는 기존 **완료5/부분6/미완료1**을 유지한다. 부품 식별은 끝났지만 H06 외부 IO 승인,전원 tPU·클록 정지 시 tCEM,최종067 전체SPI/MCU·동일 쌍,실제SD/base/menu·백업/복원 및 관측은 미완료다. installable=false. 다음 순서·정확한 변경 지점·검증 중단 조건은 [Sol 인계](../docs/development/NES-067-SOL-HANDOFF.ko.md),[계약/재현](../docs/nes-diag-memory-contract.md)에 남겼다.
