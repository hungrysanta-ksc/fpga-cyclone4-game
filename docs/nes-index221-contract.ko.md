# NES221: 정확키 슬롯 검색 인덱스

PR120은 `b8de96e`로 머지됐다.220 실기는60.08초/265표시·소리·조작·메뉴 정상이나 스크롤은 미달이었다. 계획 단계34.68초에는 순수 CPU와 callback/소스 대기가 섞여 있었다. 실제 코드에서는 화면의 각 cell마다 현재 프레임 exact key와 영속 slot을 선형 검색한다. 이번은 그 검색을 줄이는 성능 변경이며, 후속 수신량·scroll-map 작업의 우선순위를 확인할 최소 계측을 동반한다. 인덱싱 하나로16.67ms를 달성한다는 계획은 아니다.

## 내용과 수명

`nes_resident221.c/.h`를 ARM 후보의 기존 `nes_resident211.c/.h` 이름으로 사용한다. 역사적211 소스와 봉인 archive는 변경하지 않는다.256 bucket heads와1,152개 next link를16비트로 저장해 **2,816B**를 추가한다. 새 타일/화면 캐시가 아니라 기존 슬롯에 대한 검색 구조다.

- 사용 전 슬롯은 기존 retained key로 인덱싱한다. BEGIN마다 유효 retained slot으로 테이블을 재구성하며 이전 프레임 scratch key를 읽지 않는다.
- 이번 프레임에 선택한 슬롯은 기존 retained chain에서 제거한 뒤 현재 exact key chain에 넣는다. 두 수명을 같은 head/link 배열로 처리한다.
- 충돌은 full key와 kind·used·허용 slot 범위를 모두 비교한다. 후보 중 가장 작은 slot을 선택해 기존 결정적 배정 순서를 그대로 유지한다. OBJ의 exact key는 기존과 같이32비트, BG는64비트다.
- 기존 invalid 우선/사용하지 않은 slot 퇴거 순서는 유지한다. 사용 중인 slot을 퇴거하지 않는다. transformed row/alt 패턴은 기존처럼 다음 프레임의 영속 재사용을 허용하지 않는다.
- 인덱스는 데이터의 유효성을 승인하지 않는다. immutable epoch, 두 bank의 resident bits, target/active 보호, callback 성공 및 최종 실제 표시 ACK·serial/gen/bank commit 조건은 유지한다.
- OBJ 처리에서 BG exact-key scratch가 rank 검사에 재사용돼도 BG used node의 key를 다시 읽지 않는다. lookup은 kind를 먼저 검사하고 BEGIN은 retained metadata만 사용한다. callback 실패/STOP의 abort 이후에는 open/fault gate가 접근을 막는다.

이 변경은 매퍼별 특례를 추가하지 않는다. 물리 원본 키와 row/alt/mask 의미를 유지하지만, 현재의 immutable CHR-ROM 경계를 넘어 CHR-RAM/MMC4/MMC5 지원을 새로 승인하는 것은 아니다.

## 검증

선택 `test03/runtime01/arm01/check01/budget01/release01`.

- 실제220 allocator와221:187프레임/243,645요청에서 **동일 slot, 기존 상태 전체, video scratch, callback 전송 계획** 비교 통과. synthetic scrolling·중복·퇴거·epoch/gen wrap·64비트 차이·같은 bucket256키·full slot·callback 실패·잘못된 commit 포함.
- 합성180프레임242,100요청에서 기존128,588,472 probe →24,314,933 probe +191,818 BEGIN 방문. 합계 약80.94% 감소. hash 계산/초기화 비용을 모두 같은 단위로 환산한 것이 아니며 ARM 시간이나 실기 FPS 수치가 아니다. 남은 invalid/퇴거 fallback은 선형 검색이다.
- 실제 선택 planner와 기존186 converter 비교129프레임/4,234,944참조 바이트,11오류 경계 통과. 합성96스크롤의 패턴/맵 bytes는 기존211과 동일하다. 전송량을 줄인 변경으로 포장하지 않는다.
- 생산 RUN·계획 batching·window·212 sparse consumer 모델 연결:9프레임/361,152참조 bytes 및6오류 경계 통과. 실제 RTL/65816 전체 cosimulation을 다시 실행한 것은 아니다. 프로토콜과 최종 slot/계획이 그대로이므로 기존220 FPGA와212 consumer 증거를 재사용한다.
- 전체 ARM208,068B, static27,964B, foreground34,960B, IRQ508B, **잔여1,992B**. 기존1,024B gate 통과. 인덱스2,816B와 bins96B 및 새 callback/tick 호출을 실제 linked graph에 반영했다. 사운드·입력·STOP/IRQ 플랫폼 명령은 정규화 비교로 동일함을 확인했다. 여유가 미래 매퍼/세이브 기능까지 충분하다는 뜻은 아니다.
- budget 최악2,980B/4,096B, 짧은 버퍼 거부·D1/D0 구분·전송 실패 시 attempted 집계 및 post-STOP 저장 tail 유지 통과.

test01은 샌드박스 GCC DLL 재할당623으로 시작하지 못했다. test02는 호스트 printf64비트 형식과 baseline 함수 이름 치환이 typedef까지 바꾼 하네스 컴파일 오류다. 원본 로그를 보존하고 test03에서 수정 후 통과했다. 제품 오류를 무시하거나 경고를 비활성화하지 않았다.

## 최소 계측과16.67ms 목표

기존 reserved0/1을 `planner_ticks/callback_ticks`로 사용한다. planner 전체 시간에서 emit callback을 분리해 build 단계의 CPU와 finish/drain 대기를 더 좁힌다. 새2개 필드 `d1_payload/d0_clock`만 추가해 D0–D3 수신의 레코드와 조회 부분을 나눈다.10ms bin은 근사이며 각 callback 경계의 양자화 오차가 누적될 수 있다. 실패한 마지막 프레임은 성공한 전체 build 시간에 포함되지 않을 수 있으므로 마지막 bin 차감 해석을 별도로 한다.

추가 게임 중 SD 쓰기/전송/폴링은 없다.221도 수신 형식·화면 전체 계획·맵 좌표 방식은 유지한다.220의 수신26.04ms/완료는 남은 문제이므로 인덱스가 빨라져도60fps가 보장되지 않는다. 다음은 실제221 first-level 결과로 **D1 형식/변경 범위 수신, D0 조회, 원본 좌표 기반 map 갱신**의 비용을 분리하고, 검색·수신·소비를 합친16.67ms 예산에서 진행한다. 진단판만 반복하거나 작은 cache/FIT 조정으로 돌아가지 않는다.

## 배포와 작업 의미

221은 기존220 ZIP에서 ARM firmware와221 경로만 바꾼다. FPGA·212 ROM·타이밍 배선은220과 byte-exact이며 새 FIT/ASM이 없다. game ROM/base/menu/164복원 bytes 보존, saveSRAM 미사용. 실기에서는 아직 성능 향상·60fps를 확인하지 않았다.

**작업 의미:** 실제 재사용 경로에서 반복 검색을 줄여 ARM 화면 구성 비용을 낮추는 구현이다. 동시에 다음 수신·스크롤 개선을 실제 측정으로 선택하게 한다. 시험 절차는 [NES221 안내](nes-game221-ready.ko.md)를 따른다. 최소 안전 조건이 확보된 뒤 실제 SMB3 첫 레벨로 진행한다.
