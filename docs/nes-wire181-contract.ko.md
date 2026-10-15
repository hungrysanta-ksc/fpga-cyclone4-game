후속 진행: 실제 MCU 표시 변환·새 sink payload와 C출력→SNES 직접 표시 비교까지 완료했다. [현재 범위와 다음 작업](nes-consume181-contract.ko.md)을 먼저 읽는다. 아래는 전송 수신 완료 시점의 기록이다.

# NES181 — 부분 행 전송과 MCU 메모리 재사용

PR113의 부분 행 픽셀을 **exporter → 기존 SPI → MCU 수신기**로 전달하는 후보를 구현했다. CHR 수신을 마친 뒤 `required[2048]`를 픽셀 저장 공간으로 재사용한다. ARM의 수신 구조체는 기존과 같은 **18,064바이트**다. 배포 SNES 소비 경로와 보드 연결은 아직 미완료이며,180 실기의 첫 레벨 정지 해결·60fps를 통과한 것은 아니다.

## 전송 계약

외부 D0/D1/D2/D3 명령, 블록 CRC·토큰·세대·PREPARED/COMMIT 절차와 각 record의 기존 byte 폭은 유지한다. payload version만 `0x1741`에서 **`0x1811`**로 바꾼다. 새 수신기는 구버전을 거부한다. 기존 수신기와 함께 배포하면 안 된다.

| 순서 | record | 의미와 검사 |
| --- | --- | --- |
| BEGIN | kind7/index0 | 상위16비트1811, 기존 geometry counts, 하위3비트 보존 행 수0..7; 나머지 하위 예약9비트는0 |
| geometry | kind0..5 | 기존 순서·인덱스·개수 검사. raster는53비트로 확장 |
| CHR | kind6 | 기존 tile/kind/lane/byte 형식. 모든 required tile 수신 필요 |
| CHR_END | kind7/index4 | 지금까지의 records16/bytes16을 확인한 명시적 메모리 수명 전환 |
| 원시 픽셀 | kind6 | index=slot×256+x, value=0..63. 인덱스 연속·세대·정확한 총량 검사 |
| END | kind7/index1 | geometry+CHR+원시 픽셀 record 수, CHR+원시 픽셀 byte 수 확인 |
| PREPARED / COMMIT | 기존 D3 / kind7/index3 | 수신 완료와 최종 확정을 구분. 최종 POP 확인 실패도 표시 허용 금지 |

새 raw raster는 bit49=1, bits52..50=slot0..6, 나머지 하위49비트=0이다. 일반 raster의 bits49 이상은0이며 기존 팔레트 검사도 유지한다. CHR_END에서224개 행을 확인해 raw 슬롯이 행 순서대로0부터 중복 없이 등장하고 BEGIN의 행 수와 정확히 일치해야 한다.

CHR_END 수락 조건은 수신 상태, geometry6구간 완료, CHR lane0, missing0, 누계 일치다. **이 검사가 끝나기 전에는 required bitmap에 픽셀을 쓰지 않는다.** 이후 `next_kind=7`로 고정하고 `last_tile`을 다음 raw 인덱스로 재사용한다. 늦게 도착한 CHR 형식, 잘못된 색 값, 누락·중복·초과 인덱스는 거부한다. raw가0행이어도 CHR_END는 생략하지 않는다.

`nes_native181_pixels()`는 COMMITTED 상태에서 유효한 슬롯만 돌려준다. 소비 완료·ABORT·reset·실패 후에는 NULL이다. 반환 포인터를 다음 frame까지 보관해서는 안 된다. 새 영구 픽셀 배열·힙·카트리지 세이브 SRAM은 사용하지 않는다. 기존 trace166은 그대로 사용하며 CHR_END를 BEGIN/END/COMMIT으로 잘못 세지 않는다.

후보 파일은 `src/nes/firmware/nes_native181.[ch]`다. 기존 runtime API/type `nes_native165`를 유지하므로 격리된 통합 빌드에서 짝을 맞춰 `nes_native165.[ch]`로 배치한다. 실제180 checkout에 덮어쓰지 않았다. `nes_native_export181.sv` 역시 보드에 아직 연결하지 않은 후보다.

## 검증과 한계

실제180 fill과 SPI RTL, 새 exporter를 동시에 실행했다. 봉인된 frame 조회와 PSRAM 응답은 결정적 fixture다. SPI testbench가 기록한 실제 요청·응답을 새 C 수신기의 `poll/prepare`로 재생하고, exporter의 모든 record를 독립 기대값과 비교했다. 단순 패킷 생성기만 통과한 결과가 아니다. 반대로 실제 PPU·수집기·게임·SNES까지 이어진 통과도 아니다.

