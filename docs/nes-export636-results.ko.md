# 636 — 입력 선행 수신을 실제 SEAL 전송과 보드 ROM에 연결

실기 기준은 MMC613이다. 635에서 951만 재생했을 때의 3 VBlank는 전체 실행 결과와 구분한다. 636은 캡처 905부터 957까지 매번 실제 ARM 코드가 수신·계획·발행하고, Mesen의 65816이 독립 검사·DMA·표시·최종 ACK를 실행하는 일정이다. SPI 서비스 시간은 실기 기반 할당, ROM 공급은 기존 중재 추적, ARM은 CPI 2 및 실제 SysTick 코드다. FPGA RTL·보드 FIT는 같은 입력의 별도 시험이며 실기 FPS는 측정하지 않았다.

## 무엇이 실제 동작을 막았나

기존 ARM 송신 함수는 SEAL을 `io(tx,tx,...)`로 보냈다. 같은 메모리로 SPI 응답을 받은 **뒤** `tx[1]==3`을 검사해, 표시 대기 중 다음 입력 수신을 켜지 못했다. 634의 분리 시험은 송신과 수신에 다른 주소를 써서 이 결함을 검출하지 못했다. 같은 주소를 쓰는 회귀 시험을 추가했다. 636은 전송 **전** 명령 종류를 보존하고 성공한 전송에서만 일곱 번의 기회를 부여한다. 실패한 전송·CRC·시간 제한·STOP은 성공으로 집계하지 않는다. D1은 수신, D2는 블록 반환, D3는 준비 승인이다. 현재 출력의 최종 ACK와 EA 뒤에만 다음 D3를 허용하며, FPGA가 이후 COMMIT 레코드를 수용해야 collector가 해제된다.

보드에서는 기존 NES plan의 END 수락 상태와 reader drain으로 다음 export의 시작을 허용한다. 시작한 뒤에는 reader가 다시 바빠져도 export가 유지된다. 이전 lease가 살아 있으면 다음 D3는 수락하지 않는다. 두 슬롯 수와 캐시 RAM은 그대로다. 951·952의 실제 collector 자극에서 이전 OBJ hit를 다음 캡처 중과 다음 export의 PREPARED 뒤 모두 확인했다. 이전 EA 뒤에는 이전 조회만 miss이고 새 COMMIT은 성공했다(256/256 hit, 이전 EA 1회). END·drain·COMMIT·진행 중 drain을 각각 잘못 연결한 4개 변이는 별도 시험에서 모두 검출했다.

## 905~957 연속 결과

아래는 같은 시작 시각의 **동일 부트 ROM·동일 65816·동일 SPI·ROM 부하**에서 기존 ARM(응답 후 판별)과 수정 ARM(송신 전 판별)을 비교한 값이다. 밀집은 951~955 표시 간격 다섯 개의 합이고 마지막 ACK 이득은 957에서의 누계다. 전 화면에서 map·RGB를 보관된 625 기준과 대조하고 팔레트 512 B·OAM 544 B를 매 ACK 시 실제 PPU 메모리와 비교했다. 캐시 적중은 BG 48·OBJ 1,200회다.

| 시작 조건 | 951 간격(위상 1 / 2) | 수정본 실제 공개 선 | 밀집 VBlank 합(대조 → 수정) | 마지막 ACK 단축(위상 1 / 2) |
|---|---|---|---|---|
| 기존 시작 시각, 부팅 중 ARM 시작 | 4 / 4 → 3 / 3 | 246 / **249** | 21 / 22 → 19 / 19 | 531.642 / 498.216 ms |
| WRAM 본체 기동 후 ARM 시작 | 4 / 4 → 3 / 3 | 246 / 246 | 21 / 22 → 19 / 19 | 481.652 / 514.985 ms |

같은 ROM의 부팅 후 대조에서 밀집 평균 간격은 69.943 / 73.019 → 63.171 / 63.232 ms다. 차이는 53개 화면 실행의 누적 효과이며 1회 부팅하거나 951 한 화면에서 0.5초를 번다는 뜻이 아니다. 각 행에서 위상 차이는 178,684 master clocks다. 두 행은 다른 ROM 허용 구간에 걸릴 수 있어 행을 가로질러 시간을 빼지 않았다.

