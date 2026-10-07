# FXPAK Pro 하드웨어 식별·PSRAM 규격 가이드

갱신: 2026-10-07 KST. 이번 범위는 실기 HWINFO002 로그 해석, 사용자 기판 사진 판독과 부품 자료 검증이다. NES 구현·FPGA/SDC 변경·새 실기 적재 진단은 진행하지 않았다.

## 실물 사진으로 추가 확인한 사항

2026-10-07 사용자 제공 앞·뒷면 원본(각 4032×3024)을 확인하고, 앞면 U501/U502/U201/U511/U401 영역을 원본 픽셀로 잘라 회전해 판독했다. 글자를 생성하거나 복원하지 않았다. 사진과 추출 이미지는 로컬 probes/fxpak-hardware-photo-004/에만 보존한다.

| 위치 | 실제 표기 | 판단 |
| --- | --- | --- |
| 앞면 보드 실크 | FXPAK PRO Mk.III, Rev.D/2022-05-02, Manufactured by KRIKzz | HWINFO002의 Rev.D 스트랩과 일치. 날짜는 PCB 실크이며 개별 제품 제조일로 단정하지 않음 |
| U501, U502 | 두 칩 모두 IS66WVE4M16EBLL / -70BLI | 실제 PSRAM은 **IS66WVE4M16EBLL-70BLI 두 개**. 이전 BLL 후보에서 E가 추가된 정확한 코드로 갱신 |
| U201 | Altera Cyclone IV, EP4CE15F17C8N | 기존 프로젝트 대상 EP4CE15F17C8과 주요 코드 일치. 사진 관측 코드는 끝 N까지 보존 |
| U511 | IS62WV5128EBLL-45HLI | PSRAM과 별도인 SRAM. 공식 규격 512K×8=512KiB, 45ns |
| U401 | STM32F401 / RCT6 | 후속 확대 사진으로 **STM32F401RCT6** 확정. 기존 DEV_ID0x423/Flash256KiB와 일치 |
| 커넥터·테스트 패드 | SWD, JTAG, UART, GPIO 및 5.0V/3.3V/2.5V/1.2V/GND 실크 | 위치/명칭만 확인. 실제 전압·신호 파형·핀 연결을 측정한 것은 아님 |

