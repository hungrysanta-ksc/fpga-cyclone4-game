# NES217 로더 오류 비트의 병렬 갱신

## 작업 의미

216에서 수정한 정상 대기 watchdog을 실기에 올리기 위한 전체 보드 타이밍 작업이다. 60fps 전송량 개선이나 신규 디버그 기능이 아니다. 변경 타일 재사용·전송 큐·216의 대기 계약을 유지하며, 클록/SDC/seed/핀을 바꾸지 않는다. 세이브 SRAM과 GBC164는 사용하거나 수정하지 않는다.

## 변경과 이전 시도와의 차이

216의 실패 경로는168MHz `control.load_valid → loader.error_code[1].ena`, setup -0.320ns였다. 5LUT와 배선64%를 거치는 공통 오류 enable/우선순위 회로다.

예전 `nes_errorce165.py`는 공통 `error_event` enable과 조건부 오류 코드 선택기를 분리했다. 이번에는 그 구조를 반복하지 않는다. 코드1~6의 발생 조건을 서로 배타적으로 만들고, 각 오류 비트의 set/clear/hold를 병렬 계산한다. 오류 코드 레지스터에만 자동 clock-enable 추출을 막는다. 새 파이프라인·레지스터·응답 지연·전역 합성 설정은 추가하지 않는다. 이것이 실제 배치 타이밍을 개선하는지는 전체 보드 FIT/STA 결과로 판정한다.

- 명령 충돌은 상태와 관계없이 코드5로 가장 먼저 처리한다. fault가 이미 있으면 기존 코드를 유지한다.
- STOP+VALID는 충돌이 아니며 STOP이 우선한다. WRITE/HOLD에서는 코드6, 다른 해당 상태에서는 기존 중단 동작을 따른다.
- `commands_blocked`가 켜지면 BEGIN/END/START/VALID는 무시하지만 STOP과 쓰기 펄스 드레인은 유지한다.
- 오류 없는 클록에는 코드가 그대로다. reset/동기 release reset은 코드를0으로 만든다.
- 상태 전이, fault, loaded count, PSRAM 주소·데이터·쓰기 펄스와216 watchdog RTL은 바꾸지 않는다.

## 검증

216과217의 실제 로더를 같은 입력으로 비교했다. 기존16상태/명령/길이/fault/타이머 조합294,912개, 쓰기 도중8동작×132시점1,056시퀀스, 19bit count524,288개가 일치했다. 여기에 이전 오류 코드16개×상태16개×명령64개×차단2개×완료2개×sticky fault2개=131,072조건을 추가했다. 도달 불가능한 이전 코드도 오류 없는 경우 보존하는지 확인한다. 충돌 또는 STOP 오류를 의도적으로 제거한 두 잘못된 RTL은 시험에서 검출했다.

이 시험은 실제 보드/게임 시험이 아니다. 변경 없는216의 긴 소비 대기·ROM 승인 대기·미응답/취소 보호는 기존 선택 결과를 재사용하며, 재실행했다고 표시하지 않는다. 상세 전체 배치·타이밍·CDC/reset/조건부 I/O 결과는 [검증 기록](../analysis/loader217-verification.json)에 남긴다. 결과가 통과하기 전에는 새 패키지를 만들지 않는다.

## 첫 배치에서 드러난 세대 코드 경로

source01 전체 배치에서 로더 대상 경로는 -0.320ns→+0.758ns로 개선됐지만, `content_lifetime.serial[0] → gray[27]`가 -0.719ns로 실패했다.15,192LE/8,349FF이며 새 RAM·FF를 추가하지 않았다. 로더 개선을 전체 타이밍 통과로 해석하지 않는다.

