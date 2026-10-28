# NES423: NROM 후보의 진단용 ARM·FPGA·65816 산출물

419의 Lite routed DB에서 assembler 및 CPF로 SOF/RBF를 만들었다. 처음 227의 RLE 도구로 생성한 BI3를 독립 decoder로 확인하자 **510,856B RBF 전부가 일치하지만 마지막 FF 1B가 추가**됐다. 이 결과는 `fpga_nrom16.legacy.bi3`로 보존한다. 기존 도구는 파일 끝에서 연속 byte를 읽을 때 EOF 처리에 따라 마지막 값을 하나 더 내보낼 수 있다. 이 여분 byte가 실제 FPGA 설정에 영향을 주는지는 미검증이다.

별도 bounded-run encoder로 `fpga_nrom16.bi3`를 다시 만들고 독립 decoder가 RBF와 길이까지 정확히 일치함을 확인했다. 기존 생산 도구나 원본 파일은 수정하지 않았다. 418 ARM firmware의 메뉴 경로는 이 파일 이름을 가리킨다. 407의 FPGA SPI는 NROM 고정 ID `78`이고 418 loader는 이 ID와 NROM16 수평 header를 요구한다. 산출물 hash와 길이는 `analysis/nrom423-pair.json`에 고정한다.

419의 `sink-program.hex`는 실제 227의 65816 program source와 해시가 일치한다. Lite EDA가 내보낸 **기본 board.vo 한 개**에서 4,096B 65816 ROM atom을 읽어 예상 HEX와 일치함을 확인했다. 이는 세 코너 netlist·RBF 자체에서의 메모리 bit 추출 또는 실제 65816 표시 실행이 아니다. 기존 세 netlist 검사 도구를 그대로 실행한 첫 시도는 Lite 출력이 한 개라 실패했고, 단일 netlist 범위를 명시한 `nrom423-romcheck02`를 선택했다.

이 산출물은 진단용이며 사용자 SD에 설치할 package가 아니다. 419 raw STA의 음수 reset/CDC·미제약 포트 및 조건부 IO 한계가 남고, 418 ROM은 정지 부트 루프여서 화면·입력·음성을 검사하지 않는다. 실제 `native_session`·65816 화면·STOP·base token/menu 복구와 matched hardware 검증이 필요하다. 기존 227·GBC 복구 자료와 SRAM은 변경하지 않는다.
