# NES181 OAM RAM 구조와 배치·배선 결과

SELECT `oamread181/map03 + test04 + core01 + check01`. 보드 입력 69개 중 `rtl/ppu.sv`만 변경했다. 현재 후보는 전체 FIT를 통과했지만 **실기 배포 승인 전**이다. packed1813/stream1815·ACK 수명·클럭·핀·SDC·기존 ARM은 그대로다.

## 작업 의미

부분 행 복구와 압축을 통합한 NES181이 FPGA에 들어가지 못하던 자원 장벽을 해소했다. 화면 정지 대응과 전송량 절감 코드를 유지한 채 OAM 저장을 실제 내부 RAM으로 옮긴 결과다. CPU/PPU 속도를 낮추거나 영상 압축을 제거하지 않았다. 이것만으로 실기 화면 정지 해결이나 60fps 달성을 증명하지는 않는다.

## 읽기·쓰기 계약

- CPU/행 복사와 상태 복원 쓰기는 기존 양의 edge에서 수행한다. 음의 edge에서 main/copy/extra/repeat/state용 행을 미리 읽는다. 소비 주소·제어는 그 이전 음의 edge부터 다음 양의 edge까지 안정되어야 한다. 원래의 무제약 비동기 입력 인터페이스와 동등하다고 주장하지 않는다.
- 상태 복원과 runtime은 독립 RAM에 쓴다. 바이트별 최신 작성자 비트로 선택하며, 같은 바이트에 동시 쓰면 runtime 우선, 다른 주소에 쓰면 둘 다 보존한다. 초기 OAM 내용에 새 reset 의미를 부여하지 않는다.
- 8바이트 행 복사는 앞서 읽은 행을 사용한다. CPU 속성 바이트의 `E3` 마스크와 secondary OAM·eval 조건은 유지한다.
- native 관찰 출력과 extra/savestate 경로를 일반 RTL에서 삭제하지 않았다. 현재 보드에서는 이 경로가 사용되지 않아 합성기가 제거한다. 현재 54 M9K 결과를 미래 savestate/extra 기능까지 켠 수치로 사용할 수 없다.
- 저장 배열은 64비트로 선언했지만 Quartus는 현재 main/copy 각각 8개의 256비트 RAM으로 쪼갰다. **4096비트에 M9K 16개**를 사용한다. 잔여 2개는 MMC4/5까지 여유가 확보됐다는 뜻이 아니다.

## 검증 결과와 한계

| 검증 | 결과 |
|---|---|
| 실제 OAMEval 기준 RTL 대조 | 216,362 cycles, 행 복사 2,426, CPU 쓰기 3,111, 상태 쓰기 10,473, 충돌 2,012 통과 |
| 잘못된 양의 edge 사전읽기 | 대조 실패를 정상 검출 |
| 실제 CPU/PPU/MMC3 + 짧은 자체 DMA ROM | DMA 16회, 독립 기대값 4096바이트 일치, CPU bus/OAM trace 기준과 동일 |
| 실제 코어 반 주기 입력 안정성 | 175,379회 통과. 이 DMA ROM은 rendering-off이며 SMB3 렌더링 검증은 아님 |
| OAM MAP | 조합 4015→1112, FF 2366→318, RAM 0→4096비트 |
| 전체 FIT | 13,311 LE / 928 LAB / 54 M9K. 기존 ACK 후보는 973/963 LAB로 배치 실패 |
| OAM 배선 후 STA | 3 corner, 2820개 보고 경로. RAM 입력 setup +3.184ns, RAM 출력 +12.238ns, 전체 OAM hold +0.187ns. 반 주기 관계 22.727ns 확인 |
| 전체 동기/관련 PLL 경로 | nominal setup **0.000ns(보고 정밀도)** / hold +0.150ns; 강화 기준 setup **−0.162ns** |
| 기존 제한된 CDC 검증 | 486행, 별도 reply 8비트×3corner 통과. 전체 CDC/MTBF 승인은 아님 |
| 조건부 외부 IO | PSRAM70ns 여유 +4.988ns, SNES 69.455ns/270ns, SPI 165.490ns/190.476ns. native payload 음수 recovery/removal 0 |