source02는 추가로 `nes_source_epoch207.sv`의 다음 serial/Gray 계산만 변경한다. 비트 i에 들어오는 carry를 기존 serial 하위 비트의 AND로 계산한다. Gray 비트의 다음 값은 `serial[i+1] ^ serial[i] ^ (carry[i] & !serial[i])`로 직접 계산한다. 최상위는 `serial[31] ^ carry[31]`, 최하위는 `serial[1] ^ serial[0] ^ !serial[0]`다. 긴32bit 덧셈 결과를 기다린 뒤 Gray XOR를 하지 않는다. 이전 Gray가 올바르다는 불변식에 의존하지 않고 기존과 똑같이 serial에서 계산한다.

새 레지스터/파이프라인/세대 지연은 없다. BEGIN 때만 갱신하고, 최대값에서 exhausted를 설정하며 serial/Gray를 유지한다. STOP/reset·로컬 리셋·96개 동기화 레지스터·승인 장벽은 그대로다. 기존 카운터와 비교한25,067클록(모든 carry 경계/최대값/무작위4,096값/연속4,096BEGIN/리셋)이 일치한다. 임의의 잘못된 이전 Gray를 주입해도 보존 또는 갱신 결과가 같다. 기존20개 수명·소진 조건과32개 클록 정지/리셋 위상 조건도 통과하며, 잘못된 Gray 식은 검출된다. 물리적 metastability나 전체 게임 시험은 아니다.

## source02 미채택과 source03 구조 변경

source02는15,130LE/8,350FF로 들어갔지만 related setup -1.478ns로 악화됐다. 실제 `serial[1] → gray[22].ena` 경로는11LUT/7.353ns다. 넓은 AND 식이 공유되면서 `WideAnd6 → 8 → 11 → … → 29` 직렬 체인이 되고, 끝에서57개 레지스터의 enable을 구동한다. 단순히 RTL에서 수식을 병렬로 적는 것으로 배치까지 병렬이 되는 것은 아니었다. 이 후보는 미채택이다.

source03은 기존 source01을 기반으로32비트 카운터를8개4비트 묶음으로 나누고, 각 묶음이 모두1인지 나타내는 `all_ones[7:0]` 레지스터를 추가한다. 하위 묶음 플래그의 AND로 carry를 만들고, 최대값 판정도32비트 serial 대신8비트 플래그를 사용한다. serial과 Gray는 기존처럼 BEGIN의 같은 클록에 갱신한다. 글로벌 클록/SDC/핀/seed는 바꾸지 않는다.

불변식은 `all_ones[k] == &serial[k*4+:4]`다. reset에서 둘 다0이다. carry가 없으면 묶음과 플래그를 유지하고, carry가 있으면 묶음+1이 F가 되는 조건은 이전 값 E뿐이다. 따라서 다음 플래그를 이전 묶음==E로 갱신하면 불변식이 유지된다. 모든 플래그가1이면 기존대로 증가를 막고 exhausted를 설정한다. 도달 가능한 상태에서 원래32비트 증가·Gray·소진 동작과 같으며, 추가 응답 지연은 없다.

source03 시험은 같은25,067 비교 클록마다 이 불변식도 확인한다. 임의 serial 주입 시에는 대응 플래그를 함께 초기화하며, 정상 연속 갱신에서는 DUT만 스스로 플래그를 유지한다. 기존20개 수명/32개 리셋·정지 조건과 잘못된 +2 증가 negative도 통과했다. 소스 선언상 추가8FF이며 전체 FIT 자원은 별도로 판정한다. RAM/프레임 버퍼/세이브 SRAM은 추가하지 않는다.

## source03 미채택과 source04 공개 장벽

source03도 전체 배치에서15,212LE/8,357FF, related setup -2.264ns로 실패했다. 최악 경로는 `gray[31] → all_ones[7]`다. 일부 serial/Gray 비트는 동일하여 합성 시 공유되므로 이름만 보고 CDC 경로라고 해석하지 않는다. 이 후보도 미채택이며 단순 수식/플래그 재배치 반복을 중단한다.

