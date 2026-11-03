# 575 — 실제 클록·CDC·reset 경계 감사

**572 START 단독을 유지한다. 남은 raw STA 숫자만 줄이기 위한 epoch 배치·직렬화 반복은 종료한다.** 기존 배치에서 경로를 분류하고 데이터 유지·수신 조건을 검사했다. RTL·ARM·65816·보드 SDC·SOF는 바꾸지 않았고 새 MAP/FIT도 실행하지 않았다.

[검증 데이터](../analysis/boundary575-verification.json) · [574 결정](nes-serial574-results.ko.md) · [PR149](progress/pr-149.md)

## 실제 클록과 조사 범위

top은 CLKIN 8MHz에서 PLL의 host 84MHz·memory 168MHz를 만들고, SNES_SYSCLK는 별도 NES 입력으로 사용한다. 기존 SDC의 NES 예산은 22MHz다. host/memory는 같은 PLL 계열이며 NES와의 위상 관계는 보장하지 않는다.

MMC558·572의 기존 배치 DB에서 세 코너·setup/hold/recovery/removal·모든 선언된 클록 쌍을 조사했다. **목적지와 클록 쌍별 최악 음수 경로**를 수집했다. 모든 조합 경로를 열거한 것은 아니며 미제약 IO도 이 집계에 포함하지 않는다. 20,000개 제한에 도달하지 않았음을 검사했다.

| 분류 | MMC558 | 572 |
|---|---:|---:|
| raw 제어의 직접 교차 setup | 447 | 0 |
| 단일 비트 동기화 첫 단 setup | 42 | 45 |
| Gray identity 첫 단 setup | 96 | 96 |
| ACK까지 유지되는 mailbox 데이터 setup | 165 | 168 |
| 응답까지 유지되는 ROM 주소 setup | 63 | 63 |
| 진단 snapshot의 raw bus_drive setup | 3 | 3 |
| reset release chain recovery | 152 | 149 |
| raw reset을 받는 입력 sampler recovery | 18 | 18 |
| reset으로 보호되는 host_ready recovery | 3 | 3 |
| **합계** | **989** | **545** |

표는 세 코너를 합친 경로 행 수이며 LE나 최악 slack 집계 행 수가 아니다. 572의 **375개 setup 행은 모두 NES ↔ host/memory 교차**다. 같은 클록 안의 음수 setup/hold는 수집되지 않았다. 같은 클록 recovery는 loader fault → reader memory_reset[1], fast corner −0.427ns 한 행이다.

447개 직접 교차 제어의 제거는 이전 562 이후 변경의 효과를 이번에 분류한 결과다. 572의 최악 setup −5.695ns는 screen_status의 snapshot[31]에 들어오는 bus_drive 진단 비트다. 원시 bus_drive는 물리 OE의 즉시 차단에도 사용되므로 물리 차단과 진단 샘플링을 구분해야 한다. 이 비트는 현재 데이터 예산/예외 후보에서 제외했다.

## 동기화 체인과 데이터 유지 예산

배치된 572의 관련 70개 체인과 MMC558의 67개 체인을 조사했다. 첫 단의 fanout은 모두 지정된 다음 단 하나였고, 첫 단→둘째 단은 같은 클록이며 setup/hold가 양수였다.

| 572 체인 | 최소 setup ns | 최소 hold ns |
|---|---:|---:|
| Gray identity | +41.768 | +0.195 |
| 단일 비트 CDC | +4.298 | +0.268 |
| reset release | +4.297 | +0.187 |

첫 단의 raw setup 음수를 그대로 조합 논리 최적화 목표로 삼는 것은 적절하지 않다. 동시에 이 검사만으로 아날로그 metastability·전체 CDC·보드 전기적 signoff를 완료한 것도 아니다.

실제 mailbox206의 두 모드와 ROM reader를 두 시작 위상에서 실행했다. 위상당 plan 64개·tile descriptor 64개·ROM 읽기 64개다. source는 ACK까지 값이 바뀌지 않았고 수신 데이터도 독립 기대값과 일치했다.

| 경로 | 관측 최소 수신 대기 ns, 위상 1 / 2 | 임시 데이터 예산 ns |
|---|---:|---:|
| host → NES plan, consumer capture | 141.337 / 141.527 | 90.908 |
| NES → host tile descriptor | 35.817 / 35.861 | 23.808 |
| NES → memory ROM 주소 | 11.911 / 12.047 | 11.904 |

mailbox의 request 2단+capture 대기와 reader의 request 2단+IDLE 수락을 근거로 목적지 두 주기를 예산으로 잡았다. 실제 plan 소비자의 WAIT 캡처는 mailbox 내부 capture보다 뒤다.

**임시 STA 세션에서만**, 수집된 held-data 경로에 정확한 시작/끝점을 지정한 max-delay를 대조했다. 보드 SDC에 예외를 추가하지 않았다.

| 수집된 경로의 최소 예산 여유 | MMC558 | 572 |
|---|---:|---:|
| mailbox | +19.341ns | +19.837ns |
| ROM 주소 | +7.224ns | +7.341ns |

이 값은 조건부 데이터 유지 예산이다. 새 전체 WNS나 프레임 시간 개선으로 사용하지 않는다. 본격적인 제약 반영 때는 현재 최악 경로에 가려진 같은 버스의 다른 경로도 포함해야 한다.

## reset 경계

