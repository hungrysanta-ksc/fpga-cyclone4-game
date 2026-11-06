# 951 팔레트·OAM 재사용을 실제 수신 명령으로 연결

**입력 7블록 선행 복원과 실제 재사용 명령을 결합해 두 시작 위상 모두 3 VBlank가 됐다.** 최종 업로드 허가는 236 / 239번 선, 실제 화면 공개는 240 / 243번 선이었다. 246번 선 끝까지 0.398 / 0.231 ms가 남았다. 원래 625 일정 대비 최종 ACK는 17.439 / 17.254 ms 빨랐다. [검증 데이터](../analysis/reuse635-verification.json)

## 구현과 비용

ARM은 최종 표시 ACK를 받은 팔레트 512 B·OAM 후반 432 B의 공통 스냅샷과 뱅크별 ACK serial을 갖는다. 현재 출력과 바이트 단위로 같고 두 뱅크의 이력이 모두 유효할 때 opcode 9, section 4를 발행한다. 본문은 OAM 앞부분 112 B와 대상 뱅크의 이전 ACK serial 4 B다. 내용 변경·cold·한쪽 이력 누락은 기존 전체 전송을 사용한다. 새 스냅샷과 serial은 SEAL 최종 ACK 검사와 resident commit 뒤에 확정한다.

65816은 기존 sequence·generation·serial 검사에 더해 section·offset·length·span, 비활성 대상 뱅크, 그 뱅크의 최종 ACK serial, 아직 팔레트·OAM을 받지 않은 상태를 검사한다. 검증과 112 B literal DMA 완료 뒤에만 수신 길이를 설정한다. 뱅크 serial은 실제 최종 ACK 경로에서 공개하고 cold·오류·STOP에서 무효화한다.

재사용할 **944 B 전체를 활성·비활성 WRAM 사이에서 정확히 비교**한다. BEGIN에서 진행을 초기화한다. 입력 큐가 빈 동안 기존 map·tile 선행 DMA를 먼저 처리한 뒤 STOP·새 head를 다시 확인하고 16 B씩 검사한다. 한 조각 후 수신 poll로 돌아간다. 팔레트·OAM 수신이 시작되면 선행 검사를 중단한다. 실제 재사용 명령은 두 수신 길이가 0이어야 하므로 부분 덮어쓴 뱅크의 증명을 사용할 수 없다. 비교가 덜 끝났으면 명령 수락 뒤 남은 비교와 STOP 확인을 완료한다.

수신기가 두 뱅크의 동일성을 확인했으므로 표시 중인 PPU의 같은 데이터도 재사용한다. 마지막 DMA를 CGRAM 512→2 B, OAM 544→112 B로 줄인다. CGRAM 2 B는 기존 주소 설정·DMA 경로의 최소 갱신이다. 비교한 영역은 해당 트랜잭션의 최종 표시까지 쓰기 대상에서 제외하며 다음 BEGIN에서 단축 허가를 지운다. 기존 독립 tile·map·HDMA 검사와 최종 검사선은 유지한다.

951의 여섯 기존 패킷 388 B가 빠지고 새 serial 4 B가 더해져 E1 SPI 바이트는 **384 B 감소**한다. 같은 링크의 ARM 실행에서 비교 2,173개, 직렬화 386개 명령을 세었다. 재생에는 기존 literal head 비용에 이 2,559개 전체를 CPI 2로 추가하고 4 B SPI 시간도 더해 약 0.073 ms를 청구했다.

## 분리 대조

각 값은 위상 1 / 2 순서다. 간격은 앞선 950 표시 기준이다.

| 951 처리 | 표시 간격 | 실제 공개 선 | 판정 |
|---|---|---|---|
| 수락 시 944 B 비교, 마지막 전체 DMA | 4 / 4 | 239 / 243 | 검사가 후속 큐 소비를 지연 |
| 수락 시 비교, 마지막 축소 DMA | 4 / 4 | 233 / 243 | DMA 축소만으로 세 번째 blank 확보 실패 |
| 빈 큐에서 비교, 마지막 전체 DMA | 3 / 3 | 246 / 248 | 위상 2 마감 초과 |
| 빈 큐에서 비교, 마지막 축소 DMA | **3 / 3** | **240 / 243** | 두 위상 모두 246번 선 안에 공개 |
| 같은 수신기, 기존 30패킷 | 4 / 4 | 239 / 243 | 공통 코드 대조군 |

선정 후보는 **59회 × 16 B** 비교를 모두 큐가 빈 동안 완료했다. 마지막 조각의 시작은 재사용 명령 수락보다 11.413 / 11.933 ms 빨랐다. 명령 수락부터 소비 ACK까지는 0.388 / 0.388 ms다. 수락 시 비교 후보는 이 시점에 약 3.9 ms를 사용했다.

선정 후보와 같은 바이너리의 30패킷 대조군 사이에서 905–950 소비·표시 이벤트는 일치했다. 원래 625와 비교한 950 공개 시각 차이는 0 / +0.005215 ms다. 이 시작 차이도 결과에 포함했다. 최종 ACK 이득은 공통 바이너리 대조군 대비 **16.558 / 16.656 ms**, 634 무료 재사용 조합 대비 **0.381 / 0.275 ms**다.

