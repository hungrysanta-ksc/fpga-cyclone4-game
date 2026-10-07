# NES071 CF68·069 오프라인 파일 쌍 결과

## 목표와 결과

PR25 병합 `1245e0dff52c38c5713105138dcf7f9572c6931e`에서 **068 fit03 ASM/CPF·정확한 C 복원·고정069 ARM 쌍이라는 이번 범위의 목표를 달성했다**. 생산 RTL/ARM을 변경하거나 map/fit/STA/Questa를 새로 실행하지 않았다. 실제 SD 설치·물리 실행은 아직 없다.

| 검사 | 결과 |
| --- | --- |
| 원본 계보 | 068 동결850파일,DB114·입력21·report10 일치; 추가 incremental17은 별도 기록·조립 제외 |
| Standard ASM/CPF | 두 단계0오류/0경고;RBF510856바이트 |
| 정확한 압축 |212523바이트;Python/실제069 C 모든510856바이트 일치 |
| C 경계·오류 |66309바이트 경계 일치;13오류 대조 통과 |
| 사전 점검 |23검사 통과;구형CF61/065·ID/로그 혼입·EOF 추가바이트 거부 |
| 고정 ARM |069 최종179336바이트 그대로;timestamp header 정규화/새 ARM 빌드 없음 |
| 동결 감사 |374파일 manifest 및 원본068/069·쌍·실행 snapshot 대조 통과 |

RBF SHA256 `45dcb3f3908b427b66f3fe52f14e56c80efae58d422af95b322580bd57f0a572`, ARM SHA256 `268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499`, 쌍 manifest SHA256 `5d5623c53a2a935c95d8648f65a30def715ff71531f90c51f23d46c39a0dfd02`. [구성·재현·물리 시험표](../docs/nes-cf68-pair-contract.md)와 [기계 요약](cf68-pair-verification.json)을 사용한다.

최초 DB 집합 검사는 기존 inventory 범위가db114이고 원본에 incremental17도 있어 실패했다. 기록된114개는 동일했으며 독립 고정되지 않은incremental을 제외한 새 폴더로 조립했다. 최초 C 입력 수집은 공개 helper와 materialized069의 LF/오류 enum 차이를 검출했다. 정확한069 runtime/header와 실제 포함 programmer 본문으로 최종 시험을 실행했다. 두 실패의 터미널 전사와 최초/최종 C 로그를 보존한다.

## 재사용과 미완료

070의 전체180224바이트/901152프레임/50464224응답 비트·FINISH/STOP,068의195LAB/44M9K/135핀/PLL1/내부 최소hold0.140ns와069의하위95/상위/오류/ARM 호출은 같은 소스 경계에서 재사용한다. 전체 NES059의959LAB/4여유/마지막8프레임은 별도 근거다. GBC152/기존NES334 및 실제044 화면순환/GBC 기준을 보존한다.

**전체 실기 진입 목표는 미달성이다.** 오프라인 쌍은 있어도 actual SD/base/menu 분류·독립 백업/복원·물리 시간/LED/화면/재진입/GBC는 아직 없다. 전압/PCB/비동기 SPI/SNES/전원 안정과 lockedHIGH 쓰기 클록 정지 반례도 남는다. 모든 SD 시험은 로컬 모형이고 C DONE은 모형이다. 준비도5완료/6부분/1미완료, installable/hardware/clock_halt_safe=false를 유지한다.

다음은 실제 SD 원본 호환성·backup/readback/restore 조건을 수집하고, 필요하면 기존 외부 실기의 SD→TXT 흐름으로 읽기 전용 진단을 준비한다. 이 조건과 외부 한계를 검토한 뒤 제한 실기 패키지를 전달한다. 표식06980/96·`fpga_nl8.bi3`·CF68/protocol59·로그069를 유지하고 START/불확실한 재시도·오류 뒤 SD/base 접근을 허용하지 않는다. 374파일 동결을 덮어쓰거나 finalizer를 재실행하지 않는다.
