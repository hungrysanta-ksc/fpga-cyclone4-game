# 최신 코어·MMC3 자원 측정 — NES-R1-RESOURCE-018

2026-10-05. 수정 계획 R1의 첫 실측을 완료했다.
**기본 코어+MMC3+RAM 12KiB는 fit하지만 전체 제품 여유는 아직 미확정이다.**
코어는014와 같은 바이트이며 별도의 자원 probe만 추가했다.017의 DMC 정확도 문제는 남아 있다.

| 구성 | 최종 LE /15,408 | 사용 LAB /963 | M9K /56 | 메모리 payload |
| --- | ---: | ---: | ---: | ---: |
| 과거 NROM 최소 probe |12,122|885|0|0|
| 최신014+표준 MMC3, RAM 외부 입력 |12,280|880|0|0|
| 같은 코어+CPU RAM2KiB+CIRAM2KiB+PRG RAM8KiB |12,281|881|12|98,304bits|

새 측정은 Quartus25.1std build1129, EP4CE15F17C8, seed1, master46.560846ns,148virtual pins다.
과거 보고서는 SC Lite Edition, 새 보고서는 SC Standard Edition이므로 완전히 같은 빌드 조건은 아니다.
map→fit→STA 두 구성 모두 exit0. map 추정12,317/12,325LE와 최종fit12,280/12,281LE를 구분한다.
CPU/CIRAM/PRG RAM은 각각2/2/8개 M9K,16,384/16,384/65,536payload bits로 실제 유지됐다.
LE 차이1은 배치·최적화 결과이며 RAM 제어기의 일반 비용이1LE라는 뜻이 아니다.

산술상 남은 자원은 LE3,127/M9K44/LAB82다. 설계 목표13,000LE까지는719LE다.
**LAB가91% 사용돼 추가3,127LE를 실제 배치·배선할 수 있다고 보장할 수 없다.**
PPU9,375cells 중 OAMEval7,916cells가 가장 크다. T651,142/APU1,382/MMC3140cells도 보존됐다.
부모 hierarchy는 자식을 포함하므로 PPU와 OAMEval을 다시 합산하지 않는다.
OAM의 register/선택회로 구조는 자원 개선 후보지만, 지금 M9K로 바꾸거나 동작을 단순화하지 않았다.
후속 최적화는 읽기/쓰기 포트·행 복사·sprite evaluation 타이밍 보존이 필요하다.

기존009 어댑터는 진단 ROM에 맞춰 PRG64KiB/CHR16KiB로 주소를 잘랐다.
자원 probe에서는 mp/mc 전체 주소와 mask를 보존해 뱅킹 로직이 과도하게 제거되는 것을 피했다.
표준mapper4 flags는 고정이다. 전 매퍼를 합성하거나 SMB3를 실행한 것이 아니다.
새 어댑터·RAM wrapper의 기능 동등성 시험은 아직 하지 않았다. 이전 runner와 upstream은 수정하지 않았다.

## 타이밍과 경고

| 모든 보고 corner의 최소 slack(ns) | 코어/MMC3 | RAM 포함 |
| --- | ---: | ---: |
| Setup |12.340|10.943|
| Hold |0.187|0.152|
| Recovery |41.646|42.820|
| Removal |1.416|1.220|
| Minimum pulse width |22.550|22.485|

각15개 corner/check record의 TNS0, illegal/unconstrained clock0을 확인했다.
input28/output115port는 setup/hold 미제약이고 clock pin 미지정 critical warning169085가 남는다.
이 probe는 board IO를 제외했으므로 **내부 clock timing 통과만 인정**한다. board STA/IO/CDC signoff가 아니다.
false-path나 clock 완화로 경고를 숨기지 않았다.

양쪽 warning code 집합: map10027/13046/13049/12241/13024/13410,
fit169085/114001/169177, STA114001. 원시 로그와 코드별 개수는 보존했다.
internal tristate→wire48건,7hierarchy connectivity,상수 출력bit5개,미지정 clock pin 등이 포함된다.
10027은 MMC3 모듈의 array index 폭 경고다. 이번 결과를 경고0으로 표시하지 않는다.
이전 Questa42warnings와 이번 Quartus warnings는 서로 다른 검사다.

## 메모리·미포함 비용과 다음 작업

[메모리 예산](resource-memory-budget.json)에 주소·크기·포트·초기화 한계를 기록했다.
새 RAM은 master clock 동기 read-old-data이며 reset clear/초기화/loader/다른 master port가 없다.
PRG/CHR ROM은 외부 입력이다. PSRAM/SRAM controller, board pins, turnaround/중재/ready,
packet encoder,FIFO/CDC,SNES frontend,입력·음향 물리 출력·menu/loader 비용은 미측정이다.
CPU12/PPU4master cycles는 nominal enable 간격이며 외부 RAM이 그 전부를 사용 가능한 응답 예산은 아니다.
정확한 request→consume window와 최악 응답은 실제 통합 관측으로 정해야 한다.

두4KiB packet slot은 추가8M9K,두8KiB slot+16KiB source cache는 추가32M9K라는 계산 예시를 남겼다.
채택안이나 실측이 아니며 R2 부하 분석용이다.004의 CHR 상주 cache는 SNES VRAM이므로 FPGA M9K에 자동 합산하지 않는다.

다음은 **R2 실제 fetch의 causal working set/burst/packet 요구량 산출**이다.
그 수치로 encoder/FIFO/cache 크기를 정하고 R1의 unknown을 채운 뒤 전체 예산을 다시 fit한다.
R1은 최소 구성 실측만 완료이며 보드·영상·외부 메모리 여유 판정까지 완료한 것은 아니다.
초과하면 OAMEval 메모리 구조·중복 로직·메모리 배치를 검토하고 crop·색 감소·감속으로 우회하지 않는다.

원시 소스/제약/log/report는 ignored analysis/local-resource-018/{logic-01,ram-01}에 보존했다.
원본 locale bytes는 그대로 hash하고, 검증기는 report의 ASCII 필드만 읽는다.
계획 검토와 이전 상태는 baseline-status에 보존했다. GBC152hashes/Quartus inputs/2,048boot bytes PASS,
upstream clean, compiler/simulator/FLOAT process0. 이번에는 Quartus만 실행했고 Questa/license smoke는 실행하지 않았다.
ROM 수정·실기 이미지 생성·공통 GBC/MCU 변경·Git commit은 없다.
