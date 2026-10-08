# CF87 구성 경로089와 세션 예산

089는 고정 CF87 fit에서 만든 구성 파일을 SD 없이 전송하는 MCU 코드다. 전체 TXT 진단 펌웨어는 아직 아니다. 실제 구성 코드·088 reader·084 mini·공유 runtime을 호스트에서 순서대로 호출했으며, 이 순서를 제품 main에 연결하는 작업은 남아 있다.

## 같은 fit에서 생성한 파일

087 동결 manifest를 확인하고 `fit01/`의 데이터베이스·입력·보고서를 새 ASCII 경로에 복사했다. Quartus Standard 25.1std.0 Build1129의 ASM/CPF만 실행했다. 두 단계 모두 오류0·경고0이며 새 map/fit/STA를 실행하지 않았다. 원본 fit의 모든 파일과 새 사본의 RTL·QSF·SDC·fit/STA 보고서 해시를 비교했다.

- RBF: 510,856바이트. SHA-256 `c96d4d3e846a9914a3ab34cfeabc9f4c755516b5166793a510f322f6ba774708`.
- RLE: 59,700바이트. SHA-256 `e772ead5e070c71767df2318d91f5d83d629e8ffedd275b19e81c842133cb4a2`.
- 압축 해제 바이트의 CRC32: `06a503c4`. 마지막 FF는 기존080 decoder의 종료 표식이며 RBF 바이트에 포함하지 않는다. RBF에 실제로 들어 있는 마지막 바이트까지 별도로 보존한다.

생성 헤더와 바이너리는 private 근거다. 공개 소스에 구성 바이트나 boot ROM을 넣지 않는다. 공개 clone만으로 private fit 데이터베이스까지 복원할 수 있다는 의미가 아니다.

## 구성 함수의 계약

`nes_clock_config089()`의 인자는 위 도구가 생성한 신뢰된 embedded CF87 descriptor다. 일반 파일 또는 임의 포인터의 안전성을 보장하는 API가 아니다. 길이510856, 압축 길이 상한131072, 종료 표식·토큰·출력 길이와 CRC를 확인한다. 전체 사전 검증이 끝나기 전에는 nCONFIG를 변경하지 않는다. 전송한 바이트도 다시 CRC를 계산한다. CRC는 진단용이며 서명이나 악의적인 교체 방지 수단이 아니다.

호출자는 기존 diagnostic scope, SNES RESET, USB IRQ 차단을 소유해야 한다. 공유 오류·로그 쓰기 허가·SD offload·block transfer가 있으면 거부한다. 모든 출력 바이트에서 이 조건과 nSTATUS를 확인한다. 사전 검사와 전송 각각 최대32바이트마다 기존 공유 예산 및 같은 로컬 stream 예산을 검사한다. 로컬 stream 예산500tick/40000회는 두 pass 사이에 다시 시작하지 않는다. CRC의 byte/bit 반복도 정적으로 유한하다.

SPI busy 해제를 최대25tick/100000회로 기다리고 TXE를 확인한다. CS HIGH, SPI 차단 후 기존 `fpga_init()` 핀 설정을 사용한다. nCONFIG LOW 및 10µs 지연 뒤 nSTATUS/CONF_DONE LOW, nCONFIG HIGH 뒤 nSTATUS HIGH/CONF_DONE LOW를 확인한다. 각 핀 대기는100tick/100000회 상한이다. 고정 RBF를 기존 STM32 LSB-first 매크로로 전송하고 기존 구성 경로와 같은 추가 클록3개, 1ms 지연과 DONE 확인을 수행한다. clean 종료 때 DATA0를 MCU_RDY 입력으로 돌리고 원래 SPI CR1을 복원한다. 이후 CF87 ID는088 reader가 확인한다.

위 지연과 핀 handshake는 구현한 정책이다. GPIO 전압·nCONFIG/CCLK setup/hold·기판 지연을 실측하거나 외부 타이밍 승인으로 검증한 것은 아니다. 실패 시 공유 오류를 유지하고, 이미 구성을 시작했다면 nCONFIG LOW/CCLK LOW로 취소한다. RESET·USB 보호를 풀거나 SD/SRAM/다음 구성을 재시도하지 않는다. scope·fault를 초기화하지 않는다. 구성 성공만으로 mini 준비 또는 클록 정상으로 표시하지 않는다.

## 합산 호출 수

호스트는 실제084 mini/decode와 runtime, 실제089 구성 및088 reader를 하나의60초/100만 회 scope에서 실행했다. mini의 SRAM write/read와 mapper는 모델이며 실제 SD/FatFS·화면 렌더링·MCU startup은 실행하지 않았다. 구성 GPIO는 pinned STM32 매크로가 만든 LSB마다 RBF와 대조했다. SPI MISO는088과 같은 응답 모델이며 이번에는 RTL replay를 새로 실행하지 않았다.