source04는 source01의 원래32비트 증가 회로를 유지하고, Gray 등록을 별도의 다음 메모리 클록으로 분리한다. **source01~03의 내부 같은 클록 Gray 계약과 달리, Gray 공개가1mem cycle 늦어진다.** `gray_pending`이 그동안 invalid를 유지하며, 기존 NES 영역의 리셋 해제·동기화·안정성 비교가 끝나야 source_ready가 열린다. BEGIN은 즉시 invalid를 올린다. 메모리 클록이 공개 전에 멈추어도 pending이 유지되어 이전 세대의 승인을 막는다. 프레임 ACK/retire에는 세대가 바뀌지 않으며, 게임 매 프레임에 지연을 추가하지 않는다.

serial/소진은 기존과 같은 클록·값이고, Gray는 이전 serial의 인코딩임을25,067클록에서 비교했다. 기존20개 수명/32개 NES 클록 정지·리셋 조건에, publisher 메모리 클록을 pending 상태에서 멈췄다 재개하는16조건을 추가했다. pending을 invalid에서 빼거나 Gray 값을 잘못 만드는 두 negative를 모두 검출했다.96개 NES 동기화/이전값 레지스터, 원래2^32 소진 정책, 로더·STOP·RESET 계약은 유지한다. 실제 CDC/전체 배치 결과가 통과하기 전에는 배포하지 않는다.

## 최종 상태와 다음 작업

**source04 기능 시험은 통과했지만, 전체 타이밍 미달로 미채택이다. 새 ASM/실기 ZIP은 없다.**

- 전체 FIT15,160LE/8,351FF/957LAB/47M9K. 여유248LE/6LAB/9M9K.216 최종 후보보다8LE/3LAB 적고2FF 많다. ROM/프레임 RAM과 세이브 SRAM은 늘리지 않았다.
- 로더 대상 경로 +1.065ns, serial→Gray 대상 경로 +2.126ns로 통과했다. 첫 후보의 로더 +0.758ns와 최종 배치 값을 구분한다.
- 남은 최악 관련 경로는168MHz `control.bit_count[2] → offset_zero_command/offset_length_command.ena`, -0.155ns. 데이터6.006ns/3LUT 중 배선4.207ns(70%), `Equal17~0` fanout39이며 bit_count→첫 비교기 배선만1.804ns다. offset[10]에도 -0.057ns가 남는다. 오류 코드나 Gray로 다시 돌아가 seed만 바꾸지 않는다.
- nominal/strict hold는+0.147ns. CDC4,404행/첫단계45개 단일fanout/새 미분류data0, held6.505ns/Gray6.661ns.96reg reset576경로와 조건부 I/O PSRAM+1.680ns/SNES85.832ns/SPI166.565ns 및 native payload reset은 통과한다. 전체 전기적 signoff 또는 MTBF 계산을 완료한 것은 아니다.
- 217 ARM은215에서 표시/파일명 식별자3파일만 변경했다.207536B/static27868/RUN32096/IRQ508/여유4952B이며 검사 통과. 새 FPGA/212 SNES ROM과 짝지어 검증하기 전이므로 단독 설치하지 않는다.

다음에는 `nes_rom_spi.sv`의 바이트 경계 판정과 공통 `command_first_byte`/offset 갱신 enable의 fanout·지역 배선을 줄이는 변경을 검토한다. ID74/SS-high≥2us/C0~C4 명령 단계, 마지막 비트 수신 시점, CRC/주소/READ ACK·STOP·SS 겹침/reset 계약을 유지하는 실제 SPI 경계 시험을 먼저 적용한다. 원인이39fanout/배선인 만큼 또 다른 epoch 수식·보조 플래그·단독 loader microFIT·seed 변경·클록/SDC 완화는 하지 않는다. 전체 보드 타이밍이 통과한 뒤 현재212 ROM을 CDB/ASM으로 결합하고, 217 식별자 ARM과 패키지를 검증해 실기 스테이지 선택→숫자1+A→오른쪽+B/A반복으로 간다. 같은215/044/영상 재시험은 필요하지 않다.
