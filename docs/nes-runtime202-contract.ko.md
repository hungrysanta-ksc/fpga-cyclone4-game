# NES202 직접 타일 경로의 RUN 통합

PR117 같은 branch의 **컴파일 전용 후보**다. 배포186, GBC164, 세이브 SRAM은 유지한다. 보드201 source/descriptor 경로가 아직 완성되지 않아 이 ARM 바이너리를 기존 FPGA와 함께 설치하면 안 된다. 새 ZIP이나 실기 시험판은 만들지 않았다.

## 작업 의미

기존 RUN은 geometry를 받은 뒤 MCU가 BG/OBJ 픽셀을 만들어 SPI로 다시 올렸다. 이번 후보는 실제 실행 함수에서191 planner가 만든 계획을200 전송 서비스에 넘기고, FPGA가 준비한 타일의195 직접 DMA 경로를 사용한다. 단독 코덱 시험을 추가하는 대신 실제 수신기·실행 루프·표시 코드의 호출 순서를 결합했다.

**MCU에서 SNES로 보내던 기존 BG/OBJ DATA 업로드는 RUN에서 제거했다.** 다만 FPGA→MCU의 기존 CHR 수신/검증은 그대로다.191 planner가 요구하는 tag/kind 검증을 아직 이 자료로 수행하므로, 입력 CHR 바이트를 단순 삭제해서는 안 된다. 실제 보드 연결과 metadata-only 입력 프로토콜이 다음 필수 작업이다. 전체 전송량 절감이나60fps 달성으로 해석하지 않는다.

## 구현과 소유권

`nes_runtime202.py`는 선택된195 sink와186 수신기·플랫폼,191 planner,200 service를 후보 디렉터리에 모은다. 공개 `nes_runtime202.c/h`를 기존 `nes_native_runtime165.c/h` 이름으로 배치해 실제 호출부에 연결한다. 기존 파일과 완료된 증거는 수정하지 않는다.

실행 순서는 다음과 같다.

1. 기존 D0/D1/D2/D3 수신 검증과 PREPARED/COMMIT을 완료한다.
2. sink BEGIN →191 plan/200 emit →200 finish로 계획과 타일 수신을 완료한다. 계획 credit 대기 중에도195 op7을 처리해 가득 찬 타일 버퍼를 비운다.
3. 기존 metadata/raw 업로드와 sink SEAL을 수행한다. 최종 ACK와 표시 generation 일치를 확인한다.
4. 표시 frame 수와 마지막 표시 시각을 기록한다.200 retire의 EA와 NES-domain 완료 응답을 기다린다.
5. retire까지 성공한 경우에만 MCU receiver를 consumed/IDLE로 전환한다. 다음 frame BEGIN은 그 뒤에 받는다.

최종 표시가 완료돼도 retire가 실패하면 표시된 frame은 수에 포함하지만 현재 receiver는 COMMITTED로 남는다. 실패 후 재시도·다음 BEGIN은 없고 기존 호출자가 common STOP/로그/메뉴 복귀를 맡는다. 이미 성공한 표시를0프레임으로 숨기지 않는다. 이 카운터는 FPS 측정값이 아니다.

200 service의 callback은 기존 RUN transfer/guard를 사용한다. audio/input/fault/deadline 서비스는 완결된 SPI 거래 사이에서 수행하며 SPI 중 재진입하지 않는다. 제한을 늘리거나 프레임별 reset을 추가하지 않았다.201의 이전 표시 lease와 다음 캡처 분리도 유지한다.

## ARM 메모리

첫 전체 링크는 성공했지만 RUN/IRQ를 포함한 여유가812B로 기존1024B 기준보다 작았다. 이 결과 `arm03/check02`는 **미채택**이다. 기준을 낮추지 않았다.

표시 window의 E1 전송은 수신 payload를 사용하지 않는다. 후보에서 `tx[259]+rx[259]`를 `tx[259]` 하나로 바꾸고 기존 DMA의 TX==RX 계약을 사용한다. 원본 packet 포인터는 별개이므로 전송 후 last-token 복사는 유지된다. `send`의 compiler stack은544→288B, 전체 RUN 경로는37232→36976B로 줄었다. 이는256B 스택 감소이며 전송속도 향상 수치가 아니다.

최종 선택 `arm04/check03`:

| 항목 | 결과 |
|---|---:|
| 전체 펌웨어 링크 |203848B, SHA256 `e7d857d44e54560d830072912a97d03d0d20ba3057af4074a196d0cccca87a7e`|
| static RAM |26872B|
| RUN foreground 상한 |36976B|
| SysTick/TIM2/NMI 보수적 reserve |508B|
| 남은 여유 |1068B|
| 유지한 최소 기준 |1024B|

