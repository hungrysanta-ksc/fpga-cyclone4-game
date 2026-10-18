# NES247: 연속 범위 수신의 전송량·CPU 공동 비교

같은 71프레임에서 연속 map 범위 5가지를 비교했다. 모든 방식이 현재 map 및 최종 map DMA 목록을 재현하지만, **복사 부분만 바꾸는 후보는 전체 시간 여유를 입증하지 못했다.** 현재 실행 기준은 5818B maskbatch 수신기다. 이번에는 새 C/65816/RTL 수신기나 설치물을 만들지 않았다.

4KiB는 요구 조건이 아니다. 현재 6KiB 저장의 여유166B 역시 새 제한이 아니다. 이번 판단 근거는 코드 크기가 아니라 추가 전송량과 남는 실행 시간이다.

## 범위와 재현

SELECT `spantrade02`; `spantrade01`은 중간 PASS이며 보존한다. 02는 literal의 홀수 길이 검사를 명시하고, 일치하는 manifest를 제공해도 정렬 오류가 거부되는 두 검사를 추가했다. 기존 ordinary DATA 수와 실제 packet 수의 대응도 검증한다.

입력은 `maskbatch-test01`의 실제 요청/목표 map, `maskbatch-analysis01`의 실제 routine 시간, `mapjoint03`의 기존 ready1/4 전송 시나리오다. 직접 입력1249개 hash와 분석기 사본을 private run에 보존했다. 공개 결과는 [집계](../analysis/spantrade247-verification.json), [355행 비교표](../analysis/spantrade247-frames.csv), [분석기](../tools/analyze_nes_spantrade247.py)다.

workspace root에서 다음처럼 새 출력 디렉터리로 실행한다. 기존 결과를 덮어쓰지 않는다.

```powershell
python repository-nes-milestone/tools/analyze_nes_spantrade247.py --test probes/nes-wholepath247/maskbatch-test01 --timing probes/nes-wholepath247/maskbatch-analysis01 --model probes/nes-wholepath247/mapjoint03 --out probes/nes-wholepath247/spantrade-new
```

Python 재구성355건, map1,454,080B 전체 일치, 음성27건 PASS다. 양쪽 bank의 이전 표시 상태와 stale word 합집합을 유지하고 실제 필요한 word를 모두 받는지 확인했다. cold는2048word 전체 수신, warm은 초기화된 inactive bank에 적용한다. 이 Python 정책 검사는 실제 CPU의 오류·STOP 검증을 대체하지 않는다.

## 비교한 형식

|모델|범위 내부 gap|범위 최대 길이|packet 구성|
|---|---:|---:|---|
|literal_exact64|0B|64B|범위 하나당 DATA 하나|
|packed_exact64|0B|64B|여러 범위를240B payload 안에 묶음|
|packed_gap16_64|16B|64B|동일|
|packed_gap96_64|96B|64B|동일|
|packed_gap96_236|96B|236B|동일|

packed의 가상 형식은 mode3 한 바이트 뒤에 offset16LE, wordcount8, 연속 word 값이다. 최대118word면 header3+값236+mode1=240B다. frame 전체에서 정렬된 offset·짝수 길이·중복 없는 증가 순서와4096B 경계를 검사한다. 실제 새 wire version을 승인한 것은 아니다.

gap을 채우는 값도 현재 map의 정확한 값이어야 한다. 기존 stale word만 manifest에 적으면 실제 쓰기 집합과 불일치하므로, **확장된 실제 쓰기 집합의256B bitmap**을240+16 두 packet으로 보낸다. receipt·cold coverage를 생략하거나 checksum으로 대체하지 않았다.

최종 map DMA 목록은355건 모두 기존 목록과 같다. gap≤96 병합과 실제 필요한 양끝을 유지했기 때문이다. **전송 범위를 넓히는 것과 VBlank DMA를 줄이는 것은 별개**다. 기존952/955 multi-VBlank와955의4198>4192 charge 문제는 남는다.

## warm69 비교

record/packet/추가word는69프레임 합계, ready4는 최대 clock-byte 모델값이다. 현재 mask는1915record다.

|모델|record|map packet|추가 word|ready4 최대|새 decoder 시간이0이어도 예산 초과 frame|
|---|---:|---:|---:|---:|---:|
|literal_exact64|1941|1941|0|5129|7|
|packed_exact64|1941|80|0|4140|1|
|packed_gap16_64|1791|80|484|4191|1|
|packed_gap96_64|1761|543|47560|6000|31|
|packed_gap96_236|554|513|47560|5916|29|

exact packed는 전송 값을 늘리지 않지만 현재 mask보다 record가26개 많다. gap16은124record를 줄이는 대신968B를 더 보낸다. 준비·검증·service·실제 복사 비용을 측정하지 않고 빠르다고 판단할 수 없다.

