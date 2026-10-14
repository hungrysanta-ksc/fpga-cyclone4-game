# NES174 후보 — 서로 다른 타일의 비트평면 보존

## 목표와 현재 판단

173에서 재현한 프레임 거부를 실제 데이터 표현으로 수정했다. SMB3 모델의 프레임24는 이전185행에서 거부되던 상태에서224행 수집에 성공했다. 프레임24·25를 실제 C 변환기와 SNES CPU/DMA/PPU로 출력한114,688픽셀이 NES 출력과 일치한다. **실기 정지 해결이나60fps 달성은 아직 확인하지 않았다.**

FPGA 배치는 성공했지만 실제 클록 기준 memory setup **-0.807ns**다. **후보 미채택·실기 ZIP 없음**. 174 단독 MCU 빌드를 SD에 설치하지 않는다. 이번에173·044를 다시 시험할 필요도 없다.

## 표현과 호환성

기존 수집기는 같은 타일의 fineY 차이만 담았다. 모델frame24,line193,dot232의 low21e150/high21e1ff는 타일1e15/1e1f와 fineY0/7을 모두 보존해야 한다.

- low/high 이벤트 때 두 원본 타일을 required set에 표시한다. 잘못된 주소·plane lane·속성·위치·OBJ pair는 계속 거부한다. 원본 CPU/PPU 동작과 메모리 응답 시점은 바꾸지 않는다.
- 내부64비트 이벤트의 bit61은 cross-tile, low tile은 `{60:57,24:16}`, low fineY는55:53, mixed 표시56이다. 일반 이벤트는 기존 형식을 유지한다. cross-tile일 때만 기존 logical tile 영역을 low physical tile 표현에 사용한다.
- 예외128개 한도는 유지한다. 예외 하나를32비트로 바꿔 `[31:19] low physical tile`, `[18:6] row*33+column`, `[5:3] high fineY`, `[2:0] low fineY`를 저장한다. 좌표 범위0..7391이다. 같은 타일 예외도 low tile을 명시한다.
- MCU는 원래32비트 예외 배열을 사용하므로 구조체 크기가 늘지 않는다. map의 high 타일과 예외의 low 타일을 모두 요구하며, 원본이 빠지면 합성을 거부한다.
- C 변환은 필요한 행의 low plane만 교체한다. cross-tile cell은 bit63과 group/column으로 충돌 없는 별도 키를 사용한다. 일반 패턴 중복 제거는 유지하며1024패턴 한도를 넘으면 기존 오류로 중단한다.
- wire BEGIN magic은 **1651→1741**, kind3 payload는 **3→4바이트**다. 구형/신형 혼합은 BEGIN 단계에서 거부한다. FPGA와 MCU를 반드시 한 쌍으로 배포해야 한다. SNES 수신 명령·ROM은172와 동일하다.

## 확인한 범위

| 항목 | 결과 |
| --- | --- |
| 최소 RTL 경계 | pair8경우, required set24,576조회,224×33셀 compact,32비트 예외·release 통과 |
| 실제 SMB3 재현 | 26프레임, CPU ROM1,232,788회·PPU ROM303,662회 비교 통과;12~26 프레임 유효 |
| 픽셀 | frame24·25의 SNES 출력114,688픽셀 일치 |
| SPI→C | 위상0/3.5ns 각각1,733레코드·47블록·12,587wire바이트; C191호출, CRC/IO/ACK 확인 실패 거부 |
| C 부정 입력 | 구형 magic,3바이트 예외,범위 밖 좌표,누락 low tile,중복 cell 거부 |
| MCU 전체 링크 | static26,564 / foreground37,328 / IRQ508 / margin1,024바이트 |
| FPGA |15,076LE,963LAB,36M9K; 배치 성공, 실제 memory setup-0.807ns로 미채택 |

프레임 수집 모델은 기존 CPU/PPU/MMC3+70ns READ16 메모리 모델에 배포 수집기4개 중2개를 교체했다. 매 프레임 즉시 release하며 실제 fill/export/MCU/SNES 소비 속도·버튼 입력을 포함하지 않는다. 모델frame24와 실기 마지막generation30을 같은 사건으로 단정하지 않는다. 부팅 중1~11의 비유효 상태와 time0 초기화 경고46개는 원문에 남겼다.

