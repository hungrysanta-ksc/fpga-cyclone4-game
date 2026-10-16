# NES204 실제 보드의 직접 타일 경로 연결

## 작업 의미

203까지 따로 검증한 metadata 수신, 표시용 ROM lease, 직접 타일 DMA를 실제 보드 소스에 연결한다. 중복 CHR 읽기와 MCU 픽셀 왕복을 제거하는 60fps 경로의 배선 구현이다. 새 보드 후보는 합성·기능 검증용이며 설치 가능한 펌웨어 짝 또는 실기 성능 승인으로 보지 않는다. 배포186/GBC164/세이브 SRAM은 유지한다.

## 연결과 수명

- 선택184 route02의 고정 소스를 복사하고 old fill/독립 arbiter를 제거한다. source192 내부의 코어 우선 arbiter와 기존 physical READ16을 사용한다. 실제 core request, qualified slot, memory response 포트를 연결한다.
- 실제 memory-clock loader의 BEGIN, write, loaded/count, RUN, fault에서 source204를 만든다. BEGIN마다32비트 serial/등록된 Gray ID를 갱신하며 NES 도메인에서 동기화·안정화 후 허용한다. STOP/write/fault는 즉시 무효화한다. STOP 후 같은 ROM은 같은 epoch이며 serial 소진은 reset 전까지 거부한다.
- 현재 loader의256KiB PRG+128KiB CHR-ROM 완료 조건을 사용한다.32KiB mirror mode를 포함하지만 일반 CHR-RAM 지원은 아니다. 앞으로 mutable source를 추가하면 snapshot/version 계약도 바꿔야 한다.
- capture201의 **내보낸** generation/epoch를 source192에 전달한다. 현재 캡처 중인 generation을 사용하지 않는다. 다음 캡처와 표시 lease는 겹칠 수 있고 정상 retire는 다음 캡처를 지우지 않는다.
- E8/E9/EA SPI200→batch201→source192→bulk193, SNES00:6040..6050 descriptor/consume,40:0800..0fff aperture를 연결한다. 기존 sink packet 영역과 분리한다. sink/direct 버스가 동시에 소유하면 데이터 버스를 해제한다. SPI 중복 선택은 오류로 보고한다.
- SNES195의3935B 본문/4096B ROM을 그대로 넣는다. 실제 C RUN은203 후보를 재사용한다. terminal fault는 도메인별로 등록한 뒤 공통 취소로 전달하며 코어/reader/토큰을 프레임마다 reset하지 않는다.

## 검증 범위

`source01`이 전체 보드 생성본, `test01`이 새 production direct204 모듈의 경로 시험이다. 실제 SPI2.625MHz, source192/arbiter165/READ16, bulk193/194 포트를 사용한다. SNES consume은 testbench 신호 주입 대신604c..6050의 실제 버스 쓰기로 진행한다. 세 장면×3프레임=9프레임,1968B가 기존186 기대값과 일치하고 generation65534→65535→0 및 token/코어 우선 읽기를 확인했다.

계획·기대 픽셀은 보존한 C 산출물이며, CPU request/qualified slot/70ns PSRAM/epoch·frame lease/최종 표시 ACK는 fixture다. **실제 NES 게임 CPU와65816을 동시에 실행한 전체 보드 시험이 아니다.** 잘못된 consume 검사는194 기존 결과를 재사용하며 이번 성공 경로 시험의 역사적 `wrong_checks` 카운터를 새로운 오류 주입 결과로 세지 않는다.

`epoch01`은20검사: 미완료/잘못된 크기/STOP·재시작/멈춘 NES clock 중 write/reload/fault/32비트 소진/reset. loader 상태 입력은 fixture이며 실제 전체 ROM 업로드를 반복하지 않았다. 물리 CDC/MTBF 승인은 별도다.

