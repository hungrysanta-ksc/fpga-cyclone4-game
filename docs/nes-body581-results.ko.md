# 581: 반복 본문·전송 순서 조사와 R1 마감

PR151의 [580 전체 비용표](nes-whole580-results.ko.md)에 이어, 계획한 한 차례의 제한 조사를 수행했다. **MMC577 제품은 유지**한다. 실제 선택 fixture·기존 패킷·CPU 기록을 연결했고 새 펌웨어·RTL·합성·전체 시뮬레이션·실기 전달본은 만들지 않았다.

결론은 **입력 map의 record 포장과 출력 map의 변경 단위를 함께 바꿀 예산이 필요하다**는 것이다. 변경 없는 record/패킷만 생략하는 좁은 재사용안은 밀집 구간에서 잠정12ms wire 예산을 만족시키지 못했다. 이 결과가 더 넓은 ABI 변경의 불가능성이나 새 FPS 개선을 뜻하지는 않는다.

## 자료 연결과 검증 범위

- `nes-delta231/test07`의53개 geometry/raw를 당시 sealed manifest와 대조했다. 기존 패킷 생성기의 실제 경계인 **244B 초과 또는 제어 표식 뒤 seal**을 재현했다. 단순256B 분할은 선택 경로가 아니다.
- 압축 record를 별도로 해석해 map/row/object/exception/raster/palette/raw를 canonical 입력과 대조했다. 두 위상106개 화면 모두 D1의 **패킷별 길이·개수·순서**가 기존 events와 일치했다. 당시 events에는 D1 payload가 없으므로 이 대조만으로 독립적인 FPGA payload 재검증을 주장하지 않는다.
- 두 위상 각각1689개 E1 PUSH를 실제65816 load/ACK와 연결했다. 원본 payload·window 해시, E1별 전송량, publish→load→ACK 순서를 확인했다. RPC의 `ceil` 반올림은 명시적으로 반영했다.
- map을 대상 뱅크 이력에 적용한 뒤 planner의 map hash와4096B 예상 이미지, palette/OAM 예상 이미지를 비교했다. 각 뱅크의 분석 이력은 이전 최종ACK 뒤에만 사용하고 한 화면 안의 중복 쓰기는 거절했다.
- section5 비교는 동일 patch layout의 **전송 주소 공간**에 한정한다. 이를 raw VRAM의 독립 검증이나 무료 persistent cache라고 부르지 않는다. palette/OAM까지 보관한 이력은 분석용이며 제품에 모두 존재하는 RAM이 아니다.

[분석기](../tools/analyze_nes_body581.py) · [프레임별 근거](../analysis/body581-verification.json) · [로컬 보관 해시](../analysis/body581-archive.json)

## 입력: map은 현재 포장으로 더 커진다

초기 두 화면 이후907–957의51개 평균이다. `변경 B`는 바로 전 입력의 동일 좌표와 다른 canonical 바이트다. `동일 record B`는 해당 record가 다루는 모든 값이 전 입력과 같은 경우의 현재 encoded 크기이며, 바로 삭제할 수 있다는 뜻은 아니다.

| 입력 section | canonical B | 전송 record B | 변경 B | 동일 record B |
|---|---:|---:|---:|---:|
| map | 1914.00 | 2571.88 | 263.67 | 1796.24 |
| row | 224.00 | 336.00 | 0.00 | 336.00 |
| object | 89.10 | 122.51 | 25.49 | 5.18 |
| exception | 0 | 0 | 0 | 0 |
| raster | 1792.00 | 46.00 | 446.18 | 34.00 |
| palette | 32.00 | 48.00 | 0.00 | 48.00 |
| raw | 512.00 | 39.76 | 5.20 | 22.12 |

제어 record48B를 포함한 입력 body는3212.16B, D1은3257.57B다. 전체 record의 반복 generation 필드는552.75B지만, record 생략 절감과 **중복 계산하면 안 된다**. packet 재배치·generation 공유에는 새 경계 검사 비용이 필요하며 과거512의 작은 필드 변경을 다시 성능 후보로 승격하지 않는다.

현재 map literal은 최대4개의15bit 값을8B 값+4B tag/generation으로 전달한다. 반복값을 압축해도 이 자료에서는1914B가2572B로 늘어난다. 반면 raster1792B는46B, raw512B는약40B까지 이미 줄어들었다. 따라서 raw/raster codec을 다시 미세 조정하는 우선순위는 낮다.

## 출력: 같은 바이트와 생략 가능한 패킷은 다르다

아래는 위상1의51개 평균이다. 비교 대상은 **마지막으로 최종ACK한 해당 뱅크**다. 출력 map은 이전 표시와 비교한 dirty를 두 뱅크의 stale에 누적하는 현재 정책으로 이미 일부 행을 생략한 뒤의 값이다.