| 부분 행 | RTL record | SPI 블록 | 전체 wire byte | 정확 비교 픽셀 | C 확인 경우 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 567 | 20 | 4,861 | 0 | 27 |
| 1 | 823 | 26 | 6,559 | 256 | 34 |
| 7 | 2,359 | 63 | 16,774 | 1,792 | 34 |

C 확인에는 정상 replay, CRC/IO/최종POP 확인/PREPARED IO 실패, 구버전·예약비트·누계·CHR 종료 누락/중복·CHR 미완료·잘못된 raster·raw 순서/색/세대·최종 픽셀 누락, 단계별 ABORT와 재진입, packet 길이·토큰 검사가 포함된다. 구조체 앞뒤 canary도 유지됐다. CHR_END 뒤 required 공간이 덮여도 수신한 CHR tile3/5/7의48바이트는 정확했다.

별도 exporter raw 단계7경우에서는 backpressure 중 데이터 유지, query miss, 잘못된 색, lease 소실, disable, 정지된 소비자의 유한 deadline, reset을 검사했다. 이 시험의 fill 완료는 stub이며 위의 실제 fill/SPI 결합 시험과 구분한다.

ARM Cortex-M4 `-Os` compile에서 old/new 구조체는18,064바이트로 동일했다. GCC의 함수별 stack도 packet88/poll560/prepare40바이트로 기존과 같고 getter는0이다. **전체 runtime link·호출 경로·IRQ 여유1040바이트를 새로 승인한 것은 아니다.** 소비 코드가 연결된 뒤 다시 확인한다.

첫 `test01`은 Windows 절대 경로를 Questa 논리 library로 넘겨 설계 로드가 실패했다. 작업 library를 실행 디렉터리에 복사한 `test02`가 최종 통과다. 라이선스나 제품 RTL 실패가 아니며 원본 로그를 보존했다. raw 단계 오류 시험은 `fault01`이다.

## 속도와 다음 작업

현재 raw는 기존 kind6의2바이트 payload에 색 하나를 실으므로 **픽셀마다6바이트(record header4+payload2)**다.7행1,792개의 유효 색은 raw record만10,752 wire byte를 차지한다. 위 fixture에서 모든 SPI 요청·응답 교환의 길이 합은16,774바이트이며, 양방향을 두 배로 센 값은 아니다. 모델상0/1/7행 전송은 약15.48/20.85/53.16ms였다. 이는 고정된 SPI 시계·SS 간격·즉시 PSRAM 응답을 사용한 모델 값이며 실제 MCU·SNES 표시 지연이나 FPS가 아니다. **최대7행 경로는 이 단순 packing만으로16.7ms를 달성하지 못한다.** 정지 해소만으로60fps 완료라 하지 않는다.

1. 다음은 배포 MCU 변환과 SNES 소비 경로 연결이다. raw 행을 일반 mask/map 검사 전에 분기하고 OBJ 중복 표시를 막는다. 기존 독립 mode3/CGRAM64..127/VRAM 빈 영역/3HDMA 방식을 실제 staging·양쪽 뱅크·최종ACK·STOP에 적용한다. 수신 픽셀은 COMMITTED 이후부터 consumed 이전까지 사용한다.
2. 보드에 실제 PPU color/emphasis, frame181, exporter181/patch_count와 query mux를 연결한다. getter·구조체 이름만 맞춘다고 기존 video165가 raw raster를 처리하는 것은 아니다. 기존7행·512CHR·group32·palette2 한도와 frame lease를 유지한다.
3. 영상 지연 개선은 별도 미완료 항목으로 유지한다. 전체 geometry 재전송 차분/base-generation/최종ACK와 raw 묶음 전송을 검토하되, 추가 영구 frame 배열이나 세이브 SRAM을 사용하지 않는다. 이번 수신 규격을 실기 속도 승인으로 사용하지 않는다.
4. 연결 후 필요한 최소 결합·ARM 전체 stack·FPGA 자원/타이밍·조건부 IO 승인 뒤 SMB3 숫자1→A 실기로 간다. 같은180/044·긴 부팅·이미 통과한 독립 PPU 시험을 이유 없이 반복하지 않는다. 연속 AV→장시간/오류·리셋 로그→입력 유지 순서를 유지한다.

새 FW/FPGA/ZIP은 없다. GBC·164 복구판·180 배포본·이전 완료 근거는 보존했다. [검증 데이터](../analysis/wire181-verification.json)와 [인계](../cores/nes/HANDOFF.ko.md)를 함께 읽는다.