gap96 두 방식은95,120B를 추가로 보낸다. 236B 범위는record를 크게 줄여도37프레임에서 **새 decoder 시간을0으로 두어도** 현재 mask 실행보다 wire+decoder 합이 느리다. 64B 방식은42프레임이다. 이는 비교 대상 decoder 시간에 한정한 결과다.

## 가장 빠듯한954프레임

새 decoder에 남는 시간은 다음 조건부 식으로 계산했다.

`1000/60 − ready4 × 8/2625 − 실제(mark + manifest + coverage) 시간`

기존 map mask routine만 새 decoder로 교체한다. 나머지 dispatch/copy, source, ARM, 전송 공백, 최종DMA/display 시간은 여전히 제외된다. CPU와 SPI가 이 식처럼 직렬인 조건의 여유이며, 모든 겹침 일정의 불가능 증명이나 실제FPS가 아니다.

954의 고정 routine은 map 외 수신 mark2.740944ms, map manifest0.913431ms, coverage1.048644ms, 합4.703019ms다.

|모델|954 ready4|새 decoder 허용 시간ms|
|---|---:|---:|
|현재 mask wire를 유지한 가정|4095|-0.516352|
|literal_exact64|5040|-3.396352|
|packed_exact64|4140|-0.653495|
|packed_gap16_64|4191|-0.808923|
|packed_gap96_64|5745|-5.544923|
|packed_gap96_236|5668|-5.310257|

현재 wire를 그대로 써도 map decoder 외 비용만으로 이 조건에서는 이미 초과한다. 따라서 연속 복사만 구현하고60fps 경로를 해결했다고 볼 수 없다. 반대로 이 결과는 exact packed가 다른 비용 개선과 함께 쓰일 가능성까지 기각하지 않는다.

ordinary DATA의 ready 그룹 수는 실제 packet 수에서 BEGIN/SEAL과 op7 pattern bulk를 제외한 값과71프레임 모두 일치했다. op7은 원래 모델의 별도 pattern control43B와ready40B/묶음에 포함돼 있다. 이를 ordinary DATA에 다시 넣으면 이중 계산이다. CSV에 두 packet 수를 분리해 남겼다.

## 기존 기능과 다른 점, 남은 자원 조건

기존 generic DATA에는 불변 mailbox의 연속 payload를 WRAM으로 옮기는 DMA가 있다. 하지만 현재247 map section은 그 경로를 거부하고 mask 전용 경로로 받는다. packed span을 실제로 지원하려면 record별 DMA 주소·길이 설정, word receipt, cold/manifest 검사, STOP/service와 packet ACK 수명을 함께 연결해야 한다. 기존 op7 pattern bulk는 별도 tile aperture/token 경로다. map span DMA가 이미 구현됐다는 뜻이 아니다.

기존 `nes_rangemark247.py`의8/16bit 범위 bitmap prototype도 보존한다. 이는 이전 validity 배치에서 만들었고 당시 코드 크기 gate에 걸려 실행하지 않았다. 새 발명으로 세거나 현재 maskbatch 수신기의 실행 근거로 사용할 수 없다. 다만4KiB 조건이 제거됐으므로 **현재166B non-map validity 배치와 실제 수신 경계에 맞춰 재평가할 근거**가 생겼다.

이번 모델은 PC의 현재 map을 읽으며 추가 ARM full-map 할당을 승인하지 않는다. 새 decoder의 본문 크기·scratch·실행 시간은 null로 남겼다. 현재6KiB 저장과240의54/56M9K를 합친56/56은 용량 산술이고 whole-board FIT/STA가 아니다. 큰236B DMA의 STOP 간격도 미검증이다.

## 다음 경계

새 span opcode 단독 구현은 보류한다. 다음 비교는 **map 외 received/valid bitmap 범위 갱신·coverage와 map manifest의 전송/검증 비용을 함께** 대상으로 한다. 기존 범위 prototype을 현재 배치로 옮길 때 중복 수신·section 경계·양 bank 초기화·부분 실패·STOP·최종 display ACK를 그대로 지켜야 한다. manifest 축소 후보도 동일한 쓰기 집합을 정확하게 검증하고 omitted/duplicate/overlap/cold 오류를 잡아야 한다.

같은71프레임에서 이 비용과 필요한 decoder 시간을 합쳐 실제 여유를 비교한 후에만 다음 형식을 고른다. service/검사를 없애는 최적화, opcode/seed/크기 미세 조정 반복은 하지 않는다. source449/rowshift·ROM/mapper 배분, 새 입력 ARM RUN/IRQ, host/NES firstfault·CDC/IO·display lease/retire도 계속 열린 조건이다. 생산227, functional240 미배치, rejected241/246, GBC164, save SRAM 및 이전 실패 자료는 보존한다.
