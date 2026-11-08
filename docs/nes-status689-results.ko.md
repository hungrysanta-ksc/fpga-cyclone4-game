# 689: E0·ACK·queue 공유와 전체 FIT·STA 통과

689D는 688의 ARM·685의 65816 바이너리를 그대로 유지하면서 6 LAB 부족을 해소했다. 전체 Quartus Lite FIT는 15295 LE·963/963 LAB·56/56 M9K로 통과했고, 기존 제약의 최악 setup/hold/recovery/removal은 +0.104/+0.137/+1.460/+0.488ns다. 같은 두 위상106화면 재생은 688과 클록 단위로 일치했다. 실기 기준은 MMC666이며 새 설치본·실물 시험은 아직 없다.

## 실제 교체

E0 snapshot의 가변 CRC 바이트 선택과 가변 송신 바이트 선택을 고정 tap·순환 저장소로 대체했다. 마지막 후보는 변하는 17바이트만 136비트에 저장한다. 고정 F7은 CRC의 초기값과 첫 응답 바이트로 직접 사용하고, 마지막 CRC는 기존 CRC 레지스터에서 보낸다. CRC 순회는 17 host 클록이며, 첫 응답 F7을 보내는 동안 완료한다. 실제 2.625MHz SPI와 네 배 빠른 10.5MHz 비교 시험에서도 바이트·CRC·수락 엣지가 같다. 새 응답 대기나 ARM polling을 추가하지 않았다.

SNES의 6010–601D 쓰기는 동기화된 공통 주소 prefix에서 ACK byte·최종 ACK·DMA 진행을 분기한다. E0 진행 상태는 기존 empty queue·checked ACK 소유 조건을 공유한다. 새 패킷 수락, ACK 쓰기/공개, STOP·fault·RUN 취소가 진행 비트보다 우선하는 규칙은 그대로다. queue 주소는 고정 256B slot과 byte offset을 연결해 slot 간 carry 계산을 제거했다.

E1의 정상 payload는 최대240B이므로 길이 계산을 8비트 payload+9비트 전체 길이로 줄였다. 상위 길이 바이트가 0이 아니면 별도 거부 비트를 남기고 SS 종료 시 반드시 실패시킨다. 상위 바이트·241/255B·CRC/부분 전송 오류는 credit을 공개하지 않는다. 정상 전송의 CRC·범위·길이 검사는 생략하지 않았다.

처음 배치한 후보에서 168MHz loader의 command decode→SPI 충돌/STOP→84MHz E0 snapshot 경로가 −1.122ns였다. 명령 소유권을 기존 첫 바이트 수신 엣지에서 직접 기록해 decode 단계를 제거했다. 지연 엣지를 추가하지 않았고 raw SS/reset 차단을 유지했다. 다른 실패 경로인 bulk token의 수락 조건은 token 데이터 샘플링과 완료 strobe로 분리했다. `consume_token`은 기존 staged 값을 매 host 클록 샘플링하며, 실제 의미를 갖는 `consume` 엣지의 token·credit은 원본과 같다. 무효 strobe 동안의 token 레지스터 값은 달라질 수 있다.

## 전체 회로와 타이밍

각 후보는 다른 RTL 변경을 검증한 뒤 전체 컴파일을 한 번씩 실행했다. seed·핀·SDC·클록 주기·false path를 바꾸지 않았으며, 서로 다른 후보의 최소 수치를 합치지 않았다.

| 후보 | 실제 변경 | LE | FF | LAB | 판정 |
|---|---|---:|---:|---:|---|
| MMC666 | 실기 기준 | 15324 | 8386 | 962 | 기존 FIT·STA 통과 |
| 688 | 누적680 RTL·685 ROM | 15321 | 8389 | 969 필요 | FIT 실패 |
| 689A | snapshot 순회·공통 주소 | 15341 | 8399 | 963 | FIT 통과, setup −1.122ns |
| 689B | 같은 엣지 명령 소유권·bulk token | 15295 | 8400 | 964 필요 | FIT 실패 |
| 689C | F7·CRC 중복 저장 제거 | 15287 | 8384 | 964 필요 | FIT 실패 |
| **689D** | 정상 길이 계산과 오류 거부 분리 | **15295** | **8377** | **963** | **FIT·기존 제약 STA 통과** |

최종 조합 논리는14350개, RAM305264bit·M9K56개다. MMC666보다 배치 LE29개·조합 논리68개·FF9개가 줄었지만 LAB는 하나 늘어 여유가 없다. LE 산술 여유113개를 배치 가능한113개로 해석하지 않는다. 실패한 B/C의 LE는 성공한 D의 배치 비용과 구분한다.

| 최소 slack(ns) | MMC666 | 689D |
|---|---:|---:|
| setup | +0.511 | +0.104 |
| hold | +0.149 | +0.137 |
| recovery | +1.828 | +1.460 |
| removal | +0.393 | +0.488 |
| minimum pulse width | +2.630 | +2.626 |

