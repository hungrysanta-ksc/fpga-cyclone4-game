# NROM464–465: 실기 진입의 복구·timing 경계

## 완료한 준비

418 실제 ARM 메뉴 기계어를 base-only 진단 조건으로 실행해 복구 성공과 네 가지 실패를 확인했다. 프로그래머 반환 실패, 설정 완료 확인 실패, SPI BSY, base 토큰 불일치 각각에서 실제 메뉴 함수가 false를 반환하고 base_restored=0, verified=0, recovery_attempted=1, guard 실패 호출 1회, 메뉴 종료 허용 호출 0회로 끝났다. 성공 대조만 base_restored=1과 true를 반환했다. 실제 펌웨어 메뉴 호출부는 false이면 BLOCKED_RESET_HELD로 보고하고 메뉴 재적재를 차단한다. 시험에서 guard·프로그래머·DONE·토큰·주변장치는 모델이므로 전기적 reset 유지나 실제 재설정 증거가 아니다. base-only는 ROM 적재와 표시를 실행하지 않으며 정상 전체 경로는 463의 별도 범위다. 최초 두 시험은 빈 STOP 상태 모델을 잘못 설정해 실패했고 sd_command의 flags=0/count=0 계약으로 수정했다. 결과는 analysis/nrom464-recovery.json에 있다.

465의 읽기 전용 도구는 457 routed report에서 미제약 포트 전체 목록과 458 진단 산출물·보존 base/menu 해시를 재확인한다. `--sd-root`를 지정하면 아래 경로를 읽어서 해시만 비교한다. 파일 복사·설정·SD 쓰기를 수행하지 않는다.

```powershell
& '<Python 실행 파일>' tools/audit_nes_nrom465_entry.py --sd-root '<실제 SD 루트>' --out '<새 결과 JSON>'
```

고정 대상은 sd2snes/firmware.stm(418), sd2snes/fpga_nrom16.bi3(457/458), sd2snes/nes/nrom16.nes(428), 보존 sd2snes/fpga_base.bi3·m3nu.bin 및 빈 NES GAME 227.nh1 marker다. ARM 메뉴가 이 기존 marker 이름을 사용하므로 다른 이름을 임의로 만들면 진입하지 않는다. 해시는 analysis/nrom465-entry.json에 보존한다.

## 남은 제약의 실제 범위

| 경계 | 확인한 범위 | 다음 확인 |
|---|---|---|
| 동일/관련 클록 | 제한된 기존 질의 setup +0.226ns, hold +0.151ns | 변경 없는 457의 기존 결과. 전체 STA 승인과 구분 |
| reset/CDC | 음수 cross-clock recovery 표본 525행·45종단: release 체인 38, sink admission 5, fault sync 2 | release의 첫 단계·로컬 해제와 실제 상태 종단을 구분. sink host_ready·idle_ss[1:0]·idle_write[1:0]의 직접 해제를 다음 RTL 수정 대상으로 고정. fault sync의 비동기 차단·재무장 계약 확인 |
| 전체 STA | raw setup −7.040ns, recovery −9.659ns | 표본 분류만으로 예외를 추가하거나 음수를 없애지 않음. 전체 CDC 목록과 MTBF는 미완료 |
| PSRAM IO | ROM_DATA 입력 16, 출력 ROM_ADDR 19·ROM_DATA 16 및 CE/OE/WE·byte lane | 기존 70ns 접근/4ns PCB 가정 확인. 실제 장치·보드의 setup/hold·turnaround 근거 필요 |
| SNES IO | 입력 주소24·data8·제어3, 출력 data8·OE·DIR | 실제 콘솔 버스/변환기 지연과 샘플 시점 확인 |
| SPI/MCU | 입력 SCK/MOSI/SS, 출력 MISO·MCU_RDY | 2.625MHz 실제 mode/위상·응답 여유 및 turnaround 관찰 |
| DAC | 출력3 | 실제 clock/data 관계와 보드 연결 확인 |

미제약 input 54·output 56은 report에 실제 존재하며 전체 포트 목록을 JSON으로 보존했다. 클록은 4개 모두 제약되어 있다. 기존 IO 계산은 양수 조건부 여유이며 실측이 아니다. 새로운 false-path/clock-group 예외나 IO 수치를 만들어 넣지 않았다.

## 다음 실행 순서와 실물 경계

1. sink admission 5개와 fault sync의 reset 소유권을 코드와 대조하고 필요한 RTL 변경을 격리한다. 변경 시 STOP·정지 클록·표시 후 복귀 회귀와 같은 소스의 Lite FIT/관련 timing을 확인하며 산출물 해시를 갱신한다. 기존 451 후보를 457에 자동 합산하지 않는다.
2. 실제 SD 루트를 지정해 base/menu와 후보 파일의 동일성을 검사한다. 현재 프로세스에서는 C:, D:만 확인했고 SD 위치는 특정하지 못했다. Get-Volume은 CIM 접근 실패였으므로 카드가 없다고 단정하지 않는다. 보드 revision·메모리와 연결 상태도 확인한다.
3. 실제 보드에서는 먼저 기존 base 부팅/메뉴를 기록하고 설정 완료·ID78, 적재/독립 검증, START·표시, STOP 후 활동 정지, base 설정/DONE·SPI 유휴·토큰, 메뉴 재적재·reset 해제·재시작을 순서대로 기록한다. 실패 시 ARM의 false/차단 상태와 UART를 보존하고 보호를 우회하지 않는다. 보존 복원물로 되돌린다.
4. 제한 smoke 성공 뒤 같은 workload에서 지속 캡처·표시 ACK·누락·VBlank·ARM/SPI/IRQ/ROM 경쟁을 계측한다. MMC4/5와 60fps 판단은 그 측정 뒤에 진행한다.

실제 보드 설정·base 복구와 timing의 남은 경계는 아직 완료되지 않았다. 465는 진입 준비 자료와 재현 가능한 읽기 전용 점검을 제공하며 설치 승인이나 60fps 결과는 아니다. 추가 Questa 라이선스나 전체 384KiB 보드 장시간 재실행을 요구하지 않는다.

## 466–467 후속 결정

사용자가 SD를 직접 연결하지 않고 전달 ZIP을 설치·확인하는 기존 방식임을 확인했다. SD 직접 연결은 작업 선행 조건에서 제외한다. 466의 sink 로컬 reset은 목표 recovery/removal을 개선했지만 다른 setup 회귀로 보류했다. 467은 기존457/418/428의 고정 조합과 보존164 복원 파일을 묶은 제한 실물 관찰용이며 남은 CDC/IO 한계를 함께 전달한다. 전체 timing 승인이 필요한 후속 장기운용/60fps 관문과 구분하며 사용자의 실제 설정·base 복구 관찰을 다음 근거로 삼는다. 설치·기록 절차는 docs/nes-nrom467-trial.ko.md를 따른다.