간접 callback을 포함한116개 도달 함수와 라이브러리·플랫폼 명령을 확인했다. 기존13개 reviewed body는 주소 재배치 외 동일하다. 이것은 링크 분석에 따른 보수적 bound이며 실제 high-water 측정, 모든 메뉴/GBC 호출 그래프, 전체 보드 승인과 같지 않다. 최소 기준보다44B만 남으므로 관찰용 버퍼를 추가할 여유로 간주하지 않는다. 추후 입력 CHR 중복 제거와 메모리 재사용을 우선한다.

## 검증과 한계

`test05`는 실제 RUN→186 receiver→191 planner→200 service→195 sink→184 window 코드 전체를 실행한다. 하드웨어 SPI/PSRAM 타일 생성/최종 SNES ACK는 모델이다.

- 동일 세션에서9장면: 일반 BG/OBJ, low-plane 예외, raw1/7행, raw→normal, 연속 normal. 세대65535→0과 tick32 wrap을 포함한다.
- fixture를 실제1813 wire record로 직렬화하고 CRC/논리 count/CHR_END/PREPARED/COMMIT 검사를 거친다. receiver 필드에 완료 상태를 직접 주입하지 않는다.
- 실제 생성한 계획을 source byte로 해석한100개 타일을 기존186 converter의 BG/OBJ 출력과 비교한다. map/CGRAM/OAM/HDMA/raw 등 전체 video struct도 동일하다. 기존 BG/OBJ DATA 업로드를 호출하면 실패한다.
- 잘못된 SEAL ACK, 타일 수신 중 deadline, 서비스 실패, retire 응답 정지, 잘못된 descriptor generation, 수신 CRC 오류6경로에서 terminal/no retry를 확인했다. retire 실패만 실제 표시1회로 기록하고, MCU 자료는 소비하지 않는다.
- transfer14403회/service34399회는 작은 fixture record와 단일타일 descriptor 모델에서 나온 호출 수다. 실기 비용·fps·효율 측정으로 쓰지 않는다.

`dma02`는 배포186의 실제 DMA C를 register 모델로 실행했다.1..259B ×3진행 간격=777정상 전송,259개 byte 위치의 RX DMA 오류에서 송신 원본·buffer guard·stream 정지·no retry를 확인했다. TX==RX는 새 드라이버를 만들지 않고 기존198 검증 범위를 E1 최대 길이로 확장했다. STM32 bus/WCET 실측은 아니다.

기존201 RTL와195 actual65816 결과는 재사용할 뿐, 이번에 C+RTL+65816을 동시 실행했다고 주장하지 않는다. 새 FIT/STA/IO/CDC 승인이나 물리 프레임 측정은 없다. `collected_runs=[]`, 199 합성17.944ms도 여전히16.67ms를 넘는다.

보존 기록: test01은 sandbox DLL623 시작 실패, test02는 하네스 들여쓰기 경고, arm01은 GCC13의191 배열 인자 선언 불일치, arm02는 후보 version 문자열이 기존 sysinfo 길이를 초과한 실패다. 선언은 후보에서만64원소로 맞추고 version은 `NES-RUN202-DEV`로 줄였다. arm03/check02는 위 메모리 기준 실패다. test03/04와dma01은 중간 통과 기록이며 최종 선택은test05/dma02/arm04/check03이다. 기존 실패·완료 자료는 덮어쓰지 않는다.

## 다음 작업

1. 실제 loader content epoch/ROM ready/write와 board SPI/descriptor mux,192 source에201 **내보낸 표시 lease**를 연결한다. 현재 캡처 generation과 혼동하지 않는다.201 source 허용은 immutable CHR-ROM에 한정한다.
2. exporter/receiver를 함께 바꿔 geometry/tag/kind 완전성을 검증하면서 기존 CHR payload/fill 왕복을 제거한다. raw scratch의 수명 전환도 함께 보장한다. 계획만 연결하고 old fill을 남긴 상태로 성능판을 배포하지 않는다.
3. 실제 BG/OBJ가 지나가는 최소 board→C RUN→SNES 결합, 변경된 전체 ARM·FPGA FIT/IO/메모리 예산을 확인한다. 독립 코덱·boot·seed FIT 반복은 생략한다.
4. 짝패키지에서 SMB3 숫자1+A→첫 레벨 확인→RIGHT+B 유지/A press-release 반복으로 전체16.67ms 예산과 고유 표시 간격을 측정한다. 정지·오프닝·ACK수/60초로 대체하지 않고 frame별 SD 기록도 하지 않는다.

persistent delta/base generation/bank/slot/epoch/CHR-RAM write와 MMC4/5 메모리 목표는 열려 있다. AV약60fps→장기 플레이/오류·reset 로그→입력 유지 품질 순서를 유지한다.