양쪽 조건 모두 951 입력 일곱 블록 중 네 블록만 이전 최종 ACK 전에 D2까지 마쳤다. 635의 일곱 블록을 모두 미리 복원한다는 전제를 그대로 쓰면 안 된다. 수정본 957의 최종 추가 대기 0회는 유지하지만 952의 표시 간격은 두 위상 모두 **5 VBlank**로, 이전 625의 4회를 지키지 못했다.

캡처 시각도 따로 검증했다. D3 시점에 COMMIT이 즉시 enqueue된다고 두면, 한 위상에서 다음 첫 D1이 이전 COMMIT의 실제 D2 반환을 기준으로 한 보수적 허용 시각보다 빨랐다. 그래서 **COMMIT의 D2 반환 뒤에만 다음 캡처를 허용**해 부팅 후 두 위상을 재실행했다. 951의 3 / 3회·246 / 246번 선, 951~955의 19 / 19회, 957의 최종 대기 0회와 마지막 ACK(72,879,636 / 72,521,108 master clocks)가 원래 실행과 정확히 같았다. 해당 대조군의 첫 유효 상태 조회도 모두 늦은 경계 이후였다. 이 경계 검사는 실제 보드 한 대로 측정한 latency를 대신하지 않는다.

**선택:** 실기 ZIP은 보류한다. 다음은 952의 업로드를 먼저 줄인다. 952의 SEAL 수락 뒤 map 1,728 B·tile 560 B·raw 192 B가 남고, 마지막 표시 대기는 0회인데도 업로드 도중 VBlank 대기에 24.46 / 24.43 ms를 썼다. 마지막 표시 검사선을 완화하지 않고 이들 DMA를 앞선 구간으로 옮길 수 있는지를 검사한다. 950의 확정 END·마지막 bulk ACK·951 캡처 완료 이후 SEAL 발행까지는 4.08 / 4.52 ms이고, 그중 SPI 서비스가 이미 차지한 시간을 빼면 최대 1.72 / 1.84 ms다. 남은 세 입력 블록의 D1 전체 전송만 2.33 ms여서 이 구간만으로 세 블록을 옮길 수 없다. [재현 수치·해시](../analysis/export636-verification.json)

## 보드에 들어가는 실행 코드

| 항목 | 결과 |
|---|---:|
| 635 ARM → 보고서 압축 대조군 → 636 수정본 | 213,424 → 212,856 → 212,868 B |
| 수정본 Flash 여유 / BSS | 124 B / 19,544 B |
| 성공·실패 보고서 | 기존 바이너리와 출력 바이트 동일, 종료 보고 시 관측 최대 스택 7,744 B |
| 65816 실행 본체 / 실제 보드 ROM | 5,760 B / 5,120 B(벡터 포함) |
| ROM 저장 | 부트 코드 272 B, 비압축 앞부분 896 B, 압축 스트림 3,840 B; 예약 영역 제외 여유 32 B |
| 원래 부트 → 압축 부트의 WRAM 본체 진입 | 1,235,152 → 6,274,666 master clocks(부팅 1회 +234.644 ms) |
| MMC613 → 636 전체 보드 FIT | 15,332 → 15,351 / 15,408 LE, FF 8,474·RAM 303,216 bits·M9K 56/56 동일 |
| 느린/빠른 코너 전체에서 최저 setup / hold | +0.487 / +0.163 → +0.565 / +0.153 ns |
| 최저 recovery / removal | +1.652 / +0.490 → +1.682 / +0.481 ns |

ARM의 보고서 서식 8개만 종료 시 복원한다. 실제 SNES 부트는 원본 앞부분을 복사·대조하고 나머지를 WRAM에 풀어 다시 비교한다. 5,760 B 전체 일치, WRAM 손상 시 본체 진입 전 E1 정지, 실제 보드 ROM 5,120 B 읽기·주소 공백·STOP·정지 클록 reset을 확인했다. 보드 SDC와 ROM 매퍼는 바꾸지 않았다. FIT 성공과 양의 내부 제약 slack이 외부 IO 전체 sign-off나 실기 복귀 증거는 아니다. 메뉴는 같은 ARM ELF의 정상·base 실패·menu 실패·오류 latch·checkpoint 실패 경로를 검증했다.

