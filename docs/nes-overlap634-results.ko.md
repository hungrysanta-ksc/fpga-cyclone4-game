# 950 표시를 기다리는 동안 951 입력을 어디까지 받을 수 있나

**기존 출력 30패킷을 모두 유지하면 입력 7블록을 미리 받아 복원해도 951은 두 위상 모두 네 번째 VBlank에 표시된다.** 633의 팔레트·OAM 후반 여섯 패킷을 비용 없이 재사용하는 조건까지 합쳤을 때만 3 / 3회가 됐다. 그때 246번 선 이내의 최종 업로드 허가는 237 / 238번 선이었지만, 실제 화면 공개는 246 / 247번 선이었다. 두 번째 위상은 목표 검사선 마감보다 0.046 ms 늦었다. [기계 판독 결과](../analysis/overlap634-verification.json)

## 같은 작업량에서의 결과

625 tables-bg의 905–951 입력과 624의 원래 65816을 사용했다. 각 칸은 시작 위상 1 / 2 순서다. ACK 차이는 같은 위상의 원래 625 대비 값이다. 표의 SEAL 시각은 세 번째 VBlank의 246번 검사선 마감 기준이며 음수는 마감 전이다.

| 951 입력과 출력 | SEAL 수락 (ms) | 950→951 표시 간격 | 951 최종 ACK 차이 (ms) |
|---|---:|---:|---:|
| 원래 30패킷 | +6.520 / +7.311 | 4 / 4 | 0 / 0 |
| 7블록 전송만 선행, 30패킷 | −0.097 / +0.378 | 4 / 4 | −0.663 / −0.641 |
| 7블록 수신·복원 선행, 30패킷 | −2.962 / −2.205 | 4 / 4 | −0.876 / −0.620 |
| 전송만 선행 + 633 여섯 패킷 생략 | −3.177 / −2.963 | 4 / 4 | −0.399 / −0.316 |
| 수신·복원 선행 + 633 여섯 패킷 생략 | −6.653 / −5.829 | **3 / 3** | **−17.057 / −16.979** |

기존 30패킷에서 첫 BG map의 실제 65816 수락은 950 EA 후 25.499 / 25.464 ms에서 15.419 / 15.392 ms가 됐다. BG 선행량은 약 10 ms지만 그 자체로 표시 한 회를 얻지는 못했다. 여섯 패킷 생략까지 적용한 경우를 **동일한 633 생략 대조군**과 비교하면 ACK 이득은 16.371 / 16.332 ms다. 원래 625와 비교할 때만 위 표의 약 17 ms가 된다.

## 공유 SPI와 소유권

- 951 캡처 데이터는 950 EA보다 17.869 / 18.076 ms 먼저 확정됐다. 950의 END 수락, 마지막 ROM 응답, SEAL 발행을 확인한 뒤 첫 음성 E0 응답에서 수신을 시작하는 경우를 구성했다. 첫 D1은 0.826 ms, 원래 E0 사이의 최대 빈 구간은 0.172 / 0.387 ms이므로 원래 조회 시각을 모두 보존하면 첫 D1도 들어가지 않는다.
- 같은 응답을 주던 E0 36개를 생략하고 기존 observer·100 Hz tick 양쪽 조회, 마지막 음성 E0, 첫 양성 E0와 EA를 보존했다. D0/D1/복원/D2와 **POP 후 token+1을 확인하는 D0**까지 완료한 블록 7개가 들어갔다. 다음 블록은 앞 D0에서 확보한 ready 상태를 쓴다. 마지막 블록은 EA 0.834 ms 전, 기존 표시 ACK보다 0.423 / 0.221 ms 전에 끝난다. 조회 간격의 최댓값은 1.955 ms다. 이 값은 실기의 STOP 응답 시간 보증과 구분한다.
- 전송만 선행하면 원본 패킷 본문 1,758 B를 보관해야 하고, SPI·드라이버 시간 6.881 ms를 옮긴다. 임시 RAM 복사 비용은 별도로 더하지 않은 낙관 조건이다. 기존 ARM receiver로 즉시 복원하면 확인 D0까지 총 10.063 ms를 옮긴다. 이전 표시 뱅크·identity와 출력 head는 계속 950이 소유하고, 새 D3·plan·BEGIN은 EA 이후에만 허용했다. 두 위상의 905–950 소비·표시·ACK 이벤트는 대조군과 클록까지 일치했다.
- 남은 951 출력 발행 간격은 625의 실제 ARM 기록을 바탕으로 계산했다. 원래 E0가 요구한 소비 개수에 도달하지 않았으면 실제 65816 ACK를 기다리고, 측정된 조회 주기 단위로 다음 발행을 미뤘다. 네 칸 credit과 head 순서를 지킨 결과다. 633 생략 조건은 기존 949 뱅크와 951 WRAM을 바이트 단위로 대조한 뒤 두 수신 길이를 시험기가 무료로 채워 준다. 실사용 재사용 명령의 비용은 여기서 측정되지 않았다.
- 951의 CHR 공급 96건은 원래 625 기록상 모두 OBJ 캡처 적중이다. 새 BG ROM 읽기에서 생긴 이득으로 집계하지 않았다. 951 마지막 POP이 빨라지면 952 캡처 시작도 NES 위상 한 번만큼 앞당겨진다. EA 후 16.807 / 16.600 ms에 952 캡처가 시작될 때 951은 여전히 OBJ 캐시를 사용한다. 두 cache bank가 서로 다른 세대를 보유하고 이전 뱅크를 해당 EA에만 해제하는지 실제 보드 연결에서 확인해야 한다.

