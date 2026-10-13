# NES170 — 첫 표시 요청의 하위 실패 구분

## 판단과 범위

169는 첫 BEGIN에서 exchange=false, native_result5/sink_error2, 표시 완료0회였다.168의 E3는7장 표시 후 SEAL 단계이며 이번 실패보다 뒤다. 기존 로그로 초기 F6/CRC 오류·busy·후속 상태 오류·폴링 소진을 구분할 수 없으므로 이 경계만 보강한다. 무조건 리셋 재시도, 대기 증가, 예산 해제, 성공 ACK 대체는 하지 않는다.

사용자는169 시간을 약60초에서 약13~14초, 총 약4분으로 정정했다. 기존 원본 TXT와 최초 분석 기록은 보존하며 이번 정정을 우선한다.13.49초 펌웨어 표시 구간과 부합하고60초 정상 종료 코드가 아니다. 시계 고장 조사로 확대할 근거는 없다.

## 로컬 기동 이미지 확인

169의 routed database 복사본에 Quartus EDA Netlist Writer를 실행했다. 기본 및3코너 Verilog netlist의4개 ROM 메모리에서 `mem_init0..3`을 추출하고4096×8로 복원했다. 각 초기값·리셋 벡터008000은169 compact ROM과 일치했다. 기존 생성 MIF뿐 아니라 메모리 atom 초기값까지 확인한 것이다. RBF 비트 직접 추출이나 실기 ROM 읽기 검증은 아니며 CPU가 실제 기동했다는 증명도 아니다. MAP/FIT/STA와 FPGA 재생성은 하지 않았다.

```powershell
quartus_eda board --simulation --tool=questa_oem --format=verilog --output_directory=netlist170
python tools/inspect_nes_startup170_rom.py --netlist <복사본/netlist170> --expected <169/sink-program.hex> --out <새 결과 폴더>
```

완료된 원본 build 폴더에 EDA를 실행하지 않는다. 이번 export 작업은 비공개 ASCII 임시 복사본에서 실행했으며 출력·실행 로그를 별도 보존했다.

## MCU 변경과 로그

`nes_sink_spi170.c`를 기존 transport 이름으로 materialize한다. API·상태 검사·CRC·패킷·guard 호출 순서·최대65536회 폴링·실패 반환은 유지한다.20바이트 전역 상태는 첫 실패만 보존하고 메뉴 진입 시 초기화한다. RUN 도중 SD 쓰기는 없다. 실패 뒤 기존 안전 정지·TXT 경로를 사용한다.

`sink_io170=RR/PPPPPPPP/SS...`는54바이트 줄이다. RR은16진수 사유, bit7은 상태15바이트를 실제 받았다는 뜻이며 **CRC 통과 여부가 아니다**. P는 시도한 E0 폴링 전송 횟수의32비트16진수다. 초기 상태 조회·패킷 전송·guard는 폴링 수에 포함하지 않는다. S는 실패 시 RX[1..15]이며 dummy RX[0]은 제외한다. 상태를 받지 못한 사유는 S를0으로 채우며 실제0 응답으로 해석하지 않는다.

| RR의 하위7비트 | 위치 |
| --- | --- |
| 1 | 잘못된 인수 |
| 2 / 3 | 초기 guard / 상태 전송 실패 |
| 4 / 5 | 초기 상태 ID·flags·CRC 실패 / busy |
| 6 / 7 | 패킷 쓰기 guard / 전송 실패 |
| 8 / 9 | 폴링 guard / 전송 실패 |
| 10 | 폴링 상태 ID·flags·CRC 실패 |
| 11 | 설정된 폴링 횟수 소진; 마지막 수신 상태 기록 |

예를 들어 `8b/00010000/f6...`는65536회 대기 소진과 수신된 마지막 상태를 뜻한다. F6 flags의 pending/ACK와 순번을 실제 요청에 대조한다. MCU의 native_result가 DEADLINE/SERVICE/IO이면 그 선행 사유도 유지된다. 기존 sink_trace의 ACK 유효성·원문·최초 실패 요청도 그대로 남는다. 정상60초 종료에는 transport 사유가0일 수 있다.

## 검증과 다음 실기 분기

- 실제165와170 C transport를 같은 callback 응답으로 실행한267개 경우에서 반환·ACK·전송 길이/바이트·guard/transfer 호출 순서가 같았다.241개 패킷 길이, 잘못된 상태/CRC/busy, 각 guard/transfer 실패,65536번째 성공 및 소진을 포함한다. 최초 실패 고정·정상 무기록·출력 용량 경계도 검사했다. 물리 SPI 검증은 아니다.
- 실제 최대 필드 너비의 종료 TXT는4020/4096바이트다. 추가 기록은20바이트이며 실제 ARM 전체 RUN 호출 그래프·활성 IRQ 예산을 다시 계산한다. 숫자와 파일 해시는 [검증 기록](../analysis/startup170-verification.json)을 따른다.
- 169 FPGA·SNES·ROM·메뉴·164 복원 파일은 내용 그대로 재사용하며170 파일명만 바꾼다. 세이브 SRAM·GBC·화면 DMA·게임 APU/입력·리셋 순서는 변경하지 않는다.
- busy/잘못된 상태이면 첫 endpoint 소유권·SPI 상태 무결성을 확인한다. pending을 유지한 폴링 소진이고 stage/flags도0이면 SNES 기동·물리 리셋/부트 경계를 우선한다. ACK 존재 시 전달/상태 판독을 확인한다. E3라면 유효 ACK·실행 이미지 확인 후169 분할 경로로 돌아간다. 어느 경우든 무한 재시도나 임의 성공 처리는 하지 않는다.

최소 보강 후 바로 SMB3 실기 로그를 받는다. 새 범용 진단이나 불필요한 무변경 FIT를 늘리지 않는다. 연속 AV→장기 실행/오류·본체 리셋 로그→입력 유지 순서, 세이브 보호는 유지한다.