픽셀 비교의 PC 업로더가 계산한 다음 프레임24바이트 갱신은 **MCU 전송량 개선 결과가 아니다**. 두 화면의 잘린 표시 영역 RGB가 같은 것도60fps 증거가 아니다. 실제173의 build+seal 평균203.125ms 문제는 그대로 남는다.

## 타이밍 미달과 다음 작업

3개 corner·4개 clock의 setup/hold를 별도로 평가했다. NES setup+6.370ns, host+1.483ns, board+121.853ns, 최소hold+0.146ns다. 최악은 기존 `control.load_valid → loader.fault` 경로이며4단계 논리와5.372ns 배선 지연이 포함된다. `check_failed → fault/loaded_bytes`도 미달이다. 새 영상 수집기 경로가 빠르다는 이유로 전체 timing을 통과 처리하지 않는다. 원래의 더 엄격한 budget 보고서도 보존했다.

1. 위 ROM 적재/실패 제어 경로의 실제 fanout·배치와 기존 실패 실험을 대조한다. 변경 경계를 정한 구조 개선 한 번을 검증한 뒤 FIT한다. 무변경 FIT·seed 순회·클록 완화·false-path 추가는 하지 않는다. 이미 실패한 fault/counter 식의 반복도 피한다.
2. 전송 비용은 별도 개선한다. 현재 seal의 map4096+CGRAM512+OAM544 및HDMA 전량 전송과 패킷마다 ACK 대기가 남았다. 패턴별16바이트 요청 묶기, 필요 테이블 영역 감소/차이 전송을 우선 검토한다. 이미 있는 SNES 차이 DMA를 다시 만들지 않는다.
3. 묶음 전송은 기존240바이트 payload·연속 offset·완전한 ACK 소유권을 유지하는 방향으로 검토한다. 임시 공간은 기존 candidate 내 해당 단계에서 아직 사용하지 않는 영역의 수명으로 해결해야 하며, **이 최적화는 아직 구현·검증하지 않았다**. 두 번째 전체 MCU 프레임이나 세이브 SRAM을 쓰지 않는다.
4. 타이밍·변경 경계·ARM 한도를 통과한 MCU/FPGA 쌍으로 실제 SMB3에 돌아간다. 최소한의 검증 뒤 실기를 우선한다. 연속 AV → 장기 플레이 및 오류/본체 리셋 로그 → 입력 유지 순서를 유지한다.

## 재현과 보관

`tools/nes_cross174.py`의 `prepare()`는171/map02와172/client01로 FPGA 후보를, `prepare_mcu()`는173/arm04로 MCU 후보를 만든다. `tools/probe_nes_cross174.py`는 기존frame165/frame03과 이 후보에서26프레임 재현 입력을 준비한다. 준비된 `run.py`는 기존 FLOAT wrapper로 실행한다. `cross174_tb.sv`, `cross174_spi_tb.sv`, `cross174_host.c`, `cross174_receiver_host.c`가 변경 경계 시험이다. `test_nes_cross174.py`는 수집한24·25 프레임과 실제 C 실행 파일을 받아 SNES 픽셀을 대조한다.

비공개 `probes/nes-cross174`의 evidence/manifest·progress를 읽는다. unit01은 sandbox TEMP 경로 불일치로 RTL 실행 전 실패했고 unit02가 실제 통과본이다. armcheck01의 host DLL 오류는 검사 시작 전 실패이며 라이선스/RTL 결함이 아니다. armcheck03은 최종 설명·소스 해시가 맞는 검사본이다. 완료된 증거는 수정·재기록하지 않는다. GBC·164·세이브 영역·실행 중 SD 쓰기·정상 종료 경로를 변경하지 않았다.

[검증 수치와 해시](../analysis/cross174-verification.json) · [다음 작업 인계](../cores/nes/HANDOFF.ko.md)