보드 613과 같은 STA 경로 판독에서 ROM_OE 최소 setup은 +0.592 → +0.895 ns, ROM_1CE는 +3.928 → +4.165 ns, ROM_2CE는 +3.662 → +3.923 ns다. 전체 hold·removal 최소값은 각각 0.010·0.009 ns 감소했다. 모든 코너의 TNS는 0이다.

## 재현

635의 [실행기와 입력](nes-reuse635-results.ko.md)을 준비한다. 이 분석에서 `$raw`는 ASCII 시험 결과 루트, `$b`는 `../probes/nes-reuse636`이다. 출력 폴더는 새 폴더를 사용한다.

1. `tools/prepare_nes_report636.py ../probes/nes-reuse635/arm01 "$b/arm01" --keep-alias-bug`로 대조군, 같은 명령에서 옵션을 빼고 출력 경로를 `"$b/arm02"`로 바꿔 수정본을 생성한다. 각각 `tools/build_nes_trial577.ps1`로 전체 링크한다. `check_nes_reuse635_arm.py`, `check_nes_overlap634_arm.py --in-place`, `check_nes_report594.py`, `check_nes_menu533.py --trial 577`로 같은 ELF를 검증한다. 577은 시험용 이미지가 상속한 marker 이름이다.
2. `tools/nes_rom636.py ../probes/nes-reuse635/client04 "$b/client02"`로 만들고 `check_nes_rom636.py`로 reset·손상을 검사한다. `prepare_nes_export636.py --base "$raw/nes-trial613-board01" --client "$b/client02" --out "$raw/nes-export636-board01"`로 613의 78개 고정 입력 중 ROM과 RTL 4개만 교체한다. 이 경로에서 Quartus Lite `quartus_sh --flow compile board`를 한 번 수행한다. 같은 위치에서 613의 `quartus_sta -t <613 보드>/review612.tcl`로 ROM 핀을 판독한다.
3. 단일 Questa FLOAT wrapper에서 `check_nes_rom613.py --client-sha <생성한 ROM의 SHA256>`, `check_nes_board611.py`, `test_nes_prefetch498_boundary.py`, `check_nes_lifecycle611.py --overlap --geometry ../probes/nes-geometry230/stim05`를 실행한다. 마지막 시험은 951·952의 실제 캡처 두 개, 제어 경계 시험은 별도 END·drain·STOP 주입이다.
4. 아래 일정을 같은 폴더 배치로 실행한 뒤 `tools/analyze_nes_export636.py --traces $raw --build $b --out analysis/export636-verification.json`로 판정한다. 각 케이스는 같은 입력·계획·ROM calendar를 사용한다. 출력 경로는 `nes-export636-run<위상><태그>`다.

```powershell
# d/e: 기존 ARM 시작 시각(압축 boot 포함); f/g: WRAM 초기화 후에도 반 프레임 차가 있는 쌍.
foreach ($tag in 'd','e','f','g','h') {
  $arm = if ($tag -in 'd','f','h') { 'arm02' } else { 'arm01' }
  $offset = if ($tag -in 'f','g','h') { 4288416 } else { 0 }
  $bound = if ($tag -eq 'h') { @('--commit-pop-bound') } else { @() }
  foreach ($phase in 1,2) {
    $start = 3000000 + $offset + ($phase - 1) * 178684
    python tools/test_nes_export636.py --arm "$b/$arm/src" --client "$b/client02" --samples "$raw/nes-snoop601-trace01/stim.tsv" --data ../probes/nes-delta231/test07 --fixture ../probes/nes-dense519/fixture02 --plans ../probes/nes-seal538/plans01 --capture ../probes/nes-output489/audit01 --calendar "$raw/nes-service509-rom03" --driver503 analysis/hardware503-mmc502.json --mesen $mesen --start-clock $start --out "$raw/nes-export636-run${phase}$tag" --keep-run @bound
  }
}
```