release chain의 두 번째 단까지 raw reset을 비동기로 넣는 것은 즉시 assertion을 유지하기 위한 구조다. 해제는 로컬 클록 두 에지를 거친다. 관련 규칙은 [Altera의 동기 해제 가이드](https://docs.altera.com/r/docs/683082/25.1/quartus-prime-pro-edition-user-guide/use-synchronized-asynchronous-reset?contentId=to1rfCGdVjeHnExJPxYxpw)와 일치한다. 이 일반 규칙을 전체 경로의 blanket 예외로 적용하지 않는다.

동일 memory clock의 fault → memory_reset[1] 음수 recovery는 추가로 검사했다. 현재 loader RTL에서 fault의 해제는 reset/active_reset에서만 가능하고, 그동안 reader_reset도 유지된다. 실제 rom_boot·loader·reader에서 잘못된 START로 fault를 만든 뒤 32개 명령 조합, 공통 reset·해제를 실행했다. fault가 임의 명령으로 지워지거나 reader가 열리는 경우는 없었다. 두 위상 모두 통과했다. 이는 해당 RTL 규칙의 기능 증거이며 회로 전체의 analog reset 증명은 아니다.

sink의 idle_ss/idle_write, top의 sink_rom_fault, host_ready는 일반 reset chain으로 묶지 않았다. local reset과 idle 조건이 사용 시점을 보호하는지 별도 대상으로 남겼다. fault 즉시 차단용 비동기 assertion과 정상 실행을 위한 로컬 해제를 계속 구분한다.

## 보존·판정과 후속 순서

MMC558/572의 입력 소스·QSF·SDC, 기존 SOF와 STA summary 해시가 이전 검증과 일치한다. 572 비용은 **15,297 LE·8,390 FF·14,195 조합 논리·51M9K**, 기존 관련 setup/hold **+0.286/+0.145ns**다. raw 전체 STA 회귀 판정도 그대로다. 이번 결과를 근거로 기존 실기 gate를 통과했다고 선언하지 않는다.

표시 일정은 RTL·firmware가 바뀌지 않아 기존 검증을 유지한다. 두 위상 952·957은 5 VBlank·최종 대기 0회, 마지막 ACK는 87,545,284 / 88,254,606 master clocks다. 이번 단계에서 65816 연속 재생·실기 FPS·메뉴 복귀 시험을 새로 실행하지 않았다.

다음 작업 순서는 다음과 같다.

1. **동일 제약으로 MMC558/572를 비교할 정확한 CDC 목록을 만든다.** 검증된 첫 단과 held-data만 대상으로 하고, 모든 비트·실제 fanout·수신 안정 시간·STOP 취소를 확인한다. 두 번째 단의 타이밍과 물리 데이터 지연 제한을 유지한다. 원래 raw STA도 별도로 보존한다.
2. **진단 snapshot[31]과 reset sampler/host_ready를 먼저 처리한다.** raw bus_drive의 물리 즉시 차단은 보존하고 진단용 샘플의 CDC를 검증한다. reset assertion을 늦추거나 검증되지 않은 경로를 false path로 숨기지 않는다.
3. 같은 클록 데이터·정상 해제의 실제 위반이 남으면 RTL 수정 대상으로 삼는다. 전체 회로를 다시 FIT하는 것은 이 범위와 개선 근거가 확정된 뒤 한 번 실행한다.
4. 변경된 경계에 한해 STOP·두 슬롯·첫 capture/cache/plan을 재검증하고, 두 위상 952·957·마지막 ACK 및 메뉴 복귀 경로를 확인한 뒤 전달 여부를 판정한다. 실기 기준 MMC558과 5–40초·40–55초 집계, RESTORE 제외 정책을 유지한다.

CDC 제약은 동작을 빠르게 만드는 최적화가 아니다. [Altera의 CDC 제약 설명](https://www.intel.com/content/www/us/en/docs/programmable/683243/25-1/constraining-cdc-paths.html)에서 설명하듯 무차별 clock-group/false-path는 물리 경로 최적화 범위까지 바꾼다. Lite에서 검증된 명령만 사용하며 Pro 전용 명령을 그대로 옮기지 않는다.

## 재현

기존 MMC558/572 배치에서 `report_nes_boundary575.tcl`을 실행한다. `nes_boundary575.py --board <board> --out <audit>`가 endpoint 분류와 읽기 전용 chain·임시 held-budget 보고 스크립트를 만든다. 스크립트는 ASCII 빌드 경로에서 실행한다. 단일 Starter FLOAT wrapper로 `check_nes_boundary575.py`를 실행하고 `analyze_nes_boundary575.py`가 기존 소스·SOF·STA 및 새 보고서를 대조한다.

선택 자료는 `probes/nes-boundary575/572-03`, `558-04`, Temp `nes-boundary575-test03`이다. 최초 분류기는 top-level sink_rom_fault와 MMC558의 과거 raw 제어를 분류하지 못해 중단했다. 이를 별도 분류로 추가했고 기존 실패도 보존했다. 초기 mailbox-only/test01, ROM 추가/test02, reset 추가/test03을 구분한다.

원시 보고서·분류·시험·도구 등 63파일을 `probes/nes-boundary575/archive01/evidence.zip`에 보존하고 전체 바이트를 재검증했다. SHA256은 `ec53535092d14b7df59d1acd976341a374e3709ebaa3b9447757fbc22b5c0b7a`이다. 라이선스 파일과 서버 로그는 포함하지 않는다.
