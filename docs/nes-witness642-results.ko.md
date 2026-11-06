# MMC642 실기 최초 오류와 부팅 순서 기록

MMC639의 두 실패를 분리 판독할 설치본을 준비했다. 성능 기준은 실기 MMC613이다. 642 실기 결과는 아직 없다. [설치·로그 수집](nes-mmc642-trial.ko.md) · [패키지·검증 해시](../analysis/witness642-package.json)

## 1차 유형 — 세대 32 FINISH

E8 fault 응답에서 byte 14에 host 최초 검출 마스크, byte 15에 NES 측 증거를 싣는다(첫 바이트를 0으로 센다). 정상 토큰·예약 바이트 18·CRC8·20 B 응답 형식을 보존했다. 명령의 마지막 비트에서 fault가 발생해도 두 바이트를 보내기 전에 동기화할 시간을 확보한다. 이미 확정한 응답의 fault 여부는 전송 도중 바뀌지 않는다. 기존 ARM이 `nes-budget-mmc642.txt`의 `plan_reply_hex`에 응답 전체를 기록한다.

| 위치 | 하위 비트부터의 의미 |
|---|---|
| byte 14, bit 0–6 | native 입력 SPI, 일반 sink, plan SPI 자체, host 배치 검사, bulk host, aperture 소비, bulk 소비 명령 |
| byte 15, bit 0–4 | NES 배치 검사, bulk 생산 검사, lease, tile 경로, core ROM |
| byte 15, bit 5–7 | host가 별도로 동기화해 관측한 lease, tile, core ROM의 첫 비영(非零) 조합 |

host와 NES 각각 같은 검출 기회의 여러 비트를 함께 기록한다. 서로 다른 클록의 결과 사이에는 전역 순서를 부여하지 않는다. 상위의 취소로 일어난 plan SPI fault 반향은 host 최초 마스크에서 제외한다. NES 클록이 마지막 검출 전에 멈춰도 지속되는 공개 오류 레벨은 byte 15 상위 세 비트에서 읽을 수 있다. 짧아서 한 도메인에서 샘플되지 않은 사건이나 부팅 이전 이력은 미확정으로 남긴다.

641의 세대 32 대조에서 배치 CRC16, END 세대 불일치, 토큰 준비 전 소비 명령이 각각 `08/00`, `00/01`, `40/00`으로 갈렸다. NES 클록 정지 뒤 core 오류는 `00/80`, 동시 host 두 오류는 `03/00`이었다. E8 명령 판독과 겹치는 정지·core 오류에서도 `00/80`이었다. 여섯 원본을 전달 ELF에 재생해 FINISH phase 2·reason 4, 응답 전체 보존, EA 차단을 확인했다. 정상 32 B 타일 읽기·토큰 소비·EA, STOP 후 재시작도 통과했다. 639 실기 로그의 최초 회로는 여전히 미확정이다.

## 2차 유형 — 첫 화면 전 시간 초과

부팅 stage 0이고 원래 error가 0인 동안 SPI73의 error 바이트에 관측 순서를 담는다. `boot_first_hex`와 `boot_last_hex`의 하위 16비트는 `[순서 1 B][stage 1 B]`다. 실제 SPC 결과와 stage가 기동한 후의 보고는 원래 형식이다.

- bit 0은 안정된 $FFFC 또는 $FFFD 읽기 관측, bit 1은 그 첫 읽기에서 active, bit 2·3은 그 시점까지 첫 번째·두 번째 E0 명령 관측을 뜻한다.
- bit 4는 첫 $7000 쓰기 관측, bit 5는 그 쓰기에서 active, bit 6은 그 쓰기보다 먼저 vector를 관측했음을 뜻한다. 같은 표본에서 동시에 검출되면 bit 6은 이전까지의 상태다.
- 실제 SNES RESET 핀은 이 FPGA top에 들어오지 않는다. ARM이 reset을 확인한 preflight의 E0와, preflight를 연기한 실행에서 reset 해제 뒤 postflight E0를 경계로 사용한다. 두 번째 E0를 postflight로 해석할 때는 같은 실행의 startup reason·post_reason을 함께 확인한다. FPGA 관측기 reset 해제보다 앞선 사건은 관측 범위 밖이다.

별도 RTL 시험에서 vector가 없으면 `00`, 첫 E0 후 active 전에 $7000을 쓰고 vector를 읽으면 `15`, 두 E0 후 active 중에 vector를 읽으면 `0F`였다. 세 번째 대조의 후속 $7000 쓰기는 stage 3으로 보고됐다. MMC551 실패는 독립 표본으로 둔다.

## 보드 비용과 전달 판정

| Quartus Lite 전체 보드 | MMC639 | MMC642 |
|---|---:|---:|
| LE / 조합 논리 / FF | 15,351 / 14,325 / 8,474 | 15,345 / 14,308 / 8,500 |
| M9K | 56 / 56 | 56 / 56 |
| 최저 setup / hold (ns) | 0.565 / 0.153 | 0.437 / 0.156 |
| 최저 recovery / removal (ns) | 1.682 / 0.481 | 1.270 / 0.486 |
| ROM_1CE / ROM_2CE / ROM_OE setup (ns) | 4.165 / 3.923 / 0.895 | 4.575 / 4.136 / 1.082 |

첫 후보는 964 LAB이 필요해 963 LAB에 들어가지 못했다. 두 번째는 이미 전송하는 응답 바이트로 CRC를 누적해 FIT에 성공했지만 새 CDC 첫 단까지 setup −5.477 ns가 나왔다. 최종 후보는 각 2단 샘플러의 첫 레지스터 8개에만 소스 클록에서 11.904 ns 전달 제한과 비동기 hold 예외를 적용했다. 두 번째 단은 정상 타이밍 검사 대상이다. fault 정보는 byte 13 송신 때 확정해 명령 경계에서 증거가 유실되는 경우를 막았다. 전체 STA 5종 및 확인한 세 ROM 핀 모두 양의 여유다. 초기 핀 보고 Tcl은 한글 절대 경로에서 열지 못해 동일 파일을 ASCII 경로에서 실행했다.

ARM은 212,932 B, 여유 60 B이며 파일명 교체 전후 798개 함수의 기계어가 일치했다. 실제 메뉴 marker·5–40/40–55초 집계·정상 base 복귀와 네 복구 실패의 안전 차단, 보드 ROM 5,120 B 전체·STOP, 최종 BI3의 FatFS 프로그래머 바이트 비교를 통과했다. 실기 전송물은 작업 폴더의 `probes/nes-witness642/trial01/MMC642-TRIAL.zip`이다.