`map01`의 전체 합성 예상치는19,257 LE/8,586 FF/256,608 memory bits다. 기존184는15,268 LE/6,602 FF였다. 부모·자식 hierarchy 값은 중복 합산하지 않는다. 직접 경로는2,725 ALUT/1,924 FF이며 이전 fill+arbiter의341 ALUT/177 FF보다 크다. 새 epoch104 ALUT/163 FF, lease99 FF도 포함된다. 이는 FIT 수치가 아니며 실제 배치·배선 결과는 `analysis/board204-verification.json`과 raw FIT report를 따른다.

## 배치·타이밍 결과와 미채택 사유

`fit01`은 배치·배선 성공:15,310/15,408 LE,963/963 LAB,47/56 M9K. LE98개가 남지만 LAB 여유는0이다. MAP 예상치19,257을 물리 용량 초과의 최종 판정으로 사용하지 않는다. 한 번의 Fitter 실행 안에서 자동 라우팅 재시도가 있었으며 별도 seed 재실행은 하지 않았다.

`timing01`은 동일 DB/기존 SDC로3corner와 모든 clock pair를 추출했다. nominal 및 기존 implementation 조건의 관련 클록 setup 최저 **−0.638ns**, hold **+0.150ns**다. check_next[17]→reader.check_response_address[21],3논리단/배선4.809ns(74%)가 실제 동기 경로 실패다. STA 실행 자체의 exit0는 timing PASS가 아니다.

새 비동기 경로는 아직 승인하지 않았다. loader.release_reset→run_enable→content_lifetime.invalid→lease/캡처→export.pack_count가19단/15.001ns로 노출된다(도구상 slack−12.865ns). 이 수치는 비동기 관계0.002ns를 적용한 결과라 동기 경로 부족량과 합산하지 않는다. 그러나 **raw loader 상태가 NES 데이터 허용 논리까지 조합으로 연결된 상태**이므로 전체 경로를 false_path로 덮어서는 안 된다. `source_ready=!invalid&&!held&&admitted`, `source_writing=invalid`의 raw 우회부터 고치고 비동기 무효화/동기 재허용을 NES 도메인 경계에서 끝내야 한다. Gray ID 및 새 mailbox held-data/요청 ACK/reset/dual-clock RAM의 정확한 CDC 목록과 bounds도 남아 있다. 이전181 SDC만으로 새 경로가 승인된 것은 아니다.

`paths01`은 재FIT 없이 위 두 실패 경로를 상세 추출했다. IO/CDC 최종 승인·ASM·새 ARM·ZIP·실기 시험은 진행하지 않았다. 이 후보를 배포하거나 기존186과 혼용하지 않는다.

## 다음 판단 기준

먼저 raw loader 상태의 NES 데이터 경로 우회를 없애고 실제 source invalidation/admission 계약을 검증한다. 새 CDC 경계를 구조별로 분류한다. 그다음 tile191의32B register buffer와 bulk193의32B sealed RAM 중복, 가변 row/tag 선택망, 여러 endpoint의 descriptor/token 복사본을 함께 계상해 배치 여유를 만든다. 단일 버퍼로 바꿀 경우 부분 타일이 descriptor로 공개되지 않는 조건, fault/cancel/drain, backpressure와 처리량을 한 경계에서 검증한다. 새로 추가한 경로의 자원 부담을 줄이기 전에 기존 loader를 국소 재작성하는 반복으로 돌아가지 않는다. 단순히 캐시를 없애거나 대기 한도를 늘리지 않는다. 작은 seed/refit 반복·클록 완화·표시 ACK까지 캡처 직렬화는 하지 않는다.

최종 전체FIT/STA/IO와 실제 board→C→SNES 결합 뒤 짝패키지를 만든다. 첫 실측은 SMB3 숫자1+A→첫 레벨 확인→RIGHT+B 유지/A press-release의 연속스크롤이다. 전체16.67ms와 고유 표시 간격이 기준이며 정지 화면/ACK 합계로 대체하지 않는다. collected_runs는 여전히 비어 있다. persistent delta/CHR-RAM/MMC4·5 및 장기플레이·reset 로그는 미완료다.
