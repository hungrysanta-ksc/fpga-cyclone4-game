# NROM469: 467 전달본의 실제 표시·입력·복구 결과

사용자가 2026-10-29에 전달한 새 로그3개와 IMG_3720.MOV를 보존했다. 앞서468에 받은 잘못된 과거 로그와 구분한다. 사용자는 A를 누르면 붉은 격자로 바뀌고 유지되며 놓으면 파란 격자로 돌아오고 약60초 뒤 메뉴 복귀가 정상이라고 보고했다. 56.07초 영상의 표본 프레임에서도 파랑·빨강·파랑을 확인했다. 영상의 FPS는 카메라 촬영률이며 표시 갱신률이 아니다. 원본은 probes/nes-nrom469/hardware01, 재현 분석은 analysis/nrom469-hardware.json에 있다.

FPGA observed ID78, 적재393,216B·비교393,216B, verified=1·verify_error=0·START·run_passed=1·STOP·base 복구·safe_to_reload=1을 확인했다. progress에는 BASE_DONE_HIGH, BASE_TOKEN_RESULT=165/165, MENU_PREPARED가 있으며 실제 메뉴 복귀는 사용자 관찰과 결합한다. 로그의 board_expected_hex=74와 candidate=NES-GAME-227은 이전 report 문자열이 남은 것이며 실제 observed78과 구분한다. 이것만으로 wrong FPGA라고 판정하지 않는다.

표시 구간 DISPLAY_NEXT 227,870ms→DISPLAY_STOPPED 287,930ms는60.06초다. trace_commits/native_frames899, 송신·retire 각9,933, trace_aborts0·sink/video error0이다. 표시 완료 평균은14.968회/초이며 60fps에 도달하지 않았다. 이것은 정적인 자체 패턴 workload의 표시 완료율이며 NES 내부 실행 속도·상용 게임·무누락 capture 보장은 아니다. 순차 수신/준비/표시 대기는10ms tick로33.76s/12.22s/13.50s이며 callback·SPI 대기 포함 값으로 CPU 순수 시간으로 합산하거나 다른 workload와 비교하지 않는다.

마지막 native_result1은 세션 deadline이다. receiver_error23은 D1 callback false 또는 CRC 불일치를 합친 코드이며 callback은 deadline guard로 false를 반환할 수 있다. 따라서 독립적인 CRC 오류라고 단정하지 않으며 이후 종료 진단을 분리할 항목으로 남긴다. pad_trace_count0 역시 fixture가 A 첫 bit만 읽고 기록기는 완료된8bit read를 기다리는 구조와 구분한다. A 입력 효과의 근거는 영상·사용자 관찰이다.

이번 결과로 이 보드에서 제한 NROM 설정·적재/검증·표시·A 입력·자동 STOP/base/menu 복귀의 첫 실물 경로는 통과로 기록한다. 픽셀 단위 기준 비교·음성·재시작/전원 재부팅·장시간 안정성·전체 CDC/IO/STA·60fps는 별도다. 같은 제한 smoke를 파일명 변경만으로 다시 요구하지 않는다.

## 다음 전달본의 identity

ARM 빌더에 TrialLabel을 추가하고 기본 nrom469를 적용했다. 별도 소스 사본에서3개 로그 이름과 expected ID78, candidate 이름, 실행 marker를 함께 생성한다. 다음 빌드 기준은 NES NROM 469.nh1과 nes-progress-nrom469.txt·nes-game-last-nrom469.txt·nes-budget-nrom469.txt다. 생성 소스 대조와 PowerShell 구문 검사를 통과했으며 실제 ARM 재링크·새 설치본 전달은 아직 수행하지 않았다. 기존467 전달본은 기존227 로그 이름을 그대로 사용한다. 새 기능 전달 시 해당 실행 번호를 지정하고 packaging manifest와 marker를 함께 갱신해야 한다.
