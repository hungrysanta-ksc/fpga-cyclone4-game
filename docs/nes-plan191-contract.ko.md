# NES191 metadata 계획과 FPGA 타일 생성 후보

PR117의188–190 후보에 이어지는 단계다. 배포186 코드는 변경하지 않았다. 새 실기판/FIT/전체 ARM 승인이나60fps 달성 결과가 아니다.

## 작업 의미

기존 변환기의 geometry·팔레트·슬롯 배치 판단은 MCU에 남기고, CHR 픽셀 바이트를 읽어 SNES 타일로 만드는 부분을 FPGA로 분리했다. 목적은 CHR 대량 데이터가 FPGA→MCU→FPGA를 왕복하는 비용을 줄이는 것이다. 이번 구현은 그 분리 경계의 출력 동등성을 확인한다. 실제 원본 메모리와 카트리지 읽기창은 아직 연결하지 않았다.

`tools/nes_plan191.py`는 동결된 배포186 `nes_native_video165.c`를 엄격한 단일 문자열 치환으로 변환한다. 원본 해시와 생성물 해시는 검증 JSON에 고정한다. 기존 geometry/순서/슬롯/팔레트 epoch/검증을 유지하고, 새 슬롯마다 하나의 계획을 callback으로 내보낸다. 전체 프레임 계획 배열은 production 후보에 추가하지 않는다.

계획은 generation, BG/OBJ/zero 종류, 출력 slot, 원본 tag,16개 plane별 행 번호, OBJ mask,8개 선택적 대체 low-plane tag를 담는다. C 구조체는 host에서40B다. 일반적인 wire 표현은16B+대체 tag당2B로 **추정**했으며 실제 codec은 아직 없다. 현재 receiver의 tag/kind 목록과 COMMITTED 상태는 계속 필요하다. CHR 데이터 바이트를 바꿔도 계획이 같다는 검증이 수신 ABI·메모리 축소 또는 CHR ingest 제거를 뜻하지 않는다.

## 타일 생성과 수명 계약

`nes_tile191.sv`는 한 계획과32B 타일만 보유한다. BG는 행별 low/high mapping으로16B SNES2bpp를 만들며 cross-tile 예외는 해당 행의 low plane만 다른 tag에서 읽는다. OBJ는 행 mask를 적용하고32B 중 상위 plane16B를0으로 채운다. 명시적 BG slot0은 원본 읽기 없이0으로 채운다. raw 행→8bpp 경로는 기존 C 구현 그대로이며191 FPGA 구현 범위가 아니다.

메모리 주소는 `{tag13, plane1, row3}`다. 실제 backend는 kind와 generation도 사용해 올바른 봉인된 원본을 선택해야 한다. 응답 주소·generation·error를 검사한다. 소스는 요청부터 타일 출력 완료까지 불변이어야 한다. live CHR-RAM이나 mapper 전환 이후 PSRAM을 그대로 읽으면 fetch 시점과 다른 바이트가 될 수 있다. generation 숫자만 일치한다고 내용 불변이 보장되지 않는다.

32B payload에는 reset을 넣지 않고 모든 바이트를 작성한 후에만 출력한다. lease 취소는 즉시 출력 valid를 내리고 다음 클록에 fault 처리한다. STOP/reset은 ownership을 폐기하고 backend cancel을 요구한다. 새 명령은 `mem_idle && !mem_response`일 때만 받는다. backend는 이전 응답을 flush한 후 idle을 선언해야 한다. stopped-clock 재시작 전체 경로 검증이나 물리 CDC 승인으로 확대 해석하지 않는다.

기본4096클록 제한은 메모리 대기와 출력 backpressure를 포함한 유한 한도다. 실제 arbiter에 연결한 뒤 합법적 지연으로 검증해야 하며 지금의 값은 실기 처리량 보장이 아니다. 오류는 STOP/reset 전까지 sticky다. 최종 controller가 오류→STOP을 연결해야 한다. 이 모듈의 done은 타일 소비 완료이며 화면 표시 ACK가 아니다.

## 검증 결과

SELECT `probes/nes-plan191/test03`, `faults01`, `evidence01`.

