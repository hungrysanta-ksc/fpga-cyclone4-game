# NES414: 실제 run136·프로그래머 결합의 호스트 경계

412의 실제 227 loader·FatFS·FPGA 프로그래머에 407의 실제 `nes_run136.inc`와 227 `nes_run136.h`를 결합해 `run03` 9개 정상·오류 사례를 실행했다. 정상 사례에서 실제 `identify136`, `nes_rom_verified_start`, `run136`의 STOP, STOP 후 observer 반복 검사, screen/history/pad 처리 및 loader의 base 프로그래머 호출을 실행했다. 보고서의 START·STOP·passed, observer first/last/stopped와 screen/history/pad 유효 상태를 검사했다. 선택 테스트는 host C이며 synthetic FAT16·합성 설정 파일을 쓴다.

**native_session165, observer/screen/history/pad SPI 응답, GPIO·DONE·SPI·PSRAM과 IRQ는 모델이다.** 따라서 실제 표시 프레임, ARM 명령·IRQ, 실제 FPGA 또는 base 이미지 복구를 증명하지 않는다. STOP 오류와 base DONE 실패는 기존 사례에서 별도로 확인했다. `run01`은 이전 host fixture의 오래된 `nes_run136.h`가 먼저 선택되어 컴파일 실패했으며, 227 헤더를 명시한 `run02`와 보고서 검사를 추가한 최종 `run03`은 통과했다.

413은 412의 실제 프로그래머를 410의 RTL 공동 실행 fixture에 넣는 생성기를 추가했고 `combined-compile01`에서 DLL 컴파일만 확인했다. 실행 중인 411이 Starter 단일 seat를 사용하고 있으므로 **413 RTL 실행은 하지 않았고 PASS가 아니다**. 414의 실제 run136을 RTL에 추가하려면 410의 boot SPI만으로는 부족하다. 227 top은 observer(0x70 등), screen status(0x73), sink와 boot를 별도의 selected/MISO 소유자로 중재한다. 실제 `nes_run_observer134`, `nes_screen_status151` 및 native display 경계와 충돌·reset 소유권을 연결해야 한다. 414의 모델 observer를 실제 RTL 관측이라 부르지 않는다.

411은 별도 장시간 실행이며 2026-10-28 확인 시 180,224/393,216 DATA까지 진행, 전체 완료·readback·START·STOP 결과는 아직 없다. 그 실행은 412/414 변경 전 fixture이므로 이번 결합 결과를 411에 합산하지 않는다. ARM·IRQ·ROM 경쟁을 포함한 연속 프레임 계측과 MMC4/5의 같은 경계 Quartus Lite 전체 비용은 여전히 미측정이다. 기존 405 및 376의 비교와 제약을 유지한다.
