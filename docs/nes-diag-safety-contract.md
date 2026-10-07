# NES068 진단 초기 대기·외부 예산 계약

후보 **NES-DIAG-SAFETY-068 / CF68**. PR22 병합 `4d8868f2e324870137606058719fee36a6ff10db` 기준이다.067의 진단 loader를 보존하고 reader의 읽기 활성 제어를 별도 레지스터로 바꿨으며,, PSRAM 접근 전에 초기 대기를 추가했다. CF61 MCU065/쌍066·CF67 후보와 구별하며 새 ARM/설치 쌍은 없다.

## 초기 대기

`nes_diag_startup_guard.sv`는 공통 reset 또는 PLL lock 상실에서 즉시 준비 신호를 내린다. 첫 유효 클록 에지에서 시작점을 잡고 **1600개의 완전한 클록 간격** 뒤 ready를 낸다.8MHz에서200µs,10MHz에서160µs다. 카운터는 포화 후 유지한다. 대기 중 클록이 멈추면 준비되지 않으며, 대기 중 reset은 누적 시간을 버린다.

`nes_diag_safety.py`는067을 생성한 뒤 이 ready를 실제 memory_reset/MCU_RDY에 연결하고 CF 응답을68로 바꾼다. 대기 중에는 loader/CHECK 상태를 reset에 두어 CE/WE/OE와 DQ 구동을 막는다. 기존 독립 reset 해제 FF와 두 START 장벽을 유지한다.