| 출력 section | 현재 wire B | 전달한 확장 B | 대상 뱅크와 같은 B | 전체가 같은 패킷의 wire B |
|---|---:|---:|---:|---:|
| map | 1817.86 | 1640.16 | 1587.14 | 0.00 |
| palette | 344.00 | 512.00 | 512.00 | 344.00 |
| OAM | 107.55 | 544.00 | 523.65 | 42.65 |
| HDMA/raw | 594.51 | 1754.00 | 1747.43 | 386.88 |

map의 약96.8% 바이트가 같아도 모든 전송 패킷에 변화가 섞여 있어 패킷 단위 재사용 절감은0B다. 실제 다른2B 그룹은평균36.96개,8B 그룹28.96개인데64B 그룹25.63개를 보내고 있다. 밀집 구간은2B46.4개/8B35.6개/64B26개다.

이 수치는 더 작은 변경 단위를 검토할 근거다. **514/515의 생략 구간 재순회 방식은 재개하지 않는다.** 당시8B 부분 DMA는 수신·검사 비용과 polling을 늘려 종단 시간이 회귀했다. 새 후보는 기존64B dirty·stale/행 coverage·수신 해석·DMA 진행을 함께 대체하고 최종ACK 이력 검증을 저렴하게 유지할 비용을 먼저 제시해야 한다.

## 재사용만 가정한 전송 예산

실제 제품 변경이 아닌 낙관적 산술 비교다. D0/E0/E8 조회를 제외했고, retained record에 필요한 skip/address/base identity·새CRC/coverage·STOP 복구 비용을 아직 넣지 않았다. 두 출력 뱅크가 초기화된51개와 기존 밀집951–955를 구분했다.

| 시나리오, B/화면 | 51개 평균 위상1/2 | 밀집5개 위상1/2 |
|---|---:|---:|
| 현재 조회 제외 wire | 6597.35 /6597.98 | 7082.60 /7085.80 |
| 동일 입력 record 생략 가능량 | 2241.53 /2241.53 | 2103.60 /2103.60 |
| 동일 출력 패킷 생략 가능량 | 773.53 /773.53 | 767.80 /767.80 |
| 둘을 빼고 기존 packet 제어 유지 | 3582.29 /3582.92 | 4211.20 /4214.40 |
| 남은 record를 재포장해 D1/D2도 감소 가정 | 3484.59 /3485.22 | 4118.80 /4122.00 |
| 마지막 행의 wire 환산ms | 10.620 /10.622 | **12.553 /12.562** |

재포장은 평균15.14→6.25packet, 밀집16→7.6packet이라는 가정이다. 기존 literal/repeat가 암묵적으로 진행시키던 주소를 생략하면 현재 decoder 그대로는 실행할 수 없다. 따라서 표는 새 프로토콜의 구현/속도 증명이 아니며, 모든 가능한 전송의 수학적 하한도 아니다.

밀집 구간은 재포장까지 허용해도3937.5B보다181.3/184.5B 많다. **필수 조회·새 검증·gap 이전부터** 잠정12ms를 넘는다. 원래 계획대로 더 넓은 전송 단위·공동 실행 비용을 검토해야 하며, 단순 reuse만 구현해 놓고60fps를 기대하지 않는다. cold 뱅크 두 화면의 같은 가정도약25.77–25.79ms wire이며 초기 복구를 warm 예산으로 숨기지 않는다.

## 준비·수락·캡처를 구분한다

모든 화면에 source 시작, 첫/마지막 D1 완료, D3 완료, planner/prepare/출력/END 진입, 각 E1 publish·65816 load/ACK, SEAL 수락과 최종ACK를 연결했다. D3는 PREPARED 응답이며 마지막 D1 COMMIT보다 앞설 수 있다. END 함수 진입 역시 실제 END 완료를 뜻하지 않는다.

예를 들어 위상1의954는 source 시작 기준 마지막D1 21.319ms, planner23.037ms, prepare41.662ms, 출력42.136ms, SEAL 수락69.309ms, 최종ACK82.960ms다. 이는 **같은 기존 모델의 순서**이며 새 성능 변화가 아니다. 개별 패킷의 준비 완료는954 일부에만 계측돼 있으므로 다른 화면의 발행 시각을 준비 완료로 채우지 않았다.

`capture_ready`는 여러 화면에서 source 시작보다 이미 과거다. 이 모델은 고정된 다음 fixture를 공급하므로 그 차이로 실기 capture 누락 수·게임 진행 프레임·입력 지연을 계산할 수 없다. 실기 generation별 ROM 허가, 장면별 물리 ARM 사이클도 여전히 결측이다. 새 진단판을 만들더라도 계측 overhead와 공간부터 산정해야 한다.

자료 범위도 제한적이다.53개 모두 map957개/row224개/raster224개/palette32개/raw512B, exception0개이고 object는8–28개다. 따라서 정적·이동·모든 밀집 장면이나 raw0/1/3–7 patch·exception·palette64개를 대표한다고 말할 수 없다. 기존5–40/40–55초 실기 집계와 모델51개를 같은 모집단으로 합치지 않는다.