[ISSI EBLL 공식 데이터시트 Rev.D3, Sept.2022](https://www.issi.com/WW/pdf/66-67WVE4M16EALL-BLL-CLL.pdf) pp.1/30에 따라 칩당 64Mbit(4M×16), 두 개 합계 **128Mbit=16MiB**, VDD/VDDQ **2.7–3.6V**, **70ns**, 48-ball TFBGA, 산업용 -40~+85°C다. [SRAM 공식 데이터시트](https://www.issi.com/WW/pdf/62-65WV5128EALL-BLL.pdf)는 U511의 용량/속도를 뒷받침한다.

이 사진으로 해당 사용자 보드의 PSRAM 탑재 코드와 speed grade 식별은 해결됐다. ALL/EALL 생산시기 교체 주장이나 다른 생산본의 BOM까지 확정한 것은 아니다. 전압 실측·PCB 지연·외부 IO 타이밍 승인과 NES 실행 성공은 별도다.

확대 사진 3장에서도 U501/U502의 EBLL-70BLI, U511의 EBLL-45HLI 및 U201의 EP4CE15F17C8N이 일치한다. U401은 **STM32F401RCT6**로 판독된다. [ST 공식 부품 정보](https://estore.st.com/en/stm32f401rct6-cpn.html)의 256KiB Flash/64KiB SRAM/최대84MHz 사양과 기존 HWINFO002 로그가 부합한다. 사진은 제품 자체 속도·실제 클록 파형 측정이 아니다. 추가 분해/촬영은 필요하지 않으며 사용자는 기판을 재조립할 수 있다. 확대 사진은 로컬 probes/fxpak-hardware-final-005/에 보존한다.

## 확인 수준과 현재 결론

| 항목 | 확인 결과 | 근거 수준 |
| --- | --- | --- |
| 보드 스트랩 | 0xC4 → KRIKzz FXPAK Pro Rev.D | 사용자가 실기에서 생성·전달한 HW002000.TXT |
| MCU | STM32F401RCT6, DBGMCU_IDCODE 0x00016423, DEV_ID 0x423, Flash 256KiB | 확대 사진 전체 코드와 실제 레지스터 보고값 일치 |
| MCU die revision | 원시 0x0001 | 보존만 한다. A/Z 같은 이름이나 전체 주문 코드·패키지로 확대 해석하지 않는다 |
| MCU 클록 | configured_cpu_hz=84000000 | 빌드 설정. 실측 주파수가 아님 |
| FPGA | EP4CE15F17C8N | U201 실물 각인. JTAG ID 읽기는 수행하지 않음 |
| PSRAM 실물 | IS66WVE4M16EBLL-70BLI ×2 | U501/U502 각인과 ISSI EBLL 데이터시트 대응 확인 |
| 70ns | 두 칩의 -70BLI 각인 및 EBLL 주문표 일치 | 실제 탑재 speed grade 확인. 전체 보드 타이밍 승인과는 구분 |
| ALL 대안 주장 | 1.8V 전원/I/O 계열 | 생산 시기만 다른 동등 교체품으로 취급하지 않음 |

HWINFO002 버전·시작/끝 표식·내용 CRC32 17cb6ef7은 정상이다. 원본 SHA256은 2b35bce0e110e6667db7433d1a967fb674709da8f8b12aa6380f6730764e07a5. 실제 펌웨어 실행 및 SD TXT 생성·반출 근거가 생겼다. 성공 화면의 readback 표시와 원래 펌웨어/GBC 복구는 이 TXT만으로 별도 관측했다고 주장하지 않는다. PSRAM 속도 측정이나 NES 적재/비교 성공 로그도 아니다.

MCU 식별 레지스터 해석은 [ST RM0368 §23.6.1/§24.2](https://www.st.com/resource/en/reference_manual/DM00096844.pdf)를 따른다. 장치 고유 UID는 수집하지 않았다. 원시 로그·PDF·실행 기록은 로컬 probes/fxpak-hardware-identification-003/에 보존하고 공개 소스에는 요약만 남긴다.

## 사진 이전 후보 자료 대조 — 이력

[ISSI BLL Rev.B, Jan 2014](https://www.issi.com/WW/pdf/66WVE4M16BLL.pdf), pp.1/18/28: IS66WVE4M16BLL-70BLI는 64Mbit(4M×16), 48-ball TFBGA, 산업용 -40~+85°C, VDD/VDDQ 2.7~3.6V, 70ns 등급이다.

[ISSI ALL Rev.B, Feb 2012 원본 PDF의 DigiKey 보관본](https://media.digikey.com/pdf/Data%20Sheets/ISSI%20PDFs/IS66WVE4M16ALL%2C_IS67WVE4M16ALL.pdf), pp.1/18/28: IS66WVE4M16ALL-70BLI도 64Mbit/70ns이지만 VDD와 VDDQ가 1.7~1.95V다. ALL↔BLL을 생산 시기 차이로만 설명할 근거는 찾지 못했다. EALL/EBLL 등 다른 접미사도 같은 부품으로 섞지 않는다.

기존 [GBC 메모리 핀 제약](../../src/fpga/pin.qsf)은 ROM_DATA 등 메모리 신호를 3.3-V LVTTL로 지정한다. 따라서 BLL 후보가 이 설계 전압과 부합한다는 **추론**은 가능하다. QSF는 실제 보드 전압을 측정하거나 두 RAM의 칩 표기를 읽은 증거가 아니다. ALL을 이 설계에 직접 적용하려면 별도 전원·레벨 변환 회로의 근거가 필요하다.

[제조사 제품 페이지](https://krikzz.com/our-products/cartridges/fxpak-pro.html)와 [sd2snes Rev.D 공지](https://sd2snes.de/blog/archives/1261)는 정확한 PSRAM 코드/속도 접미사/사용자 보드별 BOM을 제공하지 않는다. 기존 구형 Rev.F 회로도의 MT45W8MW16도 Spartan 보드 자료여서 현 Pro의 탑재 근거로 전용하지 않는다.

## 사용자가 제시한 출처와 PDF 재검토

2026-10-07에 전달받은 2쪽 PDF의 본문·참고문헌과 내장 하이퍼링크 13개를 모두 확인했다. PDF 자체에는 회로도/BOM 원본이나 칩 마킹 사진이 첨부돼 있지 않다. 다음은 링크가 실제로 뒷받침하는 범위다.

| 인용 자료 | 원문 확인 결과 | 현재 보드 탑재 증거로 사용할 수 있는가 |
| --- | --- | --- |
| [2011-07-31 A small recap, part 2](https://sd2snes.de/blog/archives/62), [같은 월 아카이브](https://sd2snes.de/blog/archives/date/2011/07) | 네 SRAM을 단일 128Mbit PSRAM으로 바꾸고 KiCad로 옮긴 글. 원문은 보드를 **Mk.II**로 명시함 | Pro/Mk.III의 ISSI BOM 증거가 아님. 월 아카이브도 동일 글이므로 독립 교차 확인이 아님 |
| [2011-10-16 Prototype – assembled](https://sd2snes.de/blog/archives/99) | 구형 **Rev.E prototype** 소개 | 현재 Pro Rev.D의 회로/BOM과 혼동하지 않음 |
| [Reddit FxPak pro insides](https://www.reddit.com/r/snes/comments/134tts7/fxpak_pro_insides/) | 작성자는 eBay 구매품이 설명과 다른지 질문하며, 댓글들은 Chinese SD2SNES/Rev.X clone으로 지목함 | 정품 KRIKzz Pro 마킹 확인 근거로 채택하지 않음. 여기서 사진의 정확한 RAM 코드를 판독했다고 주장하지 않음 |
| [ConsoleMods 소개](https://consolemods.org/wiki/SNES:FXPak_Pro_%28SD2SNES%29) | 확인한 페이지에는 해당 ISSI 전체 주문 코드와 사용자 보드별 BOM 근거가 없음 | 해당 부품의 실장을 입증하지 못함 |
| PDF 참고문헌 [5]/[6]의 Mouser/DigiKey BLL-70BLI 링크 | 해당 부품의 판매·규격 자료 | 부품 규격 검증에만 사용. FXPAK Pro에 실제 장착됐다는 뜻은 아님 |
| PDF 참고문헌 [7]/[8]의 Mouser/DigiKey 링크 | 내장 주소의 부품명은 각각 **IS66WVE4M16EBLL-70BLI**, **IS66WVE4M16EALL-70BLI** | 본문 BLL/ALL과 E 접두사가 다름. 이 링크로 생산 시기별 Pro 채용이나 동일 부품을 입증하지 못함 |

PDF의 BLL/ALL 전압 구분 설명은 방향이 맞지만, 검토한 정확한 BLL/ALL 데이터시트에서는 core VDD뿐 아니라 **I/O VDDQ도 다르다**. 그러므로 내부 로직 차이만으로 설명하거나 같은 보드의 직접 교체품으로 취급하지 않는다. 참고문헌 [7]/[8]의 판매 페이지는 재접속 시 읽지 못했으며, 위 코드 구분은 PDF의 실제 링크 주소를 확인한 결과다.

또한 IS66WVE4M16 계열은 **칩당 64Mbit**다. 기존 Mk.III 소스의 2×64Mbit/70ns 설계 주석과 2011년 Mk.II 단일 128Mbit 설명을 합쳐 한 보드의 증거로 만들지 않는다. 출처가 많아도 같은 글의 재인용, 다른 세대/복제품, 다른 주문 코드가 섞이면 실장 확인으로 승격하지 않는다.

검토 PDF SHA256: 6a3eccaba2ecfeac931b78429644d6ea322cd9302fb3eb6e1580b2ac02935297. 원본 문서와 추출 링크·페이지 이미지는 공개 저장소에 포함하지 않는다.

## 실제 EBLL-70 데이터시트 타이밍 입력

실제 탑재 부품에 맞춰 EBLL Rev.D3 pp.22–24의 -70 열을 이미지로 재확인했다. 다음 값은 부품 규격이며 보드 전체 타이밍 여유는 별도 계산해야 한다. 단위는 별도 표시 외 ns이며 공란은 보증값이 주어지지 않은 쪽이다.

| 기호 | min | max |
| --- | ---: | ---: |
| tAA / tCO / tBA | — | 70 |
| tOE | — | 20 |
| tAPA | — | 25 |
| tPC | 20 | — |
| tBLZ / tLZ | 10 | — |
| tOLZ | 3 | — |
| tOH / tOW | 5 | — |
| tRC / tWC | 70 | — |
| tAW / tBW / tCW | 70 | — |
| tWP | 46 | — |
| tWPH | 10 | — |
| tDW | 23 | — |
| tAS / tDH / tWR | 0 | — |
| tHZ / tOHZ / tBHZ / tWHZ | — | 8 |
| tCPH | 5 | — |
| tCEM | — | 8µs |
| tPU | 150µs | — |

이 표는 실제 EBLL의 규격이다. 구형 BLL의 page access 값을 전용하지 않는다. tCEM 8µs는 산업용이며 T 계열의 예외를 E 계열에 적용하지 않는다. 원문 데이터 setup 기호는 tDW다. WE# LOW 역시 tCEM 한도를 지켜야 한다. 70ns 하나로 쓰기·방향 전환·초기화를 승인하지 않는다. FPGA tCO/입출력 지연, PCB 왕복 지연, 수신 setup/hold, CE/OE/WE/BLE/BHE 상대 시점과 여유를 별도 예산에 넣는다. Hi-Z 수치는 출력 완전 비구동의 임의 측정 기준으로 바꾸지 않고 데이터시트의 부하/전이 조건을 함께 적용한다.

원본 판본 해시: BLL e09bd4ee9d5b20108564be25ca7b59cca4b2f48d82e03bdad2e2ed6b1789a327; ALL 95e7461333d99d80eb73926aa77fd45c79e1166fc6751e50a89a3cdc93e60ced. PDF는 공개 저장소에 재배포하지 않는다.

## 추가 진단 패키지를 만들지 않는 이유

검토한 두 데이터시트에는 제조사/주문 코드/속도 등급을 반환하는 ID 명령이 정의돼 있지 않다. BLL pp.14–17의 CR은 page/refresh/sleep 설정이다. 읽기는 최대 주소에서 READ→READ→WRITE→READ 순서이며 단순 메모리 읽기와 다르다. CR을 얻어도 이 후보들의 정확한 주문 코드·speed grade는 확정되지 않는다.

따라서 이번 목적을 위해 HWINFO003 펌웨어나 FPGA를 새로 만들지 않는다. 현재의 식별 로그를 반복 수집하거나, 다른 PSRAM 계열의 DIDR 명령을 추측 적용하지 않는다. 설정 상태가 별도 원인으로 의심될 때만 문서·현재 FPGA 접근 경로·원본 복구를 갖춘 CR 진단을 검토한다. 메모리 시험 통과나 동작 가능한 최대 주파수는 제조사 worst-case speed grade 증명이 아니다.

사진 도착 전에는 실물 표기/BOM이 필요했지만, 이제 두 칩의 표기를 확보했다. 부품 식별만을 위한 추가 촬영·진단 패키지는 필요하지 않다. 아래는 사진 이후 현재 상태다.

~~~text
installed_psram_part = IS66WVE4M16EBLL-70BLI
installed_psram_count = 2
datasheet_speed_ns = 70
installed_psram_part_verified = true
verification_method = user_board_photo_markings
board_io_voltage_measured = false
external_timing_approved = false
~~~

## 이후 작업에 적용할 규칙

- 실기는 외부에 있어 작업 PC와 USB로 연결하기 어렵다. 진단 펌웨어/SD 패키지를 준비하고 사용자가 실행한 TXT를 전달받는 방식을 기본으로 한다. COM 포트나 USB 연결을 다시 전제로 요구하지 않는다.
- 이번 Rev.D/F401/Flash 관측값을 먼저 읽고 이미 아는 제품명·리비전을 반복 질문하지 않는다. 보드 스트랩, MCU ID, PSRAM 탑재 코드, 부품 규격, 보드 타이밍 승인을 각각 구분한다.
- 부품명 접미사 전체와 데이터시트 판본을 고정한다. PSRAM 탑재 코드/70ns 식별은 완료로 반영한다. H05의 전체 배선 대응 검토와 H06의 외부 IO 승인은 별도이며 완료 처리하지 않는다. NES 준비도 집계는 완료5/부분6/미완료1 그대로다.
- 사용자 확대 사진 최종 확인 후 다음 작업 진행 요청으로 NES 외부 타이밍 검토를 재개했다. [주소/CE 타이밍 검토](NES-PSRAM-TIMING-REVIEW.ko.md)를 다음 진입점으로 사용한다. 기존 HWINFO002 후보·044–066 동결 기록은 고치지 않는다.
