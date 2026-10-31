# NES505 — 실제65816 불변 prefix 선행 DMA 검증

기준은 [504 예산](nes-budget504-contract.ko.md)과 실기 MMC502다. [검증 JSON](../analysis/early505-verification.json), [구현](../tools/nes_early505.py), [시험](../tools/test_nes_early505.py), [집계](../tools/analyze_nes_early505.py)를 함께 읽는다. PR140의 A2 실행 가능성 실험이며 **실기 선택은502 그대로**다.

## 교체한 실행 경계

- BEGIN에서 기존 dirty-list cursor1252를 초기화하고 SEAL의 cursor 초기화를 삭제했다. 이미 실행한 prefix는 최종 업로드 때 재전송하지 않는다.
- packet ACK 이후 main poll에서만 시도한다. mark212가 payload 복사 전에 descriptor를 만들거나 마지막 항목을 합치는 동안에는 호출하지 않는다. 다음 항목이 생긴 불변 prefix만 실행하고 마지막8B 항목은 SEAL까지 남긴다.
- 기존 일반 DMA 설정을 공통 함수로 뽑았다. inactive VRAM만 기록하며 CGRAM/OAM/HDMA·활성 bank 선택·표시 identity·최종 ACK는 기존 검사 뒤에 남는다. 첫 표시 전에도 VBlank 조건을 적용한다.
- 실제 HVBJOY/V counter로 현재225..256행인지 확인한다. `(260−V)×128` byte-equivalent에서 setup384B를 포함한 한 descriptor가 들어갈 때만 전송한다. 이 경로는 wait169를 호출하지 않는다. 최종 uploader의 budget은 새로 초기화하므로 이전 VBlank 잔여량을 재사용하지 않는다.
- 새1260..1263의4B는 tentative 플래그와 V counter scratch다. STOP/실패/quiet에서 tentative target의152B coverage와 raw certificate를 무효화한다. 이전 활성 bank와 표시 serial은 보존한다. 성공한 최종 표시 뒤에만 tentative 플래그를 해제한다.

추가 body205B/WRAM4B로504의512B/8B 할당 안이다. 기존489 body4311→4516B,5KiB program은 같고 body 여유444B다. 관측 stack 최대11B. 새 framebuffer·ARM 실행코드·FPGA 제어·M9K는 없다. 변경 ROM을 보드에 합성한 비용은 아직 없으며 기존502의121LE/5M9K 여유를 새 실측으로 주장하지 않는다.

## 실제 실행 결과

동일 입력·시작 시각의 각489 기준 실행과 비교했다. 과거496 연속 fixture는 ARM/IRQ/ROM과 공통 시간축에 연결된502 실기 warm 재현이 아니다.

| 시험 | 선행 전송 | 전체12개 최종 ACK 차이 | 첫 프레임 이후11개 구간 차이 |
|---|---:|---:|---:|
| 시작 위상0 | 19항목/3712B | −16.637215ms | −0.012758ms |
| 시작 위상85909 masterclocks | 21항목/3840B | −16.622223ms | +0.032686ms |

음수는 단축이다. **전체 단축은 거의 첫 프레임의 VBlank 한 번에 해당하며 지속적인 warm 개선은 입증되지 않았다.** 909에서 늦어진 시간이912에서 회복되는 등 중간 경계 이동을 각 프레임의 독립 개선으로 더하면 안 된다. 실제502 cold 입력은 선행 전송0B, 최종 ACK +0.008660ms였다.

모든 정상 실행은 총 VRAM DMA 바이트와 최종 RGB가 기준과 동일했다. 이미 소비한 descriptor의 변경·재전송, 열린 tail 소비, 활성 bank 선행 기록을 callback으로 거부했다. 두 위상에서 실제 선행 DMA 양 끝은225..258행이며 setup 최대1180masterclocks로 할당3072보다 작았다.

4KiB 불변 항목이 생긴 뒤 입력을 두 주기 정체시킨 별도 경계 시험은4112B를 선행 전송했다. 4096B DMA를 포함해 실제 양 끝226..251행, setup1180을 확인했다. 강제로 바꾼 일정이므로 성능 비교에는 쓰지 않는다.

STOP, coverage 손상, version/count/zero-count/length 오류의6개 시험은 모두 선행 DMA가 실제 발생한 다음 거부했다. 이전 활성 RGB·표시 serial을 보존했고 tentative bank coverage/raw certificate는 무효화됐다. boot 전 coverage/certificate/tentative 정보를 오염시킨 cold 시험도 통과했다. 기존 raw_boot489는 VRAM을 지운 뒤 known-zero certificate8080을 새로 만들므로 boot 기대값은0000이 아니다. 잘못된 기대값으로 실패한 cold02와 수정한 cold03을 함께 보존했다. 후보 ROM bytes는 바뀌지 않았다.

독립 coverage/semantic 검사와 최종 표시 ACK는 실제65816에서 실행했다. FPGA transport CRC/STOP·ARM runtime 종료·메뉴 복귀 코드는 변경하지 않았으며 **새 FPGA 공동 실행이나 실기 메뉴 시험으로 검증한 것은 아니다.**

## 판정과 다음 순서

505는 안전한 실행 경계의 실현 가능성을 확인했지만 전달 후보로 선택하지 않는다. 이 구조의 opcode·VBlank 위상·작은 counter 조정은 반복하지 않는다. packet 준비 시점 또는 전송 ABI가 바뀌어 새로운 warm 이득 근거가 생길 때만 재검토한다.

1. 현재 wire 본문 및 map/ordinary 준비 의존성을 대상으로 실제 ARM·공유 SPI·IRQ·ROM 일정과 연결한 후보를 비교한다. 기존 조회 제외5911.51B/표시의 예산 부족과 준비 비용을 함께 줄여야 한다.
2. 초기 cold 이득과 이후 연속 구간을 별도로 판정하고, 전체60Hz 예산이 닫히는 구조만 선택한다. STOP/coverage/최종 ACK를 줄여 이득을 만들지 않는다.
3. 선택 후에만 변경 ROM/RTL과 일치하는 Quartus Lite 전체 비용·타이밍을 확인하고 고유한 이름의 실기 전달본을 만든다. RESTORE 폴더는 넣지 않는다.

새 설치본·ARM firmware·Quartus·Questa 실행은 없다. MMC502의10.59fps 실기 결과는 그대로다.

## 재현과 근거 보존

private 근거는 workspace의 `probes/nes-early505/{client01,client02,evidence,source,archive01.json}`에 있다. 원시 packet/pixel/상용 ROM 파생 입력과 바이너리는 Git에 넣지 않는다. 공개 검증 JSON은 선택 근거의 SHA256을 보존한다. cold02 실패를 삭제하지 않는다.

```text
python tools/nes_early505.py --out <new-client-directory>
python tools/test_nes_early505.py --input <frozen-fixture> --client <new-client-directory> --baseline-client <489-client04> --out <new-ASCII-directory>
python tools/analyze_nes_early505.py --root <private-evidence> --client <new-client-directory> --out <verification.json>
```

시험은 Mesen 실제65816이다. 네트워크·Questa 라이선스·실기 연결을 요구하지 않는다. fixture/expected pixel/기준 ACK가 없으면 동일성·시간 비교를 주장할 수 없다.
