# NES068 초기 대기·외부 예산 결과

**초기 PSRAM 접근 대기 구현과 routed FPGA 지연 정량화라는 이번 범위를 달성했다.** 실제 외부 IO 승인과 전원/클록 고장 전체 안전은 부분 상태다. PR22 병합 `4d8868f2e324870137606058719fee36a6ff10db` 기준, 새 식별CF68이다.067 loader와 GBC/044·전체NES 코어·065ARM/066쌍은 보존했다.

- 첫 클록 에지 이후1600개의 완전한 간격을 기다린다.8MHz에서200µs,10MHz에서160µs. 준비 신호와 메모리 reset에 연결해 대기 중 핀 접근을 막는다.8/10MHz 두 정상 시험,대기 축소·약16.13MHz 범위 밖 두 실패,실제 boundary 대기 우회 실패를 확인했다. 이는 reset 해제 전에 전원이 안정됐다는 조건의 추가 대기이며 전압 센서가 아니다.
- 실제060 C bounded load/CHECK72312응답 비트가 새 물리 top과 일치했다. load256pin bytes,CHECK96KiB TB 준비 후256검증 bytes이며 전체SPI80/96KiB 회귀는 아니다.181µs까지 강제 입력의 준비·핀 접근을 차단하고,START 두 장벽과PLL 상실/복구를 확인했다.
- 읽기 활성 제어를 별도 레지스터로 바꿔 ACTIVE→HOLD 샘플 에지에서 CE/OE의 원인이 되는 신호를 유지한다. routed reader CE/OE source 검사와 전체 pin 모델 정상 4경우(각 쓰기/읽기 344064 bytes, 취소 36회), setup/hold 실패 대조 3개·126ns 범위 밖 대조가 통과했다. 실제 글리치 관측이나 아날로그 승인으로 확대하지 않는다.
- 새 Standard25.1 fit: **2400LE/195LAB/1479registers/44M9K/135physical/0virtual/PLL1**.3corner30내부 summary 통과.최소setup2.212ns,hold0.140ns,recovery5.190ns,removal1.350ns,pulse5.606ns.
- 실제 배치 DB 복사본에서PSRAM37dynamic output/16DQ input의3168경로를 추출했다. 분석 전114DB+QSF/QPF/SDC 해시 고정,원본fit 보존. IO delay0은FPGA 경로 노출용 분석 overlay이며 보드제약이 아니다.16조건별 외부 잔여 예산을 계산했고,주소→CE109.498ns·읽기byte 경계276.658ns·읽기샘플hold127.804ns다.
- PCB각leg20ns/추가5ns라는 미측정 가정의 최소예산62.313ns,각leg60ns 대조는−17.687ns. 양수 시나리오로 실제전압/PCB/아날로그 조건을 승인하지 않는다. PSRAM 외 SPI/SNES·비동기 lock→핀 경로도 아직 별도다.
- WRITE 중8MHz 정지와locked=HIGH를 유지하면CE가8µs 제한을 넘게 유지되는 반례를 재현했다. locked=LOW 뒤 클록 없이 핀 해제·이미지 무효화는 통과했다. 실제PLL감지시간이나 독립차단 근거가 없으므로 clock_halt_safe=false다.

로컬 `probes/nes-diag-safety-068/evidence-final/`에 850파일 manifest를 동결했다. 앞선 545파일 `evidence/`는 중간 결과로 보존했다. 최초fit의snapshot.sv 중복입력 실패,IO collector의자동QSF 버전기록/EOF 기대 실패와최종성공을 보존했다. 최종collector는정확한버전행과report/cache변경만허용한다. 새068 verifier와기존067 frozen verifier 모두통과했다. 최종 메모리·C 파형·대기 우회 FLOAT 작업이 정상 종료했고, 변경 없는 guard 단위 실행은 소스 해시를 대조해 재사용했다. 첫 read-setup 변형의 다른 assertion 실패와 이전 reader fit의 구조 검사 실패도 보존했다.

현재준비도5완료/6부분/1미완료를유지한다.H06은routed PSRAM FPGA지연까지진전했지만외부승인은남는다.새ARM/ASM쌍·전체SPI·실제SD/base/menu·백업/복원·실기관측은없다.installable=false.다음은명시된외부/클록정책을검토하며CF68 MCU거부·복구/ARM과최종전체SPI를연결하고동일소스쌍을만드는작업이다.

[기계판독요약](diag-safety-verification.json) · [계약·재현·예산식](../docs/nes-diag-safety-contract.md) · [현재인계](../cores/nes/HANDOFF.ko.md).
