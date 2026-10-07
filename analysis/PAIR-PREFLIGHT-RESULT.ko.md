# NES-PAIR-PREFLIGHT-066 결과

오프라인 파일 쌍과 사전 점검의 범위는 달성했다.061 Standard fit를 별도 복사해 FPGA ASM/CPF를 완료했고,065 최종 ARM을 해시로 연결했다. **실제 SD 백업·메뉴 호환성·복원 실행과 정확한 PSRAM/외부 IO는 남아 있으므로 설치 가능한 후보는 아니다.** PR19 병합2026-10-07T04:37:36Z,master40374438ebdd82311e0882c0f59c9d451d8ef703 기준이다.

- 원본061과41개 파일 일치,23개 입력/요약 및129개 DB 파일 계보 고정. 새 map/fit/STA 없이 Standard25.1 ASM/CPF 성공. Lite Edition의 최초 DB 비호환 오류는 보존했다.
- 기존 C 압축기 EOF 추가FF1바이트를 전체 대조에서 검출했다.066 encoder의209943바이트 압축은510856바이트 RBF와 정확히 일치한다. 실제 C 프로그래머 host 모형에서도 모든 byte를 비교했고 EOF/65535·특수 token 경계66309바이트/압축531바이트를 확인했다. 수정 전510857바이트 복원과 assertion 실패를 보존했다.
-18개 시험 통과: 정확한 파일 쌍,EOF/긴 run/형식/상한,잘못된 firmware/FPGA,manifest·파일·백업 변조,경로 탈출,필수 복구 파일 부재,SD 내부 백업 금지,백업 중 변경,원본 부재/존재의 복원 계획. 모든 SD는 로컬 모형이다. 여섯 후보 파일을 적용한 모형에서 원본1개 복원/새5개 제거 계획을 확인했으며 도구가 SD를 수정하지 않았다.
- 패키지 준비066/실행 firmware065/FPGA061을 구별했다. 표식은 `NES VERIFY 065 80.nh1`, `NES VERIFY 065 96.nh1`. manifest digest와 각 파일 SHA를 고정하고 `installable=false`로 남겼다. 바이너리/ROM/DB/raw log는 공개 저장소에서 제외한다.
- GBC source152/original NES334와044 기준을 보존한다. 생산 RTL/ARM source는 바꾸지 않았고 새 Questa/ARM link는 없다.061 내부 STA2386LE/186LAB/44M9K/135핀/PLL1,최소0.131ns와063 디지털 세션은 이전의 검증 범위다. 전체 코어059959LAB/4여유·마지막8프레임은 별도다.

현재 준비도 **완료5/부분6/미완료1**을 유지한다. H11은 오프라인 쌍까지,H12는 모형 사전 점검·복원 계획까지 진전했다. 사용자 SD의 `fpga_base.bi3`·실제 `m3nu.bin` 분류·독립 백업/복원 관측이 없다. 다음은 그 조건과 정확한 PSRAM 부품/외부 min-max를 확보하여 설치/복원 경계를 검증하는 작업이다. 전체 SNES 소비자 완성을 제한 실기 진단의 선행 조건으로 추가하지 않는다.

[기계 판독 근거](pair-preflight-verification.json) · [계약·재현·실기 시험표](../docs/nes-pair-preflight-contract.md). 동결066과 이전 archive/finalizer는 다시 쓰지 않는다.
