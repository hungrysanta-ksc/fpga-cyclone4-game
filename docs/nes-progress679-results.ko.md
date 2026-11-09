# 679: 실제 map DMA 진행 공개 경계와 비용 상한

**956의 남은 map 896B는 이미 수락됐지만, VBlank에 HDMA 패딩과 후속 tile이 큐를 점유한다. DMA 진행 알림만 추가해서는 이 기회가 생기지 않는다.** 최소 인터페이스는 기존 E0의 예약 비트로 정하되, 아직 제품에 채택하지 않는다. MMC666을 유지한다. [재현 가능한 분석](../analysis/progress679-budget.json) · [분석 도구](../tools/analyze_nes_progress679.py)

이번 단계는 678의 실제 두 위상 로그·합성 입력·ARM 바이너리를 고정한 **경계·예산 검토**다. 새 ARM/65816 실행, RTL 합성, 실기 시험은 하지 않았다. 678의 빈 STATUS 수신 예산 수정, 952 표시 3회, 큰 plan 묶음을 후속 구현 기준으로 유지한다. 678 전체를 실기 선택본으로 승격했다는 뜻은 아니다.

## 실제로 막힌 구간

아래 시간은 각 위상 956의 직전 표시부터다. 같은 작업량·전체 시작 시각 7288416/7467100을 유지한 678 재생에서 추출했다.

| 관측 | 위상 1 | 위상 2 |
|---|---:|---:|
| 마지막 map 수락 ACK | 27.732386ms | 27.722795ms |
| HDMA 패딩 1100B 수락 | 31.650202ms | 31.329119ms |
| 같은 패딩 ACK | 33.109885ms | 32.804539ms |
| 패딩 수락→ACK | **1.459683ms** | **1.475420ms** |
| 다음 tile이 FPGA 큐에 도착 | 32.0408ms | 31.6787ms |
| 다음 tile의 SNES 수락 | 33.1449ms | 32.8377ms |
| 패딩 중 225–252선의 비종료 64B 확인 지점 | 13회 | 7회 |
| 그중 다음 패킷이 아직 큐에 없는 지점 | **0회** | **0회** |
| 이미 수락된 map / 선행 DMA / 남은 map | 1024 / 128 / **896B** | 동일 |
| 최종 업로드의 map 세 건 시작→다음 DMA 시작 | **0.435344ms** | **0.435716ms** |

패딩은 wire 21B를 SNES에서 64B×17+12B로 복원한다. `fill_service545`의 실제 STOP 확인 지점과 후속 패킷의 `push/load`를 대조했다. 패딩 복원에 map DMA를 끼워 넣으면 CPU 실행 여지는 있지만, **모든 해당 지점에 다음 tile이 이미 대기한다.** 현재의 새 패킷 우선 조건을 유지한 개선으로 계산할 수 없어 제외했다. 이 결과를 패딩 오류나 STOP 누락으로 해석하지 않는다.

남은 map은 384+128+384B다. 데이터 전송만의 하한은 약 0.334ms이고, 관측한 세 DMA의 시작부터 다음 tile DMA 시작까지는 약 0.435ms다. 후자는 설정·다음 진입 비용도 포함한 **관측 구간**이며, 이를 모두 제거 가능한 절감량으로 쓰지 않는다. 선행으로 옮길 때도 DMA·설정 비용 자체는 발생한다. 같은 VBlank 내의 최종 업로드에서 빠질 가능성이 있는 시간 예산일 뿐이다.

678은 밀집951–955 평균이 MMC666보다 0.045667/0.056543ms 빠르지만, 957 마지막 ACK는 **+0.010430/−0.182705ms**다. 위상1에서 최소 224 master clocks보다 큰 **순** 개선이 필요하다. 앞선 956을 움직이면 957의 ROM/VBlank 위상도 달라지므로 0.435ms를 마지막 ACK에서 그대로 빼지 않는다. 956만 줄인다면 밀집951–955 평균은 추가로 좋아지는 것이 아니라 기존 개선을 보존하는 것이다.

## 확정한 최소 공개 계약

제안 이름은 `E0.flags[3] = MAP_DMA_PROGRESS`다. 의미는 **마지막 E1 수락 뒤 큐가 빈 구간에서, 이미 독립 검사된 map DMA가 적어도 한 번 끝나고 실제 cursor가 갱신됐다**는 것이다. 전송 바이트 수·모든 map 완료·표시 완료를 뜻하지 않는다.