| 경로 | 공유 검사 수 |
| --- | ---: |
| 첫 mini | 153,828 |
| CF87 사전 CRC + 구성 | 31,944 |
| 정상/클록 부재: 첫 mini → 구성 → reader → mini 복귀 | 729,572 |
| 측정 순번 진행 없음, SysTick 정상: 같은 전체 경로 | 921,626 |

구성에 단순 byte별 검사를 추가하면 mini 두 번307656 + raw510856 + reader389972 = **1,208,484회**이며 부가 검사 전에도100만을 넘는다.089는 공유 예산을 늘리거나 다시 시작하지 않고 검사 단위를 제한해 정상 경로를 맞췄다.32바이트 단위는 보호를 모두32바이트마다 검사한다는 뜻이 아니다. 소유권·공유 오류·nSTATUS는 매 바이트 검사한다.

SysTick과 FPGA 측정 순번이 함께 정지한 모델에서는 reader의512회 상한 후 mini 복귀 도중 공유 검사1,000,001회에서 차단됐다. mini는74,803바이트까지만 전송됐다. 이 경우 TXT 저장이나 성공 화면을 약속하지 않는다. 실패 뒤 재시도하지 않는 것이 기대 결과다. NO_PROGRESS라도 공유 오류가 생기면 저장 가능한 상태가 아니다.

정상 모델 시간3.826390초, 순번 정지5.321734초는 구성1µs/byte와 명시적 지연을 적용한 모형 값이다. ARM 명령 시간·CRC CPU 비용·IRQ·실제 SRAM/SPI 시간·TV 표시 시간을 측정한 값이 아니다. 남은78,374회는 순번 정지 경로에서 SD init/공간 검색 이전의 여유일 뿐, 최종 보고서 저장을 보증하는 여유가 아니다.

## 검증 및 남은 작업

최종 host04는304검사를 통과했다. 실제 구성4,086,848비트, active/absent/no-progress 합산, 잘못된 CRC/길이, 핀 고정, delay 오류, 상태·소유권 상실12위치씩, 공유 검사127회 간격과 마지막 위치, busy/TXE/reentry/USB/SD/로그 허가, 시간 wrap/500tick 및60초 만료를 확인했다. 모든 바이트 위치에 오류를 주입했다는 의미가 아니다. CRC 사전 검사·nSTATUS·공유 guard 제거3개와 byte별 예산 변경1개가 각각 기존 assertion에서 실패한다. byte별 변경은 로컬40000회 stream 한도에서 먼저 실패하며 전체100만 회 초과 실행 증거로 대신 쓰지 않는다.

같은 구성 C는 실제 STM32F401 헤더로 ARM 오브젝트17,876바이트를 생성했다. 최종 펌웨어 링크·main 호출·실기 성공을 의미하지 않는다. 최초 host01/02는 테스트 시각을 runtime 시작 뒤0으로 되돌려 wrap 차이를 만들었던 모델 오류였다. 시각 초기화 순서 수정 후 host03은301검사, 추가 한계 검사 후 host04는304검사다. ARM01의 상대 도구 경로 때문에 발생한 cc1 탐색 실패도 보존하며, 절대 경로를 사용하는 ARM02가 통과했다.

다음 작업은 **제품 플랫폼 함수 하나**에 초기 marker →089 구성 →088 관측 RAM 보관 → mini 복귀 → 실제081 SD init/mount →084 space/writer/readback/화면을 연결하는 것이다. 실제 전체 세션의 예산과 시간, 최초 오류 뒤 IO 금지를 검증한다. 사람이 읽을 TXT에 raw16바이트×3과 판정·순번·count/window/divisor·시간·후보 ID를 넣고 ACTIVE를 주파수 승인으로 표현하지 않는다. 최종 ARM 링크/callsite, 구성 전환/SPI/RESET 조건, 동일 ASM/ARM/044 복원 manifest를 확인한 후 실기 trial을 만든다.

재현 도구는 `nes_clock_assemble089.py`, `test_nes_clock_config089.py`, `compile_nes_clock_config089.py`, `verify_nes_clock_config089.py`다. 각각 새 출력 경로를 사용한다. 기존084 저장·044 복원/menu/GBC PASS와 CF86 미해결 외부 메모리/공통 고장 조건은 유지한다. 사용자에게 알려진 부품·LED·분해·PC USB·저장 시험을 다시 요구하지 않는다. 현재 installable=false, 준비도4완료/7부분/1미완료다.