## R2에서 확인할 실제 교체 경계

| 후보 경계 | 함께 대체할 기존 경로 | 유지·추가 비용 | 현재 판정 |
|---|---|---|---|
| 입력 section/block + 선택적 base 재사용 | `nes_native_export203`의 map pack/count/record 생성, `nes_native_spi165`의 record별 width/position/tag/generation 포장, ARM `nes_native165_packet`의 record 해석·부분적인 `logical_record` 반복 | lease/query CDC·packetCRC/token·geometry 의미검사·META_END scratch 소유권·COMMIT 유지. base identity/누락·STOP 뒤cold, RAM read/write 포트와 비교 비용 추가 | R2 우선 비교, 구현 미선택 |
| 더 작은 map 변경 단위와 소비 이력 | `map_word185`의64B dirty, `map_stale/map_upload`, `map527`의64B 묶음,65816 행 수신·DMA 진행을 하나의 새 형식으로 교체 | 이전 최종ACK 뱅크/serial,coverage·손상 검사·부분전송 무효화·VBlank 유지. 같은 생략 바이트를 재순회하는514 방식 금지 | 입력 변경과 결합 예산 필요 |
| palette/OAM/HDMA 패킷 이력 | 매 프레임 전체 section 재발행·반복 전송 | 전역PPU 상태와 대상 뱅크 WRAM은 다름. section5 layout/HDMA table 활성·이력 저장·검사·STOP 복구 필요 | 단독으로12ms/60Hz 미통과 |

선택 ELF의 함수 크기는 `nes_native165_packet`1434B,`logical_record`1112B,`packet_wire`600B,`nes_sink212_seal`1132B,`map_word185`92B,`map527`216B,`nes_resident211_prepare`104B다. 이는 **포함된 함수 전체 크기**다. 인라인 record 해석·공유 검사·다른 section을 보존해야 하므로 삭제 절감으로 합산하지 않는다. 검증된 순삭제는현재0B다.

Flash84B/LE148/M9K5 여유를 유지한다. 전체 source snapshot7533B를 추가 보관하면60264bit로 남은5M9K의46080bit보다 크다(이상적 packing조차7블록 이상). map+row 최대2336B만 별도 보관해도 이상적3블록이 필요하고 포트/제어/기존 저장 대체가 별도다. ARM의 기존 배열은 BEGIN에서 reset되며 `required`와raw도 수명을 공유한다. reset을 없애는 것만으로 안전한 base 재사용이 되지 않는다.

## 단계 상태와 다음 한 단계

**R1은 결측을 명시한 상태로 마감한다.** 기존자료 분석과 이번 제한 조사를 반복하지 않는다. 물리 capture/게임진행/입력지연/밀집 ROM 달력은 미해결로 계속 표시하며60Hz 승인에 사용하지 않는다.

다음은 R2의 **입력 section/block와 map 소비 형식을 묶은 ABI·RAM 소유권·실제 삭제 예산 비교**다. cold/warm/dense 바이트에 header·skip·base·CRC·필수응답을 모두 포함하고, source 준비·ARM 변경량 산정·65816 검사/복원·DMA·VBlank의 비중첩 시간을 산정한다. 순삭제·포트·Flash/LE/RAM 예산이 성립하지 않으면 그 후보를 구현하지 않는다. 결측 때문에 판정할 수 없는 성능은 조건부로 남긴다.

독립 검사·STOP·최종ACK·VBlank·메뉴복귀·GBC/save는 변경하지 않았다. 이번 검사로 새 물리 보호 시험이나 FPS 성과를 주장하지 않는다. README도 제품 상태가 바뀌지 않아 유지했다.

## 재현과 보관

```powershell
python tools/analyze_nes_body581.py --data ../probes/nes-delta231/test07 --capture ../probes/nes-output489/audit01 --traces <원본-Temp> --arm ../probes/nes-gate577/ARM577/src --out <새-폴더>
```

선택 결과는 `probes/nes-body581/analysis05`다.01은 분석기에서 float ARM 시각과 정수 RPC publish를 반올림 없이 비교한 실패다.02는 경계를 교정해 통과했고03–05는 이력 ACK 시각·재포장 산술·ELF 경계 근거를 추가했다. 원본 일정/제품 결함이 아니다.

입력·예상 데이터·원본 두 위상 기록·분석 로그278개는 `probes/nes-body581/evidence01.zip`에 저장하고 다시 읽어 해시를 대조했다. 공개 Git에는 raw payload 대신 카운터·SHA·단계 상태를 기록한다. 게임ROM·펌웨어·라이선스는 이 보관본에 없으며 전체 공동 실행의 clean-clone 재현을 완료했다는 뜻은 아니다.