1. SNES는 기존 비활성 뱅크·수락 범위·VBlank 검사와 STOP/새 패킷 우선 판정을 그대로 실행한다. `MDMAEN` 반환과 map cursor의 실제 retire 뒤에만 신규 제어 주소 `$00601D`에 `$A5`를 쓴다. 주소는 설계 예약이며 아직 RTL에 구현하지 않았다. 일반 수신 ACK/READ, raw·tile DMA, 패딩 DMA에서는 발행하지 않는다.
2. 기존 `nes_sink_bus165`의 주소·데이터·`/WR` 동기화와 write-end 검출을 재사용한다. bridge의 bus와 endpoint는 실제로 같은 host clock이다. 새 비트와 pulse의 edge 처리는 후속 검증 대상이며 CDC가 자동으로 통과한다고 주장하지 않는다.
3. FPGA는 `used==0 && ack_valid && !checking`이고 세션이 활성·정상일 때만 event를 보관한다. E1 수락, ACK staging/publish, reset/RUN 해제, STOP·fault가 publication보다 우선해 지운다. E1 수락과 같은 edge의 publication은 버린다. 새 주소 write는 ACK checker·retired·credit·queue RAM을 절대 갱신하지 않는다. STOP은 현재 endpoint에 없는 입력이므로 bridge→endpoint 무효화 연결 비용도 포함한다.
4. event는 기존 19B snapshot 안의 예약 비트로 넣어 같은 CRC8 순회에 포함한다. snapshot 폭·ACK12·SPI 20B 거래 길이는 바꾸지 않는다. SNAPSHOT과 같은 edge의 event는 이전값 0이어도 된다. 데이터 손실을 허용하는 **성능 참고값**이다.
5. ARM은 기존 `status_flags`를 재사용한다. 현재의 `flags & 0xf8` 거부를 예약 bit3만 허용하도록 바꾸되 bit4–7의 오류/미지원 검사는 유지한다. 큐가 비고 `accepted==retired==sent`, ACK magic·opcode·seq·serial·generation이 현재 `last`와 모두 일치하며 현재 BEGIN/대상 bank 문맥이 유효할 때만 사용한다. SPI 뒤 STOP guard도 통과해야 한다. `status()`가 identity 검사 전에 저장하는 `ack_status/status_flags`를 그대로 사용하면 안 된다.
6. event 하나로 staging을 해제하거나 새 COMMIT/표시 이력을 허가하지 않는다. 다음 tile의 실제 발행은 기존 bulk·credit·token·STOP 검사로 결정한다. 표시 이력은 여전히 최종 ACK 뒤에만 확정한다. cold/부분 전송/STOP 이후 새 BEGIN이 이전 event를 사용할 수 없다. seq/credit wrap은 기존 전체 identity에 묶으며 1bit toggle 횟수로 해석하지 않는다.

이 계약은 **빈 큐에서 기존 ACK를 다시 쓰는 안과 다르다.** 현재 endpoint는 빈 큐 ACK write/publish를 fault로 처리하며, 유효 ACK는 head를 retire한다. 기존 ACK status bit를 사후 변경해도 안 된다. 또한 ACK 시점에 progress bit를 한번 붙이는 것만으로는 이후 idle DMA가 끝난 사실을 알릴 수 없다.

event가 0이어도 기다리는 루프를 만들지 않는다. STOP·새 패킷 경합으로 event가 버려질 수 있고, 최종 SEAL 없이 더 할 DMA가 없는 경우도 있기 때문이다. 기존 ARM 작업 진행/수신 callback 중 관측하는 비차단 정보로만 사용한다. 새 패킷 우선순위를 무시해 event를 만들거나, event를 얻기 위해 다음 VBlank까지 큐를 막는 방식은 제외한다.

## 회로·ROM·왕복 예산

| 경계 | 기존 재사용 | 추가분의 상한/검증 조건 |
|---|---|---|
| FPGA 저장 | 기존 ACK identity·152bit snapshot·queue RAM | event 1bit+bus pulse 1bit의 **설계 할당**. 새 identity/counter/M9K 0 |
| FPGA 제어 | 기존 write 동기화·E0 serializer·CRC8 순회 | `$601D` decode, event/STOP 무효화·snapshot 선택·bridge 배선은 새 비용. 전체 **≤15408 LE /963 LAB /56 M9K** |
| 회로 여유 | 현재15324 LE/962 LAB/56 M9K | **순증 ≤84 LE·1 LAB·0 M9K**. 합성 전 실측 증분은 미정; 삭제 실적0 LE |
| ARM | `status_flags`, 기존 last identity/guard·credit | 678 전체212800B에서 **순증≤192B**, 전체≤212992B. static RAM 추가0 목표, 전체 링크로 확인 |
| 65816 | 기존 map DMA 선택·cursor·STOP·reply | body5792→**≤5984B**, persistent WRAM 추가0 목표. 선택한 map임을 retire 후까지 보존할 scratch/stack 수명도 실제 코드에서 확인 |
| SPI | 기존 E0 20B | 기존 조회에 포함하면 추가 wire0B. 새 E0 한 번은 **20B/최소60.952µs**이며 driver·CPU·경합은 별도 |
| IRQ/CPU | 기존 poll/IRQ 경계 | 새 IRQ 추가0. idle loop마다 store/query를 반복하지 않고 실제 map DMA 완료에만 발행 |

