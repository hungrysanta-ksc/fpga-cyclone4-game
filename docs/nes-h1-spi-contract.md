# H1 SPI 통합036 계약

SPDX-License-Identifier: MIT.

[결과](../analysis/H1-SPI-RESULT.ko.md), [035 펌웨어](nes-h1-firmware-contract.md).
원래034 HDL와035 펌웨어를 보존하고, 036 빌드 도구가 SHA로 고정한034 보드 모듈 사본에 작은 수정을 적용한다.

## 발견한 통합 결함과 수정

034는 SPI 응답을 reply[7-bit_count]로 바로 구동했다. bit_count는 동기화된 SCK 상승에서 증가한다.
034 testbench는 원래 상승과 같은 시점에 읽어 정상 비트를 보았다.
035 STM32 코드는 상승 뒤 delay_us(2) 후 GPIO IDR을 읽으므로 다음 비트를 보게 된다.
035의 독립 호스트 모의 장치 역시 이 RTL 동작을 재현하지 못했다.

036은 miso_hold 레지스터를 추가한다. 동기화된 SCK 하강에서 다음 응답 비트를 넣고 high 구간에는 유지한다.
SS 비활성 및 reset에서는 초기화한다. ARM/STOP 키, 세대, 진단 revision34, SNES 프로그램은 바꾸지 않는다.
SPI mode0 <=250kHz 및 바이트/SS 간격 계약은 그대로다.

## C 파형 → 실제 RTL 검증

035 생산 C 소스를 사본으로 가져와 IDR 읽기 식 하나만 기록 콜백으로 바꾼다.
기존 호스트 GPIO 모델의 핀 쓰기와 delay_us/ms 시간을 함께 기록한다.
C delay/control 코드와 세션 코드는 그대로이며, 실행에서 나온942행 파형을 Questa RTL에 재생한다.
224번 GPIO 읽기 가운데 호출자가 사용하는 상태 응답88비트를 비교한다.
명령 전송 중 dummy 수신과 ARM/STOP의 폐기되는 수신값은 비교하지 않는다.

기존034에서 실제 응답 첫 비트(sample8)가 불일치하고, +2us 읽기로 바꾼 보드 시험은 F0=A5 대신4B를 재현한다.
수정본은 같은 파형과 기존 보드6조건을 모두 통과한다.
ROM65,536바이트와 패턴8,192바이트도 원래 입력과 일치한다.
이 시험은 C 코드의 핀/시간 기록 재생이며, ARM 명령 실행 시간이나 물리 STM32/전기 신호의 시뮬레이션은 아니다.

첫 기록 시험은 사용되지 않는 dummy 응답까지 비교해 수정본을 잘못 거부했다.
원시 첫 실행과 드라이버를 보존했고, 최종 시험은 실제 C 호출자가 소비하는 응답만 비교한다.
기존 실패가 최종 시험에서도 재현되어야 통과로 인정한다.

## 동일 소스 이미지

036 RTL 실행과 Quartus에 사용한 수정 보드 소스는 바이트 해시가 같다.
핀135개와 SDC는034 그대로다. RBF 출력 설정 및 Quartus의 버전 메타데이터만 QSF에 추가된다.
map/fit/STA/ASM 완료.1,302LE/104LAB/44M9K,내부 setup+2.224ns/hold+0.179ns 이상이다.

기존 upstream RLE 압축기는 마지막 반복 구간 뒤 EOF 처리에서 FF 한 바이트를 더 만들었다.
C44 도구는 이미 이 끝 패딩을 허용한다. 원본 도구/GBC 산출물은 보존한다.
H1에서는 원본 압축을 저장하고, 정확히 RBF+FF이며 마지막 FF 리터럴 하나를 제거했을 때
RBF와 완전히 같다는 두 조건을 확인한 경우에만 그 바이트를 제거한다.
실제 MCU의 rle_file_getc() C 코드로209,988바이트와 EOF를 확인했다.

실기 조합 기록은 ignored analysis/local-h1-spi-036/hardware-candidate-files.json이다.
MCU는035 바이너리 그대로, FPGA는036이다. 표시되는 진단 화면 ID는 기존 NES H1 034이며 프로토콜 revision도34다.
아직 SD 설치 ZIP/카드 변경이나 실기 실행은 하지 않았다.

## 재현

1. tools/run_nes_h1_spi.ps1:035와 같은 Python/FloatWrapper/QuestaBin,034 Build,HostGcc를 Gcc 인수로 전달하고 새 ASCII Out을 사용한다.
2. python -B tools/nes_h1_spi_resource.py --out <fresh-fit> --build <034-build> --quartus-bin <bin> --rle <pinned-built-rle.exe>
3. python -B tools/verify_nes_h1_image.py --fit <fit> --firmware-tree <035-derived-tree> --gcc <host-gcc> --out <fresh-decoder-test>
4. python -B tools/verify_nes_h1_spi.py:이번 보존 증거 검사.
5. 추가 IO 보고는 tools/audit_nes_h1_io.tcl을 ASCII 작업 경로에 복사해서 그 fit 사본에서 실행한다.

기존 FLOAT 래퍼를 재사용한다. license smoke·새 라이선스·영구 서버 변경은 필요 없다.

## 남은 외부 I/O 관문

새036 배치의 slow85C 최장 지연은 SNES pad 경로24.278ns,입력→register12.663ns,
register→SNES18.091ns,SPI 입력5.438ns,SS→MISO10.795ns,register→MISO5.811ns다.
38입력/804경로 및11출력/895경로의 setup·hold 미제약은 유지한다. 이 지연 수치는 slack이 아니다.

[SNESDRONE 제작자의 직접 측정](https://github.com/michael-hirschmugl/SNESDRONE#1321-bus-transfer-timing-diagram)은
한 콘솔의 reset-vector ROM 읽기를 보여준다. 해당 측정은 FXPAK Pro 및 DMA/쓰기/모든 콘솔의 최소·최대 규격이 아니므로
이 수치로 SNES 입력 지연이나 turnaround를 확정하지 않았다.
기존 GBC SDC에도 비동기 SNES pad/CDC를 가상 envelope로 한정한 주석이 있어 그대로 복사하면 signoff가 되지 않는다.

다음은 실제 SNES 읽기/쓰기/DMA의 최소 strobe·주소/데이터 setup/hold, 보드 transceiver 지연·방향전환을 함께 검토하는 일이다.
일괄 false-path나 임의 지연으로 미제약 숫자를 지우지 않는다.
그 뒤 복원용 firmware.stm 백업/메뉴·base 파일 확인 및 같은 후보 실기 묶음을 완성한다.
