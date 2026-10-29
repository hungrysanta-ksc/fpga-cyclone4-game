# NROM462: 실제 ARM 메뉴 loader의 잘못된 입력 차단

418 firmware의 실제 `nes_menu_sd_probe` ELF 기계어 전체가 `firmware.stm`의 같은 주소에 일치함을 확인한 뒤 Cortex-M4 Unicorn에서 메뉴 진입·헤더 검사 분기를 실행했다. FatFS 파일 호출과 reset·guard·checkpoint 및 하드웨어 호출은 모델이다. 보고서 구조체 필드 배치는 ELF DWARF로 확인했다.

잘못된 magic·mapper·수직 미러링·trainer·NES2·CHR RAM·파일 길이 7종은 실제 ARM 코드에서 `NES_MCU_LOAD_HEADER`로 종료됐고, FPGA 프로그래머·전송·base token 함수에 도달하지 않았다. 이 반환값의 true는 안전하게 메뉴 경로로 돌아갈 수 있다는 뜻이며 ROM 실행 성공이 아니다. 정상 fixture 대조는 파일 전체를 읽어 CRC를 계산하고 seek한 뒤 프로그래머 진입점까지 도달했으며, 실제 설정 전에 의도적으로 시험을 끝냈다. 이를 통해 잘못된 입력이 프로그래머에 들어가지 않는 검사 경계가 실제로 도달 가능한 경로임을 확인했다.

`analysis/nrom462-preflight.json`과 `probes/nes-nrom462`에 각 입력·호출 결과를 보존한다. 실제 SD/FatFS, ARM GPIO·IRQ, FPGA 설정·DONE, base/menu 복구나 60fps는 이 시험의 범위 밖이다. 457 timing/IO의 물리 승인도 여전히 열려 있다.
