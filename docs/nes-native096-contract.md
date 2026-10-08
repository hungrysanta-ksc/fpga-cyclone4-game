# 실제 SD·구성 통합096의 검증 계약

입력은 동결094 `arm04/src`와 `host04`다. 과거 report-only 소스로 대신하지 않는다. 최종094 manifest 및 개별 입력 해시를 검사하고20 native 함수, checked programmer/RLE와 lower READY를 그대로 추출한다. `report_session078_host.c`의 카드 모델과094 GPIO/SPI 응답 모델을 재사용한다. production C9와094 ARM 일치가 필수다.

실행은 `python tools/test_nes_native096.py --evidence094 <094 evidence> --gcc <gcc.exe> --out <새 경로> --suite`다.96KiB/FAT32/SDSC 묶음은 `--case banks32 --fat32 --sdsc --suite`를 더한다. 교차 프로필은 각각 `--fat32`와 `--case banks32 --sdsc`로 정상만 실행한다. 매 실행은 새 디렉터리를 사용한다. 호스트 GCC와 비공개094 소스가 필요하다. 이 경로는 Questa/라이선스를 사용하지 않는다.

대조는 새 경로에서 `--mutation sd-crc --scenario 103`, `--mutation ready-wait --scenario 1012`, `--mutation config-run`, `--mutation failed-latch --scenario 1005`다. 성공 판정은 비정상 종료만이 아니라 `verify_nes_native096.py`가 확인하는 각 예상 assertion까지 포함한다. 최종 증거 검사는 `python tools/verify_nes_native096.py --evidence <096 evidence>`다. 아직 동결 전이면 `--runs-root <TEMP>`가 명명된 최종8실행을 검사한다.

정상/첫·중간·마지막 단계별 SD 고장과 기타15시나리오를 합쳐76경우씩 실행한다. CRC/카드/핀/시간 모델의 가정 아래 검사한 샘플이다. 임의 FAT 파손/임의 지연/모든 명령 위치/전원 초기화/물리 PSRAM·CDC·PLL에 확대하지 않는다. CMD24는 시험 파일 준비이고 측정 세션은 읽기 전용이다. 이미 초기화된 카드의 준비 seam을 세션 중 허용하지 않는다.

구성 파일은 escaped control/짧은 run/긴 run을 포함한1100바이트이며 모든1353출력 바이트를 대조한다. 실제 FPGA 파일 크기/내용/구성 소요시간은 다음 단계다. lower configuration pin 함수와 전송 macro 자체는 모델이므로 전기적 구성 성공으로 부르지 않는다. READY 지연은 실제 wait loop로 검사한다.

같은 모델 시간에 SD 핀125ns/구성 바이트1µs/timer조회1µs가 누적된다. frozen READY는 시간 진행을 멈추고 poll 제한으로 종료한다.60초 main/menu window와 진단 전송 전체 시간을 혼동하지 않는다. 메인 SRAM 메뉴 재적재/표시/RESET release/보고는096에서 실행하지 않으며 SRAM 호출 stub은 실행되면 실패한다.

이후 동일086 fit의 ASM/실제 압축 파일, 최종 main 경계, 같은 ARM/FPGA/044 복원 쌍을 확인한다. 생산 변경이 생기면 관련 ARM 및 파형 검증을 새로 판단한다.096 모델 시간을095 RTL 파형에 그대로 대응시킨 것으로 주장하지 않는다.044–096 동결 자료와 완료 finalizer를 변경/재실행하지 않는다.
