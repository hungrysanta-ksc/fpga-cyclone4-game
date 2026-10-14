# NES175 최소 상태 관측의 READY·카운터 경로 검증

목표는 174 실기에서 화면이 멈춘 뒤 **후보가 계속 거부되는지, 생산·해제·전달 중 어느 단계가 정지했는지** 구분하는 것이다. 이번 변경 자체가 화면 정지나 60fps를 해결했다는 뜻은 아니다. 최종 채택 여부는 아래 결과와 [검증 기록](../analysis/ready175-verification.json)을 따른다.

## 배치 보존 방식 검토

174의 `incremental_db/compiled_partitions`에는 root partition 결과가 있지만, QSF에는 기능별 파티션이 없다. 소스가 바뀐 유일한 파티션 전체를 이전 결과로 고정하면 새 관측 배선까지 반영했다고 볼 수 없다. 공식 문서도 소스 변경 시 파티션 재합성과, 소스 변경을 무시하고 이전 netlist를 사용하는 선택을 구분한다. [파티션 재합성 조건](https://docs.altera.com/r/docs/683283/18.1/intel-quartus-prime-standard-edition-user-guide-design-compilation/what-changes-initiate-the-automatic-resynthesis-of-a-partition?contentId=muJkZt2yNq3fV8TDWEk2vg), [파티션 netlist 선택](https://docs.altera.com/r/docs/683283/18.1/design-compilation-user-guide-quartus-prime-standard-edition/netlist-type-for-design-partitions?contentId=p34QKcy8Wb7gBxn5UnMdmQ).

SignalTap의 Incremental Route with Rapid Recompile 지원 목록은 Arria V/Cyclone V/Stratix V이며 Cyclone IV는 없다. 이는 **해당 흐름의 제한**이지 모든 ECO가 불가능하다는 뜻은 아니다. Cyclone IV의 Signal Probe ECO 지원도 별도로 존재한다. [Incremental Route 지원](https://docs.altera.com/r/docs/683552/18.1/intel-quartus-prime-standard-edition-user-guide-debug-tools/incremental-route-with-rapid-recompile?contentId=~1MUmNuAFnxrRf0v8vnR8Q), [Signal Probe 명령](https://resources.altera.com/quartushelp/17.0/program/sipro/comp_com_start_sp.htm).

설치된25.1 Standard Tcl에는 `make_ape_connection`도 있지만, 명령 존재만으로 기존 이력 RAM의96비트 입력을 안전하게 재배선할 수 있다고 판단하지 않았다. 실기는 이 PC에 연결되지 않으며 현재 시험은 SD 펌웨어와 TXT 회수 방식이므로, Signal Probe의 핀 관측도 바로 쓸 수 없다. 따라서 이번에는 **검증되지 않은 ECO/파티션 보존을 배포 근거로 쓰지 않고**, 실제 실패 경로를 줄이는 소스 변경을 선택했다. 향후 적절한 파티션 설계와 ECO 지원 확인은 별도 과제이며, 이번에 지원 불가능을 전부 증명한 것은 아니다.

## 변경 계약

기준은 배포174 `errorzero174-map01`이다. 이전 A5 후보의3개 출력 배선 변경과 같은96비트 상태 형식을 유지한다. 이력 RAM·기록 주기·STOP 보존·SPI 형식, 영상/사운드/입력 경로는 동일하다.

첫 후보 `ready175-map01`은 로더의 `load_ready`에서 `release_reset[1]`의 중복 검사를 제거한다. 외부 `reset`의 즉시 차단은 유지한다. 상태 레지스터는 비동기 리셋 시 IDLE이며, 해제 대기 동안에도 IDLE로 유지된다. 따라서 리셋 이후 도달 가능한 RECEIVE 상태에서는 해제 대기가 이미 끝났다. 임의의 레지스터 손상으로 RECEIVE와 해제 대기를 동시에 만드는 상태까지 동등하다는 주장은 하지 않는다. 리셋 동기화기 자체, 명령 허용 시점, PSRAM 쓰기 펄스와 STOP/오류 처리는 바꾸지 않았다.

후속 `timer175-map01`은 측정된 `load_begin → phase_step → remaining.ena` 경로를 대상으로 한다. `phase_step`은 `!timed_phase`를 먼저 제외한 분기에서만 사용되므로 내부의 `timed_phase` 검사를 제거한다. 분기 밖에서는 그 신호값이 달라질 수 있지만 소비되지 않는다. 정상 카운트·정지·오류 발생 중 WRITE/HOLD 완료 우선순위는 같아야 한다. 클록, 타이밍 예외, seed, 레지스터 속성은 바꾸지 않았다.

## 기능 검증 범위

두 후보 각각 배포174와294,912개 상태·명령 조합,1,056개 실제 단일 바이트/명령/리셋 순서를 비교했다.19개 서브클록 시점에 짧은 리셋을 넣고 해제 대기 중 BEGIN을 유지하는 시험도 통과했다. READY 상태 검사를 빼거나 리셋 해제 중 IDLE 유지를 제거한 오류 주입은 검출했다. raw test 복사본은 Windows 개행 변환을 포함할 수 있어 RTL은 텍스트 동등성과 원본 해시를 따로 확인한다.

각 후보의 실제 RTL SPI→boot→READ16 연결 시험도 통과했다:1,126,009에지,100읽기,7ACK,19손상,72취소,2중첩. READY/길이를 seed하므로 전체 ROM 쓰기·실제 게임 플레이를 새로 검증한 것은 아니다. 기존175 생산·소비 연결 시험 및 A5 출력 배선 검토는 변경 범위가 같아 재사용하며, 새로운 실기 증거로 표현하지 않는다.

결과 보존 중 `ready.prepare()`가 가져온 변경 파일 목록에 직접 append하여, 한 프로세스에서 READY→TIMER를 연속 생성할 때 이전 목록까지 바꾸는 문제를 발견했다. 목록을 복사한 뒤 추가하도록 수정했고 같은 프로세스의 연속 재현이 통과했다. 독립 실행했던 두 빌드·시뮬레이션의 RTL 바이트는 그대로다. 수정 전 생성기와 실패한 재현 폴더, 원래 테스트의 소스 해시를 보존했다. 최상위 공개 소스 해시만 수정본으로 구분해 기록하며, 기존 테스트를 다시 실행한 것으로 세지 않는다. 완료된 `record02.py`와 evidence는 다시 실행하거나 덮어쓰지 않는다.

## 결과 및 다음 단계

READY 후보는15,073LE/963LAB로 배치되었다. 실제 클록 최악 setup은−0.048ns로 이전 A5의−1.114ns보다 개선됐지만 **미통과**다. 이전 `release_reset[1] → snapshot[40]` 조합 경로는 세 동작 조건 모두 사라졌다. 새 최악 경로는 `load_begin → remaining[1/2/4].ena`,4단 논리와60% 배선 지연이며 마지막 enable 배선이1.672ns다. 이 결과를 근거로만 후속 카운터 후보를 만들었다.

후속 TIMER 후보는14,929LE/959LAB/36M9K로 배치되어 READY 후보보다144LE와4LAB를 줄였다. 목표였던 쓰기 대기 경로는 **−0.048→+1.573ns**로 개선됐다. 그러나 `check_failed → count_begin → count_complete → count_update → loaded_bytes.ena`가 **−0.218ns**로 바뀌어 전체 타이밍은 실패했다. 실제 클록 최소 hold는 READY +0.148ns/TIMER +0.147ns다. 세 동작 조건·네 클록 전체를 판정하며, 더 엄격한 기존 구현 예산의 실패도 원본 보고서에 남겼다.

**두 후보 모두 미채택이며 새 ZIP은 없다.** 배포 기준은174 그대로다. 관측 MCU는 이전175 A5 후보와 호환될 형식이지만, 타이밍을 통과하지 못해 재빌드·배포하지 않았다. 불필요한 IO/CDC·게임 부팅·044 복원 재시험도 하지 않았다. 기존174·164 복원·GBC·세이브 SRAM과 이전 검증 자료를 보존했다. 실행 중 SD 쓰기, 두 번째 MCU 전체 화면 버퍼를 추가하지 않았다.

다음에는 TIMER 후보가 확보한 자원 여유를 참고해 **로더 카운터의 수락된 명령 효과와 live fault 차단을 분리할 수 있는지** 검토한다. 먼저 BEGIN/STOP/RELEASE 카운트 갱신과 주소 소비 시점을 표로 고정하고, 이전165~167의 실패한 카운터/CE/공유 fault 시도를 대조한다. 단순한 식 재배열·속성·seed 변경을 반복하지 않는다. 등록 단계가 필요하면 기존 SPI C0~C4와2µs SS-high 계약에 미치는 영향을 명시하고, 같은 에지 동등성으로 주장하지 않는다. READY −0.048ns 후보도 배포 기준으로 승격하지 않는다. 필요한 경계·타이밍을 통과하면 실제 SMB3 시험으로 바로 돌아간다.

174의 완료 화면당 변환/전송·표시 확인 평균167.5ms 문제는 그대로 남아 있다. 화면 정지 원인을 확인한 뒤 연속 영상·사운드 속도를 우선 개선하고, 이후 장기 플레이/오류·실기 리셋 로그와 입력 유지 품질을 진행한다. 단순히 관측 기능을 늘리거나 변경 없는174/044 시험을 반복하지 않는다.