84 LE·1 LAB는 **사용 가능한 최대 예산**이지 설계가 그 안에 들어간다는 합성 결과가 아니다. 2bit 상태만 보고 decode·배치 비용을 무시하지 않는다. 같은 보드의 기존 양의 STA는 유지 기준이며 새 ROM/RTL을 검증한 STA가 아니다. 순삭제할 기존 큐·ACK·독립 검사 제어는 없고, 대신 새 identity 저장·CRC·snapshot·완료 counter를 **추가하지 않는** 범위를 확정했다.

SNES ROM의 11B 여유도 보완했다. 현재 packer는 들어가는 가장 큰 비압축 prefix를 선택한다. **같은 5792B 실행 코드**를 다른 prefix로 다시 압축하고 별도 decoder로 정확한 원본 복원을 확인한 결과다.

| 비압축 prefix | 압축 stream | 5120B 물리 ROM 안의 여유 | 부팅 pass당 추가 해석 바이트 |
|---:|---:|---:|---:|
| 896B, 현재 선택 | 3861B | 11B | 0 |
| 768B | 3932B | 68B | 128B |
| 640B | 3999B | 129B | 256B |
| 512B | 4091B | 165B | 384B |
| 128B | 4433B | 207B | 768B |

따라서 **11B가 절대 확장 한계는 아니다.** 하지만 변경 코드가 이 압축률을 유지한다고 보장하지 않으며, 부팅의 복원·대조 두 pass가 더 많은 바이트를 해석한다. 새 실행 ROM 생성·실제 cold 시간·검사 실패 경로·메뉴 복귀와 전체 FIT를 통과하기 전에는 회수된 여유로 승인하지 않는다. 부팅 추가 비용을 warm 표시 간격과 섞어 숨기지 않는다. 이번에는 새 ROM이나 설치 ZIP을 만들지 않았다.

별도 DMA fence 패킷은 기존 identity checker를 활용할 수 있지만, 최소 E1 19B+E0 20B=39B/118.857µs wire에 header 검사·ACK·SPI driver 비용이 더해진다. VBlank 밖에서 head를 잡고 기다리면 952/911 마감을 깨뜨릴 수 있다. 무조건 fence를 넣는 안은 제외한다. 독립 mailbox도 identity/CDC 저장이 추가되므로 우선 후보가 아니다.

## 다음 작업 순서와 판정

1. **한 번의 제한 구현**으로 위 progress port·clear 우선순위·E0 identity 검사를 연결한다. 실제 map DMA 직전/중간/반환 뒤 STOP, E1 수락/ACK checker/snapshot과 같은 edge, 늦은 write, cold·부분 전송·wrap을 검사한다. 추가 패킷이나 완료 대기 루프는 넣지 않는다. 전체 ARM 링크와 실제 ROM packing/부팅 비용을 먼저 확인한다.
2. ARM이 이미 가진 descriptor를 보관하고 유용한 입력 처리를 하는 동안 **다음 패킷을 아직 발행하지 않은 진짜 빈 큐**가 생기는지를 함께 판정한다. 956의 현재 패딩 내부는 기회0회이므로 그대로 쓰지 않는다. 조회 횟수·고정 시간·세대 번호로 틈을 만들지 않는다. 준비된 후속 packet을 지연시키는 비용, 새 E0 거래, 64B STOP 확인, DMA 설정을 모두 포함한다. 실제 빈 큐 기회를 확보하지 못하면 progress 관측기만 제품에 넣지 않고 중단한다.
3. 비용 상한을 통과한 단일 결합 후보만 같은 map/OBJ·ROM 달력·두 시작 위상의53화면으로 재생한다. 678 수신 예산과 큰 묶음, 911 SEAL189/업로드214선, 951 공개≤246선, 9523 VBlank, 957 최종대기0회, 독립 출력·STOP·빈 캡처 회복·최종ACK·메뉴 경계를 모두 유지해야 한다. 밀집 평균과957 마지막ACK는 두 위상 모두 MMC666보다 빨라야 한다.
4. 시간도 통과한 후보에만 Quartus Lite 전체 FIT/STA를 한 번 연결한다. 기존 보드+새 ROM을 예전 STA로 승인하지 않는다. 전체 비용/시간 실패면 별도 진행 mailbox·고정 대기 미세조정을 반복하지 않고 공급·소비 경계를 재검토한다.

**현재 판정: 개선 가능한 잔여 DMA 구간은 확인했지만 두 위상 동시 개선은 미증명이다.** 진행 알림 자체가 약0.435ms를 절약한다거나 60fps에 도달한다고 주장하지 않는다. 실기 기준과 전달본은 MMC666 그대로다.

재현: `analyze_nes_progress679.py --traces <ASCII Temp> --board <nes-entry665-board01> --client <nes-entry665/client02> --arm <nes-handoff678/credit01/src> --out analysis/progress679-budget.json`. 원시 로그는 [678의 검증된 보관본](../analysis/handoff678-archive.json)에 있고, 새 분석은 그 로그·펌웨어·실제 보드 입력 hash를 확인한다. 이번에는 새 대용량 보관본이 필요하지 않다.
