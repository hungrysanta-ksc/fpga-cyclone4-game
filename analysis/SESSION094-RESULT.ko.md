# NES094: CF86 MCU 세션 보호

이번 범위인 CF86 상위 MCU 세션 보호와 ARM 호출 연결은 달성했다. CF86 전용 MCU 세션에 시작 조건과 유지되는 실패 상태를 연결했다. 정상 80/96KiB 전체 적재·비교를 포함한 호스트 63경우와 보호 제거 대조 4개가 통과했고, 같은 핵심 C 9파일을 사용한 ARM 펌웨어 180928바이트를 링크했다. 실제 CF86 RTL 파형 재생과 실기 쌍은 다음 단계다.

PR43 병합 `b13a379730994ddd8095aea8bad1dcd9c48b323b`에서 시작했다. [계약](../docs/nes-session094-contract.md), [검증 수치](session094-verification.json)를 함께 읽는다.

## 구현

- `CF86`만 수락한다. CF44/68/85/87과 잘못된 F0/F1은 BEGIN 전에 거부한다. 구성 후 기존 bounded RDY 대기를 유지하고, DONE/RDY·RESET·USB IRQ·SD offload·공유 오류를 확인한 다음 GPIO를 인수한다.
- 짧은 식별 명령과 ROM 전송의 비트 경계·샘플 직전에 상태를 검사한다. 관측한 고장은 MCU 세션의 FAILED 상태로 유지한다. 기존 오류 초기화, RDY/DONE 복귀, 재진입으로 풀리지 않는다.
- 고장 뒤 불확실한 DATA/ACK 재전송, 자동 STOP, 파일 close, 기본 FPGA 재구성을 시도하지 않는다. CS 비활성/SCK LOW로 전송을 취소하고 RESET 유지·USB 차단·검증 결과 취소를 적용한다. 정상 전체 CHECK/FINISH/STOP 뒤에만 기존 기본 FPGA 복귀를 진행한다.
- 044/056 기존 함수 prefix, 077 native SD, 076 메뉴 판정, 기존 main의 수동 진입은 유지한다. 새 `fpga_n86.bi3` 이름은 후보 식별이며 아직 배포 파일이 아니다. RUN은 호출하지 않는다.

## 근거와 한계

호스트 63경우에는 정상 81920/98304바이트 전부 비교, 기존 오류 37개, 시작 대기 실패, DATA/CHECK/ACK/FINISH/STOP/CF 중 RDY 상실, DONE/소유권/공유 오류, 잘못된 식별 및 시작 조건을 포함한다. 파일/구성 모델도 FAILED 이후 호출을 거부한다. 보호 제거 대조는 RDY 검사, sticky 상태, verify 오류 전파, CF 식별의 네 가지다.

ARM은 동결077의 새 복사본에 적용했다. 펌웨어 180928바이트, SHA256 `70aa72fa1a70a90d501bac386ff4d159f46a12a48e15f0880c95f6fd78d208da`. main 수동 표식 3개와 공유 run 호출/분기 2개, 실제 probe의 CF86 비교·arm-before-GPIO, SPI·verify의 세션 검사 호출을 확인했다. 호스트와 ARM의 핵심 9파일이 같고 공유 상태 함수 7개도 같다. 호스트 전체 `nes_menu_return.c`는065에서 생성되며 ARM은076 메뉴 whitelist를 유지한다. 전체 파일이 같다고 주장하지 않는다.

FatFS 호출·카드·FPGA 응답·틱·GPIO는 모델이다. 시작 RDY 하위 대기도 이번 호스트에서는 모델이며, 실제 bounded 함수는 ARM에 연결됐다는 증거만 추가했다. 새 C를 실제 CF86 RTL에 재생하지 않았으므로 과거070 파형 성공을 승계하지 않는다. GPIO 검사 비용에 따른 실제 전송 시간, 짧은 RDY 펄스 포착, 최신 전체 native SD 세션, 외부 전기 조건과 두 클록 동시 정지는 이번 시험이 보장하지 않는다. 093 SDF 분석은 MCU polling의 물리적 응답 시간 증거가 아니다.

host01의 존재하지 않는 enum38, ARM01의 복사본 캐시 해시 검사, ARM02의 긴 VERSION 컴파일 오류, Make 의존성 재시도, ARM04의 최적화된 함수명 검사 실패를 보존했다. 최종은 host04/causal03/ARM04이며 ARM checker만 같은 ELF에서 함수명 suffix를 반영했다.

## 다음 작업

094 실제 C GPIO를 CF86 고정 RTL에 80/96KiB 전체 재생하고 응답·고장·STOP을 비교한다. 이후 같은 fit의 ASM/최종 ARM/044 복원 쌍을 검증한다. 외부 IO·공통 클록 고장 조건은 별도 남긴다.

전체 준비도는 완료4/부분7/미완료1, 설치 승인은 false다. 084 저장·복원·메뉴/GBC PASS와092 기준클록 관측/복원 PASS를 반복 요구하지 않는다. 첫 게임은 SMB3(J), mapper4·PRG256KiB/CHR128KiB이며 현 80/96KiB 진단은384KiB 게임 적재 지원이 아니다.

로컬 동결 `probes/nes-session094/evidence/`: 2617파일, manifest `d34c3dc8c1927b0981d1c4b5bef3ce06e1d29f183de7f031c3e0812331e96143`. 검증기는 비공개 증거가 있어야 하며 공개 clone만으로 이 동결 검사를 재현할 수 없다. 공개 호스트 시험은 별도로 실행할 수 있다.
