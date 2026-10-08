# CF86 전송 재생095의 조건

094 생산 C와086 fit03의 생산 RTL은 변경하지 않는다. 호스트 카드/FatFS·구성·lower READY는 모델이다.250ns guard 비용만 명시적으로 더하고 나머지 C 실행/인터럽트/SD 지연은 실제 CPU 시간으로 주장하지 않는다. MISO는 delay callback이 아니라 guard 이후 C가 샘플한 뒤의 SCK 하강 지점에서 기록한다. 같은 시각까지 다른 모델 시간이 흐르지 않음을 캡처 검사로 확인한다.

정상 전체 재생은8MHz memory와20MHz reference의 고정 이상적 클록, reset 불변 조건이다. guard의14레지스터/34비트 목록은 실제 생산 소스 선언과 대조한다. qualification 이후 모든 상태 및 두 클록 위상이4000ns 후 같고 X가 없으며 allow=1/fault=0이어야 한다. 동일 상태·동일 미래 주기 입력에 대한 결정적 반복을 사용한다. 생산 guard에는 SPI/주소/데이터 입력이 없으므로 전송 내용에 의존하지 않는다.

첫1024프레임 이후에만 guard 포트를 별도 표현식으로 분리하여 두 guard 클록을 정지한다. loader/SPI/PSRAM8MHz는 정지하지 않는다. 정상 종료까지 guard 출력이 유지되는 조건부 모델이며 실제 장치의 클록 고장을 대신하지 않는다. `--guard-fold 0`은 전체 실제 guard 실행 경로다. 기존 RESET-held H1/legacy 도메인 정지도 결과에 명시한다. STOP 이후 ARM base/메뉴 복귀는 재생하지 않는다.

raw-lock 고장 trace101/106은 별도 testbench에서 실제 guard, 원래 포트와 클록을 사용한다. 모델 C에 주어진 RDY=0 전제가 RTL 핀 차단과 맞는지 확인하고, 고장 제거 대조에서 전제 불일치를 검출한다. 이 시험은 독립적으로 캡처한 파형 비교이며 C가 RTL 응답을 실시간 소비하는 co-simulation은 아니다. 단독클록 정지/두클록 동시정지/후반부 고장까지 일반화하지 않는다.

재현 순서: 비공개094 `host04`를 `nes_session095_capture.py --baseline <경로> --gcc <gcc> --out <새 경로>`로 캡처한다. `run_nes_session095.ps1`에 기존 FLOAT wrapper, QuestaBin, HostRun, 동결086 FpgaEvidence와 새 Out을 지정한다. Case는fine_x/banks32, ParkLegacy=1, GuardFold=1이다. LimitFrames로 전제 점검을 먼저 하고 전체 실행에서는0을 사용한다. response/guard-proof 변조는 각 새 경로에서 실행한다. 고장은 `nes_session095_fault_capture.py`와 `run_nes_session095_fault.ps1`을 사용한다. 현재1-seat FLOAT를 순차 실행하고 다른 세션의 서버를 중단하지 않는다.

보존용 검사는 `python tools/verify_nes_replay095.py --evidence <동결095 evidence>`다. 단독 공개 clone에는 비공개 C/fit 증거와 도구가 없으므로 동결 재검증을 완전 공개 재현이라고 표현하지 않는다. 다음 실제 SD/config/시간·소유권 통합이 통과해야 쌍 이미지 작업으로 넘어간다.