이는 전압 센서가 아니다. PSRAM 전원이 reset 해제 전에 안정돼 있고 클록이10MHz 이하라는 조건에서 ISSI tPU150µs보다 긴 추가 대기를 확보한다. 실제 전원 램프·brownout·클록 주파수를 측정한 것은 아니다. 부품은 사용자 사진의 **IS66WVE4M16EBLL-70BLI ×2**와 [ISSI EBLL 규격](https://www.issi.com/WW/pdf/66-67WVE4M16EALL-BLL-CLL.pdf)을 쓴다. 추가 분해/식별 요청은 필요 없다.

## 읽기 활성 유지

합성된 reader 상태는 one-hot이다. ACTIVE→HOLD의 두 상태 비트를 OR해 CE/OE를 만드는 방식은 샘플 에지에서 짧은 비활성 전이를 배제할 수 없어, `nes_diag_safe_rom_physical.sv`에 `reading_active` 레지스터를 추가했다. SETUP→ACTIVE에서 켜고 HOLD→RELEASE에서 끄며 ACTIVE→HOLD 샘플 에지에서는 그대로 유지한다. reset/PLL 상실 차단은 유지한다. 실제 글리치를 관측했다는 뜻은 아니다.

최종 routed CE/OE 경로의 reader source가 `reading_active`인지 수집기가 검사한다. 이전 fit02의 state decode 경로는 이 검사에 실패한다. 전체 메모리 정상 4경우에서 각 쓰기/읽기 344064 bytes, 취소 36회를 검증했다. setup/hold 변형 3개와 주소 지연 126ns 범위 밖 대조는 지정 assertion으로 실패했다. 첫 read-setup 변형은 새 활성 비트를 켜지 않아 다른 READ_CONTENT assertion에서 실패했으므로 인정하지 않고 변형을 수정해 새 실행으로 확인했다.

## 외부 지연 추출

실제068 Standard25.1 fit DB를 새 ASCII 분석 폴더로 복사하고 **분석 전 모든 DB/QSF/QPF/SDC 해시를 고정**한다. 원본 DB는 수정하지 않는다. `nes_diag_io_paths.tcl`이 세 timing corner에서 PSRAM output의 register→pad와 DQ pad→reader.data_hold 경로3168개를 추출한다.

분석 복사본에만 IO delay=0을 적용해 FPGA 내부 경로를 노출한다. 이것은 실제 카드의 입력/출력 제약이 아니며 overlay slack으로 보드 승인을 하지 않는다. output bound는 arrival−launch로 launch clock 배선까지 포함한다. input bound와 capture adjustment는 실제 reader 종점에서 계산한다. Setup 최대/hold 최소를 세 corner·관련 source register에 걸쳐 보수적으로 합친다. [설치 버전 Tcl 도움말](https://www.intel.com/programmable/technical-pdfs/654662.pdf)의 get_timing_paths/get_path_info 동작과 로컬25.1 도움말을 확인했다.

PSRAM dynamic output37비트와 input16비트의 각corner/setup/hold 존재를 확인한다. ROM_ADDR[14:18], [20:21]은 고정 geometry에서 상수라 경로가 없다. 빈 경로를 무조건 통과시키지 않는다. SPI/SNES와 비동기 lock→핀 차단 경로는 이 PSRAM board8 예산에 포함하지 않는다.

| 구분 | FPGA clock→pin min/max (ns) |
| --- | ---: |
| 주소 | 3.833 / 19.542 |
| CE | 4.040 / 16.727 |
| OE | 6.437 / 20.077 |
| WE | 3.779 / 14.900 |
| byte enable | 4.039 / 23.299 |
| 데이터·해당 pad 경로 | 3.620 / 20.160 |

DQ input min/max는1.768/6.184ns, setup capture adjustment 최소1.141ns, hold adjustment 최대3.004ns다. 상대 지연 예산은 예를 들어 `125 + CE_min − ADDR_max = 109.498ns`, 읽기 byte-enable 경계는 `375 + capture_adjust − DQ_input_max − BE_max − 70 = 276.658ns`다. 전체16경계의 식과 결과는 `nes_diag_io_budget.py`·공개 요약에 고정한다. 여러 경로의 독립 극값을 합쳐 보수적 예산을 만들었으며 SDF/아날로그 모든 전이를 검증한 결과는 아니다.

PCB 각 leg20ns 이하·추가 불확실성5ns라는 **미측정 가정**에 두 leg 비용을 빼면 최솟값62.313ns다. 각 leg60ns로 키운 대조에서는−17.687ns다. 양수 시나리오가 실제 PCB 지연·전압/부하·IO 표준 시험 조건의 확인을 대신하지 않는다.

## 클록 정지 반례와 실행 조건

물리 top의 WRITE 중8MHz를 정지시키고 locked=HIGH를 유지한 시험에서 CE가9µs 이상 LOW로 남는다. 이것은 tCEM 최대8µs를 넘는 **반례**다. locked를 내리면 클록 없이도 핀이 해제되고 이미지가 무효화된다. 이 두 사건을 구분한다.

현재 모든 내부 클록은 같은 외부 입력/PLL 계열이다. 실제 PLL의 lock 상실 감지 시간, 또는 독립적인 차단 경로가 확인되지 않으면 클록 정지에도8µs를 지킨다고 승인할 수 없다. 내부 카운터를 하나 추가해 이 문제를 해결했다고 쓰지 않는다. 정상 연속 클록 예산과 고장 정책은 별도 조건이다. 전원/클록 고장 뒤 이미지 무결성은 보장하지 않고 재구성·재적재/비교 전 재사용을 막는다.

## 검증·재현

- 초기 대기 정상2경우(8/10MHz), reset/포화·대기 중 정지 검사. 대기1클록 변형과약16.13MHz 범위 밖은 지정 assertion 실패를 요구한다.
- 실제060 C bounded load256pin bytes와TB96KiB 준비 후CHECK256bytes,총72312응답 비트. 초기 강제 입력이181µs까지 memory/ready를 활성화하지 않음,START 두 장벽·PLL loss/복구를 검사한다. 전체80/96KiB SPI 성공 시험은 아직이다.
- 실제 physical boundary의 warmup 연결 제거는 EARLY_MEMORY_READY assertion 실패를 요구한다. simulator exit0만으로 판정하지 않는다.
- 새 map/fit/STA, 분석 DB 입력 해시, 실행 소스 snapshot을 함께 고정한다. 최초 map의 snapshot.sv 중복 입력 실패와 IO collector의 QSF 자동 버전/EOF 처리 실패를 보존한다. 최종 회로 의미는 이 수집기 수정으로 바뀌지 않았다.

```powershell
& ./tools/run_nes_diag_startup.ps1 -Python $Python -FloatWrapper $FloatWrapper -QuestaBin $QuestaBin -Out $FreshStartup
& ./tools/run_nes_diag_safety_memory.ps1 -Python $Python -FloatWrapper $FloatWrapper -QuestaBin $QuestaBin -Out $FreshMemory
& $Python -B -X utf8 ./tools/nes_diag_safety.py --out $FreshFit --quartus-bin $QuartusStandardBin
& $Python -B -X utf8 ./tools/nes_diag_io_extract.py --fit $FreshFit --out $FreshIO --quartus-bin $QuartusStandardBin
& ./tools/run_nes_diag_safety_wave.ps1 -Python $Python -FloatWrapper $FloatWrapper -QuestaBin $QuestaBin -Out $FreshWave -HostRun $Frozen060Host
# 동일 호출에 -Mutation bypass-startup: 예상 실패를 수집하는 별도 새 출력 폴더.
& $Python -B -X utf8 ./tools/verify_nes_diag_safety.py --evidence $Frozen068Evidence
```

경로 변수는 절대 경로로 지정한다. 기존 Starter FLOAT 한 seat를 순차 사용한다. public startup/fit 생성과 private060 파형·동결 evidence audit의 재현 범위를 구분한다.

다음은 외부 미확인 조건/클록 고장 정책을 명시한 최종 후보에 CF68 MCU와 실제 호출/ARM·전체 SPI 회귀를 연결하는 것이다. 이어 같은 fit의 ASM/압축/manifest,실제 SD/base/menu·독립 백업/복원 조건과 사용자 외부 실기 TXT·화면·GBC 회귀로 진행한다. installable=false를 유지한다.