## 검사

- 두 위상에서 905–951의 47화면씩 실제 65816을 실행했다. 모든 화면의 실제 CGRAM 512 B·OAM 544 B, 기존 map·HDMA 검사 및 RGB 결과를 원본과 대조했다. 큐 credit과 E0의 실제 소비 완료 의존성도 확인했다.
- 전체 링크 ELF의 실제 ARM 비교·직렬화·commit과 정상 SEAL 진입 함수를 실행했다. warm, 내용 변경·이력 누락 시 전체 전송, 최종 ACK 실패 후 이력 미공개, reset 무효화를 확인했다. 전송 endpoint는 시험 모델이다.
- 잘못된 뱅크 serial, 잘린 본문, 비교 시작 전 팔레트·OAM 끝 바이트 손상, 부분 수신, cold 재사용을 거부했다. 비교 중 STOP와 최종 업로드 STOP는 이전 화면을 보존하고 ACK 이력을 지웠다. 중단 WRAM·VRAM에서 두 cold 화면을 전체 복원하고 최종 ACK를 확인했다.
- 별도 연속 시험에서 950의 뱅크 1에도 같은 명령을 적용하고 951 뱅크 0의 최종 업로드를 중단해 950 화면 보존을 확인했다. 선행 비교 뒤 임의의 외부 메모리 비트 손상을 계속 감시하는 기능은 이번 증명의 범위 밖이다.

## 자원과 다음 연결

전체 ARM 파일은 **213,424 B**, 한도 212,992 B보다 **432 B 초과**다. 634 대비 Flash +312 B, 실제 BSS +952 B이며 sink 구조체는 988 B다. 같은 ELF로 단위 시험을 실행했다. 선정 65816 본체는 5,760 B로 기존 6,144 B 프로그램 영역 안에 들어간다.

시간 검증은 625의 실제 ARM 기록에 634의 7블록 선행 일정을 적용하고 새 명령의 ARM 계산·SPI 비용과 실제 65816 소비 ACK 지연을 추가한 재생이다. 이전 905–950 ARM의 스냅샷 유지 비용까지 포함한 전체 RUN·IRQ 재실행, exporter·두 캡처 cache bank의 보드 소유권 연결, 952–957 후속 일정, 메뉴 복귀의 새 실기 결과는 남아 있다. 이번 단계에서 Quartus 전체 FIT·STA와 새 전달본은 진행하지 않았다.

다음은 실제 전체 실행에 ARM 이력·선행 복원을 결합하고 Flash 432 B를 회수한다. END/drain 이후 export, 이전 최종 ACK·EA 뒤 D3, 952 캡처 중 951 OBJ cache 유지와 STOP/cold를 같은 보드 경로에서 검증한다. 그 뒤 957까지 연속 일정과 전체 FIT·STA·메뉴 복귀를 확인한다. 실기 기준은 MMC613, 보드 준비 기준은 616B다.

## 재현

기존 625 원자료를 `$raw`, Mesen 실행 경로를 `$mesen`으로 지정한다. 출력 폴더는 새 경로여야 한다.

```powershell
python tools/nes_reuse635.py ../probes/nes-reuse635/client04 --short-display --idle-proof
python tools/prepare_nes_reuse635.py ../probes/nes-overlap634/link02 ../probes/nes-reuse635/arm01
./tools/build_nes_trial577.ps1 ../probes/nes-reuse635/arm01
python tools/check_nes_reuse635_arm.py --trace "$raw/nes-seal625-tables-bg-1" --arm ../probes/nes-reuse635/arm01/src --out ../probes/nes-reuse635/arm02.json
foreach ($phase in 1,2) {
  foreach ($mode in 'control','collapse') {
    python tools/replay_nes_reuse635.py --trace "$raw/nes-seal625-tables-bg-$phase" --client ../probes/nes-reuse635/client04 --reference ../probes/nes-raw624/client --arm-result ../probes/nes-reuse635/arm02.json --mode $mode --mesen $mesen --out "$raw/nes-reuse635-${mode}-${phase}e"
  }
}
python tools/check_nes_reuse635.py --trace "$raw/nes-seal625-tables-bg-1" --client ../probes/nes-reuse635/client04 --arm-result ../probes/nes-reuse635/arm02.json --mesen $mesen --out "$raw/nes-reuse635-guards04"
python tools/analyze_nes_reuse635.py --root $raw --probes ../probes/nes-reuse635 --out analysis/reuse635-verification.json
```

분리 대조에는 분석기의 각 행에 대응하는 추가 실행이 필요하다. `client`는 기본 빌드와 a, `client02`는 `--short-display`와 b, `client04`는 두 옵션과 d·e, `client05`는 `--idle-proof`와 f다. d는 두 모드, e·f는 collapse를 실행한다. 분석기는 633·634 대조군의 보존된 결과도 읽는다.