- 변경 없는 실제186 C 변환기가 생성한 BG/OBJ 바이트를 기준값으로 사용했다. 소프트웨어로 새 변환기를 재구현한 기준값이 아니다.
- 합성8장면97계획/1840출력 바이트가 RTL 결과와 모두 일치한다. BG 행 mapping/cross-tile, OBJ mask/겹침/flip/팔레트 epoch 분할, fine_x, raw0/1/7행을 포함한다.
- 각 장면의 전체15912B host video metadata가 기존 C와 같다. CHR 데이터 전체를A5로 바꾼 재실행도 모든 계획과 metadata가 같다. raw 픽셀 입력은 바꾸지 않았다. host ABI 수치이며 ARM stack/RAM 승인이 아니다.
- 읽기 ready 및 출력 ready를 간헐적으로 낮추고 응답을1..5클록 지연했다.1304회 원본 읽기 결과가 일치한다. 이는 작은 봉인 fixture이며 실제 PSRAM/arbiter 처리속도나 게임 FPS가 아니다.
- 부정9사례: 계획 generation, 잘못된 OBJ slot, 응답 generation/주소/error, 무응답 timeout, WAIT 중 lease 취소, STOP 후 backend flush 전 재시작 차단, 출력 대기 중 lease 취소.
- 초기 test01/prepare01은 legacy wrapper로 인한 치환 횟수 오류, test02는 host C indentation 경고로 실패했다. 원본 기록을 보존하고 수정한 test03을 선택했다. prepare02는 중간 생성 확인이며 별도 기능 통과 주장이 아니다.
- 이전186/실기186/187/188/189/190 동결 파일을 해시 대조했다. 현재 증거의 원본 로그·vectors·source pins를 별도 manifest로 동결한다.

## 전송량과 자원 판단

| 장면 | 계획 수 | 예상 계획 B | 출력 B | cross-tile 계획 수 |
|---|---:|---:|---:|---:|
| 0 | 9 | 144 | 144 | 0 |
| 1 | 10 | 164 | 160 | 1 |
| 2/3/4 각각 | 12 | 196 | 224 | 1 |
| 5/6/7 각각 | 14 | 228 | 288 | 1 |

합계1580B 계획 대1840B 출력은 이 합성 장면들에 한정한다. 일반 BG는16B 계획=16B 출력이고 cross-tile은 오히려 커진다. OBJ는16B 계획으로32B를 만든다. 따라서 계획 전송만으로 대폭 개선됐다고 주장하지 않는다. 왕복 제거와 안정된 패턴/계획 재사용이 함께 필요하다.

기존2.625MHz SPI에서60Hz당 이상적 payload 예산은5468.75B이며 제어/대기/다른 통신을 빼기 전 값이다. 새 BG512개만 매번16B 계획으로 보내도8192B다. 모든 타일을 매 프레임 재계획·재전송하는 구조는 목표와 맞지 않는다. 초기 keyframe과 지속 스크롤 delta를 구분하고 수집 겹침도 유지해야 한다.

배포186은13466LE/939LAB/42M9K, 여유24LAB/14M9K다.188의4M9K 예상치와191의32B payload·계획 레지스터·제어 회로는 아직 함께 FIT하지 않았다. 현재 코드는32bit watchdog와 가변 행/tag 선택을 포함한다. 작은 byte 수가 LAB에 들어간다는 증거는 아니다. 원본 snapshot/cache 추가 비용도 미확정이다. 세이브 SRAM은 사용하지 않는다. host 시험의 전체 프레임 비교 배열은 MCU 구현 제안이 아니다.

## 다음 구현

1. 현재 qualified CHR source reader의 fetch-time tag/kind/내용 lifetime과191의 lease를 연결한다. 실제 변경 가능한 CHR-RAM을 재조회해도 된다고 가정하지 않는다. STOP/오래된 응답 배제와 source 보유 기간을 같은 경계에서 검증한다.
2. 만들어진 타일을188 불변 읽기창 및 SNES-ready section/descriptor로 직접 공급한다. MCU가 타일 payload를 SPI로 다시 공급하는 경로를 bypass라고 부르지 않는다. 계획 codec/ACK/STOP 및 최종 displayACK는 별도 실제 연결이 필요하다.
3. 안정된 pattern identity/내용 generation·delta와 수집 겹침을 포함해16.67ms 전체 예산 및 메모리/포트/LAB 표를 확인한다. MMC4 latch/MMC5·CHR-RAM·save/load/mute/frameskip 요구를 잃지 않는다. 조건을 충족한 최소 경로만 FIT/IO와 실기 짝패키지로 진행한다.

동일 generation의 실제 첫 레벨 스크롤 source/출력 자료는 아직 없다. 사용자 절차는 숫자1 타일+A→레벨 확인→RIGHT+B 유지+A press/release 반복이다. 이번에는 실행하지 않았다. 합성 결과를 실제 스크롤 성능으로 바꾸어 표현하지 않는다. 일반 FIFO 시험 확대·무변경 긴 boot/FIT·186/044 복원 반복은 다음 단계가 아니다.

186/GBC164/저장 영역/완료 archives 보존. 약60fps+사운드 확보 후 장기 플레이와 오류·reset 로그, 입력 유지 품질 순서로 진행한다.