nominal 수치는 NES↔PLL 비동기 경로를 제외한 동기/관련 PLL 분류의 최저값이다. 전체 원시 STA에는 reset 관련 NES↔PLL setup 음수(−6.270ns)도 남아 있다. 이를 숨기거나 전체 타이밍 통과로 합치지 않는다. IO의 1000ns 추출용 제약은 승인 기준이 아니며 기존 디지털 조건부 계산만 재사용했다.

듀얼 클럭 RAM의 read-during-write 경고는 실제 양/음 edge 분리, primitive 동작 및 반 주기 검증과 함께 확인해야 한다. 일반 RTL 대조와 STA는 통과했지만 **합성 RAM primitive 대조·rendering-on 실제 코어 경계**는 아직 미검증이다. 실제 CPU/PPU 검사에는 ideal ROM/RAM backend를 사용했다. 전체 게임·핀 신호·실기 FPS 증거는 없다.

## 보존한 실패와 출처

`map01/test02`는 사전읽기만 추가한 후보: 기능 통과했으나 MAP 19,890 LE/8,675 FF, OAM RAM 0으로 악화되어 FIT하지 않았다. `test01`은 bench 줄바꿈 생성 오류, `map02/test03`은 `primary_copy` 선언 순서 오류이며 해당 파일·출력을 보존했다. `map03/test04`에서 수정했고 FPGA 기능을 약화한 우회는 없다.

다중 writer를 별도 저장소와 최신 작성자 선택으로 구현하는 구조는 [LVT 작성자 설명](https://fpgacpu.ca/fpga/RAM_Multiported_LVT.html)을 참고했다. 코드를 가져온 것은 아니며, 여기의 byte collision·edge 계약은 이 프로젝트에서 따로 구현·검증했다. Cyclone IV 메모리 참고 문서는 [공식 Memory Blocks 문서](https://cdrdv2-public.intel.com/654744/cyiv-51003.pdf)다. 이번 웹 접근은 403으로 본문을 재확인하지 못했으므로 장치 동작 승인의 새 근거로 집계하지 않는다.

## 다음 작업

1. 먼저 rendering-on 실제 CPU/PPU의 짧은 전환·행 복사 소비와 합성 RAM primitive의 반 주기 동일주소 동작을 확인한다. 일반 OAM 단위 검사나 긴 SMB3 부팅을 반복하지 않는다.
2. 현재 16개로 분할된 RAM을 byte-enable이 있는 넓은 포트로 묶을 수 있는지 MAP에서 검증한다. 다른 읽기 시점이나 쓰기 우선순위를 만들지 말고, 미래 mapper/상태 기능에 필요한 여유도 별도 계산한다. 목표 잔여 8 M9K/97 LAB는 계획치이며 최소 MMC3 실기를 이것만으로 막지 않는다.
3. 명확한 구조 변경이 있을 때만 FIT한다. 현 nominal 0.000/강화 −0.162의 loader CHECK 경로와 OAM 반 주기·기존 CDC/IO를 함께 확인한다. seed/작은 식 변경 FIT 반복, 관련 PLL false-path, 클럭 완화는 하지 않는다.
4. 승인 가능 후보가 되면 기존 paired ARM 여유 1384B와 실제 SNES1815 결과를 연결해 SMB3 숫자1 타일→A 실기로 간다. raw7 최소22.154ms 모델·단일 capture lease는 여전히 60fps 목표의 별도 병목이다.

배포 NES180, GBC164, 세이브 SRAM, 완료 archive는 유지한다. ASM/FW/ZIP은 이번에 만들지 않았다. AV→장시간 실행·오류/리셋 로그→입력 유지 확인 순서도 유지한다.