## 실제 ARM 링크와 검사

625의 링크 소스에 SEAL 전송 성공 후에만 활성화되는 제한 수신 callback을 붙였다. 최종 ACK를 기다리는 E0에서 진행이 없을 때만 receiver poll을 최대 일곱 번 호출한다. 기존 D1 CRC와 D2 후속 D0를 사용하며 callback 안에서는 D3를 발행하지 않는다. 표시 identity는 950 video/sink에서 읽는다. [498의 이전 구현과 소유권](nes-prefetch498-contract.ko.md)

실제 Cortex-M4 ELF를 실행한 분리 시험에서는 보통 E1·credit 대기·E0 진행 응답에서 선행 수신이 없었고, SEAL 후에는 정확히 7개를 수신·복원했다. map prefix를 원본 951 geometry와 비교했고, video generation은 950을 유지했다. 입력 IO 실패, CRC 오류, D2 직후 service 취소와 deadline을 주입해 모두 중단했고 조기 D3는 없었다. 분리 호출에서 관측된 최대 스택은 728 B다.

전체 ARM 파일은 **212,976→213,112 B**로 136 B 증가해 Flash 한도 212,992 B를 **120 B 초과**했다. 이번 수치는 SPI·서비스 응답을 모델링한 실제 ARM 단위 시험과 별도의 65816 재생에서 나왔다. 보드에서 새 exporter·ARM·IRQ를 한꺼번에 구동한 실측은 남았다. 이번 단계에서는 Quartus와 실기 전달본을 진행하지 않았다.

## 다음 판정

621을 유지한다. 다음은 비용이 0이었던 팔레트·OAM 재사용을 **대상 뱅크의 최종 ACK 이력을 독립 확인하는 실제 명령**으로 대체했을 때 두 위상의 여유가 남는지부터 본다. 951에서 수신·복원 7블록을 유지하고 단독·조합을 분리한다. 특히 위상 2의 화면 공개를 246번 선 안에 넣어야 한다. 그 뒤에 498의 END/drain export·조기 D3 거부·STOP/cold를 현재 보드에 결합하고 Flash 120 B 초과를 해소한다. 957까지의 연속 일정과 메뉴 복귀는 그 후보에서 판정한다.

## 재현

625 tables-bg와 633 원자료가 있는 `$raw`, 624 client 및 기존 Mesen을 사용한다. 준비 단계 후 기존 ARM 전체 빌드 스크립트를 실행한다.

```powershell
$arm = '../probes/nes-overlap634/link02'
python tools/prepare_nes_overlap634.py ../probes/nes-seal625/tables-bg $arm
./tools/build_nes_trial577.ps1 $arm
python tools/check_nes_overlap634_arm.py --arm "$arm/src" --data ../probes/nes-delta231/test07 --out ../probes/nes-overlap634/arm.json
foreach ($phase in 1,2) {
  foreach ($policy in 'fixed','buffer','restore') {
    foreach ($mode in 'control','collapse') {
      if ($policy -eq 'fixed' -and $mode -eq 'collapse') { continue }
      python tools/replay_nes_overlap634.py --trace "$raw/nes-seal625-tables-bg-$phase" --client ../probes/nes-raw624/client --mesen $mesen --feedback --mode $mode --policy $policy --out "$raw/nes-overlap634-$policy-$mode-${phase}c"
    }
  }
}
python tools/analyze_nes_overlap634.py --root $raw --arm ../probes/nes-overlap634/arm.json --out analysis/overlap634-verification.json
```