모두 양수지만 setup 여유가 MMC666보다0.407ns 줄었다. 최악 경로는 loader CRC→pending header error다. ROM_OE/1CE/2CE는 +0.939/+3.553/+3.847ns, BG word의 기존 bundled CDC 제약은 최소+22.578ns, reader 내부는+1.586ns, native MISO는+1.923ns다. 신규 illegal/unconstrained clock은0이다.

기존 외부 IO signoff는 완료하지 않았다. 미제약 input port54개, output port56/57개는 동일하다. input path 수는661→664, output path 수는3005/3008→2991/2994이며 그대로 기록했다. 전체 STA 통과는 기존 보드 제약 범위이고 모든 외부 IO가 검증됐다는 뜻이 아니다.

## 기능·두 위상 일정

- 최종 실제 RTL을 원본688과 두 시작 위상·두 SPI 속도에서 비교했다. 각46개 체크, 총2458113 host 비교 엣지에서 SPI 선택·MISO·SNES 읽기·queue credit·진행 공개 시점이 일치했다. 최대256B packet을8개 전송해4slot wrap을 검증하고, ACK/STOP과 E0 snapshot 중첩·잘못된 길이 거부도 확인했다.
- loader는256개 opcode·부분 bit 전송·정지된 clock에서 SS 해제를 두 위상에서 대조했다. bulk는 위상별34회 정상 consume·66회 거부와 STOP/fault 뒤 부분 token 무효화·복구를 검사했다. token은 실제 consume 엣지에서 독립 비교했다.
- 688의 실제 ARM map/조회 소유권47개·SEAL23개·입력56개·메뉴/base5개·marker4개, 동일685 CPU의 beam/STOP/cold/최종 ACK 검사는 같은 바이너리 hash에 연결했다. 새로운 실물 메뉴 복귀 시험은 아니다.
- 새53화면×두 위상 재생의 작업량·픽셀·tile·map·E9 묶음·입력 CRC/POP·최종 ACK·모든 표시 간격은688과 같다. 초기 A 인터페이스로 실행한 모델 재생에 최종 D의 실제 serial boundary 비교를 연결했다. 모델에 배치 지연을 임의로 넣거나 실제 FPGA 전체 공동 실행으로 주장하지 않는다.

| 보호조건/시간 | 위상1 | 위상2 |
|---|---:|---:|
| 951 공개 | 236선 | 236선 |
| 955 큰 선행 map DMA | 1536B | 1152B |
| 955 ACK 전7블록 완료 여유 | 1.452186ms | 1.503415ms |
| 952 표시 / 957 최종대기 | 3 / 0회 | 3 / 0회 |
| MMC666 대비 밀집 평균 | −0.051906ms | −0.001248ms |
| MMC666 대비957 마지막 ACK | −0.188944ms | −0.385896ms |

첫 BG ROM창·큰 묶음·마지막384B 선행 DMA·911 마감도 유지했다. 위상2의 밀집 개선은 약1.25µs로 작다. 실기26.84ms에 모델 비율을 곱하거나 새 FPS를 주장하지 않는다.

ARM은688의 SHA256 `6685fdaea7b0bccad4d0a9303eb881bd76dea47831e4cb82981208f89b851148`, Flash212984B/free8B, 추가 ARM RAM0B다. CPU는685의 `c79e2b013701fa9cde8a8164da3f0545f2b7c916b8477aa6d74ec405002ebf2e`이며 ROM·WRAM·명령 일정이 바뀌지 않았다.

## 재현과 다음 순서

[검증 JSON](../analysis/status689-verification.json) · [원시 archive](../analysis/status689-archive.json).

최종 생성은 `tools/prepare_nes_status689.py --base <688 board> --out <새 경로> --owner --compact --length`다. ARM/CPU 빌드는 재실행하지 않는다. 실제 RTL 검사는 기존 Starter FLOAT 한 좌석에서 순차 실행했고, Lite 전체 컴파일·STA 경로 보고·두 CPU 일정은 별도 근거로 묶었다. 초기 재생 wrapper가 testbench를 보드 파일로 찾은 오류는 경로 검사만 수정했다. 비ASCII 경로의 Quartus 보고서 호출 실패와 보고 Tcl의 줄끝 차이도 원시 로그를 보존하고 분석 경계만 바로잡았다. 실패한 A/B/C와 최종 D를 덮지 않았다.

다음은689D 보드와 고정688 ARM·685 CPU를 묶어 고유 설치/로그 이름의 제한 실기 전달본을 준비한다. 새 기능이나 같은 발행/seed 미세 조정은 더하지 않는다. package hash·실제 programmer/loader·STOP/base/menu 경계를 확인하고 MMC666과 같은 첫 레벨 동선에서5–40초·40–55초를 비교한다. RESTORE는 제외한다. 새 실기 결과 전까지 제품·FPS 기준은MMC666을 유지하며, LAB여유0·setup0.104ns·Flash8B와 외부 IO 미완료 범위를 전달 문서에 남긴다.
