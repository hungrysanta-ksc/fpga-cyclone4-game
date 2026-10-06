# 실제 OAM DMA 중 인터럽트 — NES-P2-OAM-INTERRUPT-016

2026-10-05. 검증 후보016, 구현 후보NES-P2-RDY-014 유지. 코어 변경 없음.

CPU의 실제 $4014 write로 시작한 DMA 중 IRQ/NMI 보존과 복귀 검사를 완료했다.
3도착 위치(쓰기 후 CPU cycle1/256/512) × 4입력(없음/held IRQ/1-cycle NMI/동시) × 두 DMA 위상 = 24조건.
각 도착/입력 조합에서 실제 pause513/514cycles를 모두 확인했다. cycle512는 끝부분이며 마지막 cycle 자체는 아니다.

- 6,144 source bytes, 12,288 DMA read/write bus accesses, 6,144 OAM snapshot bytes가 원래 진단 패턴과 일치.
- 실제 DmaController가 CPU를 정지했다. 테스트벤치는 mapper_irq와 nmi 입력만 강제하며 pause_cpu/DMA 경로는 강제하지 않는다.
- IRQ12회/NMI12회; 동시6조건은 NMI→IRQ. 정지 중 짧은 NMI edge가 보존되고, DMA 종료 전에 interrupt stack/vector 접근이 없다.
- DMA 뒤 INC $10이 각 조건당 정확히1회 수행되고 누적값1..24가 맞는다. interrupt return PC=resume_pc+2, stack status=$20, saved/restored A=source page, RTI stack reads 및 handler counter도 검사한다.
- 데이터/주소/시간/pause/OAM/IRQ/NMI/vector/stack/handler/INC/잘린 trace 변조12종 모두 거부.
- 최종 Questa 오류0, 기존 경고42; CPU 주기 오류0, 미정 bus0. 약11.844ms 실제 RTL 실행.

ROM SHA256: `802b7e50f3de706827027d34f135216f61fb54107d7664b884ee2d5800b778d9`.
compiled source inventory17개가015와 완전히 동일하다. T65 SHA256:
`884a7c84128a9936690f1a73a14036b7742aed646a78209471a769071edfa692`.

초기 실행은 인터럽트/전송 동작은 맞았지만 일부 pair에서 한 pause 길이만 확인되어 최종 coverage 기준에 실패했다.
핸들러 실행 길이에 따른 다음 DMA 위상을 고려해5개 case의 BIT/NOP padding을 조정했다.
초기 verifier는 다음 case의 counter 초기화 쓰기까지 이전 case에 포함해 handler_increment 오류를 냈다.
$20 completion write를 검사 종료 경계로 사용하도록 고쳤고, 최초 소스/실패 결과도 baseline/에 보존했다.
최종 verifier로 초기 RTL을 재검사하면 phase_coverage만 실패한다. 실패 기록을 통과 횟수에 포함하지 않는다.

기준은 원래 ROM의 전송 패턴과 제한된 인터럽트 보존/스택/진행 계약이다.
이번 synthetic pin 입력은 Mesen runtime에 주입하지 않았다. 관측된 첫 vector는 pause 종료 후11cycles,
동시 IRQ vector는36cycles이며 관측값으로 기록할 뿐 독립 기준과 절대 interrupt latency 일치를 선언하지 않는다.
015의 actual Mesen DMA 비교 및014의 IRQ/Mapper4 영상 회귀는 보존된 과거 결과이고 이번 새 실행이 아니다.

보존 확인: 직전015 manifest132개 해시 일치 후 상태파일 복사. GBC152 source hashes/Quartus inputs/2048 boot bytes PASS.
upstream clean, 원래 진단 초안 보존. 무료 FLOAT 정상 종료: 관련 process/listener0. 라이선스/서버 기록은 증거 복사와 Git에서 제외.
원시 증거는 ignored `analysis/local-oam-interrupt-016/`에 있으며 summary/manifest/원래 진단 소스만 allowlist에 추가했다.

다음 우선 작업은 DMC 요청과 실제 OAM DMA가 겹칠 때 bus arbitration과 CPU 복귀 검사다.
rendering/APU DMC는 이번 진단에서 꺼져 있고 memory는 ideal이다. rendering-time OAM 쓰기, RMW $4014,
외부 stall, BRK hijack, 반복 NMI, 전체 CPU/PPU/APU, NES→SNES, SMB3, full fit/STA/실기 및 license hold는 미완료다.
